"""Clip streamlines to a binary image mask (port of CutShapeNew.m).

White pixels (value 255) are the printed region; black is void.
"""

import numpy as np
from PIL import Image


def cut_shape(
    layer: list[dict],
    ANGLES: list[dict],
    mask_image_path: str | None = None,
    mask_array: np.ndarray | None = None,
) -> list[dict]:
    """Filter layer courses to points inside the binary mask.

    Supply either *mask_image_path* (path to a B&W PNG/JPEG, white = print)
    or *mask_array* (2-D uint8 or float array, >0 = print).

    Parameters
    ----------
    layer          : streamline layer list.
    ANGLES         : angle field list (used to determine physical bounding box).
    mask_image_path: path to mask image.
    mask_array     : pre-loaded mask (Iy × Ix).

    Returns
    -------
    Trimmed layer list.
    """
    # Load mask
    if mask_array is not None:
        bw = mask_array
    elif mask_image_path is not None:
        img = Image.open(mask_image_path).convert('L')
        bw = np.array(img, dtype=float) / 255.0
    else:
        raise ValueError("Supply mask_image_path or mask_array")

    Iy, Ix = bw.shape

    # Physical bounding box from ANGLES
    allX = np.concatenate([a['X'].ravel() for a in ANGLES])
    allY = np.concatenate([a['Y'].ravel() for a in ANGLES])
    min_x, max_x = allX.min(), allX.max()
    min_y, max_y = allY.min(), allY.max()

    def to_img_coords(x, y):
        xi = np.clip(
            np.round((x - min_x) / (max_x - min_x) * (Ix - 1)).astype(int), 0, Ix - 1
        )
        yi = np.clip(
            (Iy - 1) - np.round((y - min_y) / (max_y - min_y) * (Iy - 1)).astype(int),
            0, Iy - 1,
        )
        return xi, yi

    out_layer = []
    for lyr in layer:
        mem_course = []
        for c in lyr['courses']:
            P = c['POINT']
            if len(P) == 0:
                continue

            xi, yi = to_img_coords(P[:, 0], P[:, 1])
            inside = bw[yi, xi] > 0.5

            # Split at transitions (NaN-separated segments)
            xnew, ynew, znew, wnew = [], [], [], []
            prev_inside = False
            for k, isin in enumerate(inside):
                if isin:
                    xnew.append(P[k, 0])
                    ynew.append(P[k, 1])
                    znew.append(P[k, 2])
                    wnew.append(P[k, 3])
                    prev_inside = True
                elif prev_inside:
                    xnew.append(np.nan)
                    ynew.append(np.nan)
                    znew.append(np.nan)
                    wnew.append(np.nan)
                    prev_inside = False

            if not xnew:
                continue

            xnew, ynew, znew, wnew = map(np.array, [xnew, ynew, znew, wnew])

            # Remove trailing NaN if present
            if np.isnan(xnew[-1]):
                xnew, ynew, znew, wnew = xnew[:-1], ynew[:-1], znew[:-1], wnew[:-1]

            # Split into sub-segments at NaN separators
            nan_idx = np.where(np.isnan(xnew))[0]
            starts = np.concatenate([[0], nan_idx + 1])
            ends   = np.concatenate([nan_idx, [len(xnew)]])
            for s, e in zip(starts, ends):
                if e - s > 2:
                    seg_x = xnew[s:e]
                    seg_y = ynew[s:e]
                    seg_z = znew[s:e]
                    seg_w = wnew[s:e]
                    mem_course.append({
                        'POINT': np.column_stack([seg_x, seg_y, seg_z, seg_w])
                    })

        out_layer.append({'courses': mem_course})

    return out_layer
