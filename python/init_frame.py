"""Create perimeter frame points outside the domain bounding box (port of initFrame.m).

These serve as the first Delaunay seed points so circumcenter seeding
always produces candidates inside the domain from the first iteration.
"""

import numpy as np


def init_frame(
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    spacing: float,
) -> np.ndarray:
    """Generate a rectangular frame of seed points just outside the domain.

    Parameters
    ----------
    x_min, x_max, y_min, y_max : domain bounding box.
    spacing : point spacing along each edge.

    Returns
    -------
    (N, 2) array of frame points.
    """
    # MATLAB uses bw = bandwidth/100 — a tiny margin so frame sits just
    # outside the domain, producing circumcenter candidates near the boundary
    margin = spacing / 100.0
    x0, x1 = x_min - margin, x_max + margin
    y0, y1 = y_min - margin, y_max + margin

    # Point spacing ~1 unit along each edge (matches MATLAB's linspace(le,re,Lx+1))
    n_x = max(2, int(round(x_max - x_min)) + 1)
    n_y = max(2, int(round(y_max - y_min)) + 1)
    xs = np.linspace(x0, x1, n_x)
    ys = np.linspace(y0, y1, n_y)

    top    = np.column_stack([xs, np.full(len(xs), y1)])
    bottom = np.column_stack([xs, np.full(len(xs), y0)])
    left   = np.column_stack([np.full(len(ys), x0), ys])
    right  = np.column_stack([np.full(len(ys), x1), ys])

    return np.vstack([top, bottom, left, right])
