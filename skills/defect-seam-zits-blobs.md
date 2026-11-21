---
name: defect-seam-zits-blobs
description: Visible Z seam, zits, pimples, blobs and bulges or dents at the start/end of wall loops: seam position, seam gap, scarf joint seam, wipe options, wall order, pressure advance, retraction at the seam, random dots from wet filament. Read when the user reports a visible seam, seam line, Z seam, zipper, zits, pimples, dots, bumps or blobs on the walls, a gap or dent at the seam, or asks about scarf seam or wipe.
---
# Seam, zits and blobs

## How to recognize it
- **Seam line**: a vertical line of small bumps or a slight groove where each wall loop starts and ends. Unavoidable in FDM (except spiral vase); goal is to hide it or make it clean. Most visible on cylinders and smooth curves without corners.
- **Bulge/blob at the seam end**: wider line where the loop closes → nozzle still pressurized (pressure advance too low, flow too high, seam gap too small).
- **Blob at the seam start**: material oozed or was over-primed after travel/deretraction.
- **Gap or dent at the seam**: pressure advance too high, seam gap too large, too much retraction or ooze lost during travel.
- **Zits scattered over the whole surface**: seam position `random`, or wet filament (steam bursts; often with popping and stringing).
- **Larger blobs at random places**: material accumulated on the nozzle and dropped off (often PETG, see defect-clogs-heat-creep), or travel crossing walls.
- Tip from Simplify3D's method: watch an outer wall print. Defect appears as the loop starts → priming/ooze problem; appears as the loop ends → pressure/coasting problem.

## Likely causes, most common first
1. Seam placement: `random` or `nearest` on smooth/visible faces; no corner to hide the seam.
2. Pressure advance not calibrated (too low → bulge at end; too high → gap at end).
3. Ooze during travel before the outer wall starts: slow travel, long travel, outer wall printed first after a long move, retraction weak or extra restart too high.
4. Over-extrusion (flow ratio too high).
5. Wet filament (random dots/zits).
6. Wall order outer-first (`outer wall/inner wall`) puts the outer wall straight after a travel.
7. Hardware: high-flow/volcano or CHT-type nozzles and larger nozzle diameters have poorer extrusion control at seams; mechanical tolerance (belts, toolhead rigidity) when stopping.

## Questions worth asking (only when the answer changes the fix)
- Is the defect a line in one place, or dots everywhere? (line → seam settings; everywhere → seam position or moisture)
- Bulge, blob or gap/dent? At start or end of the loop?
- Does the model have a back side or a corner where the seam can hide?
- Pressure advance calibrated for this filament? Standard or high-flow nozzle?
- Cosmetic only, or does the part need strength at the seam?

## Slicer fixes
| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `seam_position` (process) | `aligned`, `aligned_back` or `back` (from `random`/`nearest`) | - | - | aligned line instead of scattered zits; `random` only for strength (pins, round parts) |
| `pressure_advance` (filament) + `enable_pressure_advance` (filament) | set calibrated value | from PA calibration | 0-2, use the calibrated value | wrong value moves the defect to corners |
| `seam_gap` (process) | bulge: increase; visible gap: decrease | ±5 % of nozzle | ≥ 0; 0-15 % typical on a tuned printer (default 10 %) | larger gap can leave a hole in the loop |
| `wall_sequence` (process) | `inner-outer-inner wall` (best) or `inner wall/outer wall` | - | - | IOI needs 3+ walls and lowers overhang quality |
| `wipe_before_external_loop` (process) | enable `1` | - | useful with outer/inner or inner-outer-inner order | small inward deretraction move |
| `wipe_on_loops` (process) | enable `1` | - | needs 2+ walls | tucks the loop end inward |
| `role_based_wipe_speed` (process) | enable `1` | - | - | otherwise `wipe_speed` (process) applies, % of travel speed |
| `wipe_inward` (process) | enable `1` | `wipe_inward_distance` 50 % | needs `filament_wipe` = `1`, 2+ walls and inner walls printed first | falls back to normal wipe where no room |
| `filament_wipe` (filament) | enable `1` | `filament_wipe_distance` 1-2 mm | ≥ 0 | - |
| `seam_slope_type` (process) | `external` (contour) or `all` (contour and holes) | - | beta; not used on first layer or spiral vase | slight time increase; less effective on sharp corners/overhangs |
| `seam_slope_conditional` (process) | enable `1` with scarf | `scarf_angle_threshold` default 155 | - | scarf only on smooth loops; corners keep a normal seam |
| `scarf_joint_speed` (process) | lower | e.g. 100 % → 50-80 % of wall speed | keep < 100 mm/s | slower walls |
| `seam_slope_min_length` (process) | default 20 mm | ±5 mm | 0 disables scarf | - |
| `travel_speed` (process) | increase | +20-50 mm/s | never above machine limits | ringing; also raise `travel_acceleration` (process) within limits |
| `filament_retraction_minimum_travel` (filament) | increase for seams | 2-4 mm | ≥ 0 | fewer retract/deretract cycles before the outer wall; may add strings across small gaps |
| `filament_retract_when_changing_layer` (filament) | enable `1` | - | - | each layer starts depressurized |
| `filament_flow_ratio` (filament) | decrease if over-extruding | -0.01 to -0.02 | 0.8-1.2 | under-extrusion if too low |
| `filament_retract_restart_extra` (filament) — BY HAND | small negative only for a blob at loop start | -0.02 to -0.05 mm | by hand only (plugin cannot check it), keep within ±0.1 mm: Filament → Setting overrides → Retraction → Extra length on restart; `nil` = printer value | gap at seam start if overdone |
| `outer_wall_speed` (process) | decrease | -10-20 % | ≥ 1 mm/s | longer print |
| `staggered_inner_seams` (process) | enable `1` for strength/watertightness | - | - | does not hide the outer seam |
| `spiral_mode` (process) | `1` only for single-wall vases | - | one wall, no infill/top | no seam on walls at all |

