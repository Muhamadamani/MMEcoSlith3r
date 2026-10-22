"""Smooth polygonal boundary loops with a cubic spline (port of smoothBoundary.m)."""

import numpy as np
from scipy.interpolate import CubicSpline


def smooth_boundary(loops: list[np.ndarray], n_pts_per_seg: int = 8) -> list[np.ndarray]:
    """Fit a smooth cubic spline to each closed polygonal loop.

    Parameters
    ----------
    loops          : list of (K, 2) vertex arrays.
    n_pts_per_seg  : spline samples per original edge.

    Returns
    -------
    List of smooth (M, 2) arrays.
    """
    smooth = []
    for P in loops:
        # Enforce closure
        if not np.allclose(P[0], P[-1]):
            P = np.vstack([P, P[0]])

        t = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
        n_out = n_pts_per_seg * (len(t) - 1) + 1
        tq = np.linspace(0.0, t[-1], n_out)

        # Use not-a-knot BCs to match MATLAB's built-in spline()
        cs_x = CubicSpline(t, P[:, 0], bc_type='not-a-knot')
        cs_y = CubicSpline(t, P[:, 1], bc_type='not-a-knot')
        smooth.append(np.column_stack([cs_x(tq), cs_y(tq)]))

    return smooth
