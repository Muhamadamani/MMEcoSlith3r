"""VTU-based pipeline for Slith3r-MM.

One VTU file contains everything needed:

* **Multimaterial** (fields ``xPhys1``, ``xPhys2``, ``thetaPhys``):
  - ``xPhys1 > 0.5`` → bamboo region
  - ``xPhys2 > 0.5`` → carbon region
  - both ≤ 0.5        → void (not printed, excluded from both masks)
  Separate angle fields are built from each material's active elements.

* **Single-material** (field ``density``):
  All active elements (``density > 0.5``) printed on one extruder.

Typical usage::

    from slith3r_python.vtu_pipeline import run_from_vtu, run_single_material_from_vtu

    run_from_vtu('c1300_bamboo.vtu', out_path='output/c1300.gcode')
    run_single_material_from_vtu('bamboo.vtu', out_path='output/bamboo.gcode')
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import numpy as np
from scipy.interpolate import griddata

DENSITY_THRESHOLD = 0.5   # elements above this are considered solid


# ── centroid helper ───────────────────────────────────────────────────────────

def _compute_centroids(data: dict) -> np.ndarray:
    pts  = data['points']
    conn = data['connectivity']
    offs = data['offsets']
    n_cells = len(offs)
    starts     = np.concatenate([[0], offs[:-1]])
    cell_sizes = offs - starts
    if np.all(cell_sizes == cell_sizes[0]):
        n_per     = int(cell_sizes[0])
        conn_mat  = conn.reshape(n_cells, n_per)
        centroids = pts[conn_mat].mean(axis=1)
    else:
        centroids = np.array([
            pts[conn[s:e]].mean(axis=0)
            for s, e in zip(starts, offs)
        ])
    return centroids


# ── public API: parse ─────────────────────────────────────────────────────────

def parse_vtu(path: str) -> dict:
    """Parse a VTU file and return structured material data.

    Supports two formats:

    **Multimaterial** (fields ``xPhys1``, ``xPhys2``, ``thetaPhys``):
    Returns ``has_two_materials=True``, ``density`` = xPhys1 (bamboo),
    ``density2`` = xPhys2 (carbon).

    **Single-material** (field ``density``):
    Returns ``has_two_materials=False``, ``density2=None``.

    Return dict keys
    ----------------
    centroids          : (n, 2) cell barycentres
    theta              : (n,) fibre orientation in radians
    density            : (n,) material-1 density (0–1)
    density2           : (n,) material-2 density, or None
    has_two_materials  : bool
    x_range, y_range   : (min, max) physical extents
    """
    from .generate_masks import _parse_vtu_binary

    data      = _parse_vtu_binary(path)
    centroids = _compute_centroids(data)
    n         = len(centroids)

    if 'xPhys1' in data and 'xPhys2' in data:
        density  = data['xPhys1']
        density2 = data['xPhys2']
        theta    = data.get('thetaPhys', data.get('theta', np.zeros(n)))
        has_two  = True
    else:
        density  = data.get('density', np.ones(n))
        density2 = None
        theta    = data.get('theta', np.zeros(n))
        has_two  = False

    x_range = (float(centroids[:, 0].min()), float(centroids[:, 0].max()))
    y_range = (float(centroids[:, 1].min()), float(centroids[:, 1].max()))

    return {
        'centroids':         centroids,
        'theta':             theta,
        'density':           density,
        'density2':          density2,
        'has_two_materials': has_two,
        'x_range':           x_range,
        'y_range':           y_range,
    }


# ── angle-field builder ───────────────────────────────────────────────────────

def theta_to_angles(
    centroids:  np.ndarray,
    theta:      np.ndarray,
    grid_shape: tuple[int, int] = (20, 50),
    x_range:    tuple[float, float] | None = None,
    y_range:    tuple[float, float] | None = None,
) -> list[dict]:
    """Interpolate scattered fibre-angle data onto a regular grid.

    Returns ANGLES list compatible with :func:`even_streamlines.even_streamlines`.
    """
    if x_range is None:
        x_range = (float(centroids[:, 0].min()), float(centroids[:, 0].max()))
    if y_range is None:
        y_range = (float(centroids[:, 1].min()), float(centroids[:, 1].max()))

    ny, nx = grid_shape
    xs = np.linspace(x_range[0], x_range[1], nx)
    ys = np.linspace(y_range[0], y_range[1], ny)
    Xg, Yg = np.meshgrid(xs, ys)
    grid_pts = np.column_stack([Xg.ravel(), Yg.ravel()])

    theta_grid = griddata(centroids, theta, grid_pts, method='linear')
    nan_mask = np.isnan(theta_grid)
    if nan_mask.any():
        theta_nearest = griddata(centroids, theta, grid_pts, method='nearest')
        theta_grid[nan_mask] = theta_nearest[nan_mask]

    theta_grid = theta_grid.reshape(ny, nx)
    return [{'X': Xg, 'Y': Yg, 'U': np.cos(theta_grid), 'V': np.sin(theta_grid)}]


# ── pipelines ─────────────────────────────────────────────────────────────────

def run_from_vtu(
    vtu_path:          str,
    out_path:          str = 'output/toolpath.gcode',
    prt_opt:           dict | None = None,
    grid_shape:        tuple[int, int] = (20, 50),
    integ_step:        float = 0.3,
    n_max:             int = 200,
    begin_gcode:       str | None = None,
    end_gcode:         str | None = None,
    tool_change_files: dict[str, str] | None = None,
    mat1_name:         str = 'Material 1',
    mat2_name:         str = 'Material 2',
    thickness_mm:      float = 10.0,
    plot:              bool = False,
    ax=None,
    run_dir:           'Path | None' = None,
    line_callback=None,
) -> None:
    """Multimaterial toolpath from a single VTU file.

    The VTU must have fields ``xPhys1`` / ``xPhys2`` (material densities)
    and ``thetaPhys`` (fibre angle).  Elements where both densities ≤
    ``DENSITY_THRESHOLD`` are void and excluded from all masks and G-code.

    Streamlines are generated ONCE from all active elements; the same set
    is cut twice — once per material — so there is no duplicate generation.

    ``thickness_mm`` controls the number of printed layers:
    ``n_layers = round(thickness_mm / layer_height)``.
    """
    from pathlib import Path as _Path
    from .slith3r_main import (DEFAULT_PRT_OPT, _save_fig, _add_courses_lc,
                               _visualize_courses, _visualize_combined_courses)
    from .generate_masks import _rasterize_with_dilation
    from .even_streamlines import even_streamlines
    from .cut_shape import cut_shape
    from .simplify_paths import simplify_paths
    from .reorder_paths import reorder_paths
    from .move_print import move_print
    from .gcode_format import merge_material_gcodes

    opt        = {**DEFAULT_PRT_OPT, **(prt_opt or {}), 'gcode_fname': out_path}
    frame_bool = bool(opt.get('frameBool', 0))
    IMG_W = IMG_H = 800
    DIL_MM        = 2.5

    # Number of layers from thickness
    layer_height   = float(opt.get('layer_height', 0.2))
    n_layers       = max(1, round(thickness_mm / layer_height))
    opt['nLayers'] = n_layers
    print(f"  Print thickness: {thickness_mm} mm  →  {n_layers} layers "
          f"@ {layer_height} mm", flush=True)

    if run_dir is not None:
        run_dir = _Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

    # ── parse ─────────────────────────────────────────────────────────────────
    print(f"Parsing VTU: {vtu_path} …", flush=True)
    vtu = parse_vtu(vtu_path)

    if not vtu['has_two_materials']:
        raise ValueError(
            f"{vtu_path} does not contain xPhys1/xPhys2 fields. "
            "Use run_single_material_from_vtu() for single-material files.")

    centroids = vtu['centroids']
    theta     = vtu['theta']
    d1        = vtu['density']   # material 1
    d2        = vtu['density2']  # material 2
    x_range   = vtu['x_range']
    y_range   = vtu['y_range']

    is_m1  = d1 > DENSITY_THRESHOLD
    is_m2  = d2 > DENSITY_THRESHOLD
    m1_pts = centroids[is_m1]
    m2_pts = centroids[is_m2]
    n_void = ((~is_m1) & (~is_m2)).sum()

    print(f"  {mat1_name}: {is_m1.sum()} elements  |  "
          f"{mat2_name}: {is_m2.sum()} elements  |  Void: {n_void}", flush=True)

    # ── single angle field from ALL active elements ───────────────────────────
    print("Building angle field …", flush=True)
    is_active = is_m1 | is_m2
    ANGLES = theta_to_angles(
        centroids[is_active], theta[is_active],
        grid_shape=grid_shape, x_range=x_range, y_range=y_range,
    )

    # ── material masks (rasterised; void excluded from both) ──────────────────
    print("Building material masks …", flush=True)
    mask_m1 = _rasterize_with_dilation(m1_pts, x_range, y_range, IMG_W, IMG_H, DIL_MM)
    mask_m2 = _rasterize_with_dilation(m2_pts, x_range, y_range, IMG_W, IMG_H, DIL_MM)

    # ── generate streamlines ONCE ─────────────────────────────────────────────
    print("\nGenerating even streamlines …", flush=True)
    layer_raw = even_streamlines(
        ANGLES, opt, integ_step=integ_step, n_max=n_max,
        plot=plot, ax=ax, line_callback=line_callback)
    n_all = sum(len(l['courses']) for l in layer_raw)
    print(f"  → {n_all} streamlines total", flush=True)

    # Save all-streamlines plot (YlGnBu_r palette) as PNG + SVG
    if run_dir is not None:
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            fig_s = Figure(figsize=(10, 4)); FigureCanvasAgg(fig_s)
            ax_s  = fig_s.add_subplot(111)
            ax_s.set_aspect('equal'); ax_s.set_facecolor('white')
            lc = _add_courses_lc(ax_s, layer_raw, cmap_name='YlGnBu_r', lw=1.2)
            ax_s.autoscale()
            ax_s.set_title(f'All streamlines — {n_all} total')
            ax_s.set_xlabel('x (mm)'); ax_s.set_ylabel('y (mm)')
            if lc is not None:
                fig_s.colorbar(lc, ax=ax_s, label='width (mm)', shrink=0.8)
            fig_s.tight_layout()
            _save_fig(fig_s, str(run_dir / 'streamlines_all'))
        except Exception as _e:
            print(f"  [streamline plot skipped: {_e}]", flush=True)

    # ── clip each material from the same raw set ───────────────────────────────
    # y_flip_bound: FEM X extent → corrects Y-inversion after swap=True
    _y_flip = float(x_range[1])

    def _process(raw, mask_arr, name):
        raw_copy  = copy.deepcopy(raw)
        print(f"  Clipping to {name} mask …", flush=True)
        lyr = cut_shape(raw_copy, ANGLES, mask_array=mask_arr)
        n   = sum(len(l['courses']) for l in lyr)
        print(f"    → {n} courses", flush=True)
        lyr = simplify_paths(lyr, opt)
        lyr = reorder_paths(lyr, frame_bool=frame_bool)
        save_path = str(run_dir / f'{name}_courses') if run_dir else None
        _visualize_courses(lyr, name, '#5b8c5a', save_path=save_path)
        # return pre-move layer for combined plot, post-move for G-code
        lyr_moved = move_print(
            lyr, (opt['x_printstart'], opt['y_printstart']),
            swap=True, y_flip_bound=_y_flip)
        return lyr, lyr_moved

    lyr_m1_orig, lyr_m1 = _process(layer_raw, mask_m1, mat1_name)
    lyr_m2_orig, lyr_m2 = _process(layer_raw, mask_m2, mat2_name)

    # ── combined courses plot (FEM coords, before move_print) ─────────────────
    if run_dir is not None:
        _visualize_combined_courses(
            lyr_m1_orig, lyr_m2_orig, mat1_name, mat2_name,
            save_path=str(run_dir / 'combined_courses'),
        )

    # ── merge G-code ──────────────────────────────────────────────────────────
    n1 = sum(len(l['courses']) for l in lyr_m1)
    n2 = sum(len(l['courses']) for l in lyr_m2)
    print(f"\nMerging G-codes ({n1} {mat1_name} + {n2} {mat2_name} courses) …",
          flush=True)

    merge_material_gcodes(
        lyr_m2, lyr_m1, opt, out_path,
        tool_change_files=tool_change_files,
        begin_file=begin_gcode,
        end_file=end_gcode,
        mat1_name=mat1_name,
        mat2_name=mat2_name,
    )
    print(f"Done → {out_path}", flush=True)


def run_single_material_from_vtu(
    vtu_path:     str,
    out_path:     str = 'output/toolpath.gcode',
    prt_opt:      dict | None = None,
    grid_shape:   tuple[int, int] = (20, 50),
    integ_step:   float = 0.3,
    n_max:        int = 200,
    begin_gcode:  str | None = None,
    end_gcode:    str | None = None,
    run_dir:      'Path | None' = None,
    line_callback=None,
) -> None:
    """Toolpath pipeline for a single-material VTU file.

    All elements with density > ``DENSITY_THRESHOLD`` are printed as one
    material on the active extruder.  No tool change inserted.

    Accepts both file formats:
    - Legacy: ``density`` + ``theta`` fields
    - Multimaterial format (``xPhys1`` / ``xPhys2``): uses ``xPhys1`` as density
      and ``thetaPhys`` as the angle field.
    """
    from pathlib import Path as _Path
    from .slith3r_main import DEFAULT_PRT_OPT, _save_fig, _add_courses_lc, _visualize_courses
    from .even_streamlines import even_streamlines
    from .simplify_paths import simplify_paths
    from .reorder_paths import reorder_paths
    from .move_print import move_print
    from .gcode_format import gcode_format

    opt        = {**DEFAULT_PRT_OPT, **(prt_opt or {}), 'gcode_fname': out_path}
    frame_bool = bool(opt.get('frameBool', 0))

    if run_dir is not None:
        run_dir = _Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

    # ── parse ─────────────────────────────────────────────────────────────────
    print(f"Parsing VTU: {vtu_path} …", flush=True)
    vtu       = parse_vtu(vtu_path)
    centroids = vtu['centroids']
    theta     = vtu['theta']
    density   = vtu['density']
    x_range   = vtu['x_range']
    y_range   = vtu['y_range']

    active = density > DENSITY_THRESHOLD
    print(f"  Active elements: {active.sum()} / {len(density)}", flush=True)

    # ── angle field from active elements ──────────────────────────────────────
    print("Building angle field …", flush=True)
    ANGLES = theta_to_angles(
        centroids[active], theta[active],
        grid_shape=grid_shape, x_range=x_range, y_range=y_range,
    )

    # ── streamlines ───────────────────────────────────────────────────────────
    print("\nGenerating even streamlines …", flush=True)
    layer_raw = even_streamlines(
        ANGLES, opt, integ_step=integ_step, n_max=n_max,
        plot=False, ax=None, line_callback=line_callback,
    )
    n_all = sum(len(l['courses']) for l in layer_raw)
    print(f"  → {n_all} streamlines", flush=True)

    # Save all-streamlines plot (YlGnBu_r palette) as PNG + SVG (thread-safe)
    if run_dir is not None:
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            fig_s = Figure(figsize=(10, 4)); FigureCanvasAgg(fig_s)
            ax_s  = fig_s.add_subplot(111)
            ax_s.set_aspect('equal'); ax_s.set_facecolor('white')
            lc = _add_courses_lc(ax_s, layer_raw, cmap_name='YlGnBu_r', lw=1.2)
            ax_s.autoscale()
            ax_s.set_title(f'All streamlines — {n_all} total')
            ax_s.set_xlabel('x (mm)'); ax_s.set_ylabel('y (mm)')
            if lc is not None:
                fig_s.colorbar(lc, ax=ax_s, label='width (mm)', shrink=0.8)
            fig_s.tight_layout()
            _save_fig(fig_s, str(run_dir / 'streamlines_all'))
        except Exception as _e:
            print(f"  [streamline plot skipped: {_e}]", flush=True)

    # ── simplify / reorder / offset ───────────────────────────────────────────
    print("Simplifying paths …", flush=True)
    lyr = simplify_paths(layer_raw, opt)
    print("Reordering paths …", flush=True)
    lyr = reorder_paths(lyr, frame_bool=frame_bool)

    save_path = str(run_dir / 'courses') if run_dir else None
    _visualize_courses(lyr, 'single-material', '#5b8c5a', save_path=save_path)

    lyr = move_print(lyr, (opt['x_printstart'], opt['y_printstart']),
                     swap=True, y_flip_bound=float(x_range[1]))

    # ── write G-code ──────────────────────────────────────────────────────────
    n = sum(len(l['courses']) for l in lyr)
    print(f"\nWriting G-code ({n} courses) …", flush=True)
    gcode_format(lyr, opt, begin_file=begin_gcode, end_file=end_gcode)
    print(f"Done → {out_path}", flush=True)
