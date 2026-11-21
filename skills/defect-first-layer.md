---
name: defect-first-layer
description: First layer problems: filament not sticking, lines dragged or peeling, gaps between lines, lines too squished with ridges, uneven first layer across the bed, elephant foot (flared base), parts stuck too hard to remove. Read when the user reports the first layer not sticking, bad bed adhesion, gaps or ridges in the first layer, nozzle scraping the plate, elephant foot, or a print that will not come off.
---
# First layer: not sticking, too squished, gaps, ridges, elephant foot, too stuck

## How to recognize it
- Good first layer: flat, even lines that just merge, no gaps or ridges, same look over the whole plate; small flaws on 5-10% of the area are normal.
- Nozzle too high: round, thin or wavy lines, gaps between lines, lines that drag or curl, parts loose mid print, blobs/spaghetti.
- Nozzle too low: lines flattened to a thin, see-through film, ridges between lines, rough or overflowing surface, edges curling up, nozzle scraping, little or no extrusion on layer 1 (can clog).
- Good in some spots, bad in others: fingerprints/residue (patchy) or levelling/uneven plate (one side or one zone differs).
- Lines not touching each other or the wall although Z looks right: pressure advance (K) far too high, or under-extrusion.
- Elephant foot: the bottom 1-3 layers are wider than the walls above (a lip at the base). As a fit/tolerance issue also see defect-dimensional-accuracy.
- Too stuck: the part cannot be removed, PEI tears or chips.
- Corners lifting later in the print: defect-warping.

## Likely causes, most common first
1. Dirty plate (skin oil, dust, old glue).
2. Nozzle-to-plate distance wrong (Z offset / Live Z / levelling stale or skipped).
3. Wrong plate type selected in Orca: wrong bed temperature; Bambu Textured PEI also loses its automatic 0.04 mm lower offset.
4. Bed temperature too low (not sticking) or too high (elephant foot, too stuck, PLA heat creep).
5. First layer printed too fast; part fan on during the first layers.
6. Flow too low or too high (uncalibrated flow ratio), partial clog, dirty nozzle tip, wet filament.
7. Mechanical: nozzle/hotend loose or set at the wrong height, plate not seated or debris under it, worn plate coating.
8. Too stuck: PETG/TPU on smooth PEI without glue, bed too hot, nozzle too low.

## Questions worth asking (only when the answer changes the fix)
- A top-down photo of the first layer or of a one-layer test square.
- Which plate is on the printer, which plate type is set in Orca, glue? When was it last washed?
- Did this combination work before; what changed (plate, nozzle, printer moved)? Levelling enabled at start? Where on the plate is it bad?
- For too stuck: material, plate, did they wait for the plate to cool?

