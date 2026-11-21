---
name: defect-clogs-heat-creep
description: Diagnosis and prevention (not repair) of clogs, heat creep, extrusion stopping mid print or missing at the start, grinding, filament stuck on the nozzle and blobs around the hotend. Read when the user reports a clog, clogged or jammed nozzle, heat creep, extruder clicking or skipping, ground filament, no extrusion, air printing, print stopped extruding, filament sticking to the nozzle or a blob on the hotend.
---
# Clogs, heat creep, grinding, blobs on the hotend

Scope: the plugin cannot clear a clog. Explain the checks and repair steps to the user, then use slicer settings only to prevent a repeat. Never "fix" a hardware cause with parameters.

## How to recognize it
- **Full clog**: toolhead moves but nothing comes out ("air printing"); filament does not come out when extruded from the printer screen at temperature.
- **Partial clog**: thin, inconsistent lines, gaps, missing layers; filament curling up onto the nozzle (early sign).
- **Clicking extruder**: loud clicks usually mean resistance in the nozzle/hotend; light clicks more often point to the gears (Prusa Nextruder guidance). Shavings or a bitten notch in the filament = grinding/stripping.
- **Heat creep**: print starts fine, then extrusion fades or stops after some time with no error; typical with PLA (also TPU, PETG) in a closed or hot enclosure or a warm room. Filament softens too high in the heatbreak and swells.
- **Stops mid print**, other causes: spool empty/tangled, brittle filament snapped, ground filament, overheated extruder motor driver.
- **No extrusion at start**: nozzle drained by oozing during preheat; nozzle too close to the plate (extrusion recovers after 2-3 layers); ground filament; clog.
- **Build-up on the nozzle**: residue grows on the nozzle outside during long prints (mostly PETG/PETG-CF), leaves gaps and rough spots.
- **Blob on the hotend**: plastic wrapped around nozzle and heater block, usually after the first layers detach and stick to the nozzle.

## Likely causes, most common first
1. Heat creep from a hot printing environment: closed door/lid with PLA, high bed temperature heating the chamber, ambient above about 30-35 °C. Bambu: keep the enclosure at least 10 °C below the filament's glass transition.
2. Debris in the nozzle: CF/GF particles, burnt material, high-temp filament residue after switching to PLA/PETG/TPU, dust, many short heat/cool cycles.
3. Melt rate too low for the speed: nozzle temperature too low or speed/flow too high (filament does not fully melt).
4. Extruder side: debris in the gears, wrong idler tension, filament softened and flattened by the gears (very soft TPU, damp PVA), inconsistent diameter (bad spool), filament sensor or cutter blocked (Bambu X1/P1).
5. Very low flow for long times: very thin layers, very slow printing or long ironing → filament sits in the hot zone (feeds heat creep).
6. Excessive retraction length/speed (pulls molten material into the cold zone; grinds filament).
7. Wet filament (steam, swelling, partial clogs over time).
8. Hardware cooling faults: hotend/heatsink fan slow or blocked, dust in heatsink fins, missing thermal paste, PTFE not seated, metal-filled filament conducting heat upward.
9. Profile mismatch: high-flow nozzle printed with a standard profile (or the reverse), fiber-filled filament on a 0.2 mm nozzle.
10. Blob/build-up: poor first-layer adhesion, wet PETG, flow too high, faulty nozzle wiper, many travels.

## Questions worth asking (only when the answer changes the fix)
- When did extrusion fail: from the first line, after some minutes/hours, at a specific height? (start → priming/Z offset/clog; later → heat creep/grinding/spool)
- Can the printer extrude by hand from the screen at print temperature? Is there clicking, are there shavings?
- Printer model, door/lid open or closed, room temperature, plate type and bed temperature?
- Material, previous material in the nozzle (high-temp or CF/GF?), nozzle size and type (standard/high flow, brass/hardened)?
- Any printer error (Bambu HMS: hotend fan speed, extruder overload)?

