---
name: defect-top-surface
description: Covers top-surface defects: pillowing, holes or gaps in the top layers, pinholes along the walls, ridges and overfilled tops, scars or scratches from the nozzle, visible lines or uneven texture on top, and ironing setup and ironing problems. Read when the user reports "pillowing", "holes on top", "top layer not closed", "gaps in top layer", "bumpy top", "scratches/scars on top", "lines on the top surface", "rough top" or asks about "ironing".
---
# Top surface defects and ironing

## How to recognize it
- **Pillowing**: bumps, sagging lines or small holes on the top surface, often in a grid matching the infill cells below; worse on thin top shells, low infill, thin layers and curved or sloped tops.
- **Gaps in top layers**: top lines do not touch each other (under-extrusion) or pinholes stay where the top infill meets the walls.
- **Overfilled top**: ridges, material piled along the walls, rough or wavy surface; the nozzle can drag excess plastic.
- **Scars / scratches**: grooves or smears along travel paths across finished top layers.
- **Lines or uneven texture**: ridges where zig-zag lines change direction, different sheen between areas, visible infill pattern through a thin top.
- **Ironing problems**: shiny unironed grooves (ironing flow too low), plastic pushed to the edges (too high), fuzzy edges, part knocked off, clog during ironing.

## Likely causes, most common first
1. Top shell too thin for the layer height: few top layers bridge over sparse infill and sag. Aim for about 0.8-1.0 mm of solid top (e.g. 4-5 layers at 0.2 mm, 8-9 at 0.1 mm).
2. Sparse infill too sparse for the top to bridge on (low density, wide-cell pattern).
3. Under-extrusion (flow ratio, partial clog, dirty extruder): even slight under-extrusion is visible on top. See defect-extrusion.
4. Over-extrusion: ridges at the walls and nozzle dragging (scars).
5. Sloped or curved tops: small internal bridges are filtered out by default, so solid infill curls over unsupported spots and pillows.
6. Travel over finished top layers without Z-hop.
7. Top surface printed too fast or with high acceleration; rectilinear top pattern.
8. Wrong pressure advance: bulges or thin starts at each line end near the walls.

## Questions worth asking (only when the answer changes the fix)
- Holes/bumps everywhere on top, only near the walls, or only on curved/sloped areas?
- Layer height, top shell layers and infill density in use (read them from the process preset).
- Scratches: do they follow travel moves between parts or islands?
- Is the top surface flat (ironing helps) or curved (ironing is useless there)?
- Was flow calibrated for this spool?

## Slicer fixes
Pillowing / holes (most effective and least risky first):

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `top_shell_layers` (process) | increase | +1-2 layers | about 0.8-1.0 mm total top thickness is enough for most prints | more time and material |
| `top_shell_thickness` (process) | increase (adds layers automatically at thin layer heights) | 0.6 → 0.8-1.0 mm | 0 disables it | more time and material |
| `sparse_infill_density` (process) | increase | +5-10% (e.g. 15% → 20-25%) | rarely needed above 30-40% for top support | heavier part, longer print |
| `dont_filter_internal_bridges` (process) | `limited` for sloped or curved tops; `nofilter` only for heavily sloped tops | one enum step | default `disabled` = filter | extra internal bridges, more time |
| `thick_internal_bridges` (process) | keep `1` (default) when printing over sparse infill | - | - | slightly worse look of internal bridges, more reliable support |
| `top_surface_speed` (process) | decrease | -20-30% | machine limits | longer print |
| `top_surface_acceleration` (process) | decrease | -20-30% | machine limits | longer print |
| `top_bottom_infill_wall_overlap` (process) | increase for pinholes along walls | 25% → 30% | ≤ 35% | small ridge at the edge |
| `filament_flow_ratio` (filament) | increase if top lines do not touch | +0.02 or calibrate | 0.8-1.2 | over-extrusion elsewhere if overdone |
| `top_surface_expansion` (process) | increase when the top is interrupted by raised text or bosses leaving holes around them | 1-5 mm | 0 disables | may reach the walls and leave a hull line; `top_surface_expansion_margin` keeps distance |

Overfilled top, ridges, lines:

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `filament_flow_ratio` (filament) | decrease if the whole print is overfilled | -0.02 or calibrate | 0.8-1.2 | under-extrusion if overdone |
| `top_solid_infill_flow_ratio` (process) — BY HAND | decrease if only the top is overfilled | 1.0 → 0.95-0.98 | by hand only (plugin cannot check it), keep 0.8-1.2; Process → Quality → Wall and surfaces → Surface flow ratio, see defect-triage | gaps if too low |
| `top_surface_pattern` (process) | `monotonicline` (default) or `monotonic` instead of `rectilinear`; `concentric` or `archimedeanchords` for round tops | - | - | concentric/spiral patterns take longer |
| `top_surface_line_width` (process) | 100-105% of nozzle | - | ≤ 150% of nozzle; below 100% bonds worse | narrower = slower |
| `only_one_wall_top` (process) | `1` for small tops such as letters, so the pattern covers them | - | - | slightly weaker top edge |
| `small_area_infill_flow_compensation` (process) | `1` (beta) for overfilled small solid areas | - | only with rectilinear, aligned rectilinear, monotonic, monotonic line patterns | uses the compensation model; experimental |

