---
name: defect-extrusion
description: Covers global or local under-extrusion, over-extrusion, inconsistent or bumpy extrusion, gaps between walls or between walls and infill, weak stringy infill and uneven gloss (shiny vs matte bands). Read when the user reports "under-extruding", "not enough plastic", "gaps between lines/walls", "holes in walls", "too much plastic", "overfilled/rough surface", "weak infill", "infill not touching walls", "missing material at corners" or "different shine/gloss".
---
# Extrusion problems (under, over, inconsistent, gloss)

## How to recognize it
- **Global under-extrusion**: thin separated lines everywhere; on a 3-wall cube the walls do not fuse at the top; fragile parts.
- **Local**: gaps only in fast infill/long lines, or only at corners and line starts (pressure advance).
- **Over-extrusion**: walls too wide, material piled near walls on top surfaces, rough overfilled look, nozzle dragging, parts too big.
- **Inconsistent**: one line changes width; random bumps or bands not linked to geometry.
- **Gaps between infill and walls**: infill not touching the inner wall; pinholes along edges.
- **Weak infill**: thin, stringy, broken lines.
- **Different gloss**: shiny vs matte zones where speed changes (overhang or layer-time slowdown).

## Likely causes, most common first
1. Resistance or partial clog: stuck spool, kinked/dirty PTFE tube, dirty or worn gears, wrong idler tension, debris in the nozzle (common after CF/GF). Sudden onset on a profile that used to work = almost always this.
2. Flow above what the hotend can melt (speed × line width × layer height): under-extruded fast infill, weak layers, matte patches.
3. Flow ratio wrong for this spool (differs by material, brand, even colour).
4. Pressure advance wrong: missing material at corners/line starts, or lines not touching after accelerations when far too high (Bambu: 0.25 typed instead of 0.025).
5. Nozzle temperature too low for the speed; steel/hardened nozzles need a bit more heat.
6. Wet filament, or poor filament with variable diameter.
7. Line width far below nozzle, extremely low layer height, too little infill/wall overlap, sparse infill too fast.
8. Gloss: big speed (flow) differences on the same outer surface.

## Questions worth asking (only when the answer changes the fix)
- Sudden (hardware) or always with this filament (profile)?
- Everywhere, only corners, only infill, only fast features?
- Vendor filament on its stock profile or third-party? Flow / pressure advance ever calibrated for this spool?
- Extruder clicking, ground filament, spool left out for days?
- Which nozzle (size, brass/hardened) is installed, and does the printer profile match?

## Slicer fixes
Fix hardware first (next section). Then, in this order:

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `filament_flow_ratio` (filament) | increase for gaps, decrease for overfill | ±0.02 (visual), or the result of the Orca flow test | 0.8-1.2; normal range 0.95-1.05 | masks hardware faults; Bambu filament: keep the profile default |
| `filament_max_volumetric_speed` (filament) | decrease when fast features under-extrude | -10% to -20% | lower freely; raise at most +10% | slows every fast feature, longer print |
| `nozzle_temperature` (filament) | increase if melt limit is reached at speed; decrease if overfilled and glossy-runny | +5 °C (max +10 °C) | inside the filament nozzle_temperature_range | stringing, overhang droop |
| `sparse_infill_speed` / `inner_wall_speed` / `internal_solid_infill_speed` (process) | decrease | -20% to -30% | never above machine limits | longer print |
| `pressure_advance` (filament, used when `enable_pressure_advance` = `1`) | set from calibration; lower if lines do not touch after accelerations | calibrated value only | typical 0.02-0.04 (fast direct drive); >0.1 almost never right | corner bulges or gaps if wrong |
| `infill_wall_overlap` (process) | increase for gaps between sparse infill and walls | 15% → 20-25% | ≤ 30% | rough surface from excess at wall junction |
| `top_bottom_infill_wall_overlap` (process) | increase for pinholes where solid infill meets walls | 25% → 30% | ≤ 35% | slight ridge at edges |
| `line_width`, `inner_wall_line_width`, `sparse_infill_line_width` (process) | raise if set below the nozzle diameter | to 100-115% of nozzle | 75%-150% of nozzle | more flow needed per mm |
| `layer_height` (process) | increase if very thin layers (≤0.08 mm) extrude unevenly or show "fish scale" at speed | to 0.12-0.20 mm | ≤ 75% of nozzle diameter | more visible layer lines |
| `set_other_flow_ratios` = `1` + `outer_wall_flow_ratio` / `inner_wall_flow_ratio` / `sparse_infill_flow_ratio` (process) — BY HAND | per-feature tuning once filament flow is right | ±0.02-0.05 | by hand only (plugin cannot check it), keep 0.8-1.2; Process → Quality → Wall and surfaces, see defect-triage | can mask a wrong filament flow |

**Weak infill**: lower `sparse_infill_speed` (up to -50% to test); `sparse_infill_line_width` ~115% of nozzle; `fill_multiline` (process) 2 for stronger infill at the same density; raise `sparse_infill_density` (process) in 5-10% steps; prefer `gyroid` or `cubic` for `sparse_infill_pattern` (process) on mechanical parts. Strength comes mainly from walls: `wall_loops` (process) +1. If `infill_combination` (process) = `1`, disable it (thicker combined infill layers need more flow). Do not set `infill_anchor_max` (process) to 0 (PETG especially benefits from anchors).

**Gaps where a smaller section starts on a larger one (floor corners)**: `wall_loops` +1-2, `top_shell_layers` (process) +1-2, `sparse_infill_density` +10%.