Order of attack: seam position/painting → pressure advance → seam gap → wall order and wipe options → scarf seam → travel/retraction details. Two valid strategies (Orca wiki): hide the seam (scarf seam on smooth models) or make it small and consistent (seam gap, role based wipe speed, wipe on loops, wipe inward, wipe before external loop). Wipe options make the seam more consistent, not invisible.

Seam vs stringing conflict: a higher travel distance threshold helps seams but may add strings across small gaps; if both defects exist, fix stringing first (see defect-stringing), then raise the threshold only if strings stay away.

## Checks the user must do by hand (hardware, material, printer settings)
- **Seam painting**: with Orca's Seam painting tool, paint seam enforcers/blockers on the model to put the seam on an edge or the back. Newer Orca builds also offer Precise Seam modifiers (right-click object → Add Precise Seam) that pin the seam to a point or zone and survive model edits; the plugin cannot paint, the user must.
- Orient the model so a corner or the back faces where the seam goes; fewer objects per plate means less travel before outer walls.
- **Dry the filament** if zits are random and the nozzle pops (see materials-overview).
- **Nozzle**: high-flow/volcano nozzles and large diameters give worse seams; a 0.2-0.4 mm standard nozzle gives the cleanest seams. Replace worn nozzles.
- **Printer retraction (printer settings, user changes by hand)**: Printer settings → Extruder → Retraction (length, wipe, retract amount before wipe). Explain; the plugin only uses filament overrides.
- Belts and toolhead rigidity: loose belts make the loop end inconsistent.

## Calibration in Orca (menu Calibration → ...)
1. **Pressure Advance** (first): look at corners and seams of the test; save into the filament preset. For high-speed printers consider adaptive pressure advance.
2. **Flow ratio**: if walls look overfilled.
3. **Retraction test**: shortest clean length into `filament_retraction_length`.
4. Then adjust `seam_gap` in small steps. See calibration-guide.

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- **PLA**: best seams once pressure advance is tuned; zits usually seam position or moisture.
- **PETG**: oozes, so blobs at seams and material dropping from the nozzle are common: flow 0.93-0.96, a bit lower temperature, wipe enabled, dry spool.
- **ABS/ASA**: seams generally clean; check pressure advance and flow.
- **TPU**: little retraction possible; rely on seam position, slow outer walls and pressure advance; dry it.
- **PA/PC**: moisture causes random zits; dry before printing.
- **CF/GF filled**: abrasive fill wears brass nozzles and a worn nozzle oozes more and gives worse seams; use a hardened nozzle and check wear.

## Sources
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_seam.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html
- https://www.orcaslicer.com/wiki/print_prepare/prepare_precise_seam.html
- https://www.orcaslicer.com/wiki/print_prepare/prepare_seam_painting.html
- https://www.orcaslicer.com/wiki/printer_settings/extruder/printer_extruder_retraction.html
- https://www.orcaslicer.com/wiki/calibration/pressure_advance_calib.html
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/seam
- https://wiki.bambulab.com/en/software/bambu-studio/Seam
- https://wiki.bambulab.com/en/knowledge-sharing/dots-on-the-print
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/filament-sticks-to-nozzle
- https://help.prusa3d.com/article/seam-position_151069
- https://help.prusa3d.com/article/seam-painting_168620
- https://help.prusa3d.com/article/drying-filament_332086
- https://www.simplify3d.com/resources/print-quality-troubleshooting/blobs-and-zits/
- https://www.obico.io/blog/3d-print-troubleshooting-guide/
