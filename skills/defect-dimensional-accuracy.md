---
name: defect-dimensional-accuracy
description: Parts out of size: holes too small, pegs or screws that do not fit, outer dimensions too big or small, shrinkage that grows with part size, wrong Z height, ovals instead of circles, elephant foot as a dimensional error; Orca XY hole/contour compensation, elephant foot compensation, precise wall, polyholes and the tolerance test. Read when the user reports wrong dimensions, holes too tight, parts that do not fit together, tolerances, clearance, press fit, shrinkage, a part smaller or bigger than designed, or a flared bottom ruining the fit.
---
# Dimensional accuracy

## How to recognize it
Ask for caliper measurements of the print before changing anything; get the designed values with measure_section instead of asking for them.
- **Holes undersized** (most common): screws, pins, bearings or magnets do not go in; outer size is close to nominal.
- **Outer size off by a constant amount** (e.g. always +0.15 mm on any size): line width / flow / wall placement.
- **Error growing with part size** (e.g. -0.1 mm at 20 mm, -0.5 mm at 100 mm): thermal shrinkage of the material.
- **Only the bottom layers wider**: elephant foot (first layer squish).
- **Height off by up to one layer**: the model height is not a multiple of the layer height.
- **Circles printed as ovals, or one axis off**: mechanics (belts, firmware steps), not the slicer.

## Likely causes, most common first
1. Holes shrink inward: plastic contracts toward the hole centre, round holes are approximated by short segments, and the seam bump sits inside the hole.
2. Flow ratio too high (parts and walls oversize, bulging tops) or too low (undersize, gaps).
3. Elephant foot: first layer squished by a low Z offset or soft from a hot bed, plus the weight of the layers above.
4. Thermal shrinkage: highest on ABS/ASA, PA, PC; small on PLA and PETG; reduced by fibre-filled grades.
5. Wall order: with inner walls printed first, the outer wall is pushed outward by the overlap.
6. Mechanics: belts loose (ovals), wrong steps/mm or rotation distance in firmware (whole axis scaled).
7. Model: low-resolution STL (faceted holes), holes close to the nozzle size (below about 1 mm), no chamfers or lead-ins, tolerances never designed in.
8. Measuring error: measuring near the first layer, at corners (pressure advance effects), on a warm part, or squeezing the caliper.

## Questions worth asking (only when the answer changes the fix)
- Tools first: measure_section gives the designed hole diameters and wall thickness at a height (show_figure section to show them); ask the user only for the caliper readings of the print.
- What is too big or small: holes, outer size, bottom edge, height? By how much (mm)?
- Is the error the same on a small and a large part, or proportional to size?
- Which material and plate? Elephant foot compensation differs by plate type.
- Was flow ratio calibrated for this filament?
- Is the fit part designed with clearance (typically a few tenths of a mm for sliding fits)?

## Slicer fixes
Fix the cause in this order: measurement → flow → elephant foot → holes/contours → shrinkage (by hand).

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `xy_hole_compensation` (process) | increase if holes are tight | +0.05 mm (hole diameter grows by 2× the value) | usually 0 to +0.2 mm; more points to a model or flow problem | affects every hole, also ones meant to be tight |
| `xy_contour_compensation` (process) | decrease if outside is too big, increase if too small | ±0.05 mm | usually within ±0.15 mm | thin features and text get thinner or vanish with negative values |
| `elefant_foot_compensation` (process) | increase if the base is flared | +0.05 mm; about 0.1-0.2 mm with a 0.4 mm nozzle | ≤ 0.25 mm with a 0.4 mm nozzle; skipped with a raft | brim may look detached in preview; too much: brim does not attach, thin first-layer details distort |
| `elefant_foot_compensation_layers` (process) | increase if the flare spans several layers | 1 → 2-3 | integer ≥ 1 | compensation fades linearly over these layers |
| `precise_outer_wall` (process) | enable | `1` | only works with `wall_sequence` = `inner wall/outer wall` | none relevant; more consistent outer wall |
| `wall_sequence` (process) | outer wall undisturbed | `inner-outer-inner wall` (needs ≥ 3 walls) or `outer wall/inner wall` | | weaker overhangs; outer/inner makes the seam less consistent; `precise_outer_wall` is then ignored (use one or the other) |
| `hole_to_polyhole` (process) | enable for round holes on pins/screws | `1` | | holes become polygons (by design) |
| `precise_z_height` (process) | enable for exact height | `1` | | last few layers get adjusted heights |
| `filament_flow_ratio` (filament) | adjust from the Flow Rate calibration | ±0.02 | 0.8-1.2 | wrong value causes gaps or bulging tops |
| first-layer plate temperature of the plate in use, e.g. `textured_plate_temp_initial_layer`, `hot_plate_temp_initial_layer`, `cool_plate_temp_initial_layer`, `eng_plate_temp_initial_layer`, `supertack_plate_temp_initial_layer`, `textured_cool_plate_temp_initial_layer` (filament) | decrease if elephant foot persists | -5 °C | stay in the material's recommended bed range; increases at most +10 °C, never above 120 °C | weaker adhesion, more warping |
| `seam_position` (process) | move the seam away from critical holes | `back` or `aligned` (or paint the seam) | | seam moves to another visible place |

