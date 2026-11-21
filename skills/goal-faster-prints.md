---
name: goal-faster-prints
description: Goal skill for shorter print time and/or less filament - layer height, walls and shells, infill density and pattern (lightning, adaptive cubic), speeds against the filament's max volumetric speed, accelerations, supports, brim, variable layer height, reading Orca's time estimate, and what each saving costs. Read when the user asks "make it print faster", "reduce print time", "it takes too long", "use less filament", "save material", "draft mode", "quick prototype".
---
# Faster prints and less filament

Every saving is paid with strength, looks or risk. Find where the time goes, cut plastic first, then raise what is still below a cap. State the price of each change.

## What to ask first
- Less time, less filament, or both?
- What may get worse: looks (prototype, hidden part) or strength (decorative part)? If neither, say that the gain will be small.
- Printer, nozzle, material. Is the filament's max volumetric speed a vendor value, a calibrated one or a guess?
- Ask the user to slice and read the Preview tab:
  - total time and the Line Type legend (time and share per feature: outer wall, inner wall, sparse infill, support, travel);
  - colour scheme "Flow" (mm³/s): large areas sitting at the filament's cap mean the hotend is the limit;
  - colour scheme "Speed": real speeds after the cap and the cooling slowdown.
- How to read it:
  - most time in sparse infill or support: pattern, density, support rows;
  - most time in walls: layer height, wall count, wall speeds;
  - Flow at the cap almost everywhere: mm/s settings do nothing; only less plastic or a higher cap helps;
  - speeds far below the settings on a small part: acceleration or minimum layer time is the limit.

## Levers, biggest gain first
| Key (preset) | Change | Typical step | Safe limit | What it costs |
|---|---|---|---|---|
| `layer_height` (process) | increase | 0.2 → 0.24 or 0.28 on a 0.4 mm nozzle | ≤ 75% of nozzle diameter (0.30 on 0.4 mm), min 0.04 mm | visible layer lines, rougher curves and overhangs, weaker bonding near the limit; more flow per mm, so the cap bites at lower mm/s |
| `sparse_infill_pattern` (process) | change | visual parts: `lightning` or `supportcubic`; large functional parts: `adaptivecubic`; quick: `rectilinear`, `zigzag`, `grid`, `cubic` | avoid `gyroid`, `honeycomb`, `3dhoneycomb`, `tpmsfk`, `hilbertcurve` | `lightning` and `supportcubic` only hold up the top: no strength, uneven layer times; `grid` crosses itself in each layer (nozzle noise at speed) |
| `sparse_infill_density` (process) | decrease | -5 points, down to 10-15% | about 10%; with `lightning` it is the density right under the top | less crush resistance and stiffness; top sags over wide cells |
| `wall_loops` (process) | decrease | 3 → 2 | ≥ 2 on anything handled or loaded | largest strength loss per minute saved; infill shows through |
| `top_shell_layers`, `bottom_shell_layers` (process) | decrease | -1 | top ≥ 3; `top_shell_thickness` (process) adds layers back when count × layer height is below it | pillowing, holes on top (defect-top-surface) |
| `inner_wall_speed`, `sparse_infill_speed`, `internal_solid_infill_speed` (process) | increase | +10-20% per round | ≤ printer machine limits; no effect once the flow reaches `filament_max_volumetric_speed` | weaker layer bonding close to the cap, ringing, noise |
| `default_acceleration`, `inner_wall_acceleration`, `sparse_infill_acceleration`, `travel_acceleration` (process) | increase | +20-30% | ≤ printer max acceleration; `default_acceleration` 0 = firmware values, the others are ignored | ringing, noise; keep `outer_wall_acceleration` and `top_surface_acceleration` low |
| `filament_max_volumetric_speed` (filament) | increase, only after Calibration → Max flowrate | to the measured quality limit minus 10-20% | plugin: at most +10%; more only by hand | under-extrusion, matte patches, weak layers, clicking extruder, clogs |
| `nozzle_temperature` (filament) | increase when printing close to the cap | +5-10 °C | inside the filament's temperature range | stringing, drooping overhangs, soft small details |
| `infill_combination` (process) | `1` | `infill_combination_max_layer_height` (process) `100%` fastest, `80%` stronger | works only if 2 × `layer_height` fits in the nozzle diameter (0.2 on 0.4 mm yes; 0.24-0.28 no) | infill needs double flow (cap); weaker infill |
| `inner_wall_line_width` (process) | increase | to 110-125% of nozzle | ≤ 150% of nozzle | saves time only if a wall loop is dropped for the same thickness; more flow per mm |
| `support_type`, `support_style` (process) | `tree(auto)` with `default` or `tree_slim`; `snug` for normal supports | - | - | slim supports can fail under heavy overhangs (defect-supports) |
| `support_threshold_angle` (process) | decrease | 30 → 25 or 20 | what the material still prints cleanly | drooping steep overhangs |
| `brim_type` (process) | `no_brim` | - | not for ABS/ASA/PA, tall thin parts, small footprints | warping, parts knocked loose (defect-warping) |
| `ironing_type` (process) | `no ironing` | - | - | no ironed top; ironing is among the slowest features |
| `reduce_infill_retraction` (process) | `1` | - | - | slight ooze inside the infill |
| `outer_wall_speed`, `top_surface_speed` (process) | increase, last of all | +10-20% | ≤ machine limits and the cap | gloss changes, ringing, rough top: visible quality goes first |