**Different gloss**: keep outer wall speed uniform.
- `outer_wall_speed` (process) lower, towards the slowest speed in the Preview speed view (worst case: match bridge speed). On small models lower all speeds.
- `dont_slow_down_outer_wall` (filament) = `1` keeps outer walls out of the layer-time slowdown (silk PLA, PETG); small layers then cool less.
- `enable_overhang_speed` (process) = `0` removes overhang slowdowns; only if the model has mild overhangs (worse overhangs otherwise).
- `max_volumetric_extrusion_rate_slope` (process): 300-350 mm³/s² on fast direct-drive printers with pressure advance; 10-15 (direct drive) or 5-10 (Bowden) on slow printers without PA. Disables arc fitting.
- Fish-scale gloss at 0.08 mm and high speed: raise `layer_height` to 0.16 mm, or slow outer wall 20-30% and add +5-10 °C within range.
- Print several objects together to avoid layer-time slowdowns.

## Checks the user must do by hand (hardware, material, printer settings)
- Spool turns freely; PTFE tube free of kinks, wear, debris.
- Extruder gears clean and not worn, idler tension correct. Clean before any flow calibration or the result is wrong.
- Partial clog: manual extrusion must give a straight, even strand; else cold pull or new nozzle (see defect-clogs-heat-creep).
- Nozzle seated and tight. Prusa Nextruder (CORE One, MK4/S, MK3.9/S): nozzle pushed fully up, thumb screws hand-tight; after opening the gearbox cover run the gearbox alignment. XL: check the nozzle tube for dents. Bambu H2/A1/P2S: hotend clip and magnet seated, no wobble; X1/P1: nozzle fastening screws tight. A loose hotend causes random layer lines.
- Installed nozzle matches the nozzle diameter in the printer profile (printer setting the user changes by hand); a mismatch gives systematically wrong flow.
- Hardened or stainless nozzles often need +5-10 °C compared to brass.
- First layer not set too close (Z offset is a printer setting the user adjusts by hand); a squashed first layer can choke extrusion.
- Hotend heatsink fan working; PLA in a closed enclosure (Prusa: room above ~27 °C) can soften early and under-extrude.
- Dry filament that pops or hisses (PETG, PA, TPU, PC most sensitive). Diameter should be 1.75 ± 0.02-0.05 mm; try a known-good spool.
- When switching material, load the new filament at the higher temperature of the previous one.
- Bambu: Sport/Ludicrous on the printer screen raise flow without more heat; change speeds in the slicer instead.

## Calibration in Orca (menu Calibration → ...)
- **Temperature**: temp tower; for high speed use the upper part of the good range.
- **Flow ratio**: YOLO (recommended): smoothest block without gaps, new `filament_flow_ratio` = old ± modifier (Pass 1/2: old × (100 + modifier) / 100). Bambu: do not tick the printer's own "Flow calibration" when sending Orca tests.
- **Pressure advance**: tower, pattern or line; save to `pressure_advance`. Bambu: Flow Dynamics calibration does the same job.
- **Max flowrate**: note heights where gloss is lost, walls deform, extrusion fails; flow = start + height × step. Set `filament_max_volumetric_speed` 10-20% below the deformation point. For uniform gloss keep outer wall flow (layer height × line width × speed) under the gloss-loss value.
- Order and reading: see calibration-guide.

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- Typical max volumetric speed on standard hotends (always calibrate): PLA 12-20, PETG 8-15, ABS/ASA 10-16, TPU 2-5, PC 6-10, PA 8-12 mm³/s. Standard V6-class hotend 8-12, Nextruder 15-20, high-flow hotends 20-40 mm³/s.
- **PLA**: easiest to melt; silk PLA shows gloss changes strongly, keep outer walls slow and uniform (about 40-60 mm/s).
- **PETG**: viscous, sticks to the nozzle, needs lower flow; moisture sensitive.
- **ABS/ASA**: melt slower than PLA; under-extrude at PLA speeds.
- **TPU**: buckles if pushed; lowest flow; simple infill (`grid`); see material-tpu.
- **PA/PC**: viscous, hygroscopic; dry before diagnosing.
- **CF/GF, wood/metal fills**: wear brass and clog fine nozzles; hardened ≥0.4 mm (wood often ≥0.6 mm); see material-composites.

## Sources
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/under-extrusion
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/different-gloss
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/severe-layer-artifacts
- https://wiki.bambulab.com/en/knowledge-sharing/volumetric-speed
- https://wiki.bambulab.com/en/knowledge-sharing/common-print-quality-problem
- https://wiki.bambulab.com/en/knowledge-sharing/lines-not-connected
- https://wiki.bambulab.com/en/software/bambu-studio/parameter/line-width
- https://wiki.bambulab.com/en/filament/pla
- https://help.prusa3d.com/article/under-extrusion_2007
- https://help.prusa3d.com/article/under-extrusion-nextruder-printers_821253
- https://help.prusa3d.com/article/extrusion-multiplier-calibration_2257
- https://help.prusa3d.com/article/max-volumetric-speed_127176
- https://help.prusa3d.com/article/problems-with-infill_1994
- https://help.prusa3d.com/article/infill_42
- https://help.prusa3d.com/article/infill-patterns_177130
- https://www.orcaslicer.com/wiki/calibration/flow_ratio_calib.html
- https://www.orcaslicer.com/wiki/calibration/volumetric_speed_calib.html
- https://www.orcaslicer.com/wiki/calibration/pressure_advance_calib.html
- https://www.orcaslicer.com/wiki/material_settings/filament/material_flow_ratio_and_pressure_advance.html
- https://www.orcaslicer.com/wiki/material_settings/filament/material_volumetric_speed_limitation.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_line_width.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_infill.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html
- https://www.simplify3d.com/resources/print-quality-troubleshooting/under-extrusion/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/inconsistent-extrusion/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/weak-infill/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/gaps-between-infill-and-outline/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/gaps-in-floor-corners/
