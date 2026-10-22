"""Slith3r-MM main pipeline (Python port of Slith3r_main.m).

Correct multimaterial workflow
------------------------------
1. Load angle field (ANGLES.mat / .npz).
2. Generate even streamlines across the full domain.
3. Cut streamlines with BAMBOO mask → bamboo courses.
4. Cut streamlines with CARBON mask → carbon courses.
5. Simplify + reorder each material independently.
6. Apply print-origin offset.
7. Merge into one Prusa XL G-code: [begin] T1(bamboo) TC T2(carbon) [end].

The masks can come from:
  - A .mat mesh file (centroids + density_ids)  → generate_masks.masks_from_mat()
  - Two pre-made B&W PNG images                 → passed directly as --mask-bamboo / --mask-carbon

Usage — bundled c100 example (Prusa XL multimaterial):
    python -m slith3r_python.slith3r_main --example c100

Usage — custom:
    python -m slith3r_python.slith3r_main \\
        --angles  slith3r/examples/c100/ANGLES.mat \\
        --mesh    slith3r/examples/mesh_data_full_beam_bamboo.mat \\
        --out     output/c100.gcode
"""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime
from pathlib import Path

import numpy as np

from .load_mat import load_angles_mat
from .even_streamlines import even_streamlines
from .cut_shape import cut_shape
from .simplify_paths import simplify_paths
from .reorder_paths import reorder_paths
from .move_print import move_print
from .gcode_format import gcode_format, merge_material_gcodes


def load_angles(path: str) -> list[dict]:
    p = Path(path)
    if p.suffix == '.npz':
        d = np.load(p)
        return [{'X': d['X'], 'Y': d['Y'], 'U': d['U'], 'V': d['V']}]
    if p.suffix == '.mat':
        return load_angles_mat(path)
    raise ValueError(f"Unsupported format: {p.suffix}")


DEFAULT_PRT_OPT = {
    'upperbound':        0.6,
    'lowerbound':        0.4,
    'tol':               0.05,
    'widthInterp':       0.22,
    'distInterp':        5.0,
    'boolFilter':        1,
    'threshDist':        1.2,
    'layer_height':      0.2,
    'fil_dia':           1.75,
    'print_speed':       1200,
    'travel_speed':      4500,
    'thresh_traveldist': 2.0,
    'x_printstart':      10.0,
    'y_printstart':      10.0,
    'nLayers':           1,
    'nRepeats':          1,
    'frameBool':         1,
    'retract_dist':      0.8,    # mm
    'retract_speed':     2100,   # mm/min
    'unretract_speed':   1500,   # mm/min
    'z_hop':             1.0,    # mm
}


def _courses_to_line_collection(lyr: list[dict]):
    """Convert layer courses to segments + width arrays for LineCollection."""
    import numpy as np
    segments = []
    widths   = []
    for layer in lyr:
        for c in layer.get('courses', []):
            pts = c.get('POINT')
            if pts is None or len(pts) < 2:
                continue
            for i in range(len(pts) - 1):
                segments.append([(pts[i, 0], pts[i, 1]),
                                  (pts[i + 1, 0], pts[i + 1, 1])])
                widths.append(float(pts[i, 3]))
    return segments, widths


def _add_courses_lc(ax, lyr: list[dict], cmap_name: str = 'YlGnBu_r',
                    lw: float = 1.5, alpha: float = 0.9, label: str = ''):
    """Add courses as a LineCollection coloured by extrusion width (MATLAB style).

    Matches MATLAB: ``colormap(brewermap([],"-YlGnBu"))`` + ``patch`` coloured by width.
    Returns the LineCollection (for adding a colourbar).
    """
    import numpy as np
    from matplotlib.collections import LineCollection
    from matplotlib.colors import Normalize
    import matplotlib

    segments, widths = _courses_to_line_collection(lyr)
    if not segments:
        return None

    w_arr = np.array(widths)
    norm  = Normalize(vmin=w_arr.min(), vmax=w_arr.max())
    try:
        cmap = matplotlib.colormaps[cmap_name]   # matplotlib ≥ 3.9
    except AttributeError:
        cmap = matplotlib.cm.get_cmap(cmap_name)  # matplotlib < 3.9
    lc    = LineCollection(segments, cmap=cmap, norm=norm, linewidths=lw, alpha=alpha,
                           label=f'{label} ({len(lyr[0]["courses"] if lyr else [])} courses)')
    lc.set_array(w_arr)
    ax.add_collection(lc)
    ax.autoscale()
    return lc


