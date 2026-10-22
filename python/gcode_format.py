"""G-code emitter for single-material and multimaterial toolpaths (Prusa XL).

Ports GCodeFormat.m (single material) and GCodeFormatNew.m (multimaterial).

Correct MM workflow
-------------------
1. Run even_streamlines once on the full domain.
2. cut_shape twice — once with bamboo mask, once with carbon mask.
3. Simplify/reorder each material's courses independently.
4. gcode_body() for each material (no begin/end wrappers, no tool selection).
5. merge_material_gcodes() to assemble: begin + T1 carbon + TC + T2 bamboo + end.
"""

from __future__ import annotations

import math
import os
from datetime import date
from pathlib import Path


def _extrusion(dist: float, height: float, width: float, fil_dia: float) -> float:
    """Volume-based extrusion amount (mm of filament)."""
    return 4.0 * dist * height * width / (math.pi * fil_dia ** 2)


def _read(path: str | None) -> str:
    if path and os.path.exists(path):
        return Path(path).read_text()
    return ''


# ── single-material ───────────────────────────────────────────────────────────

def gcode_format(
    layer: list[dict],
    prt_opt: dict,
    begin_file: str | None = None,
    end_file: str | None = None,
) -> None:
    """Write single-material G-code.

    Parameters
    ----------
    layer    : simplified, reordered layer list.
    prt_opt  : dict with keys: 'gcode_fname', 'layer_height', 'fil_dia',
               'print_speed', 'travel_speed', 'thresh_traveldist',
               'nLayers', 'nRepeats', 'ironingFrame'.
    begin_file, end_file : wrapper G-code file paths.
    """
    fname      = prt_opt['gcode_fname']
    lh         = prt_opt['layer_height']
    fil_dia    = prt_opt['fil_dia']
    spd        = int(prt_opt['print_speed'])
    thr_dist   = prt_opt.get('thresh_traveldist', 10.0)
    n_repeats  = int(prt_opt.get('nRepeats', 1))
    ret_dist   = float(prt_opt.get('retract_dist',    0.8))
    ret_spd    = int(prt_opt.get('retract_speed',  2100))
    unret_spd  = int(prt_opt.get('unretract_speed', 1500))
    z_hop      = float(prt_opt.get('z_hop', 1.0))
    t_spd      = int(prt_opt.get('travel_speed', 4500))

    n_layers = prt_opt.get('nLayers', len(layer))
    if len(layer) == 1 and n_layers > 1:
        layer = layer * n_layers

    tot_fil  = 0.0
    tot_time = 0.0

    Path(fname).parent.mkdir(parents=True, exist_ok=True)
    with open(fname, 'w') as fid:
        fid.write('M83 ; relative extruder mode')
        for _rep in range(n_repeats):
            fid.write('\n;NEW PART')
            curr = None
            minx = maxx = miny = maxy = None

            for L, lyr in enumerate(layer):
                fid.write(f'\n;LAYER {L + 1}')
                z = lh * (L + 1)
                for ci, c in enumerate(lyr['courses']):
                    P = c['POINT']
                    if len(P) < 2:
                        continue
                    fid.write(f'\n;COURSE {ci + 1}')
                    sx, sy = P[0, 0], P[0, 1]

                    if curr is not None:
                        d_travel = math.sqrt((sx - curr[0])**2 + (sy - curr[1])**2 + (z - curr[2])**2)
                        if d_travel > thr_dist:
                            fid.write(f'\nG1 E-{ret_dist:.4f} F{ret_spd}')
                            fid.write(f'\nG1 Z{z + z_hop:.4f}')
                            fid.write(f'\nG1 X{sx:.4f} Y{sy:.4f} Z{z + z_hop:.4f} F{t_spd}')
                            fid.write(f'\nG1 E{ret_dist:.4f} F{unret_spd}')

                    fid.write(f'\nG1 X{sx:.4f} Y{sy:.4f} Z{z:.4f}')
                    curr = [sx, sy, z]

                    for i in range(1, len(P)):
                        cx, cy = P[i, 0], P[i, 1]
                        width = P[i, 3]
                        dist  = math.sqrt((cx - curr[0])**2 + (cy - curr[1])**2)
                        ext   = _extrusion(dist, lh, width, fil_dia)
                        fid.write(f'\nG1 X{cx:.4f} Y{cy:.4f} Z{z:.4f} E{ext:.4f} F{spd}')
                        tot_fil  += ext
                        tot_time += dist / spd
                        curr = [cx, cy, z]
                        if minx is None or cx < minx: minx = cx
                        if maxx is None or cx > maxx: maxx = cx
                        if miny is None or cy < miny: miny = cy
                        if maxy is None or cy > maxy: maxy = cy

    header = (
        f';FLAVOR: MARLIN\n'
        f';Generated with Slith3r-MM (Shaping Matter Lab) on {date.today()}\n'
        f';Total filament (m): {tot_fil / 1000:.2f}\n'
        f';Estimated time (min): {tot_time:.1f}\n'
    )
    core  = Path(fname).read_text()
    begin = _read(begin_file)
    end   = _read(end_file)
    Path(fname).write_text('\n'.join(filter(None, [header, begin, core, end])))


