"""Trim a new streamline by proximity to existing points.

Accepts an optional pre-built KDTree to avoid rebuilding it each call.
"""

import numpy as np
from scipy.spatial import KDTree


def trim_streamline(
    xy: np.ndarray,
    existing: np.ndarray,
    min_dist: float,
    tree: KDTree | None = None,
) -> np.ndarray:
    """Remove points of *xy* within *min_dist* of any point in *existing*.

    Returns the first contiguous valid run (matching MATLAB behaviour).
    """
    if len(existing) == 0 or len(xy) == 0:
        return xy

    if tree is None:
        tree = KDTree(existing)

    dists, _ = tree.query(xy, k=1)
    valid = dists >= min_dist

    # MATLAB returns xy[0:cut_off+1] — starts from point 0 always, ends
    # at (and including) the first invalid point.  If all points are valid,
    # return the full array.
    for i, v in enumerate(valid):
        if not v:
            return xy[:i + 1]
    return xy