def _save_fig(fig, base_path: str) -> None:
    """Save figure as both PNG and SVG."""
    from pathlib import Path
    stem = str(Path(base_path).with_suffix(''))
    fig.savefig(stem + '.png', dpi=150, bbox_inches='tight')
    fig.savefig(stem + '.svg', bbox_inches='tight')
    print(f"  [plot saved] {stem}.png + .svg", flush=True)


def _visualize_courses(
    lyr: list[dict], label: str, color: str,
    save_path: str | None = None,
) -> None:
    """Save a MATLAB-style plot for one material's courses (coloured by width).

    Thread-safe when ``save_path`` is given (uses Agg backend, no pyplot window).
    """
    try:
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        if save_path:
            fig = Figure(figsize=(10, 4)); FigureCanvasAgg(fig)
            ax  = fig.add_subplot(111)
        else:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(10, 4))

        ax.set_aspect('equal')
        ax.set_facecolor('white')
        ax.set_xlabel('x (mm)'); ax.set_ylabel('y (mm)')

        lc = _add_courses_lc(ax, lyr, cmap_name='YlGnBu_r', lw=1.5)
        n  = sum(len(l.get('courses', [])) for l in lyr)
        ax.set_title(f'{label} — {n} courses')
        if lc is not None:
            fig.colorbar(lc, ax=ax, label='width (mm)', shrink=0.8)

        ax.set_axis_off()
        fig.tight_layout()

        if save_path:
            _save_fig(fig, save_path)
        else:
            import matplotlib.pyplot as plt
            plt.tight_layout()
            plt.show(block=False); plt.pause(0.5)
            print(f"  [plot] {label}: {n} courses", flush=True)
    except Exception as e:
        print(f"  [plot skipped: {e}]", flush=True)


def _visualize_combined_courses(
    lyr1: list[dict], lyr2: list[dict],
    label1: str, label2: str,
    save_path: str | None = None,
) -> None:
    """Save a combined MATLAB-style plot for two materials side by side.

    Material 1 → cool cmap (YlGnBu_r).
    Material 2 → warm cmap (YlOrRd_r).
    Thread-safe when save_path is given.
    """
    try:
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        if save_path:
            fig = Figure(figsize=(12, 5)); FigureCanvasAgg(fig)
            ax  = fig.add_subplot(111)
        else:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(12, 5))

        ax.set_aspect('equal')
        ax.set_facecolor('white')

        lc1 = _add_courses_lc(ax, lyr1, cmap_name='YlGnBu_r', lw=1.5, alpha=0.85,
                               label=label1)
        lc2 = _add_courses_lc(ax, lyr2, cmap_name='YlOrRd_r', lw=1.5, alpha=0.85,
                               label=label2)

        n1 = sum(len(l.get('courses', [])) for l in lyr1)
        n2 = sum(len(l.get('courses', [])) for l in lyr2)
        ax.set_title(f'{label1} ({n1}) + {label2} ({n2}) courses')
        ax.set_axis_off()
        if lc1: fig.colorbar(lc1, ax=ax, label=f'{label1} width (mm)',
                              shrink=0.6, pad=0.02)
        if lc2: fig.colorbar(lc2, ax=ax, label=f'{label2} width (mm)',
                              shrink=0.6, pad=0.06)
        fig.tight_layout()

        if save_path:
            _save_fig(fig, save_path)
        else:
            import matplotlib.pyplot as plt
            plt.tight_layout()
            plt.show(block=False); plt.pause(0.5)
    except Exception as e:
        print(f"  [combined plot skipped: {e}]", flush=True)


