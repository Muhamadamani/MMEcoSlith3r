"""Simplify paths with Douglas-Peucker + linear interpolation at large jumps.

Port of SimplifyPaths.m.  Also filters out short courses.
"""

import numpy as np

from .dpsimplify import dpsimplify


def _even_linear(p: np.ndarray, max_dist: float) -> np.ndarray:
    """Insert intermediate points where consecutive distance > max_dist."""
    out = [p[0]]
    for i in range(1, len(p)):
        d = np.linalg.norm(p[i, :2] - p[i - 1, :2])
        if d > max_dist:
            n_insert = int(np.ceil(d / max_dist))
            for k in range(1, n_insert):
                t = k / n_insert
                out.append(p[i - 1] * (1 - t) + p[i] * t)
        out.append(p[i])
    return np.array(out)


def simplify_paths(
    layer: list[dict],
    prt_opt: dict,
) -> list[dict]:
    """Apply DP simplification and interpolation to all courses.

    Parameters
    ----------
    layer   : list of layer dicts (from even_streamlines / cut_shape).
    prt_opt : dict with keys 'tol', 'widthInterp', 'distInterp',
              'boolFilter' (1/0), 'threshDist',
              'x_printstart', 'y_printstart'.

    Returns
    -------
    Simplified layer list.
    """
    tol         = prt_opt.get('tol', 0.05)
    w_interp    = prt_opt.get('widthInterp', 0.25)
    d_interp    = prt_opt.get('distInterp', 5.0)
    filter_bool = bool(prt_opt.get('boolFilter', 1))
    thresh_dist = prt_opt.get('threshDist', 0.9)

    import time
    out = []
    for li, lyr in enumerate(layer):
        n_total = len(lyr['courses'])
        print(f'  Simplifying layer {li+1}: {n_total} courses …', flush=True)
        t0 = time.time()
        new_courses = []
        for c in lyr['courses']:
            P = c['POINT']  # (N, 4): x y z w
            if len(P) < 2:
                continue

            # Length filter
            total_len = np.sum(np.linalg.norm(np.diff(P[:, :2], axis=0), axis=1))
            if filter_bool and total_len < thresh_dist:
                continue

            # Douglas-Peucker on (x, y, width) — matches MATLAB's pol=[x y width]
            # dpsimplify returns ix: boolean mask into P rows
            _, ix = dpsimplify(P[:, [0, 1, 3]], tol)
            P_dp = P[ix]
            if len(P_dp) < 2:
                continue
            P_new = P_dp

            # Interpolate where width or distance jumps are large
            out_pts = [P_new[0]]
            for i in range(1, len(P_new)):
                dw = abs(P_new[i, 3] - out_pts[-1][3])
                dd = np.linalg.norm(P_new[i, :2] - out_pts[-1][:2])
                if dw > w_interp or dd > d_interp:
                    n_ins = max(int(np.ceil(dd / (d_interp / 2))), 2)
                    for k in range(1, n_ins):
                        t = k / n_ins
                        out_pts.append(out_pts[-1] * (1 - t) + P_new[i] * t)
                out_pts.append(P_new[i])

            P_final = np.array(out_pts)

            # NOTE: print-origin translation is done later by move_print()
            # in the pipeline (matches MATLAB: movePrint called from GCodeFormat,
            # not from SimplifyPaths).

            new_courses.append({'POINT': P_final})
        print(f'    → {len(new_courses)} courses kept  ({time.time()-t0:.1f}s)', flush=True)
        out.append({'courses': new_courses})

    return out
