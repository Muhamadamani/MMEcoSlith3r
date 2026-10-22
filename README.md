# MM Eco Slith3r

**Multimaterial toolpath generator for eco-efficient composite 3D printing**

MM Eco Slith3r converts topology optimisation results into G-code for multimaterial FDM printers. It generates continuous, orientation-aligned toolpaths for two materials — designed to work with the companion topology optimisation code [MMEcoTopOpt](https://github.com/gj-asai/MMEcoTopOpt).

> **Shaping Matter Lab · TU Delft**

---

## Overview

The full workflow is:

```
MMEcoTopOpt  →  VTU file  →  MM Eco Slith3r  →  G-code
(topology opt.)  (field data)   (this repo)       (printer)
```

1. **Topology optimisation** — Run [MMEcoTopOpt](https://github.com/gj-asai/MMEcoTopOpt) to obtain an optimised material layout. The output is a `.vtu` file containing the density fields (`xPhys1`, `xPhys2`) and fibre orientation field (`thetaPhys`).
2. **Toolpath generation** — Load the `.vtu` file into MM Eco Slith3r. The code integrates streamlines along the orientation field, cuts them into printable courses, and writes G-code.
3. **Print** — Send the G-code to a dual-material FDM printer.

This repository contains two implementations:

| Folder | Language | Description |
|--------|----------|-------------|
| `matlab/` | MATLAB | Original implementation used for the paper |
| `python/` | Python 3 | Python port with a cross-platform GUI |

---

## Input: VTU Files from MMEcoTopOpt

VTU files are produced by [MMEcoTopOpt](https://github.com/gj-asai/MMEcoTopOpt). The file contains the following fields:

| Field | Description |
|-------|-------------|
| `xPhys1` | Density of material 1 (e.g. bamboo) at each element |
| `xPhys2` | Density of material 2 (e.g. carbon fibre) at each element |
| `thetaPhys` | Fibre orientation angle (radians) at each element |

For single-material cases the VTU may contain `density` and `theta` instead.

---

## Output

For each run MM Eco Slith3r produces three files saved to the output folder:

| File | Description |
|------|-------------|
| `<case>.gcode` | G-code ready to send to the printer |
| `streamlines_all.png / .svg` | All raw streamlines, coloured by line width (YlGnBu palette) |
| `combined_courses.png / .svg` | Final cut courses, material 1 in green-blue tones, material 2 in orange-red |

---

## MATLAB Implementation

### Requirements

- MATLAB R2020a or later (no additional toolboxes required)

### Usage

1. Open `matlab/Slith3r_main.m` in MATLAB.
2. Set the path to your VTU file and configure print parameters in the parameters section.
3. Run the script.

Key parameters:

| Parameter | Description |
|-----------|-------------|
| `d_sep` | Separation distance between streamlines (mm) |
| `d_test` | Test distance for streamline seeding |
| `lineWidth` | Nominal extrusion width (mm) |
| `printThickness` | Layer thickness / print height (mm) |
| `x_printstart`, `y_printstart` | Print bed origin offset (mm) |

### File Structure

```
matlab/
├── Slith3r_main.m          # Main entry point
├── evenStreamlines.m       # Even-spaced streamline generation
├── CutShape.m              # Cut streamlines at boundary
├── CutShapeNew.m           # Updated boundary cutting
├── GCodeFormat.m           # G-code writer
├── GCodeFormatNew.m        # Updated G-code writer
├── kdSegmentCourses.m      # Course segmentation (k-d tree)
├── maskByMaterial.m        # Material mask extraction from VTU
├── movePrint.m             # Coordinate transform to printer frame
├── ReorderPaths.m          # Path reordering to minimise travel
├── SimplifyPaths.m         # Douglas-Peucker path simplification
├── FEMesh.m                # FE mesh utilities
├── GetDistance.m           # Distance field computation
├── smoothBoundary.m        # Boundary smoothing
├── trim_streamline.m       # Streamline trimming
├── plotGcode.m             # G-code visualisation
├── plotSegmentedCourses.m  # Course visualisation
├── begin_endGcodes/        # G-code start/end templates
│   ├── begin_text.gcode
│   ├── end_text.gcode
│   ├── T1_to_T2_tool_change.gcode
│   └── T2_to_T1_tool_change.gcode
└── examples/               # Example input data (.mat)
    ├── c90/                # MBB beam, volume fraction 90%
    ├── c100/               # MBB beam, volume fraction 100%
    ├── c110/               # MBB beam, volume fraction 110%
    ├── CHAIR.mat
    ├── WOOD.mat
    ├── VORTEX.mat
    └── Images/             # Material mask images
```

---

## Python Implementation (MM Slith3r GUI)

### Requirements

- Python 3.10 or later
- Dependencies listed in `python/requirements.txt`

### Installation

```bash
cd python
pip install -r requirements.txt
```

### Launch the GUI

```bash
cd python
python gui.py
```

### GUI Workflow

1. **Load VTU file** — click "Browse" and select the `.vtu` output from MMEcoTopOpt.
2. **Select mode** — choose *Single material* or *Multimaterial*.
3. **Name your materials** — enter names for Material 1 and Material 2 (used for file naming).
4. **Set parameters** — adjust print thickness, line width, separation distance, integration step, and print bed origin.
5. **Set G-code files** — provide begin/end G-code and tool-change G-code templates.
6. **Set output folder** — choose where to save the results.
7. **Generate** — click the green *Generate G-code* button. Progress is shown in the console. Click *Stop* to cancel.

### File Structure

```
python/
├── gui.py              # MM Slith3r GUI (tkinter, Apple-style)
├── vtu_pipeline.py     # Top-level VTU → G-code pipeline
├── slith3r_main.py     # Core streamline + course generation
├── even_streamlines.py # Even-spaced streamline algorithm
├── cut_shape.py        # Boundary cutting
├── gcode_format.py     # G-code formatting and writing
├── move_print.py       # Coordinate transform to printer frame
├── reorder_paths.py    # Path reordering
├── simplify_paths.py   # Path simplification
├── mask_by_material.py # Material mask extraction
├── angle_field.py      # Orientation field utilities
├── get_distance.py     # Distance field
├── smooth_boundary.py  # Boundary smoothing
├── trim_streamline.py  # Streamline trimming
├── load_mat.py         # MATLAB .mat file loader
├── generate_masks.py   # Mask generation helpers
├── mmstream2.py        # Streamline integration
├── init_frame.py       # Frame initialisation
├── dpsimplify.py       # Douglas-Peucker simplification
├── logo.png            # App icon
└── requirements.txt    # Python dependencies
```

### Python Dependencies

```
numpy
scipy
pyvista
matplotlib
Pillow
```

---

## Algorithm

MM Eco Slith3r follows the even-spaced streamline algorithm adapted for manufacturing:

1. **Streamline integration** — Integrate streamlines along the orientation field `θ(x,y)` using the even-spacing algorithm (Jobard & Lefer 1997) adapted for anisotropic fields.
2. **Boundary cutting** — Trim streamlines at the material boundary defined by the density field.
3. **Course segmentation** — Divide streamlines into printable courses based on line width and boundary proximity.
4. **Path reordering** — Reorder courses to minimise travel moves using a nearest-neighbour heuristic.
5. **G-code generation** — Convert courses to G-code, accounting for extrusion width, layer thickness, and printer coordinate frame.

For multimaterial parts, steps 1–5 are run independently for each material mask, then combined into a single G-code file with tool-change commands.

---

## Citation

If you use this code in your research, please cite the associated paper:

```
[Citation will be added upon publication]
```

The topology optimisation code used to generate the VTU input files:

```
@software{MMEcoTopOpt,
  author  = {Asai, G.J. and others},
  title   = {MMEcoTopOpt: Multimaterial Eco-Efficient Topology Optimisation},
  url     = {https://github.com/gj-asai/MMEcoTopOpt}
}
```

---

## Authors

Developed at the **Shaping Matter Lab, TU Delft**.

- Muhammad Amani — m.amani@tudelft.nl

---

## License

This code is released for academic and research use. Please contact the authors for commercial use.
