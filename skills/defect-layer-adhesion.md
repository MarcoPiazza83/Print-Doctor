---
name: defect-layer-adhesion
description: Weak bonding between layers: layers splitting or separating, horizontal cracks along layer lines (often on tall ABS/ASA/PC or CF parts), delamination, parts that snap or peel apart along the layers. Read when the user reports layer separation, layers splitting, cracks in the walls, delamination, weak or brittle parts that break along layer lines.
---
# Layer separation, splitting, cracks, weak layer bonding

## How to recognize it
- Cracking from thermal stress: clean horizontal cuts along a layer line, edges often bent slightly upward or outward; typical on tall or large ABS, ASA, PC, PET-CF, PA-CF parts, frequently on the side facing a fan, a door or a draft.
- Weak bonding: the part breaks or peels apart along layer lines with little force; surface may look matte or rough where flow was too high for the hotend.
- One thin or missing layer at a single height (a groove all around) is not cracking: usually a short under-extrusion (partial clog, tangled spool): see defect-clogs-heat-creep and defect-extrusion.
- Gaps between walls and infill, weak infill: defect-extrusion. Base lifting at the corners together with cracks: also defect-warping.

## Likely causes, most common first
1. Too much cooling for the material: part/auxiliary fan, drafts, open-frame printer or open doors (ABS/ASA/PC/PA are very sensitive to cold air).
2. Nozzle temperature too low for the filament, or too low for the speed being printed.
3. Printing too fast / volumetric flow too high: the plastic leaves the nozzle colder and has less time to fuse.
4. Shrinkage forces larger than the bond: large parts in high-shrink materials, cold room, no enclosure.
5. Under-extrusion: flow ratio too low, partial clog, wet filament (popping, bubbles).
6. Layer height too large for the nozzle (above about 75-80% of nozzle diameter).
7. Material: fibre-filled filaments have weaker layer bonding by nature; PLA is brittle across layers.

## Questions worth asking (only when the answer changes the fix)
- Material and brand, enclosed or open printer, doors/lid closed, drafts nearby?
- Did it crack during the print (thermal stress) or break later under load (weak bonding or orientation)?
- Where are the cracks: at what height, which side?
- Popping or hissing while printing (wet filament)?
- Was the profile edited (speeds, fan, temperature, layer height)? Nozzle diameter and layer height?
- Direction of the load on the part: parts are weakest when pulled across the layers; reorienting can solve a strength problem without any setting change.

## Slicer fixes
| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `nozzle_temperature` (filament) | increase | +5 °C per step (also `nozzle_temperature_initial_layer` if low) | inside the filament's nozzle_temperature_range_low..high | stringing, softer overhangs and small features |
| `fan_max_speed` (filament) | decrease | -10-20 points; ABS/ASA about 30-40% or less, large ABS parts 0 | PLA/PETG: keep enough for overhangs | overhangs and bridges droop |
| `fan_min_speed` (filament) | decrease | -10-20 points | ≥ 0 | as above |
| `additional_cooling_fan_speed` (filament) | decrease, 0 for ABS/ASA/PC | -20-30 points | printers with an auxiliary fan | small details cool less |
| `reduce_fan_stop_start_freq` (filament) | `0` for ABS/ASA/PC | - | - | fan stops on long layers |
| `fan_cooling_layer_time` (filament) | decrease (fan starts only on very short layers) | -25% | ≥ 0 | small layers cool less |
| `outer_wall_speed` / `inner_wall_speed` (process) | decrease | -20-30% (Bambu ABS example: inner 150, outer 100 mm/s) | never above printer machine limits | longer print |
| `filament_max_volumetric_speed` (filament) | decrease | -10-20% | lower freely; raise at most +10% | caps all speeds, longer print |
| plate temp pair for the plate in use (filament): `textured_plate_temp`, `hot_plate_temp`, `eng_plate_temp`, `cool_plate_temp`, `textured_cool_plate_temp`, `supertack_plate_temp` (and their _initial_layer versions) | increase | +5 °C | ≤ +10 °C over current, never above 120 °C | helps the lower part only; PLA/PETG elephant foot |
| `layer_height` (process) | decrease when above about 75% of nozzle | e.g. 0.32 → 0.2 mm on 0.4 mm | ≤ 75% of nozzle diameter, min 0.04 mm | longer print |
| `filament_flow_ratio` (filament) | increase only if under-extrusion is confirmed (better: calibrate) | +0.02 | 0.8-1.2 | over-extrusion, rough surface |
| `wall_loops` (process) | increase (strength) | +1-2 (structural parts: about 5 walls, 25% infill) | - | time, material; more shrink stress on large ABS/PC |
| `draft_shield` (process) | `enabled` for ABS/ASA/PC on open frames | with `skirt_loops` ≥ 1 | - | filament, time |