# ── multimaterial (Prusa XL) ──────────────────────────────────────────────────

def gcode_format_mm(
    layer: list[dict],
    prt_opt: dict,
    tool_change_files: dict[str, str] | None = None,
    begin_file: str | None = None,
    end_file: str | None = None,
) -> None:
    """Write multimaterial G-code for Prusa XL.

    Each course dict must have a 'material' key: 'bamboo' (T2) or 'carbon' (T1).

    Tool assignment (Prusa XL):
        T1 = carbon fibre   (tool_change_files['carbon'])
        T2 = bamboo         (tool_change_files['bamboo'])

    tool_change_files example::

        {
            'carbon': 'begin_endGcodes/T2_to_T1_tool_change.gcode',  # switch TO carbon
            'bamboo': 'begin_endGcodes/T1_to_T2_tool_change.gcode',  # switch TO bamboo
        }

    Parameters
    ----------
    layer            : material-segmented layer list.
    prt_opt          : print options dict.
    tool_change_files: material → path mapping for tool-change snippets.
    begin_file, end_file: wrapper G-code file paths.
    """
    fname      = prt_opt['gcode_fname']
    lh         = prt_opt['layer_height']
    fil_dia    = prt_opt['fil_dia']
    spd        = int(prt_opt['print_speed'])
    thr        = prt_opt.get('thresh_traveldist', 10.0)
    tcf        = tool_change_files or {}
    ret_dist   = float(prt_opt.get('retract_dist',    0.8))
    ret_spd    = int(prt_opt.get('retract_speed',  2100))
    unret_spd  = int(prt_opt.get('unretract_speed', 1500))
    z_hop      = float(prt_opt.get('z_hop', 1.0))
    t_spd      = int(prt_opt.get('travel_speed', 4500))

    # Load tool-change snippets (once)
    tc_gcode: dict[str, str] = {mat: _read(p) for mat, p in tcf.items()}

    tot_fil  = 0.0
    tot_time = 0.0

    Path(fname).parent.mkdir(parents=True, exist_ok=True)
    with open(fname, 'w') as fid:
        fid.write('M83 ; relative extruder mode')
        last_mat: str | None = None

        for L, lyr in enumerate(layer):
            fid.write(f'\n\n;--- LAYER {L + 1} ---')
            z = lh * (L + 1)
            curr: list[float] | None = None

            for si, c in enumerate(lyr['courses']):
                P   = c['POINT']
                mat = c.get('material', 'carbon')

                if len(P) < 2:
                    continue

                # ── tool change ───────────────────────────────────────────────
                if mat != last_mat and mat in tc_gcode and tc_gcode[mat]:
                    if curr is not None:
                        # retract before tool change
                        fid.write('\nG92 E0')
                        fid.write('\nG1 E-2 F2400 ; retract before tool change')
                    fid.write(f'\n\n; === TOOL CHANGE → {mat.upper()} ===')
                    fid.write('\n' + tc_gcode[mat])
                    fid.write('\nG92 E0 ; reset extruder after tool change')
                    last_mat = mat
                    curr = None  # position unknown after tool change + purge

                fid.write(f'\n; SEGMENT {si + 1} ({mat})')
                sx, sy = P[0, 0], P[0, 1]

                # travel move to segment start
                if curr is not None:
                    d_travel = math.sqrt((sx - curr[0])**2 + (sy - curr[1])**2)
                    if d_travel > thr:
                        fid.write(f'\nG1 E-{ret_dist:.4f} F{ret_spd} ; retract')
                        fid.write(f'\nG1 Z{z + z_hop:.4f}')
                        fid.write(f'\nG1 X{sx:.4f} Y{sy:.4f} Z{z + z_hop:.4f} F{t_spd}')
                        fid.write(f'\nG1 E{ret_dist:.4f} F{unret_spd} ; un-retract')
                    else:
                        fid.write(f'\nG1 X{sx:.4f} Y{sy:.4f} Z{z:.4f} F{t_spd}')
                else:
                    fid.write(f'\nG1 X{sx:.4f} Y{sy:.4f} Z{z:.4f}')

                fid.write(f'\nG1 X{sx:.4f} Y{sy:.4f} Z{z:.4f}')
                curr = [sx, sy, z]

                for i in range(1, len(P)):
                    nx, ny = P[i, 0], P[i, 1]
                    width  = P[i, 3]
                    dist   = math.sqrt((nx - curr[0])**2 + (ny - curr[1])**2)
                    if dist < 1e-6:
                        continue
                    ext = _extrusion(dist, lh, width, fil_dia)
                    fid.write(f'\nG1 X{nx:.4f} Y{ny:.4f} Z{z:.4f} E{ext:.4f} F{spd}')
                    tot_fil  += ext
                    tot_time += dist / spd
                    curr = [nx, ny, z]

    header = (
        f';FLAVOR: MARLIN\n'
        f';Generated with Slith3r-MM (Shaping Matter Lab) on {date.today()}\n'
        f';Multimaterial: T1=Carbon, T2=Bamboo\n'
        f';Total filament (m): {tot_fil / 1000:.2f}\n'
        f';Est time (min): {tot_time:.1f}\n'
    )
    core  = Path(fname).read_text()
    begin = _read(begin_file)
    end   = _read(end_file)
    Path(fname).write_text('\n'.join(filter(None, [header, begin, core, end])))


