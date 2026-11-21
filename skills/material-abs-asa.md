---
name: material-abs-asa
description: ABS, ASA and ASA Aero (foaming ASA): enclosure and chamber heat, bed and plate keys, low part cooling, warping and layer-crack prevention, shrinkage, drying, styrene fumes and air filtration, ASA Aero lightweight settings. Read when the user prints ABS or ASA and asks for settings or reports ABS/ASA warping, corners lifting, layers splitting or cracking on tall parts, parts detaching, bad smell or fumes, parts shrinking, or printing ABS on an open printer.
---
# ABS and ASA

ABS: tough, heat resistant (Bambu ABS HDT about 87 °C), acetone-smoothable, yellows and embrittles outdoors. ASA: the outdoor version with UV and weather resistance (HDT about 100 °C), slightly less warping and odour. Both shrink while cooling (about 1-2%), warp strongly, have weak Z adhesion (Bambu impact Z: ABS 7.4, ASA 4.9 kJ/m² vs PLA 13.8) and release styrene.

## Baseline (start from the vendor preset)
| Item | Typical value | Notes |
|---|---|---|
| `nozzle_temperature` (filament) | ABS 240-260 °C (Prusa 255), ASA 245-265 °C (Prusa 260) | Bambu range 240-280 °C for both. |
| Bed, PEI or Engineering plate | 90-110 °C (Bambu 90-100; Prusa ABS 100, ASA 105 first layer / 110) | Bigger part = hotter bed. Glue stick on every plate. |
| Cool Plate / Cool Plate SuperTack | do not use | SuperTack coating is for PLA/PETG only. |
| Part cooling | low; 10-20% only where steep overhangs or small parts curl; off for the first layers | Too much fan = warping and layer cracks. |
| Enclosure | required for anything but small parts | Bambu: not for P1P or A-series (open frames). |

Bed keys per plate (filament preset, each with an "_initial_layer" twin): `eng_plate_temp` (Engineering Plate), `hot_plate_temp` (Smooth PEI / High Temp Plate), `textured_plate_temp` (Textured PEI). Change only the one matching the plate selected in Orca.

## Slicer fixes (warping, cracks, detachment)
| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `brim_type` / `brim_width` (process) | `outer_only`; `brim_ears` (mouse-ears value of `brim_type`) on sharp corners | +3 mm | 0-100 mm | removal marks |
| `eng_plate_temp` / `hot_plate_temp` / `textured_plate_temp` (+ "_initial_layer") (filament) | increase for lifting corners | +5 °C | max +10 °C per change, ≤ 120 °C | elephant foot |
| `fan_max_speed` / `fan_min_speed` (filament) | decrease for cracks between layers and warping | -10% | ≥ 0; keep 10-20% if small overhangs curl | worse overhangs/bridges |
| `close_fan_the_first_x_layers` (filament) | increase for first-layer lift | to 3 | 0-5 | none |
| `draft_shield` (process) | `enabled` on open-frame printers, with `skirt_loops` ≥ 1 (the shield is automatically as tall as the tallest object; `skirt_height` only counts when it is `disabled`) | on | n/a | more material/time |
| `sparse_infill_density` (process) | decrease on large flat parts | ≤ 25%, with `sparse_infill_pattern` (process) = `gyroid` (shrinks evenly) | ≤ 50% | less strength |
| `wall_loops` (process) | do not exceed 6; 2 walls + 15% infill is enough for non-structural parts | -1 | ≥ 2 | less strength |
| `nozzle_temperature` (filament) | increase for layer splitting / cracks | +5 °C | inside nozzle_temperature_range_low..high | more odour, stringing |
| `outer_wall_speed`, `inner_wall_speed`, `sparse_infill_speed` (process) | decrease for warping and cracks on big parts | -20% | ≤ printer limits | longer print |
| `print_sequence` (process) — BY HAND | `by object` for many small parts | n/a | by hand only: Process → Others → Special mode → Print sequence; gantry clearance limits | long layer times otherwise weaken small parts |

- Shrinkage: parts come out about 1-2% small. The plugin may not change filament shrinkage data: route to defect-dimensional-accuracy and explain to the user that shrinkage compensation is set by hand in the filament preset.
- Orientation: loads must not pull layers apart. A part tilted about 45° balances warping and strength (Bambu); large flat contact areas warp most.
- Air filtration (BY HAND, the plugin cannot check it; Filament → Cooling → Exhaust fan; printers with an exhaust fan): `activate_air_filtration` = `1`, `complete_print_exhaust_fan_speed` high to clear fumes after the print; keep `during_print_exhaust_fan_speed` low on warping-prone parts because exhausting during the print removes chamber heat. Higher chamber temperature also lowers filter efficiency (Orca wiki).