def _process_material(
    layer_raw: list[dict],
    ANGLES: list[dict],
    mask_path: str | None,
    mask_array: np.ndarray | None,
    opt: dict,
    label: str,
    *,
    visualize: bool = False,
    run_dir: Path | None = None,
) -> list[dict]:
    """Cut → simplify → reorder → offset one material's streamlines."""
    if mask_path or mask_array is not None:
        print(f"  Clipping to {label} mask …", flush=True)
        lyr = cut_shape(layer_raw, ANGLES,
                        mask_image_path=mask_path, mask_array=mask_array)
        n = sum(len(l['courses']) for l in lyr)
        print(f"    → {n} courses", flush=True)
    else:
        lyr = copy.deepcopy(layer_raw)

    print(f"  Simplifying {label} paths …", flush=True)
    lyr = simplify_paths(lyr, opt)

    print(f"  Reordering {label} paths …", flush=True)
    lyr = reorder_paths(lyr, frame_bool=bool(opt.get('frameBool', 0)))

    if visualize:
        color = '#5b8c5a' if 'bamboo' in label.lower() else '#2c5282'
        save_path = str(run_dir / f'{label}_courses.png') if run_dir else None
        _visualize_courses(lyr, label, color, save_path=save_path)

    lyr = move_print(lyr, (opt['x_printstart'], opt['y_printstart']), swap=True)
    return lyr


