"""Assign material labels (bamboo / carbon) to course points (port of maskByMaterial.m + kdSegmentCourses.m).

Uses a KDTree of FE centroid coordinates to decide which material each
streamline point belongs to.
"""

import numpy as np
from scipy.spatial import KDTree


def segment_by_material(
    layer: list[dict],
    bamboo_pts: np.ndarray,
    carbon_pts: np.ndarray,
    radius: float | None = None,
) -> list[dict]:
    """Label every course point as 'bamboo' or 'carbon'.

    Each course dict gains two sub-dicts:
        course['bamboo']['POINT']  and  course['carbon']['POINT']

    Parameters
    ----------
    layer       : streamline layer list.
    bamboo_pts  : (Nb, 2) centroid coordinates of bamboo FE elements.
    carbon_pts  : (Nc, 2) centroid coordinates of carbon FE elements.
    radius      : if given, points farther than this from *both* materials
                  are discarded.

    Returns
    -------
    layer list with bamboo/carbon sub-dicts added to each course.
    """
    b_tree = KDTree(bamboo_pts)
    c_tree = KDTree(carbon_pts)

    out_layer = []
    for lyr in layer:
        new_courses = []
        for c in lyr['courses']:
            P = c['POINT']
            if len(P) == 0:
                new_courses.append({**c, 'bamboo': {'POINT': np.empty((0, 4))},
                                         'carbon': {'POINT': np.empty((0, 4))}})
                continue

            xy = P[:, :2]
            db, _ = b_tree.query(xy)
            dc, _ = c_tree.query(xy)
            is_bamboo = db <= dc

            if radius is not None:
                valid = np.minimum(db, dc) <= radius
                is_bamboo &= valid

            new_c = dict(c)
            new_c['bamboo'] = {'POINT': P[is_bamboo]}
            new_c['carbon'] = {'POINT': P[~is_bamboo]}
            new_courses.append(new_c)

        out_layer.append({'courses': new_courses})

    return out_layer


def flatten_by_material(
    layer: list[dict],
) -> list[dict]:
    """Flatten material-labelled courses into a single list of courses with a 'material' key.

    Each output course dict has:
        {'POINT': np.ndarray, 'material': 'bamboo' | 'carbon'}
    """
    out_layer = []
    for lyr in layer:
        new_courses = []
        for c in lyr['courses']:
            for mat in ('bamboo', 'carbon'):
                P = c.get(mat, {}).get('POINT', np.empty((0, 4)))
                if len(P) >= 2:
                    new_courses.append({'POINT': P, 'material': mat})
        out_layer.append({'courses': new_courses})
    return out_layer
