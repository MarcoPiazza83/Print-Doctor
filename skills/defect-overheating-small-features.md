---
name: defect-overheating-small-features
description: Covers overheated small parts (melted, droopy or rounded tips, spires, pins, deformed small layers), small features or thin walls that are missing or not printed, and gaps in the middle of thin walls. Read when the user reports "melted tip", "top of the cone is a blob", "small parts deformed", "overheating", "droopy layers", "details missing", "text/thin wall not printed", "thin wall has a gap in the middle" or "feature disappears in preview".
---
# Overheating of small features, missing small features, gaps in thin walls

## How to recognize it
- **Overheating**: tips of cones, spires, pins and small towers are melted, rounded, curled or blobby; small cross-sections sag or lean; layers look glossy and soft while larger parts on the same plate are fine. Usually worse near the top of a part where layers get smaller.
- **Small features missing**: text, fins, thin walls or sharp details are absent already in the slicer Preview (a slicing issue), or present in Preview but not on the print (extrusion issue, see defect-extrusion).
- **Gaps in thin walls**: a wall a few lines thick shows a slit or holes between its two sides, or a zig-zag fill that does not fuse.

## Likely causes, most common first
Overheating:
1. Layer printed too fast for it to cool: minimum layer time too short, or slowdown for layer cooling disabled. Typical with single small objects.
2. Not enough part cooling: fan too low for the material, or the part cooling fan not working (hardware).
3. Nozzle too hot for the speed actually used (small layers are slowed down, so they need less heat).
4. Outer walls excluded from the slowdown, or minimum print speed so high that the target layer time cannot be reached.
5. Enclosed printer with doors/lid closed while printing PLA or PETG: warm chamber, weak cooling.
6. Printer speed mode raised from the printer screen (Bambu Sport/Ludicrous) on a small model.

Missing features / thin-wall gaps:
1. Feature thinner than what the wall generator can print: Classic cannot place a closed loop narrower than its line width; Arachne skips features below the minimum feature size.
2. Wall thickness that is not a good multiple of the line width (Classic leaves a gap in the middle).
3. Negative X-Y contour compensation or large elephant-foot compensation shrinking thin features.
4. Nozzle too large for the detail (hardware).

## Questions worth asking (only when the answer changes the fix)
- Tools first: with an attached G-code, its analysis lists the layers at or below slow_down_layer_time; show_figure (layer_times) shows where they are.
- One small object alone on the plate, or many? (Printing several copies is the simplest overheating fix.)
- Is the feature missing in the slicer Preview, or only on the print?
- Which wall generator is active (Arachne or Classic)?
- Enclosed printer: door and lid open or closed during PLA/PETG?
- Does the part cooling fan spin at 100% when tested from the printer menu?

## Slicer fixes
Overheating (most effective and least risky first):

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `slow_down_for_layer_cooling` (filament) | set `1` | - | - | small layers print slower |
| `slow_down_layer_time` (filament) | increase (minimum layer time) | +2-4 s (e.g. 4 → 8 s for PLA) | 0-1000 s; large values make small parts very slow | longer print; very slow extrusion can cause heat creep |
| `fan_max_speed` (filament) | increase | +10-20% (PLA up to 100%) | 0-100%; keep moderate for ABS/ASA/PC | warping/cracking on ABS/ASA, weaker layer bonding on PETG |
| `fan_cooling_layer_time` (filament) | increase so the fan ramps up on more layers | +10-20 s | 0-1000 s | more cooling on medium layers |
| `slow_down_min_speed` (filament) | decrease so the layer time can actually be reached | to 10-20 mm/s | > 0; extremely low speeds risk heat creep | longer print |
| `dont_slow_down_outer_wall` (filament) | set `0` for small detailed parts | - | - | gloss may vary between layers (see defect-extrusion) |
| `nozzle_temperature` (filament) | decrease | -5 °C (max -10 °C) | inside the filament nozzle_temperature_range | under-extrusion and weaker layers if too cold |
| `small_perimeter_speed` (process) | decrease | 50% → 30-40% of outer wall | ≥ 1 mm/s | slower small loops |
| `small_perimeter_threshold` (process) | increase so more small loops are slowed | 0 → 5-10 mm radius | 0 disables | longer print |
| `outer_wall_speed` (process) | decrease on small models | -20-30% | machine limits | longer print |
| `additional_cooling_fan_speed` (filament) | increase on printers with an auxiliary part-cooling fan (Bambu H2, P and X series) | +10-20% | 0-100%; only works if the printer has and enables the auxiliary fan | warping on ABS/ASA, more noise |
| `reduce_fan_stop_start_freq` (filament) | `1` keeps the fan always on at least at minimum speed | - | not for ABS/ASA/PC | - |

Model-level fixes the AI should suggest in words: print 2+ copies or add a small sacrificial tower placed some centimetres away so each layer takes longer; keep `print_sequence` (process) = `by layer` (printing `by object` loses this benefit).

