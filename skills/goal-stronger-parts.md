---
name: goal-stronger-parts
description: Goal skill for stronger, tougher and watertight parts - wall loops versus infill, infill pattern and density, line width, layer height, nozzle temperature and cooling for layer bonding, overlaps, top/bottom shells, orientation on the plate, material choice, parts that take screws or loads. Read when the user asks "make it stronger", "it breaks", "it snapped", "more solid", "more rigid", "functional part", "watertight", "airtight", "it leaks", "holds a screw".
---
# Stronger, tougher and watertight parts

A printed part is strong along its lines and weak between layers. Order: orientation and material (the user decides), then walls, then layer bonding (temperature, cooling, flow), then infill. A part that split while printing is a defect: defect-layer-adhesion.

## What to ask first
- How does it fail or what must it resist: snapping along layer lines, bending, crushing, impact, a screw pulling out, leaking?
- Direction of the load compared with the layers (ask for a photo of the part as it lies on the plate).
- Material, printer, nozzle, enclosure; does the part work in heat or outdoors?
- Current `wall_loops`, `sparse_infill_density`, `layer_height`, temperature and fan (read the presets).
- Watertight: just holding water, or pressure? Never promise food safety.
- Did it break at a thin section that is already solid? Then only design, orientation or material help.

## Levers, biggest gain first
| Key (preset) | Change | Typical step | Safe limit | What it costs |
|---|---|---|---|---|
| `wall_loops` (process) | increase | +1-2: 2 → 3-4; loaded parts 4-5 | none; once the walls fill the section more loops change nothing | time, material; more shrink stress on large ABS/ASA/PC parts |
| `nozzle_temperature` (filament) | increase | +5 °C per round, up to +10 | inside the filament's temperature range | stringing, drooping overhangs, soft small details |
| `fan_max_speed`, `fan_min_speed` (filament) | decrease (PETG, ABS/ASA, PA, PC) | -10 to -20 points | PLA: keep cooling; check overhangs in the preview | drooping overhangs and bridges |
| `outer_wall_speed`, `inner_wall_speed` (process) | decrease | -20-30% | - | longer print |
| `filament_max_volumetric_speed` (filament) | decrease | -10-20% | lowering is free; raising max +10% | caps every speed, longer print |
| `layer_height` (process) | bring to the middle of the range | 0.15-0.2 mm on a 0.4 mm nozzle | ≤ 60-65% of nozzle for strength (plugin limit 75%, min 0.04) | time; very thin layers only add interfaces that can fail |
| `inner_wall_line_width`, `outer_wall_line_width` (process) | increase | inner to 120%, outer to 105-120% of nozzle | ≤ 150% of nozzle | more flow per mm (speed cap), less fine detail |
| `sparse_infill_density` (process) | increase | +5-10 points, to 25-40% | above 30% rarely pays | time, material, warping stress on ABS/PC |
| `sparse_infill_pattern` (process) | change | `cubic` (strong and quick), `gyroid` or `tpmsd` (equal in all directions, slow), `honeycomb`, `tri-hexagon`, `grid` | not `lightning`, `supportcubic`, `line`, `concentric` on loaded parts | curved patterns print slower; `grid`, `triangles` pile material at the crossings |
| `fill_multiline` (process) | increase | `2` or `3` | ≤ 3 with crossing patterns | same material in thicker infill walls with larger cells: keep enough top layers |
| `top_shell_layers`, `bottom_shell_layers` (process) | increase | +1-2 | aim for 0.8-1.0 mm; `top_shell_thickness`, `bottom_shell_thickness` (process) enforce a minimum | time, material |
| `infill_wall_overlap` (process) | increase | 15% → 20-25% | ≤ 30% | infill pushes the outer wall out, shows through |
| `alternate_extra_wall` (process) | `1` | - | not with `lightning`; set `ensure_vertical_shell_thickness` (process) to `ensure_moderate` | time; uneven wall count |
| `gap_fill_target` (process) | `everywhere` | - | - | time; possible over-fill in solid areas |
| `minimum_sparse_infill_area` (process) | increase | 15 → 50-100 mm² | - | small regions become solid: more material |
| `extra_solid_infills` (process) — BY HAND | set | `10#2` = 2 solid layers every 10; or a list of layer numbers | by hand only (free-text field the plugin cannot check): Process → Strength → Infill | long layers can leave a faint band on the walls |
| `filament_flow_ratio` (filament) | increase (watertight parts, confirmed under-fill) | +0.02, at most +0.05 | 0.8-1.2; better: Calibration → Flow ratio | rough surface, tighter fits, stringing |

