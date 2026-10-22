"""Per-point inter-line width estimation using KDTree (port of GetDistance.m).

Two successive nearest-neighbour queries against the current point cloud give
estimates for each side; the average, clamped to [lowerbound, upperbound],
becomes the local width.
"""

import numpy as np
from scipy.spatial import KDTree


def get_distance(
    xy: np.ndarray,
    all_pts: np.ndarray,
    lower: float,
    upper: float,
) -> np.ndarray:
    """Estimate per-point inter-line widths.

    Parameters
    ----------
    xy       : (N, 2) points of the *current* streamline.
    all_pts  : (M, 2) all previously accepted streamline points (the KD-tree
               is built from these; *xy* should NOT be in this array yet).
    lower    : minimum width (mm).
    upper    : maximum width (mm).

    Returns
    -------
    widths : (N,) array of local widths, clipped to [lower, upper].
    """
    if len(all_pts) < 2:
        return np.full(len(xy), (lower + upper) / 2.0)

    tree = KDTree(all_pts)
    # First nearest neighbour (skip self if xy ∈ all_pts)
    d1, _ = tree.query(xy, k=1)

    # Second nearest neighbour gives the other side
    k2 = min(2, len(all_pts))
    d_all, _ = tree.query(xy, k=k2)
    d2 = d_all[:, -1] if k2 > 1 else d1

    widths = 0.5 * (d1 + d2)
    return np.clip(widths, lower, upper)