Notes for the AI:
- Order: reduce cooling (ABS/ASA/PC) or raise nozzle temperature (PLA/PETG) first, then slow down / cap volumetric flow, then layer height. Hardware and environment (enclosure, drafts, wet filament, clog) come before all of these.
- After lowering the fan, check overhangs and bridges in the preview; restore `overhang_fan_speed` (filament) if they matter.
- If the fan must stay high (overhangs) and bonding suffers, raise the nozzle temperature a step instead of removing all cooling (Prusa).
- More walls and denser infill make parts stronger but increase shrinkage stress on large ABS/PC parts: there prefer temperature, cooling and enclosure changes.

## Checks the user must do by hand (hardware, material, printer settings)
- Enclosure: close doors and top cover for ABS/ASA/PC/PA; keep the printer away from windows, AC vents and fans. Ventilate the room without blowing on the printer.
- Printers with active chamber heating: the user can raise the chamber temperature by about 5 °C on the printer (Bambu suggestion). The plugin never changes chamber settings.
- Partial clog or dirty nozzle (one weak layer, thin lines): cold pull / unclog as in the printer guide (defect-clogs-heat-creep).
- Wet filament (popping, bubbles, rough surface): dry it, store sealed with desiccant. PA and PC absorb moisture within hours.
- Part cooling fan and shroud: fan working, shroud not blocked, deformed or melted.
- Start from the vendor filament profile for the material; most cases come from custom profiles with wrong temperatures or too much cooling (Prusa).
- Material choice: large ABS parts that keep cracking: suggest ASA, or PETG where heat resistance allows.
- Orientation: rotate the part so the main load runs along the layers, not across them.

## Calibration in Orca (menu Calibration → ...)
- Calibration → Temperature: print the tower and choose the block with the best layer bonding; for fast printing use the upper part of the good range. Result → `nozzle_temperature` (filament).
- Calibration → Max flowrate (max volumetric speed test): read where the surface loses gloss (a sign of degrading bonding) and where walls deform; set `filament_max_volumetric_speed` below the quality-loss point.
- Calibration → Flow ratio: rules out under-extrusion; result → `filament_flow_ratio` (filament).
- See calibration-guide for order and reading.

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- PLA: weaker layer bonding than other materials, breaks along layers or shatters on impact. Usual range 195-220 °C by brand; raise in 5 °C steps until layers bond. Keep cooling for quality; bonding problems are mostly temperature or speed.
- PETG: good layer adhesion. For maximum toughness print hotter and with little or no fan (accept worse overhangs).
- ABS: very sensitive to cold air: fan off or low, enclosure, draft shield on open frames. Typical nozzle range starts around 220-235 °C; much lower gives easy splitting.
- ASA: like ABS but more tolerant; still needs stable warm surroundings for large parts.
- TPU: excellent layer bonding; poor bonding usually means printing too fast (under-extrusion).
- PA/PC: high shrink and moisture uptake: dry first, enclose, minimal fan. PA has excellent layer bonding when dry.
- CF/GF: fibres reduce layer-to-layer adhesion (PET-CF and PA-CF crack easily): higher end of the temperature range, slower walls, low fan, enclosure.

## Sources
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/interlayer-cracking
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/warping-falling-off-collapsing
- https://wiki.bambulab.com/en/knowledge-sharing/printed-model-warping
- https://wiki.bambulab.com/en/general/engineering-plate-not-working-as-expected
- https://wiki.bambulab.com/en/general/filament-guide-material-table
- https://help.prusa3d.com/article/layer-separation-and-splitting-fdm_1806
- https://help.prusa3d.com/article/warping_2011
- https://help.prusa3d.com/article/cooling_127569
- https://help.prusa3d.com/article/abs_2058
- https://help.prusa3d.com/article/asa_1809
- https://help.prusa3d.com/article/petg_2059
- https://help.prusa3d.com/article/pla_2062
- https://help.prusa3d.com/article/polyamide-nylon_167188
- https://help.prusa3d.com/article/polycarbonate-pc_165812
- https://help.prusa3d.com/article/flexible-materials_2057
- https://help.prusa3d.com/article/composite-materials-filled-with-carbon-kevlar-or-glass_167387
- https://www.simplify3d.com/resources/print-quality-troubleshooting/layer-separation-and-splitting/
- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html
- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_layer_height.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_walls.html
- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_skirt.html
- https://www.orcaslicer.com/wiki/calibration/temp_calib.html
- https://www.orcaslicer.com/wiki/calibration/volumetric_speed_calib.html
- https://www.orcaslicer.com/wiki/calibration/flow_ratio_calib.html