Missing small features:

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `wall_generator` (process) | `arachne` | - | - | Arachne can leave more seams or uneven walls on some models |
| `min_feature_size` (process) | decrease (Arachne) | 25% → 10-15% of nozzle | 0% = no filter | very thin features print poorly, strings/blobs |
| `min_bead_width` (process) | decrease slightly so widened thin features stay closer to size | 85% → 70-75% | keep ≥ ~50% | weaker, under-filled thin walls |
| `detect_thin_wall` (process) | `1` (Classic only; ignored with Arachne) | - | - | single open lines, overlaps, weak thin walls |
| `outer_wall_line_width` / `inner_wall_line_width` (process) | decrease so a narrow feature fits | to 90-100% of nozzle | ≥ 75% of nozzle | weaker walls, slower |
| `xy_contour_compensation` (process) | set to 0 if negative | - | - | parts may come out slightly larger |
| `only_one_wall_top` (process) | `1` for tiny top areas such as letters | - | - | - |

Gaps in thin walls:

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `wall_generator` (process) | `arachne` (adapts line width to the wall) | - | - | see above |
| `wall_transition_angle` (process) | increase if wedge-shaped walls leave a gap in the middle | +5° | 1-59° | more transitions, possible over-extrusion |
| `wall_transition_filter_deviation` (process) | decrease if transitions leave gaps; increase to reduce start/stops | ±5% | default 25% | over-extrusion or more travel |
| `wall_distribution_count` (process) | increase to spread width changes over more walls | 1 → 2-3 | ≥ 1 | outer wall width varies more |
| `outer_wall_line_width` / `inner_wall_line_width` (process) | make the wall a whole number of lines (e.g. 1.0 mm wall = 2 × 0.5 mm) | ±0.05 mm | 75%-150% of nozzle | more or less flow per line |
| `filter_out_gap_fill` (process, Classic wall gap fill) | lower so short gaps between walls are filled | towards 0 mm | - | more small moves |
| `filament_flow_ratio` (filament) | if walls are thin because of under-extrusion | see defect-extrusion | 0.8-1.2 | - |

## Checks the user must do by hand (hardware, material, printer settings)
- Part cooling fan: test it at 100% from the printer menu (Bambu: Device tab → part cooling fan). Not spinning, noisy or blocked duct = hardware fault (fan, cable, toolhead board); no setting fixes it.
- The part cooling duct on the toolhead must be fitted and unobstructed: it directs the air to the area around the nozzle.
- Auxiliary fan: only used if the printer setting `auxiliary_fan` is enabled in the printer preset (printer setting the user changes by hand).
- Enclosed printers with PLA/PETG: open the front door and/or lid; a warm chamber weakens cooling and can soften filament in the extruder.
- Bambu: do not raise the speed mode on the printer screen for small models; adjust speeds in the slicer.
- Detail finer than the nozzle: a smaller nozzle (e.g. 0.2-0.3 mm) is a hardware change, and the nozzle diameter in the printer preset must then be changed by the user. Otherwise thicken the features in CAD (wider than the nozzle diameter).
- For thin walls designed in CAD: two walls of 0.45 mm at 0.2 mm layers make about 0.86 mm, not 0.9 mm, because lines overlap; design to the slicer's line spacing.

## Calibration in Orca (menu Calibration → ...)
- **Temperature**: find the lowest temperature that still extrudes well at your speeds; small features prefer the cooler end.
- **Flow ratio**: thin walls depend on correct flow.
- No dedicated cooling test: verify in the Preview speed and layer-time views that small layers are slowed down; see calibration-guide.

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- **PLA**: needs as much cooling as possible; fan high, minimum layer time several seconds; most prone to melted tips.
- **PETG**: less fan than PLA; for small parts use longer layer time and the low end of its temperature range.
- **ABS/ASA**: little cooling; prefer longer layer time, copies on the plate or a cooling tower over a stronger fan (fan causes cracks and warping).
- **TPU**: some flexibles need little fan; rely on layer time; fine features are hard, thicken them.
- **PA/PC**: PC needs little fan; rely on layer time and lower speed for small parts.
- **CF**: fibres improve stiffness but need ≥ 0.4 mm hardened nozzles, so very fine details are often impossible (see material-composites).

## Sources
- https://wiki.bambulab.com/en/knowledge-sharing/melted-prints
- https://wiki.bambulab.com/en/software/bambu-studio/auto-cooling
- https://wiki.bambulab.com/en/software/bambu-studio/wall-generator
- https://wiki.bambulab.com/en/software/bambu-studio/WallGenerator
- https://wiki.bambulab.com/en/filament/pla
- https://wiki.bambulab.com/en/filament-acc/acc/fans
- https://help.prusa3d.com/article/cooling_127569
- https://help.prusa3d.com/article/arachne-perimeter-generator_352769
- https://help.prusa3d.com/article/layers-and-perimeters_1748
- https://help.prusa3d.com/article/petg_2059
- https://help.prusa3d.com/article/composite-materials-filled-with-carbon-kevlar-or-glass_167387
- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_generator.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_walls.html
- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_other_layers_speed.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_precision.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_infill.html
- https://www.simplify3d.com/resources/print-quality-troubleshooting/overheating/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/small-features-not-printed/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/gaps-in-thin-walls/
- https://www.matterhackers.com/articles/3d-printer-troubleshooting-guide