Notes:
- XY compensation is the right tool for a constant error. A proportional error is shrinkage and is not fixed by XY compensation.
- Hole and contour compensation are per filament and process: repeat the test when the material changes.

## Checks the user must do by hand (hardware, material, printer settings)
- **Measure correctly**: let the part cool to room temperature; measure the middle of a face, not corners; measure well above the first layer (or on a tall test piece, the upper layers only); light caliper pressure.
- **Shrinkage is material data: the plugin never changes it.** If the error is proportional to size, the user can enter the filament's Shrinkage (XY) and Shrinkage (Z) values by hand in the filament preset, as measured / designed × 100% (a 20 mm cube measuring 19.9 mm gives 99.5%), or scale the object in Orca. Re-check holes afterwards.
- **First layer**: correct Z offset and levelling (too low a nozzle makes the first layers wide for many layers); clean plate. See defect-first-layer.
- **Belts**: correct tension; loose belts print circles as ovals. Bambu CoreXY: loosen the tensioner screws, move the toolhead, retighten, then run Vibration compensation. Prusa: see the belt checks in defect-layer-shift.
- **Firmware steps / rotation distance** (printer side, by hand): only if a 100 mm part is off on one axis while flow and compensation are right.
- **Filament**: dry it (moisture makes extrusion uneven); diameter should be within about ±0.02 mm of 1.75 mm.
- **Model**: export STL at high resolution or import STEP; design clearances and chamfers; holes near nozzle size are not reliable.

## Calibration in Orca (menu Calibration → ...)
- **Calibration → Flow ratio** first (see calibration-guide), together with pressure advance; dimensional tests come last because they depend on all the others.
- **Orca Tolerance Test**: right-click the plate → Add Handy models → Orca Tolerance Test. Hexagonal holes with 0, 0.05, 0.1, 0.2, 0.3, 0.4 mm clearance and a hex tester (or a 6 mm Allen key). The tightest hole that fits shows the clearance the printer needs; tune `xy_hole_compensation` and `xy_contour_compensation`, reprint, repeat.
- **Screw hole test** (Bambu method): print a hole gauge with compensation 0, find the hole that fits a known screw snugly (an M6 is about 5.9 mm), enter that offset, reprint to confirm; add further offsets if needed.
- **Elephant foot measurement**: print a 25 × 25 × 10 mm cube with compensation 0 and no brim (`brim_type` (process) = `no_brim`), let it cool on the plate, measure X and Y at the top and at the base (mid-face). Compensation ≈ average of (base - top) for X and Y, e.g. (0.09 + 0.11) / 2 = 0.10 mm. Repeat when changing plate type.

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- PLA, PETG: low shrinkage; errors are usually flow, holes or elephant foot. A hotter bed increases elephant foot on any material.
- ABS/ASA: noticeable shrinkage (often around 0.5-1%) and warping that also distorts size; keep the enclosure closed.
- TPU: soft, measures smaller under caliper pressure; design generous clearances.
- PA/PC: high shrinkage and moisture uptake; dry before printing and calibrating.
- CF/GF filled: fibres limit shrinkage, usually the most dimensionally stable choice for fits.

## Sources
- https://wiki.bambulab.com/en/knowledge-sharing/3d-prints-shrinkage
- https://wiki.bambulab.com/en/software/bambu-studio/xy-hole-contour-compensation
- https://wiki.bambulab.com/en/software/bambu-studio/parameter/elephant-foot
- https://wiki.bambulab.com/en/x1/maintenance/belt-tension
- https://wiki.bambulab.com/en/p2s/maintenance/belt-tension
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/severe-layer-artifacts
- https://help.prusa3d.com/article/elephant-foot-compensation_114487
- https://www.orcaslicer.com/wiki/calibration/tolerance_calib.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_precision.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html
- https://www.orcaslicer.com/wiki/guides/calibration_guide.html
- https://www.simplify3d.com/resources/print-quality-troubleshooting/dimensional-accuracy/
- https://www.obico.io/blog/3d-print-troubleshooting-guide/
