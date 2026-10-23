"""Even-spacing streamline generation via Delaunay circumcenter seeding.

Port of evenStreamlines.m with:
  - Live matplotlib visualization (plot=True)
  - One KDTree built once per iteration, reused for gap/trim/width
  - Tiny Delaunay cloud (3 pts per streamline) → fast triangulation
  - Console progress every 10 streamlines
"""

from __future__ import annotations

import time

import numpy as np
from scipy.spatial import Delaunay, KDTree

from init_frame import init_frame
from mmstream2 import mmstream2
from trim_streamline import trim_streamline


def even_streamlines(
    ANGLES: list[dict],
    prt_opt: dict,
    integ_step: float = 0.5,
    n_max: int = 200,
    *,
    plot: bool = False,
    ax=None,
    line_callback=None,
) -> list[dict]:
    """Generate evenly-spaced streamlines for each layer.

    Parameters
    ----------
    ANGLES        : list of dicts with keys 'X', 'Y', 'U', 'V'.
    prt_opt       : dict with 'upperbound', 'lowerbound', 'nLayers'.
    integ_step    : RK2 step (mm). Use ≤ lowerbound/2 for smooth lines.
    n_max         : max integration steps per half-streamline.
    plot          : open a live matplotlib window during generation.
    ax            : optional pre-existing matplotlib Axes (standalone CLI use).
                    Do NOT pass from a GUI background thread — use line_callback.
    line_callback : callable(xy, seed, n_added, lnum) called after each accepted
                    streamline.  Thread-safe — use self.after(0, ...) in a GUI.
    """
    upper    = float(prt_opt['upperbound'])
    lower    = float(prt_opt['lowerbound'])
    n_layers = int(prt_opt.get('nLayers', len(ANGLES)))

    layer = []
    t_start = time.time()

    for lnum in range(min(n_layers, len(ANGLES))):
        ang = ANGLES[lnum]
        X, Y, U, V = ang['X'], ang['Y'], ang['U'], ang['V']

        x_min, x_max = float(X.min()), float(X.max())
        y_min, y_max = float(Y.min()), float(Y.max())

        # ── live plot setup ───────────────────────────────────────────────
        fig = None
        _own_ax = None  # axes we created ourselves (vs injected)
        if ax is not None:
            # GUI mode: use the provided axes, clear it for this layer
            _own_ax = ax
            _own_ax.cla()
            _own_ax.set_xlim(x_min, x_max)
            _own_ax.set_ylim(y_min, y_max)
            _own_ax.set_aspect('equal')
            _own_ax.set_facecolor('#f5f5f5')
            _own_ax.set_title(f'Layer {lnum + 1} — generating…')
            try:
                _own_ax.figure.canvas.draw_idle()
                _own_ax.figure.canvas.flush_events()
            except Exception:
                pass
        elif plot:
            import matplotlib.pyplot as plt
            plt.ion()
            fig, _own_ax = plt.subplots(figsize=(10, 4))
            _own_ax.set_xlim(x_min, x_max); _own_ax.set_ylim(y_min, y_max)
            _own_ax.set_aspect('equal'); _own_ax.set_facecolor('#f5f5f5')
            _own_ax.set_title(f'Layer {lnum + 1} — generating…')
            plt.tight_layout(); plt.show(); plt.pause(0.001)

        # ── Delaunay cloud: frame points + 3 pts per accepted streamline ──
        frame_pts = init_frame(x_min, x_max, y_min, y_max, upper)
        seed_pts  = frame_pts.copy()

        # Separate full accumulator for KDTree (trim / width / gap)
        all_pts = np.empty((0, 2), dtype=float)

        courses: list[dict] = []
        n_added = 0
        tree: KDTree | None = None

        print(
            f'  Layer {lnum + 1}: [{x_min:.0f},{x_max:.0f}]×[{y_min:.0f},{y_max:.0f}]  '
            f'spacing {lower:.2f}–{upper:.2f} mm  step {integ_step:.2f} mm',
            flush=True,
        )

        max_iters = 50_000
        for _iter in range(max_iters):

            # ── Delaunay on compact cloud ─────────────────────────────────
            if len(seed_pts) < 3:
                break
            try:
                tri = Delaunay(seed_pts)
            except Exception:
                break

            # ── vectorised circumcenters ──────────────────────────────────
            s = tri.simplices
            A = seed_pts[s[:, 0]]; B = seed_pts[s[:, 1]]; C = seed_pts[s[:, 2]]
            D = 2.0 * (A[:,0]*(B[:,1]-C[:,1])
                       + B[:,0]*(C[:,1]-A[:,1])
                       + C[:,0]*(A[:,1]-B[:,1]))
            with np.errstate(divide='ignore', invalid='ignore'):
                a2 = A[:,0]**2 + A[:,1]**2
                b2 = B[:,0]**2 + B[:,1]**2
                c2 = C[:,0]**2 + C[:,1]**2
                ux = np.where(D!=0,
                    (a2*(B[:,1]-C[:,1])+b2*(C[:,1]-A[:,1])+c2*(A[:,1]-B[:,1]))/D, np.nan)
                uy = np.where(D!=0,
                    (a2*(C[:,0]-B[:,0])+b2*(A[:,0]-C[:,0])+c2*(B[:,0]-A[:,0]))/D, np.nan)

            cands = np.column_stack([ux, uy])
            ok = (np.isfinite(cands).all(1)
                  & (cands[:,0] >= x_min) & (cands[:,0] <= x_max)
                  & (cands[:,1] >= y_min) & (cands[:,1] <= y_max))
            cands = cands[ok]
            if len(cands) == 0:
                break

            # ── gap finding ───────────────────────────────────────────────
            if len(all_pts) > 0:
                # Build ONE tree per iteration, reused below
                tree = KDTree(all_pts)
                gaps, _ = tree.query(cands, k=1)
                best = int(np.argmax(gaps))
                if gaps[best] < lower:
                    break
                seed = cands[best]
            else:
                tree = None
                seed = cands[0]

            # ── RK2 integration ───────────────────────────────────────────
            xy_fwd, _ = mmstream2(X, Y,  U,  V, seed, integ_step, n_max)
            xy_bwd, _ = mmstream2(X, Y, -U, -V, seed, integ_step, n_max)

            # ── trim each half separately before concatenating (MATLAB) ───
            # Each half starts at the seed (always valid); trim cuts off the
            # far end where it gets too close to existing streamlines.
            if tree is not None:
                xy_fwd = trim_streamline(xy_fwd, all_pts, lower, tree=tree)
                xy_bwd = trim_streamline(xy_bwd, all_pts, lower, tree=tree)

            # Concatenate: reversed backward + forward (drop duplicate seed)
            xy = (np.vstack([xy_bwd[::-1], xy_fwd[1:]]) if len(xy_bwd) > 1
                  else xy_fwd)

            if len(xy) < 2:
                seed_pts = np.vstack([seed_pts, seed[None]])
                continue

            # ── width (reuse same tree) ───────────────────────────────────
            if tree is not None:
                d1, _ = tree.query(xy, k=1)
                k2 = min(2, len(all_pts))
                d2 = tree.query(xy, k=k2)[0][:, -1] if k2 > 1 else d1
                widths = np.clip(0.5 * (d1 + d2), lower, upper)
            else:
                widths = np.full(len(xy), (lower + upper) * 0.5)

            # ── store course ──────────────────────────────────────────────
            z = np.ones((len(xy), 1))
            w = widths[:, None]
            courses.append({'POINT': np.hstack([xy, z, w])})

            # ── accumulate full pts for future KDTree ─────────────────────
            all_pts = np.vstack([all_pts, xy]) if len(all_pts) else xy

            # ── add only 3 representative pts to Delaunay cloud ──────────
            mid = xy[len(xy) // 2]
            seed_pts = np.vstack([seed_pts, xy[0][None], mid[None], xy[-1][None]])

            n_added += 1
            freq = 5 if n_added < 50 else 20
            if n_added % freq == 0:
                elapsed = time.time() - t_start
                rate = elapsed / n_added
                print(f'    {n_added:5d} streamlines  {elapsed:.1f}s'
                      f'  (~{rate*1000:.0f} ms/line)', flush=True)

            # ── live plot (standalone CLI only) ───────────────────────────
            if _own_ax is not None:
                _own_ax.plot(xy[:, 0], xy[:, 1], '-', lw=0.6, alpha=0.8,
                             color='steelblue')
                _own_ax.plot(seed[0], seed[1], '.r', ms=2)
                _own_ax.set_title(f'Layer {lnum + 1}  —  {n_added} streamlines')
                try:
                    _own_ax.figure.canvas.draw_idle()
                    _own_ax.figure.canvas.flush_events()
                except Exception:
                    pass

            # ── GUI callback (thread-safe — caller uses self.after) ───────
            if line_callback is not None:
                try:
                    line_callback(xy, seed, n_added, lnum)
                except Exception:
                    pass

        elapsed = time.time() - t_start
        print(f'  → Layer {lnum + 1}: {n_added} streamlines  {elapsed:.1f}s total',
              flush=True)

        if _own_ax is not None:
            _own_ax.set_title(f'Layer {lnum + 1} — done ({n_added} streamlines)')
            if fig is not None:
                import matplotlib.pyplot as plt
                plt.show(block=False)
                plt.pause(0.5)
            else:
                try:
                    _own_ax.figure.canvas.draw_idle()
                    _own_ax.figure.canvas.flush_events()
                except Exception:
                    pass

        layer.append({'courses': courses})

    return layer