def run_pipeline(
    angles_path: str,
    mesh_path: str | None,
    bamboo_mask_path: str | None,
    carbon_mask_path: str | None,
    out_path: str,
    prt_opt: dict | None = None,
    integ_step: float = 0.5,
    n_max: int = 200,
    multimaterial: bool = False,
    begin_gcode: str | None = None,
    end_gcode: str | None = None,
    tool_change_files: dict[str, str] | None = None,
    plot: bool = False,
    ax=None,
    run_dir: Path | None = None,
    line_callback=None,
) -> None:
    opt = {**DEFAULT_PRT_OPT, **(prt_opt or {}), 'gcode_fname': out_path}

    print("Loading angle field …")
    ANGLES = load_angles(angles_path)
    print(f"  → {len(ANGLES)} layer(s), grid {ANGLES[0]['X'].shape}")

    # ── generate masks from mesh mat if not provided as images ───────────────
    bamboo_arr: np.ndarray | None = None
    carbon_arr: np.ndarray | None = None

    if multimaterial and mesh_path and not (bamboo_mask_path and carbon_mask_path):
        print("Generating material masks from mesh …")
        from .generate_masks import masks_from_mat
        ang0 = ANGLES[0]
        x_range = (float(ang0['X'].min()), float(ang0['X'].max()))
        y_range = (float(ang0['Y'].min()), float(ang0['Y'].max()))
        bamboo_arr, carbon_arr = masks_from_mat(
            mesh_path, x_range=x_range, y_range=y_range,
            img_size=(800, 800), dilation_mm=2.5,
        )
        n_b = bamboo_arr.sum(); n_c = carbon_arr.sum()
        print(f"  → bamboo {n_b} px ({100*bamboo_arr.mean():.1f}%), "
              f"carbon {n_c} px ({100*carbon_arr.mean():.1f}%)")

    # ── generate all streamlines once ────────────────────────────────────────
    print("Generating even streamlines …")
    layer_raw = even_streamlines(ANGLES, opt,
                                 integ_step=integ_step, n_max=n_max,
                                 plot=plot, ax=ax,
                                 line_callback=line_callback)
    n_all = sum(len(l['courses']) for l in layer_raw)
    print(f"  → {n_all} streamlines across {len(layer_raw)} layer(s)")

    # Save all-streamlines plot (YlGnBu_r palette, PNG + SVG)
    if run_dir is not None:
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            fig2 = Figure(figsize=(10, 4))
            FigureCanvasAgg(fig2)
            ax2 = fig2.add_subplot(111)
            ax2.set_aspect('equal'); ax2.set_facecolor('white')
            lc2 = _add_courses_lc(ax2, layer_raw, cmap_name='YlGnBu_r', lw=1.2)
            ax2.autoscale()
            ax2.set_title(f'All streamlines — {n_all} total')
            ax2.set_xlabel('x (mm)'); ax2.set_ylabel('y (mm)')
            if lc2 is not None:
                fig2.colorbar(lc2, ax=ax2, label='width (mm)', shrink=0.8)
            fig2.tight_layout()
            _save_fig(fig2, str(run_dir / 'streamlines_all'))
        except Exception as e:
            print(f"  [streamline plot skipped: {e}]", flush=True)

    if plot:
        print("  (plot window stays open — pipeline continuing …)", flush=True)

    if not multimaterial:
        # ── single-material path ─────────────────────────────────────────────
        lyr = _process_material(
            layer_raw, ANGLES,
            bamboo_mask_path or carbon_mask_path, None,
            opt, 'shape',
            visualize=run_dir is not None,
            run_dir=run_dir,
        )
        opt['gcode_fname'] = out_path
        print("Writing G-code …")
        gcode_format(lyr, opt, begin_file=begin_gcode, end_file=end_gcode)
        print(f"Done → {out_path}")
        return

    # ── dual-material path ───────────────────────────────────────────────────
    print("\n── Bamboo (T1) ──")
    lyr_bamboo = _process_material(
        layer_raw, ANGLES,
        bamboo_mask_path, bamboo_arr,
        opt, 'bamboo',
        visualize=True,
        run_dir=run_dir,
    )
    n_bam = sum(len(l['courses']) for l in lyr_bamboo)

    print("\n── Carbon fibre (T2) ──")
    lyr_carbon = _process_material(
        layer_raw, ANGLES,
        carbon_mask_path, carbon_arr,
        opt, 'carbon',
        visualize=True,
        run_dir=run_dir,
    )
    n_cf = sum(len(l['courses']) for l in lyr_carbon)

    print(f"\nMerging G-codes ({n_bam} bamboo + {n_cf} carbon courses) …")
    merge_material_gcodes(
        lyr_carbon, lyr_bamboo, opt, out_path,
        tool_change_files=tool_change_files,
        begin_file=begin_gcode,
        end_file=end_gcode,
    )
    print(f"Done → {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Slith3r-MM toolpath generator")
    parser.add_argument('--example', choices=['c100', 'c90', 'c110'],
                        help='Run a bundled example (Prusa XL multimaterial)')
    parser.add_argument('--angles',       default=None, help='.mat or .npz angle field')
    parser.add_argument('--mesh',         default=None, help='.mat mesh file with centroids + material IDs')
    parser.add_argument('--mask-bamboo',  default=None, help='B&W PNG mask for bamboo (white=bamboo)')
    parser.add_argument('--mask-carbon',  default=None, help='B&W PNG mask for carbon (white=carbon)')
    parser.add_argument('--out',          default='output/toolpath.gcode')
    parser.add_argument('--options',      default=None, help='JSON file with prt_opt overrides')
    parser.add_argument('--mm',           action='store_true', help='multimaterial mode')
    parser.add_argument('--begin-gcode',  default=None)
    parser.add_argument('--end-gcode',    default=None)
    parser.add_argument('--step',  type=float, default=0.5,
                        help='RK2 integration step mm (default 0.5)')
    parser.add_argument('--nmax',  type=int,   default=200,
                        help='Max integration steps per half-streamline')
    parser.add_argument('--plot',  action='store_true',
                        help='Live matplotlib during streamline generation')
    args = parser.parse_args()

    slith3r_dir = Path(__file__).parent.parent / 'slith3r'

    prt_opt: dict = {}
    angles_path   = args.angles
    mesh_path     = args.mesh
    bamboo_mask   = args.mask_bamboo
    carbon_mask   = args.mask_carbon
    out_path      = args.out
    tc_files: dict[str, str] | None = None
    begin_g = args.begin_gcode
    end_g   = args.end_gcode

    # ── timestamped run directory ────────────────────────────────────────────
    timestamp  = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    base_label = args.example if args.example else Path(out_path).stem
    run_dir    = Path('output') / f'{timestamp}_{base_label}'
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output folder: {run_dir}/")

    if args.example:
        ex          = args.example
        angles_path = str(slith3r_dir / 'examples' / ex / 'ANGLES.mat')
        mesh_path   = str(slith3r_dir / 'examples' / 'mesh_data_full_beam_bamboo.mat')
        out_path    = str(run_dir / f'{ex}_prusa_xl.gcode')

        gcodes_dir  = slith3r_dir / 'begin_endGcodes'
        begin_g     = begin_g or str(gcodes_dir / 'begin_text.gcode')
        end_g       = end_g   or str(gcodes_dir / 'end_text.gcode')
        tc_files = {
            'bamboo': str(gcodes_dir / 'T2_to_T1_tool_change.gcode'),  # T2→T1: activates T1 (bamboo)
            'carbon': str(gcodes_dir / 'T1_to_T2_tool_change.gcode'),  # T1→T2: activates T2 (carbon)
        }

        # Use pre-made PNG masks if available, else generate from mesh mat
        img_dir = slith3r_dir / 'examples' / 'Images'
        _bam = img_dir / 'bamboo.png'
        if _bam.exists():
            bamboo_mask = str(_bam)
            _cf_total = img_dir / 'full_carbon_bamboo.png'
            if _cf_total.exists():
                from PIL import Image as PILImage
                import numpy as _np
                _bam_arr  = _np.array(PILImage.open(_bam).convert('L')) > 127
                _tot_arr  = _np.array(PILImage.open(_cf_total).convert('L')) > 127
                _cf_arr   = _tot_arr & ~_bam_arr
                _cf_path  = str(run_dir / f'{ex}_carbon_mask.png')
                PILImage.fromarray((_cf_arr * 255).astype(_np.uint8)).save(_cf_path)
                carbon_mask = _cf_path
                print(f"  Derived carbon mask: {100*_cf_arr.mean():.1f}% white → {_cf_path}")

        prt_opt = {
            'upperbound':    0.6,
            'lowerbound':    0.4,
            'layer_height':  0.2,
            'print_speed':   1200,
            'travel_speed':  4500,
            'thresh_traveldist': 2.0,
            'x_printstart':  10.0,
            'y_printstart':  10.0,
            'frameBool':     1,
        }
        if args.step == 0.5:
            args.step = 0.3
        args.mm = True
        print(f"Running bundled example '{ex}' — dual-mask multimaterial …")
    else:
        # Custom run: put gcode inside run_dir
        out_path = str(run_dir / Path(out_path).name)

    if args.options:
        with open(args.options) as f:
            prt_opt.update(json.load(f))

    if angles_path is None:
        parser.error("Provide --angles or use --example")

    run_pipeline(
        angles_path=angles_path,
        mesh_path=mesh_path,
        bamboo_mask_path=bamboo_mask,
        carbon_mask_path=carbon_mask,
        out_path=out_path,
        prt_opt=prt_opt,
        integ_step=args.step,
        n_max=args.nmax,
        multimaterial=args.mm,
        begin_gcode=begin_g,
        end_gcode=end_g,
        tool_change_files=tc_files,
        plot=args.plot,
        run_dir=run_dir,
    )


if __name__ == '__main__':
    main()
