"""Greedy nearest-neighbour TSP reordering (port of ReorderPaths.m).

Vectorised: each step does one cdist call against all remaining endpoints
instead of a Python loop — O(N) per step instead of O(N) × 2 linalg.norm calls.
"""

import numpy as np
from scipy.spatial.distance import cdist


def reorder_paths(layer: list[dict], frame_bool: bool = False) -> list[dict]:
    """Reorder courses to minimise travel distance between successive courses.

    Parameters
    ----------
    frame_bool : if True, strip the last course (boundary frame), reorder the
                 rest, then re-append it at the end — matching MATLAB's
                 frameBool=1 branch in ReorderPaths.m.
    """
    import time
    out = []
    for lyr in layer:
        courses = [c for c in lyr['courses'] if len(c['POINT']) >= 2]

        # frameBool: strip boundary outline, reorder body, re-append at end
        frame_course = None
        if frame_bool and len(courses) > 1:
            frame_course = courses[-1]
            courses = courses[:-1]

        n = len(courses)
        print(f'  Reordering {n} courses …', flush=True)
        t0 = time.time()
        if n == 0:
            out.append({'courses': ([frame_course] if frame_course else [])})
            continue
        if n == 1:
            result = courses + ([frame_course] if frame_course else [])
            out.append({'courses': result})
            continue

        # Pre-extract start/end points once
        starts = np.array([c['POINT'][0,  :2] for c in courses])  # (N, 2)
        ends   = np.array([c['POINT'][-1, :2] for c in courses])  # (N, 2)
        flipped = np.zeros(n, dtype=bool)

        visited = np.zeros(n, dtype=bool)
        order   = []

        # Start from course index 0 — matches MATLAB (always starts from course 1)
        first = 0
        order.append(first)
        visited[first] = True

        for _ in range(n - 1):
            last_pt = ends[order[-1]][None]          # (1, 2)
            unvisited = np.where(~visited)[0]

            # Distance from last_pt to start and end of each unvisited course
            d_s = cdist(last_pt, starts[unvisited])[0]   # (M,)
            d_e = cdist(last_pt, ends[unvisited])[0]     # (M,)

            # Best is min over both orientations
            d_min = np.minimum(d_s, d_e)
            best_local = int(np.argmin(d_min))
            best = unvisited[best_local]

            # Flip course if approaching from the end
            if d_e[best_local] < d_s[best_local]:
                flipped[best] = True
                # Swap the pre-extracted endpoints so future steps stay correct
                starts[best], ends[best] = ends[best].copy(), starts[best].copy()

            order.append(best)
            visited[best] = True

        # Build output, flipping courses where needed
        new_courses = []
        for i in order:
            c = courses[i]
            if flipped[i]:
                c = {**c, 'POINT': c['POINT'][::-1]}
            new_courses.append(c)

        # Re-append frame outline at the end (frameBool=1 behaviour)
        if frame_course is not None:
            new_courses.append(frame_course)

        print(f'    → done  ({time.time()-t0:.1f}s)', flush=True)
        out.append({'courses': new_courses})

    return out
