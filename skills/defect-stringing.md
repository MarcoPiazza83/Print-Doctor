---
name: defect-stringing
description: Stringing and oozing: thin strings, hairs, wisps and cobwebs between separate parts or across gaps, caused by molten filament leaking during travel moves (retraction, temperature, wet filament, travel, plate layout). Read when the user reports stringing, strings, hairs, hairy print, cobwebs, spider webs, wisps, whiskers, oozing or threads between parts.
---
# Stringing and oozing

## How to recognize it
- Thin threads or cobwebs spanning open space between towers, separate objects or features of one object; fine hairs on the surface.
- Oozing: material keeps leaking when the nozzle should not extrude; small drips or lumps where travel moves start or end, residue building up on the nozzle.
- Many fine hairs everywhere plus popping/hissing, bubbles or a rough, matte-dull surface: almost always wet filament, not retraction.
- Strings only between objects on a crowded plate: travel/plate layout. Strings inside one part across small gaps: retraction threshold or temperature.
- Related: blobs or zits at the seam (see defect-seam-zits-blobs); material building up on the outside of the nozzle or a blob on the hotend (see defect-clogs-heat-creep); ooze from the idle nozzle in multi-material (see defect-multimaterial).

## Likely causes, most common first
1. **Wet filament.** Moisture turns to steam in the nozzle, the melt expands and keeps flowing. Retraction tuning cannot fully fix it. PETG, TPU, PA, PC, PVA and wood-filled PLA are the most sensitive; even new spools can be wet.
2. **Nozzle temperature too high** for the material or for the actual speed: the melt is too fluid. Slow prints need a lower temperature than fast ones (more time in the melt zone).
3. **Retraction too short or too slow**, or not triggered on short travels (travel distance threshold too high).
4. **Long travels over open space**: many separate objects far apart, printing layer by layer, travels crossing walls, slow travel.
5. **Pressure advance not calibrated / too low**: the nozzle is still pressurized at the end of a line and leaks during travel.
6. **Over-extrusion** (flow ratio too high), especially PETG.
7. **Z-hop**: vertical lifts on every retraction can pull threads; normal lift strings more than spiral/slope.
8. **Hardware**: worn or enlarged nozzle, wrong nozzle size selected in the profile, residue film inside/outside the nozzle (long PETG runs), leaking or badly assembled hotend, poor heatbreak cooling. High-flow/volcano nozzles and large nozzles ooze more by design.
9. **Low-density/foaming filaments** (e.g. PLA Aero, LW-PLA) used with normal flow and temperature.

## Questions worth asking (only when the answer changes the fix)
- Material and brand; how long the spool was open and how it is stored; any popping sounds or bubbles? (yes → dry first, before any setting change)
- Direct drive or Bowden extruder? (decides the retraction range)
- Strings only between separate objects, or also inside one part?
- Was pressure advance, temperature or retraction ever calibrated for this filament?
- Standard or high-flow nozzle, and which diameter?

## Slicer fixes
Read the current values first. Retraction overrides in the filament preset show `nil` when they inherit the printer value: read the printer value before computing a new one. Change 1-2 keys per test print.

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `nozzle_temperature` (filament) | decrease | -5 °C per test | inside the filament's nozzle temperature range | too low: under-extrusion, weak layers; going much too low can also string |
| `filament_retraction_length` (filament) | increase | +0.2 mm direct drive, +0.5 mm Bowden | 0 .. min(8 mm, max(2 mm, 2x printer retraction)); direct drive usually ≤ 2 mm | too long: clogs, under-extrusion after travel, gaps at seams |
| `filament_retraction_speed` (filament) | increase | +5-10 mm/s | > 0 and ≤ max(1.5x printer value, 30 mm/s) | too fast: ground filament, skipped extruder steps |
| `reduce_crossing_wall` (process) | enable `1` | - | - | slightly longer print time; set `max_travel_detour_distance` (process) to limit detours (0 = no limit) |
| `travel_speed` (process) | increase | +20-50 mm/s | never above the printer's machine limits | ringing, missed steps if too fast |
| `filament_retraction_minimum_travel` (filament) | decrease | e.g. 2 → 1 mm | ≥ 0 | more retractions, longer print, more extruder wear; strings across small gaps disappear |
| `filament_wipe` (filament) | enable `1` | - | - | none relevant; cleans the tip while retracting |
| `filament_wipe_distance` (filament) | increase | +0.5 mm (1-2 mm typical) | ≥ 0 | longer wipe is limited by retraction length/speed |
| `filament_retract_when_changing_layer` (filament) | enable `1` | - | - | none relevant |
| `filament_z_hop` (filament) | decrease | e.g. 0.4 → 0.2 mm | 0-2 mm | less clearance: nozzle may hit curled parts/top surfaces |
| `filament_z_hop_types` (filament) | set `Spiral Lift` or `Auto Lift` | - | - | `Auto Lift` picks slope or spiral per travel |
| `print_sequence` (process) — BY HAND | `by object` for several small parts | - | by hand only (collision risk the plugin cannot check): Process → Others → Special mode → Print sequence; only if parts fit the printer's extruder clearance; Orca warns about collisions | parts cool less between layers; collision risk |
| `pressure_advance` (filament) with `enable_pressure_advance` (filament) | set calibrated value | from the PA calibration | 0-2; use the calibrated value, no guessing | wrong value moves the defect to corners/seams |
| `filament_flow_ratio` (filament) | decrease if over-extruding | -0.01 to -0.02 | 0.8-1.2 | under-extrusion, weaker layers |
| `wipe_on_loops` (process) | enable `1` | - | needs 2+ walls | small inward move cleans the nozzle before travel |