## Slicer fixes
Prevention only, after the clog is cleared. These settings do not unclog anything.

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| plate temperature key in use: `cool_plate_temp`, `textured_plate_temp`, `hot_plate_temp`, `eng_plate_temp`, `supertack_plate_temp` or `textured_cool_plate_temp` (filament) | decrease (PLA/TPU heat creep in enclosed printers) | -5 °C | raise at most +10 °C over current, never above 120 °C; Bambu PLA on textured PEI about 55 °C, Cool Plate about 35 °C | less adhesion: add brim if corners lift |
| `nozzle_temperature` (filament) | increase if under-melting at high speed; decrease if heat creep with metal-filled filament or overheating | ±5 °C | inside the filament's nozzle temperature range | higher: more stringing; lower: under-extrusion |
| `filament_max_volumetric_speed` (filament) | decrease if clogs/grinding appear at high speed | -10-20 % | lower freely; raise at most +10 % | slower print |
| `layer_height` (process) | increase very thin layers (more flow, less heat creep) | e.g. 0.08 → 0.15-0.2 mm | ≤ 75 % of nozzle diameter | coarser surface |
| `filament_retraction_length` (filament) | decrease if excessive | -0.2-0.5 mm | 0 .. min(8 mm, max(2 mm, 2x printer retraction)); direct drive about ≤ 2 mm | more stringing |
| `filament_retraction_speed` (filament) | decrease if grinding | up to -50 % as a test | > 0 and ≤ max(1.5x printer value, 30 mm/s) | slightly more ooze |
| `slow_down_min_speed` (filament) | increase if long very slow layers precede the jam | +5 mm/s | within machine limits | small layers cool less |
| `ironing_type` (process) | `no ironing` if jams happen during ironing | - | - | rougher top surface |
| `filament_long_retractions_when_cut` (filament) — BY HAND | disable (beta feature raises clog risk) | - | by hand only (plugin cannot check it): Filament → Setting overrides → Retraction → Long retraction when cut | more purge waste |
| `skirt_loops` (process) | 1-2 to prime a drained nozzle | +1 | 0-10 | slightly more filament |
| `filament_flow_ratio` (filament) | decrease for PETG build-up on nozzle | to 0.93-0.94 | 0.8-1.2 | under-extrusion below about 0.93 |
| `fan_min_speed` / `fan_max_speed` (filament) | increase for PETG build-up on nozzle | +10-20 points | 0-100 % | weaker layer bonding |

PETG build-up recipe (Bambu): dry the filament, check nozzle wear, then nozzle temperature -5 to -10 °C, max volumetric speed -4 to -5 mm³/s, a bit more cooling, flow 0.93-0.94; for many travels, retraction about 1.2-1.6 mm at 40-60 mm/s (inside the limits above) and parts closer together. For build-up, when print or volumetric speed is lowered, lower the nozzle temperature too.