# ── per-material body (no begin/end wrappers) ─────────────────────────────────

def gcode_body(
    layer: list[dict],
    prt_opt: dict,
    material: str = 'carbon',
) -> tuple[str, float, float]:
    """Return raw G-code body string for ONE material layer set.

    Uses relative extruder mode (M83): each E value is the extrusion delta
    for that segment, not a cumulative position.

    This writes toolpath moves only — no begin/end G-code, no tool selection.
    The caller (merge_material_gcodes) wraps it with the full preamble.

    Returns
    -------
    (body_str, total_filament_mm, total_time_min)
    """
    lh        = prt_opt['layer_height']
    fil_dia   = prt_opt['fil_dia']
    spd       = int(prt_opt['print_speed'])
    thr       = prt_opt.get('thresh_traveldist', 10.0)
    t_spd     = int(prt_opt.get('travel_speed', 4500))
    ret_dist  = float(prt_opt.get('retract_dist',    0.8))
    ret_spd   = int(prt_opt.get('retract_speed',  2100))
    unret_spd = int(prt_opt.get('unretract_speed', 1500))
    z_hop     = float(prt_opt.get('z_hop', 1.0))

    lines = ['M83 ; relative extruder mode']
    tot_fil  = 0.0
    tot_time = 0.0
    curr: list[float] | None = None

    for L, lyr in enumerate(layer):
        lines.append(f'\n;--- {material.upper()} LAYER {L + 1} ---')
        z = lh * (L + 1)
        for ci, c in enumerate(lyr['courses']):
            P = c['POINT']
            if len(P) < 2:
                continue
            lines.append(f'; COURSE {ci + 1}')
            sx, sy = P[0, 0], P[0, 1]

            if curr is not None:
                d = math.sqrt((sx - curr[0])**2 + (sy - curr[1])**2)
                if d > thr:
                    lines.append(f'G1 E-{ret_dist:.4f} F{ret_spd} ; retract')
                    lines.append(f'G1 Z{z + z_hop:.4f}')
                    lines.append(f'G1 X{sx:.4f} Y{sy:.4f} Z{z + z_hop:.4f} F{t_spd}')
                    lines.append(f'G1 E{ret_dist:.4f} F{unret_spd} ; un-retract')
                else:
                    lines.append(f'G1 X{sx:.4f} Y{sy:.4f} Z{z:.4f} F{t_spd}')
            else:
                lines.append(f'G1 X{sx:.4f} Y{sy:.4f} Z{z:.4f}')

            curr = [sx, sy, z]
            for i in range(1, len(P)):
                nx, ny = P[i, 0], P[i, 1]
                width  = P[i, 3]
                dist   = math.sqrt((nx - curr[0])**2 + (ny - curr[1])**2)
                if dist < 1e-6:
                    continue
                ext = _extrusion(dist, lh, width, fil_dia)
                lines.append(f'G1 X{nx:.4f} Y{ny:.4f} Z{z:.4f} E{ext:.4f} F{spd}')
                tot_fil  += ext
                tot_time += dist / spd
                curr = [nx, ny, z]

    return '\n'.join(lines), tot_fil, tot_time


