"""Translate (and optionally swap XY) all course points (port of movePrint.m)."""

import numpy as np


def move_print(
    layer: list[dict],
    start_pos: tuple[float, float],
    swap: bool = False,
    y_flip_bound: float | None = None,
) -> list[dict]:
    """Offset layer courses to the printer coordinate frame.

    Parameters
    ----------
    layer        : layer list.
    start_pos    : (x_offset, y_offset) translation applied after transform.
    swap         : if True, swap X and Y axes (portrait→landscape).
    y_flip_bound : if given, flip the post-swap Y axis so that
                   y_gcode = y_flip_bound - y_original + y_offset.
                   Pass the FEM X extent (x_range[1]) to correct the
                   Y-inversion that arises when swap=True.
    """
    x0, y0 = start_pos
    out = []
    for lyr in layer:
        new_courses = []
        for c in lyr['courses']:
            P = c['POINT'].copy()
            if swap:
                x_new = P[:, 1] + x0
                if y_flip_bound is not None:
                    y_new = y_flip_bound - P[:, 0] + y0
                else:
                    y_new = P[:, 0] + y0
                P[:, 0] = x_new
                P[:, 1] = y_new
            else:
                P[:, 0] += x0
                if y_flip_bound is not None:
                    P[:, 1] = y_flip_bound - P[:, 1] + y0
                else:
                    P[:, 1] += y0
            new_courses.append({**c, 'POINT': P})
        out.append({'courses': new_courses})
    return out