Notes for the AI:
- Order of attack: dry filament → temperature → retraction (calibrated) → travel/avoid crossing walls → wipe/Z-hop → layout/print sequence.
- `reduce_infill_retraction` (process) skips retractions for travel inside infill; it hides oozing inside the part and does not cause visible strings. Leave as is unless strings appear inside open infill.
- Bambu guidance for PETG with strings/nozzle build-up: about 1.2-1.6 mm and 40-60 mm/s retraction, flow ratio 0.93-0.96; keep retraction under about 2 mm on direct drive and inside the Safe limit column.
- Low-density PLA (Aero/LW): vendor values use flow well below 0.8, which the plugin cannot set: tell the user to use the vendor's profile or set it by hand (Filament → Filament → Flow ratio and Pressure Advance → Flow ratio); meanwhile lower `nozzle_temperature` and dry the spool.
- If strings are still bad at the top of a clean retraction tower, stop raising retraction: dry the filament and check the nozzle.

## Checks the user must do by hand (hardware, material, printer settings)
- **Dry the filament** (see materials-overview for times): typical PLA 45-55 °C, PETG 55-65 °C, TPU 60-75 °C, PA/PC 80-90 °C. Store sealed with desiccant (Bambu: below 20 % RH). Try a different spool to confirm.
- **Nozzle**: check for wear (brass after CF/GF or long use) and that the installed nozzle diameter matches the selected printer profile; replace a worn nozzle.
- **Clean the nozzle**: a film of old filament (often PETG) on or inside the tip drags strings; heat and clean it, remove residue from previous materials.
- **Hotend assembly**: if parts were changed recently, check for leaks and correct assembly; Prusa: poor heat dissipation in the hotend can cause stringing, renew the thermal paste on the heatbreak threads that sit in the heatsink.
- **Printer retraction (printer settings, user changes by hand)**: Printer settings → Extruder → Retraction: length, speed, Z-hop. The plugin only uses the filament overrides; if the printer value is 0 or extreme, explain and let the user fix it. Bowden printers need much longer retraction than direct drive.
- **Plate layout**: place objects closer together; fewer objects per plate reduces travel.
- Finished parts: a very short pass of a heat gun (about 200 °C, 1-2 s) removes fine strings; longer exposure deforms the part.

## Calibration in Orca (menu Calibration → ...)
1. **Temperature**: temperature tower; choose the block with least stringing that still bonds well; the result goes into `nozzle_temperature`.
2. **Pressure Advance**: result into `pressure_advance` with `enable_pressure_advance` = `1`.
3. **Retraction test**: tower with a different retraction length per section. Defaults 0-2 mm step 0.1 mm suit direct drive; for Bowden use about 1-6 mm step 0.2 mm. Pick the shortest length that gives a clean tower; measure the height and find the "Calib_Retraction_tower" comment in the G-code preview to read the length. Result into `filament_retraction_length`. PLA/ABS are often clean from the bottom: 0.2-0.4 mm is enough then.
4. Flow rate if over-extrusion is suspected (see calibration-guide).

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- **PLA**: low stringing when dry; check temperature first. Silk/high-speed variants are more fluid. Aero/LW foaming PLA needs low flow and low temperature (vendor profile).
- **PETG/PCTG**: strings and oozes the most; lower temperature 5-10 °C, flow 0.93-0.96, slightly longer/faster retraction, dry it (very hygroscopic), clean the nozzle regularly.
- **ABS/ASA**: little stringing; short retraction (0.2-0.4 mm) is usually enough; look at temperature and moisture.
- **TPU**: hygroscopic, dry it first. Keep retraction short (long or fast retraction jams soft filament); increase in small steps (+0.2 mm) only if leaking is severe. Avoid many objects per plate printed by layer; prefer `print_sequence` = `by object` and avoid crossing walls.
- **PA/PC**: very hygroscopic: drying is mandatory, strings are usually moisture.
- **CF/GF filled**: abrasive, enlarge brass nozzles over time → more ooze; use a hardened nozzle and check wear.

## Sources
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/stringing-oozing
- https://wiki.bambulab.com/en/software/bambu-studio/parameter/retraction
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/filament-sticks-to-nozzle
- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament
- https://wiki.bambulab.com/en/knowledge-sharing/tpu-printing-guide
- https://help.prusa3d.com/article/stringing-and-oozing_1805
- https://help.prusa3d.com/article/drying-filament_332086
- https://www.orcaslicer.com/wiki/calibration/retraction_calib.html
- https://www.orcaslicer.com/wiki/calibration/temp_calib.html
- https://www.orcaslicer.com/wiki/printer_settings/extruder/printer_extruder_retraction.html
- https://www.orcaslicer.com/wiki/printer_settings/extruder/printer_extruder_z_hop.html
- https://www.orcaslicer.com/wiki/material_settings/setting%20overrides/material_setting_overrides.html
- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_travel.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_seam.html
- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_g_code_output.html
- https://www.simplify3d.com/resources/print-quality-troubleshooting/stringing-or-oozing/
- https://www.obico.io/blog/3d-print-troubleshooting-guide/