# ── merge two material G-code bodies into one MM file ───────────────────────

def merge_material_gcodes(
    mat2_layer: list[dict],
    mat1_layer: list[dict],
    prt_opt: dict,
    out_path: str,
    tool_change_files: dict[str, str] | None = None,
    begin_file: str | None = None,
    end_file: str | None = None,
    mat1_name: str = 'Material 1',
    mat2_name: str = 'Material 2',
) -> None:
    """Assemble a Prusa XL multimaterial G-code from two material layer sets.

    Material 1 is printed first (extruder already active after begin G-code).
    Tool change fires before Material 2.

    tool_change_files keys:
        'mat2' (or legacy 'carbon') → snippet that activates the second extruder
    """
    tcf = tool_change_files or {}

    mat1_body, m1_fil, m1_time = gcode_body(mat1_layer, prt_opt, mat1_name)
    mat2_body, m2_fil, m2_time = gcode_body(mat2_layer, prt_opt, mat2_name)

    tot_fil  = m1_fil + m2_fil
    tot_time = m1_time + m2_time

    header = (
        f';FLAVOR: MARLIN\n'
        f';Generated with Slith3r-MM (Shaping Matter Lab) on {date.today()}\n'
        f';Multimaterial: extruder1={mat1_name}, extruder2={mat2_name}\n'
        f';Total filament (m): {tot_fil / 1000:.2f}\n'
        f';Estimated print time (min): {tot_time:.1f}\n'
    )

    # Snippet to switch from mat1 extruder → mat2 extruder
    tc_to_mat2 = _read(tcf.get('mat2') or tcf.get('carbon'))

    sections = [
        header,
        _read(begin_file),
        'G92 E0 ; reset extruder',
        f'; === {mat1_name.upper()} ===',
        mat1_body,
        '\nG92 E0 ; reset E before tool change',
    ]
    if tc_to_mat2:
        sections += [
            f'\n; === TOOL CHANGE → {mat2_name.upper()} ===',
            tc_to_mat2,
            'G92 E0 ; reset E after tool change',
        ]
    sections += [
        f'\n; === {mat2_name.upper()} ===',
        mat2_body,
        '\nG92 E0',
        _read(end_file),
    ]

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text('\n'.join(s for s in sections if s))
    print(f"  Written → {out_path}  ({tot_fil/1000:.2f} m filament, ~{tot_time:.0f} min)")