Notes for the AI:
- Flow (mm³/s) ≈ layer height × line width × speed: 0.2 × 0.45 mm at 200 mm/s = 18 mm³/s. Orca lowers every speed whose flow would exceed `filament_max_volumetric_speed`: highest useful speed = cap ÷ (layer height × line width).
- At the cap, time ≈ plastic volume ÷ cap: thicker layers stop saving time. Remove plastic (infill, walls, supports) or raise the cap with a calibration. If a tall-layer profile is capped everywhere, a lower layer height gives more detail in about the same time.
- Typical caps (Prusa): PLA 12-20, PETG 8-15, ABS/ASA 10-16, PA 8-12, PC 6-10, TPU 2-5 mm³/s; classic all-metal hotend 8-12, Prusa Nextruder 15-20, high-flow 20-40. Vendor presets hold tested values.
- Keep inner-wall flow below the cap for bonding; after a Max flowrate test keep a 10-20% margin.
- `fill_multiline` (process) `2` uses the same material: `gyroid` and `honeycomb` print about 15-20% faster, crossing patterns (`grid`, `cubic`) can get slower.
- Never pair `lightning` with `alternate_extra_wall` (process).
- Recipes for a 0.4 mm nozzle:
  - Draft / visual prototype: `layer_height` 0.28, `wall_loops` 2, `lightning` or `adaptivecubic` at 10-15%, 3 top and 3 bottom layers, no ironing.
  - Functional but quicker: keep walls, temperature and outer wall; `adaptivecubic` or `cubic` at 15%; inner-wall and infill speeds up to the cap.
  - Less filament only: infill pattern and density, supports, brim; leave speeds alone.

## Limits you cannot tune past (explain to the user)
- **Hotend melt rate.** Above it walls come out thinner than sliced, surfaces turn matte, layers bond badly, the extruder clicks, the nozzle clogs.
- **Machine limits.** Orca clamps process speeds, accelerations and jerk to the printer's Motion ability values; the plugin never edits printer settings.
- **Minimum layer time.** Layers shorter than `slow_down_layer_time` (filament) are slowed, down to `slow_down_min_speed` (filament), so the plastic can set. On small or pointed parts speed settings do not help, and a lower layer time trades minutes for melted tips (defect-overheating-small-features).
- **Small parts never reach the set speed**: only accelerations change their time, at the cost of ringing.
- **First layer.** Leave `initial_layer_speed` (process) alone: a failed first layer costs more than it saves.
- **Overhangs.** Keep `enable_overhang_speed` (process) on.
- **The estimate** is the slicer's own: real time can differ, and a speed mode set on the printer changes it.

## Checks and choices the user makes by hand
- **Orientation**: a lower part with fewer supports prints faster. Auto orient (Prepare toolbar) looks for the least support; orientation also changes strength (goal-stronger-parts).
- **Variable layer height** (Prepare toolbar, object selected): Adaptive with the Quality/Speed slider toward Speed, then Smooth. Thick layers go on vertical walls, thin ones only on curves. The range comes from the min/max layer height in the printer's extruder settings. Restrictions (Bambu documentation): a prime tower needs the same layer profile on all objects; not available with organic tree supports. The plugin cannot apply this tool.
- **Per-object settings**: in the Process panel switch from Global to Objects and give walls and dense infill only to the object that needs them; a modifier (right-click → Add modifier) covers one region.
- **Calibration → Max flowrate** (calibration-guide): the only sound way to raise the flow cap.
- **Printer speed modes** (Bambu Sport / Ludicrous, set on the printer): Sport suits prototypes that must still work; Ludicrous is for drafts and costs surface, detail and layer bonding.
- **Larger nozzle** (hardware plus the matching printer preset): 0.6 mm allows thicker layers, wider lines and a somewhat higher cap; fine detail is lost.
- **Machine limits** (Printer settings → Motion ability): only by hand, within the manufacturer's values.

## Related skills
- goal-stronger-parts, goal-surface-quality (the opposite trades).
- calibration-guide, defect-extrusion, defect-layer-adhesion, defect-ringing-ghosting, defect-top-surface, defect-supports, defect-warping, defect-overheating-small-features.
- printers-bambu, printers-prusa (speed modes, hotend flow).

## Sources
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_layer_height.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_line_width.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_walls.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_top_bottom_shells.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_infill.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_advanced.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_patterns.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_patterns_quick_reference.html
- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_other_layers_speed.html
- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_acceleration.html
- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_support.html
- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_brim.html
- https://www.orcaslicer.com/wiki/material_settings/filament/material_volumetric_speed_limitation.html
- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html
- https://www.orcaslicer.com/wiki/calibration/volumetric_speed_calib.html
- https://www.orcaslicer.com/wiki/print_prepare/prepare_variable_layer_height.html
- https://www.orcaslicer.com/wiki/print_prepare/prepare_auto_orient.html
- https://wiki.bambulab.com/en/knowledge-sharing/volumetric-speed
- https://wiki.bambulab.com/en/software/bambu-studio/layer-height
- https://wiki.bambulab.com/en/software/bambu-studio/adaptive-layer-height
- https://wiki.bambulab.com/en/software/bambu-studio/fill-patterns
- https://wiki.bambulab.com/en/software/bambu-studio/parameter/strength-advance-settings
- https://wiki.bambulab.com/en/software/bambu-studio/how-to-set-slicing-parameters
- https://wiki.bambulab.com/en/software/bambu-studio/view-slicing-information
- https://help.prusa3d.com/article/max-volumetric-speed_127176
- https://help.prusa3d.com/article/speed-settings_480325
- https://help.prusa3d.com/article/infill_42
- https://help.prusa3d.com/article/infill-patterns_177130
- https://help.prusa3d.com/article/layers-and-perimeters_1748