## Slicer fixes
Bed temperature: change only the _initial_layer key of the plate in use (filament): `textured_plate_temp_initial_layer`, `hot_plate_temp_initial_layer`, `cool_plate_temp_initial_layer`, `textured_cool_plate_temp_initial_layer`, `eng_plate_temp_initial_layer`, `supertack_plate_temp_initial_layer`.

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `initial_layer_speed` (process) | decrease (not sticking) | -25%, e.g. 30 mm/s for walls | never above printer limits | slower first layer |
| `initial_layer_infill_speed` (process) | decrease (not sticking) | -25%, e.g. 60 mm/s | never above printer limits | slower first layer |
| `close_fan_the_first_x_layers` (filament) | increase | to 1-3 | ≤ 5 layers | - |
| plate _initial_layer temp (filament) | not sticking: increase; elephant foot / too stuck: decrease | ±5 °C | ≤ +10 °C over current, never above 120 °C | hotter: elephant foot, PLA heat creep |
| `initial_layer_print_height` (process) | increase for uneven or textured plates | to 0.25 mm on a 0.4 mm nozzle | ≤ 65% of nozzle recommended, hard limit 75%, min 0.1 mm | user may need to re-check Z/Live Z |
| `initial_layer_line_width` (process) | increase | to 0.5 mm on a 0.4 mm nozzle | ≤ 0.6 mm on a 0.4 mm nozzle | wider first-layer footprint |
| `nozzle_temperature_initial_layer` (filament) | increase (not sticking) | +5 °C | inside nozzle_temperature_range_low..high | stringing, elephant foot |
| `first_layer_flow_ratio` (process) — BY HAND | gaps: increase; ridges/overflow: decrease | ±0.02-0.05 | by hand only (plugin cannot check it), keep 0.9-1.1; Process → Quality → Wall and surfaces, see defect-triage | needs `set_other_flow_ratios` = `1`; does not fix wrong Z |
| `initial_layer_acceleration` (process) | decrease | -25% | never above printer limits | slower first layer |
| `brim_type` / `brim_width` (process) | small footprints: `outer_only`, 3-5 mm | - | ≤ 18 mm | brim removal |
| `elefant_foot_compensation` (process) | increase (elephant foot) | 0.1-0.2 mm on a 0.4 mm nozzle | ≤ 0.3 mm | brim may print detached; thin first-layer features shrink |
| `elefant_foot_compensation_layers` (process) | increase | 1 → 2-3 | - | - |
| `raft_layers` (process) | 0 → 2-3 for worn/uneven plates or tiny contact | - | 2-4 | rough bottom, time; disables elephant foot compensation |
| `pressure_advance` (filament) | if lines do not touch and value looks 10× too high | recalibrate, do not guess | Bambu: typical 0.02-0.04, > 0.05 rare | only active with `enable_pressure_advance` = `1` |

Notes for the AI:
- First decide from the photo if the nozzle is too high or too low. Z is a hardware matter: explain it, never fake it with flow or temperature.
- Bed and speed first, line width/height next, flow last. Calibrate `filament_flow_ratio` (filament) before touching `first_layer_flow_ratio` (by hand, see the table).
- Elephant foot: lower the first-layer bed temperature 5 °C, then add compensation. A raft disables it.
- Too stuck: lower the _initial_layer plate temperature 5 °C and give the hand checks below.

## Checks the user must do by hand (hardware, material, printer settings)
- Clean the plate. Bambu textured/smooth PEI: warm water and dish soap with a sponge or soft brush, rinse, dry, do not touch the surface. Prusa: IPA 90%+ on the cold sheet with an unscented towel; dish soap + warm water if IPA stops working; acetone about once a month on smooth PEI only (not on textured/satin sheets, never before PETG). SuperTack: soap and water, no acetone or strong solvents, no stiff brush.
- Plate type in Orca must match the plate on the printer (selector in the Prepare tab). The AI cannot change it.
- Bed levelling: run it after moving the printer or maintenance; keep levelling enabled at print start (Bambu). Clean the nozzle tip first.
- Nozzle height. Bambu: re-run levelling; some newer models offer Calibration → First Layer Calibration on the screen in 0.01 mm steps (negative = closer). Prusa MK3/MINI: Live Adjust Z during the first layer or First Layer Calibration from the LCD; one value per sheet type (Steel sheet profiles). Prusa MK4/CORE One/XL (load cell): automatic; long-press the knob to fine-tune (not saved). Do not over-squish to fix adhesion: it damages the sheet and can clog.
- Printer setting, changed only by the user by hand: `z_offset` in the printer preset (negative = closer). Only if the printer has no Live Z or first-layer calibration; 0.01-0.02 mm steps. The plugin never edits it.
- Hardware. Bambu X1/P1: hotend screws tight, hotend straight. A1/H2/P2S: nozzle buckle locked; A1: loose heater-assembly screws give wrong probing. Prusa Nextruder: nozzle fully up, expansion joints facing the carriage centre, Loadcell test.
- Plate seated flat, nothing under it, not bent. Worn coating: use the other side or replace.
- Glue: needed on the Bambu Engineering Plate and smooth PEI for non-PLA; thin layer on cold plate. As release layer it also fixes too stuck PETG/TPU/PC.
- Too stuck: let the plate cool (Bambu PEI: ≤ 35 °C) and flex it. SuperTack: reheat to about 50 °C or wet the edge with alcohol, then scrape.
- Partial clog or dirty nozzle: cold pull (defect-clogs-heat-creep). Wet filament: dry it.
- Test: a one-layer 0.2 mm square over most of the plate. Gaps = too high or under-extrusion; ridges = too low or flow too high; patches = dirty; one zone different = levelling or debris.

