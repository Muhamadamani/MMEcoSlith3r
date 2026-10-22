"""RK2 (trapezoidal) streamline integrator — fully vectorised hot path.

Uses pure-numpy bilinear interpolation; avoids any scipy per-point overhead.
"""

import numpy as np


def _make_field(U: np.ndarray, V: np.ndarray, x0: float, y0: float,
                dx: float, dy: float):
    """Return a fast field-evaluation closure."""
    Ny, Nx = U.shape
    inv_dx, inv_dy = 1.0 / dx, 1.0 / dy

    def field(pt):
        fx = (pt[0] - x0) * inv_dx
        fy = (pt[1] - y0) * inv_dy
        if fx < 0.0 or fx > Nx - 1 or fy < 0.0 or fy > Ny - 1:
            return None
        jx = int(fx); tx = fx - jx
        iy = int(fy); ty = fy - iy
        jx = min(jx, Nx - 2); iy = min(iy, Ny - 2)
        w00 = (1.0 - ty) * (1.0 - tx)
        w10 = ty          * (1.0 - tx)
        w01 = (1.0 - ty) * tx
        w11 = ty          * tx
        u = U[iy, jx]*w00 + U[iy+1, jx]*w10 + U[iy, jx+1]*w01 + U[iy+1, jx+1]*w11
        v = V[iy, jx]*w00 + V[iy+1, jx]*w10 + V[iy, jx+1]*w01 + V[iy+1, jx+1]*w11
        return u, v

    return field


def mmstream2(
    X: np.ndarray,
    Y: np.ndarray,
    U: np.ndarray,
    V: np.ndarray,
    seed: np.ndarray,
    step: float,
    n_max: int,
    *,
    stag_tol: float = 1e-6,
    closed_tol: float | None = None,
) -> tuple[np.ndarray, bool]:
    """Integrate a streamline with RK2 (trapezoidal corrector).

    Returns
    -------
    xy       : (N, 2) array of traced points.
    is_closed: True if the line looped back to the seed.
    """
    if closed_tol is None:
        closed_tol = step * 2.0

    x0, x1 = float(X[0, 0]),  float(X[0, -1])
    y0, y1 = float(Y[0,  0]), float(Y[-1, 0])
    dx = (x1 - x0) / (X.shape[1] - 1)
    dy = (y1 - y0) / (Y.shape[0] - 1)

    field = _make_field(U, V, x0, y0, dx, dy)

    # Pre-allocate output buffer for speed
    pts = np.empty((n_max + 1, 2), dtype=float)
    pts[0] = seed
    n_pts = 1
    curr = np.asarray(seed, dtype=float).copy()
    is_closed = False
    sx, sy = curr[0], curr[1]   # seed coords for closure check

    for _ in range(n_max):
        r1 = field(curr)
        if r1 is None:
            break
        u1, v1 = r1
        mag1 = (u1*u1 + v1*v1) ** 0.5
        if mag1 < stag_tol:
            break
        inv1 = step / mag1
        p2x = curr[0] + u1 * inv1
        p2y = curr[1] + v1 * inv1

        r2 = field((p2x, p2y))
        if r2 is None:
            break
        u2, v2 = r2
        mag2 = (u2*u2 + v2*v2) ** 0.5
        if mag2 < stag_tol:
            break
        inv2 = step / mag2

        nx = curr[0] + 0.5 * (u1*inv1 + u2*inv2)
        ny = curr[1] + 0.5 * (v1*inv1 + v2*inv2)

        if nx < x0 or nx > x1 or ny < y0 or ny > y1:
            break

        curr[0] = nx; curr[1] = ny
        pts[n_pts, 0] = nx; pts[n_pts, 1] = ny
        n_pts += 1

        # Closure check (skip early steps)
        if n_pts > 6:
            ddx = nx - sx; ddy = ny - sy
            if (ddx*ddx + ddy*ddy) < closed_tol * closed_tol:
                is_closed = True
                break

    return pts[:n_pts], is_closed