## Checks the user must do by hand (hardware, material, printer settings)
Safety: power off before touching wiring; heat the nozzle only from the printer menu.
- **Locate the clog**: heat and extrude from the screen. Bambu X1/P1: AMS disconnected, detach the hotend and push filament through by hand (passes → hotend clear, check the extruder).
- **Clear the nozzle**: push fresh PLA at high temperature (Prusa: 260 °C after PLA, 280 °C after PETG/ASA, wait about 2 min); needle (0.3-0.35 mm) only in non-high-flow nozzles; cold pull (monthly as maintenance, nylon works well); replace the nozzle if nothing helps.
- **After high-temp or CF/GF filaments** before PLA/PETG/TPU: unload at 250-300 °C, load the new filament and keep extruding while cooling to 220-240 °C until it flows clean.
- **Heat creep**: PLA/TPU on X1/P1S/enclosed printers: open the door and/or remove the top glass, or use the Cool Plate. Check the hotend fan (Prusa MK3: 4000-4400 RPM), dust in the heatsink, thermal paste on the heatbreak thread, PTFE fully seated, E3D V6: about 0.5 mm gap nozzle hex to heater block. Unload filament while hot after printing.
- **Extruder**: clean gear teeth, check idler tension and motor strength; Bambu: clean filament sensor, replace a dull cutter blade; cut off deformed filament.
- **Filament**: dry it; diameter 1.75 ± 0.03 mm; avoid very soft TPU (85A) and damp PVA where unsupported; spool runs free, filament not brittle.
- **Nozzle choice**: fiber-filled filament on 0.6-0.8 mm, never 0.2 mm; select the profile matching the installed nozzle (high flow vs standard).
- **Start of print**: if extrusion returns after 2-3 layers, the nozzle is too close to the plate: Z offset/levelling (printer setting, by hand).
- **Blob on hotend**: heat about 30 °C above print temperature, remove softened plastic with pliers away from heater/thermistor wires; refit the silicone sock; clean the plate, check first-layer adhesion; Bambu: enable nozzle clumping detection, check the nozzle wiper.
- **Printer retraction (printer settings, user changes by hand)**: if the printer retraction length is very long for a direct drive, explain and let the user reduce it.

## Calibration in Orca (menu Calibration → ...)
- **Temperature** tower: confirm the filament is printed hot enough for its speed.
- **Max flowrate** (max volumetric speed): find the real melt limit; put a value 10-20 % below the point where the walls start to deform into `filament_max_volumetric_speed`.
- **Retraction test**: use the shortest clean length instead of a long guess.
- **Flow ratio**: for PETG build-up or over-extrusion. See calibration-guide.

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- **PLA**: most prone to heat creep (lowest softening point): door open or Cool Plate, moderate bed temperature, avoid very slow/thin printing for hours.
- **PETG**: build-up on the nozzle and blobs; dry, flow 0.93-0.96, lower temperature when printing slower. Softens in hot enclosures too.
- **ABS/ASA**: printed closed; clogs mostly from residue or too-low temperature. When switching to PLA afterwards, purge hot first.
- **TPU**: heat creep and gear tangling; minimal retraction, slow printing, gentle load/unload (Bambu H2D: retract only twice at 175 °C, then pull it out).
- **PA/PC**: dry thoroughly; residue when switching back to low-temp materials.
- **CF/GF**: particles build up in the nozzle: larger hardened nozzle, regular cold pulls.

## Sources
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/clog
- https://wiki.bambulab.com/en/filament-acc/filament/heat-creep
- https://wiki.bambulab.com/en/knowledge-sharing/how_to_avoid_nozzle_clogs
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/filament-sticks-to-nozzle
- https://wiki.bambulab.com/en/x1/troubleshooting/how-to-check-which-part-is-clogged
- https://wiki.bambulab.com/en/x1/troubleshooting/filament-not-extruding
- https://wiki.bambulab.com/en/general/troubleshooting/extrusion-failure
- https://wiki.bambulab.com/en/p2s/troubleshooting/hotend_blob
- https://wiki.bambulab.com/en/h2/troubleshooting/tpu-clogging
- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament
- https://wiki.bambulab.com/en/software/bambu-studio/parameter/retraction
- https://help.prusa3d.com/article/extrusion-stopped-mid-print-heat-creep_1948
- https://help.prusa3d.com/article/extruder-blob_2005
- https://help.prusa3d.com/article/clogged-nozzle-core-one-core-one-l-xl-mk4-s-mk3-9-s_411823
- https://help.prusa3d.com/article/cooling_127569
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_ironing.html
- https://www.orcaslicer.com/wiki/printer_settings/extruder/printer_extruder_retraction.html
- https://www.orcaslicer.com/wiki/calibration/volumetric_speed_calib.html
- https://www.simplify3d.com/resources/print-quality-troubleshooting/clogged-extruder/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/stops-extruding-mid-print/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/grinding-filament/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/not-extruding-at-start-of-print/
- https://www.obico.io/blog/3d-print-troubleshooting-guide/