## Calibration in Orca (menu Calibration → ...)
- Nozzle height is calibrated on the printer, not in Orca.
- Calibration → Flow ratio: when gaps or ridges remain with correct Z; result goes to `filament_flow_ratio` (filament).
- Calibration → Pressure advance: when lines do not touch each other or the walls; result to `pressure_advance` (filament). Bambu printers can use their own Flow Dynamics calibration.
- Elephant foot value (Bambu method): print a 25×25×10 mm cube with `elefant_foot_compensation` = 0 and `brim_type` = `no_brim`, let it cool, measure the bottom and the top in X and Y with calipers at mid-side; average the two (bottom - top) differences and enter it. Different plates need different values. See calibration-guide.

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- PLA: easy. Bambu Textured PEI 55-65 °C, SuperTack works from about 40 °C, old Cool Plate needs glue. On textured sheets the nozzle must be a bit closer to fill the texture; small PLA parts on textured may need a brim (Prusa).
- PETG: bonds too strongly to smooth PEI (tears it): glue or textured sheet. Prusa: bed 85/90 °C, nozzle 230/240 °C (first/other layers); a little more squish than PLA.
- ABS/ASA: bed 90-110 °C, part fan off for the first layers, glue on PEI.
- TPU: textured sheet without glue; on smooth PEI use glue (too strong bond). Never on SuperTack. Print slowly.
- PA/PC: glue on PEI; PA sticks poorly to standard PEI (Prusa PA Nylon sheet). Dry the filament first.
- CF/GF: a bad first layer easily clogs; use at least a 0.4 mm nozzle and 0.2 mm first layer (Prusa). Bambu: glue stick for PA-CF/GF, PET-CF, ASA-CF.
- SuperTack: Bambu PLA Silk sticks too hard; Support for PLA/PETG must not touch it (2+ raft layers).

## Sources
- https://wiki.bambulab.com/en/knowledge-sharing/first-layer-not-sticking
- https://wiki.bambulab.com/en/knowledge-sharing/identify-and-fix-first-layer-issues-with-a-test-print
- https://wiki.bambulab.com/en/knowledge-sharing/lines-not-connected
- https://wiki.bambulab.com/en/x1/troubleshooting/first-layer-printing-optimization-guide
- https://wiki.bambulab.com/en/h3c/troubleshooting/first-layer-quality-calibration
- https://wiki.bambulab.com/en/general/textured-PEI-plate-not-working-as-expected
- https://wiki.bambulab.com/en/filament-acc/acc/plates
- https://wiki.bambulab.com/en/filament-acc/acc/bambu-cool-plate-supertack
- https://wiki.bambulab.com/en/PLA/PETG-with-bambu-bool-plate-supertack
- https://wiki.bambulab.com/en/filament-acc/acc/pei-plate-clean-guide
- https://wiki.bambulab.com/en/software/bambu-studio/parameter/elephant-foot
- https://help.prusa3d.com/article/first-layer-issues_1804
- https://help.prusa3d.com/article/live-adjust-z_112427
- https://help.prusa3d.com/article/first-layer-calibration-i3_112364
- https://help.prusa3d.com/article/first-layer-calibration-mini-mini_229122
- https://help.prusa3d.com/article/print-surface-preparation_686951
- https://help.prusa3d.com/article/elephant-foot-compensation_114487
- https://help.prusa3d.com/article/petg_2059
- https://help.prusa3d.com/article/flexible-materials_2057
- https://help.prusa3d.com/article/special-pa-nylon-steel-sheet_341570
- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_initial_layer_speed.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_layer_height.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_line_width.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_precision.html
- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html
- https://www.orcaslicer.com/wiki/calibration/flow_ratio_calib.html