Scars from travel:

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| fix over-extrusion first | - | - | - | - |
| `filament_z_hop` (filament) | increase | 0.2-0.4 mm | 0-2 mm; `nil` = printer value | slightly more stringing, longer travels |
| `filament_retract_lift_enforce` (filament) | `Top Only` to lift only over top surfaces | - | `nil` = printer value | - |

### Ironing (flat tops only)
Ironing reruns the nozzle over the last top layer with a tiny flow at the same height. It only works on flat, horizontal surfaces; on curved or organic shapes it adds time for no benefit. Calibrate flow first: ironing is very sensitive to it.

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `ironing_type` (process) | `top` (all top surfaces) or `topmost` (last layer only); `solid` only for clearer translucent parts | - | default `no ironing` | much longer print, mostly with `solid` |
| `ironing_flow` (process) | increase if unironed grooves remain; decrease if plastic piles at edges | ±2% from the default 10% | keep small; thinner layers may need a bit more | over-extruded, rough surface if too high |
| `ironing_spacing` (process) | decrease for smoother finish | 0.1 mm default | ≤ nozzle diameter | longer ironing |
| `ironing_speed` (process) | decrease | default 20 mm/s | slower = better | longer print, more heat-creep risk |
| `ironing_inset` (process) | increase if edges build up | +0.1-0.2 mm | 0 = half the nozzle diameter | edges stay unironed |
| `ironing_pattern` (process) | `concentric` for round or rounded tops | - | - | - |
| `ironing_angle` (process) | offset to the top infill direction (45 is a common good choice) | - | 0-359 | - |
| `ironing_fan_speed` (filament) | lower than normal to reduce clogging at the low flow | - | -1 disables | - |

Per-filament overrides exist: `filament_ironing_flow`, `filament_ironing_spacing`, `filament_ironing_inset`, `filament_ironing_speed` (filament). Alternative to ironing: print the flat face down on the plate; the bottom face is usually smoother than an ironed top.

## Checks the user must do by hand (hardware, material, printer settings)
- Partial clog, dirty extruder gears or filament path drag cause top gaps and falsify any flow test: clean before calibrating (see defect-clogs-heat-creep).
- The nozzle installed must match the nozzle diameter of the printer profile (printer setting the user changes by hand); a mismatch gives wrong top flow.
- Printer Z-hop height and lift rules are printer settings; the AI may only use the filament overrides above.
- Ironing pushes on the part: make sure the part is well stuck to the plate (clean plate, brim if needed).
- Ironing and heat creep: low, slow flow can clog, mainly PLA in hot rooms or enclosed printers with doors closed. Check hotend cooling; open the door/lid for PLA on enclosed printers.
- Wet filament gives rough, bubbly tops; dry it.

## Calibration in Orca (menu Calibration → ...)
- **Flow ratio** (YOLO recommended): the blocks are judged on the top surface, smoothest without gaps; exactly the criterion for this defect.
- **Pressure advance**: for bulges or thin spots at line ends near walls.
- **Temperature**: if tops are rough or dull at the chosen speed.
- See calibration-guide for order and reading.

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- **PLA**: pillowing is most frequent with PLA; more top layers, more infill and slower top speed help. Irons very well but is the most heat-creep prone during ironing (summer, closed enclosure). Silk PLA: `archimedeanchords` top pattern gives more luster.
- **PETG**: irons well but excess plastic sticks to the nozzle, darkens and can drop on the part; keep nozzle clean, moderate ironing flow.
- **ABS/ASA**: ASA irons very well, giving very smooth tops.
- **TPU**: avoid ironing; strong buildup on the nozzle and clog risk.
- **PA/PC**: dry the filament first; moisture shows as rough, pitted tops.
- **CF and wood fills**: wood-filled filaments iron poorly (Prusa). For CF/GF see material-composites.

## Sources
- https://wiki.bambulab.com/en/knowledge-sharing/common-print-quality-problem
- https://wiki.bambulab.com/en/software/bambu-studio/parameter/ironing
- https://wiki.bambulab.com/en/filament/pla
- https://help.prusa3d.com/article/ironing_177488
- https://help.prusa3d.com/article/layers-and-perimeters_1748
- https://help.prusa3d.com/article/infill-patterns_177130
- https://help.prusa3d.com/article/extrusion-multiplier-calibration_2257
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_ironing.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_top_bottom_shells.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_bridging.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_line_width.html
- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html
- https://www.orcaslicer.com/wiki/calibration/flow_ratio_calib.html
- https://www.simplify3d.com/resources/print-quality-troubleshooting/gaps-in-top-layers/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/scars-on-top-surface/
- https://www.matterhackers.com/articles/3d-printer-troubleshooting-guide
- https://www.obico.io/blog/3d-print-troubleshooting-guide/