## ASA Aero (foaming, Bambu)
Lightweight RC/outdoor parts. Density falls as temperature rises (220 °C ≈ no foam, 260 °C ≈ 86% foam). High temperature, low speed.
- Flow ratio 0.42-0.7 is needed; the plugin cannot set `filament_flow_ratio` below 0.8, so explain the value and let the user set it by hand (Filament → Filament → Flow ratio).
- Bambu reference values (process): `line_width` 0.48 mm, `slice_closing_radius` 0.02 mm, `bridge_flow` 0.7 (BY HAND, the plugin cannot check it: Process → Quality → Bridging → Flow ratio), `reduce_crossing_wall` `1` with `max_travel_detour_distance` `90%`, `wall_loops` 1, `top_shell_layers` 0, `bottom_shell_layers` 2, `sparse_infill_density` `0%`, all feature speeds 80 mm/s, `default_acceleration` 5000, `outer_wall_acceleration` 3000 (never above printer limits), `brim_type` `outer_only` 3 mm with `brim_object_gap` 0.2 mm, `enable_prime_tower` 0, `slicing_mode` `even_odd`.
- Supports only if needed: `support_threshold_angle` 50, `support_top_z_distance` 0.26 mm, `support_interface_top_layers` 3, `support_interface_spacing` 0.2 mm, `support_object_xy_distance` 0.6 mm.
- Avoid travel-heavy models; print one part or `by object`. Fan neither very low nor very high.
- 0.4 mm nozzle only; Smooth PEI with glue or Engineering plate, not Textured PEI (bottom tears on removal).

## Checks the user must do by hand
- Enclosure and chamber heat: close door and top lid. Chamber heating and chamber temperature settings are not changed by the assistant. Bambu H2/X1E/X2D heat the chamber actively; on X1C/P1S without chamber heating, preheat the bed at maximum for about 15 min before printing in a cold room. No enclosure: small parts only, draft shield on, no drafts.
- Ventilation: styrene can cause dizziness or nausea; print in a ventilated room, not a bedroom, but keep drafts away from the printer. Replace Bambu activated-carbon filters about every 1,440 printing hours; clean the carbon rod and glass after about 5 kg of ABS/ASA.
- Prusa enclosure: long ABS/ASA sessions can deform the printer's own PETG/PLA parts (fan shroud): consider reprinting them in a heat-resistant material.
- Plate: clean, then glue stick (Bambu glue on all plates; Prusa smooth PEI or textured/satin with glue). Never ABS juice or acetone on Prusa powder-coated sheets; Prusa smooth PEI tolerates occasional acetone. Bambu Engineering plate: glue always.
- Bambu: do not feed ABS/ASA from the AMS lite; the AMS is fine.
- Dry: 80 °C for 4-8 h (Prusa ASA 80 °C / 4 h; Bambu 75-85 °C / 8 h). AMS 2 Pro (max 65 °C) cannot dry it fully; AMS HT 80 °C / 8 h. Remove PLA/TPU spools from the dryer first.
- Ring-shaped bulges where a thick base meets thin walls: add an inner fillet in CAD.

## Material notes
- Post-processing: wet/dry sanding, acetone vapour smoothing and acetone welding (both ABS and ASA); smoothing rounds edges.
- ABS for low-cost technical parts and acetone finish; ASA for anything outdoors.
- ABS-GF, ASA-CF: see material-composites. PC and PC blends: see material-pa-pc. Supports for ABS: see material-special.

## Calibration in Orca
Calibration → Temperature, Flow ratio, Pressure advance, Max flowrate; print tests inside the closed enclosure so results match real prints (calibration-guide).

## Sources
- https://wiki.bambulab.com/en/filament/abs_asa_pc
- https://wiki.bambulab.com/en/filament-acc/filament/asa-aero-printing-guide
- https://wiki.bambulab.com/en/general/filament-guide-material-table
- https://wiki.bambulab.com/en/filament-acc/filament/slice-param
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/warping-falling-off-collapsing
- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament
- https://wiki.bambulab.com/en/filament-acc/acc/plates
- https://help.prusa3d.com/article/abs_2058
- https://help.prusa3d.com/article/asa_1809
- https://help.prusa3d.com/article/warping_2011
- https://help.prusa3d.com/article/smooth-steel-sheet_196550
- https://help.prusa3d.com/article/textured-steel-sheet_196534
- https://help.prusa3d.com/article/drying-filament_332086
- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html
- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html
- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_skirt.html
- https://wiki.bambulab.com/en/filament-acc/acc/fans
