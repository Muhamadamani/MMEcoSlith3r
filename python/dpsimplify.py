"""Douglas-Peucker polyline simplification (port of dpsimplify.m).

Handles NaN row-separators for multi-segment polylines, works in N-D.
"""

import numpy as np


def dpsimplify(p: np.ndarray, tol: float) -> tuple[np.ndarray, np.ndarray]:
    """Simplify a polyline using the Douglas-Peucker algorithm.

    Parameters
    ----------
    p   : (N, D) array, may contain NaN rows as sub-polyline separators.
    tol : maximum perpendicular distance threshold (same units as p).

    Returns
    -------
    ps  : simplified points, same NaN structure preserved.
    ix  : boolean index array into p rows that were kept.
    """
    if len(p) == 0:
        return p.copy(), np.ones(0, dtype=bool)

    nan_rows = np.any(np.isnan(p), axis=1)
    sep = np.where(nan_rows)[0]

    if sep.size == 0:
        ps, ix = _dp_single(p, tol)
        return ps, ix

    # Split at NaN separators, simplify each segment, rejoin
    starts = np.concatenate([[0], sep + 1])
    ends   = np.concatenate([sep, [len(p)]])
    ps_parts, ix_parts = [], np.zeros(len(p), dtype=bool)

    for s, e in zip(starts, ends):
        seg = p[s:e]
        if len(seg) == 0:
            continue
        seg_ps, seg_ix = _dp_single(seg, tol)
        ix_parts[s:e] = seg_ix
        ps_parts.append(seg_ps)
        ps_parts.append(np.full((1, p.shape[1]), np.nan))  # re-insert separator

    if ps_parts and np.all(np.isnan(ps_parts[-1])):
        ps_parts.pop()

    return (np.vstack(ps_parts) if ps_parts else np.empty((0, p.shape[1]))), ix_parts


def _dp_single(p: np.ndarray, tol: float) -> tuple[np.ndarray, np.ndarray]:
    """DP on a single segment with no NaNs."""
    n = len(p)
    if n <= 2:
        return p.copy(), np.ones(n, dtype=bool)

    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    _dp_recurse(p, 0, n - 1, tol, keep)
    return p[keep], keep


def _dp_recurse(p, lo, hi, tol, keep):
    if hi - lo < 2:
        return
    a, b = p[lo], p[hi]
    ab = b - a
    ab_len = np.linalg.norm(ab)

    if ab_len == 0:
        dists = np.linalg.norm(p[lo:hi+1] - a, axis=1)
    else:
        pts = p[lo:hi+1] - a       # (k, D)
        if p.shape[1] == 2:
            # 2D: scalar cross product = |ab_x * pts_y - ab_y * pts_x|
            dists = np.abs(ab[0] * pts[:, 1] - ab[1] * pts[:, 0]) / ab_len
        else:
            dists = np.linalg.norm(np.cross(ab, pts), axis=1) / ab_len

    idx = np.argmax(dists[1:-1]) + 1 + lo
    if dists[idx - lo] > tol:
        keep[idx] = True
        _dp_recurse(p, lo, idx, tol, keep)
        _dp_recurse(p, idx, hi, tol, keep)