Notes for the AI:
- **Walls before infill.** Strength comes mainly from the wall count; infill adds crush resistance and stiffness and supports the top. Add walls first, infill second.
- **Bonding depends on heat.** Plastic laid colder or faster than the hotend can melt it fuses badly: a hotter nozzle, less fan and lower flow help all together. Orca advises keeping inner walls well below the volumetric cap and a 10-20% margin after a Max flowrate test.
- **Wall order.** Keep `wall_sequence` (process) on `inner wall/outer wall` (default): overhanging walls print against a wall already laid. Leave `is_infill_first` (process) at `0`. `precise_outer_wall` (process) only removes the overlap next to the outer wall; Orca states it does not reduce strength.
- **Thin features.** `wall_generator` (process) `arachne` fills thin walls with variable-width lines; with `classic`, `detect_thin_wall` (process) prints single open lines that are weak, and the gap fill between walls adds strength: do not filter it out.
- `ensure_vertical_shell_thickness` (process): keep `ensure_all` on sloped or domed parts, otherwise the shell gets thin on slopes.
- Large ABS/ASA/PC parts: more walls and dense infill raise shrink stress and cracking; there work on enclosure, fan and temperature first (defect-layer-adhesion, defect-warping).
- Recipes for a 0.4 mm nozzle:
  - Functional bracket, clip, hook: `wall_loops` 4, `cubic` or `gyroid` at 25%, `layer_height` 0.2, 5 top and 4 bottom layers, `nozzle_temperature` +5 °C.
  - Part that takes screws: `wall_loops` 4-5 (the walls around a hole follow the same count), `minimum_sparse_infill_area` 50, solid layers at the height of the load with `extra_solid_infills`, or a modifier around the hole (by hand, below).
  - Gears and parts under torque: `fill_multiline` `2`-`3` transfers torque better.
  - Watertight: `wall_loops` 3-4, `layer_height` 0.15-0.2, `outer_wall_line_width` and `inner_wall_line_width` +5-10%, `nozzle_temperature` +5-10 °C, `filament_flow_ratio` +0.02 to +0.05, `bottom_surface_pattern` (process) `concentric`; for leaks where floor and wall meet, `top_bottom_infill_wall_overlap` (process) 25% → 30-35%. Even wall thickness matters: thick walls with sparse infill leak into the cavity. Single-wall vases: a wider line (0.6 mm on a 0.4 mm nozzle), see goal-surface-quality.

## Limits you cannot tune past (explain to the user)
- **Layers are the weak direction.** No setting makes the bond between layers as strong as the lines themselves. A part pulled or bent across its layers needs a different orientation.
- **Solid sections.** Where the walls already fill the whole section, more walls or infill change nothing: the feature must be thicker (design) or the material different.
- **Material.** Heat resistance, brittleness and toughness belong to the plastic: see materials-overview and material-pla, material-petg, material-abs-asa, material-pa-pc, material-composites, material-tpu. High-shrink materials (ABS, ASA, PC, PA-CF, PET-CF) crack between layers without an enclosure.
- **Flow above the hotend's limit** gives under-filled, colder lines and weak layers.
- **Wet filament** prints with voids: weak and leaky whatever the settings.
- **Nozzle size.** A 0.2 mm nozzle lays thin lines that bond less: parts are weaker than with 0.4 or 0.6 mm.
- **Watertight is never guaranteed** and is not food-safe: pores remain between layers. Not for hazardous liquids.
- **100% infill** is rarely the answer: more shrink stress, worse surfaces, much more time.

## Checks and choices the user makes by hand
- **Orientation** (most effective, free): rotate the part (Rotate or Lay on face in the Prepare toolbar) so that the main load runs along the layers, not across them. Hooks, clips, tabs and pins: lay them so the layer lines follow their length. Auto orient optimizes for supports, not for strength: check its result. Then `align_infill_direction_to_model` (process) `1` keeps infill directions fixed to the part.
- **Local reinforcement**: right-click the object → Add modifier, place the shape over the hole, boss or thin arm, and set more wall loops or a higher infill density on that modifier in the object list. Per-object values are set by switching the Process panel from Global to Objects.
- **Dry the filament** before a functional or watertight print (PETG, TPU, PA, PC above all): materials-overview.
- **Enclosure and drafts** for ABS/ASA/PC/PA: doors and lid closed, no fan or window nearby. Chamber heating is set on the printer by the user; the plugin never changes it.
- **Calibrations** (calibration-guide): Temperature (pick the block with the best bonding), Max flowrate, Flow ratio.
- **Larger nozzle** (hardware plus the matching printer preset): thicker, wider lines and stronger parts, less detail.
- **Hole sizes for screws and inserts**: defect-dimensional-accuracy.
- **Leak test**: fill with water and leave it on a paper towel; a leak where floor and wall meet calls for more overlap (recipe above).

## Related skills
- defect-layer-adhesion (splitting, cracks), defect-extrusion (gaps, weak infill), defect-warping, defect-dimensional-accuracy.
- materials-overview and the material-* skills; calibration-guide.
- goal-faster-prints, goal-surface-quality (opposite trades: thin layers and slow outer walls do not add strength).

## Sources
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_walls.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_infill.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_advanced.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_top_bottom_shells.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_patterns.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_patterns_quick_reference.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_line_width.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_layer_height.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_precision.html
- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_other_layers_speed.html
- https://www.orcaslicer.com/wiki/calibration/volumetric_speed_calib.html
- https://www.orcaslicer.com/wiki/print_prepare/prepare_auto_orient.html
- https://wiki.bambulab.com/en/filament/reduce-vase-leaking-guide
- https://wiki.bambulab.com/en/software/bambu-studio/fill-patterns
- https://wiki.bambulab.com/en/software/bambu-studio/parameter/strength-advance-settings
- https://wiki.bambulab.com/en/knowledge-sharing/volumetric-speed
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/interlayer-cracking
- https://wiki.bambulab.com/en/filament-acc/filament/support-for-abs
- https://wiki.bambulab.com/en/knowledge-sharing/02-mm-nozzle-FAQ
- https://wiki.bambulab.com/en/software/bambu-studio/how-to-set-slicing-parameters
- https://help.prusa3d.com/article/watertight-prints_112324
- https://help.prusa3d.com/article/layers-and-perimeters_1748
- https://help.prusa3d.com/article/infill_42
- https://help.prusa3d.com/article/infill-patterns_177130
- https://help.prusa3d.com/article/layer-separation-and-splitting-fdm_1806
