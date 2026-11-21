---
name: material-pla
description: PLA and its variants (basic, matte, PLA+/tough, high-speed, silk, translucent, wood, LW-PLA/PLA Aero foaming): temperatures, plate and bed keys, cooling, drying, heat creep in enclosed printers and variant-specific Orca settings. Read when the user prints PLA, silk PLA, matte PLA, PLA+, transparent PLA, LW-PLA, foaming PLA or PLA Aero and asks for settings or reports dull/uneven silk shine, brittle silk parts, PLA clogging in a closed printer, oozing foaming PLA or cloudy transparent PLA.
---
# PLA and PLA variants

PLA is the easiest material: low temperature, minimal warping, strong part cooling. Weak points: softens at about 55-60 °C (Bambu PLA Basic HDT 57 °C), brittle, poor UV/heat resistance, layers split on impact. Not for parts in hot cars, outdoors or near heat; suggest PETG/ASA instead (see material-petg, material-abs-asa).

## Baseline (start from the vendor preset; change only what the symptom needs)
| Item | Typical value | Notes |
|---|---|---|
| `nozzle_temperature` (filament) | 200-220 °C (Prusa: 210, first layer 215) | Whole family 190-240 °C; silk 210-240 °C. Faster printing needs the hotter end. |
| Bed, smooth/textured PEI or Engineering plate | 45-65 °C (Prusa PEI: 60 °C) | Engineering plate needs glue. |
| Bed, Cool Plate / Cool Plate SuperTack | 35-45 °C | SuperTack is for PLA/PETG only. |
| Part cooling | strong after the first layers | `close_fan_the_first_x_layers` (filament) 1-3 for adhesion. |
| `filament_max_volumetric_speed` (filament) | from the vendor preset | Calibrate per brand/colour; high-speed PLA allows more. |

Bed keys are per plate type (all filament preset, each with an "_initial_layer" twin): `cool_plate_temp` (Cool Plate), `supertack_plate_temp` (Cool Plate SuperTack), `textured_cool_plate_temp` (Textured Cool Plate), `eng_plate_temp` (Engineering Plate), `hot_plate_temp` (High Temp / Smooth PEI Plate), `textured_plate_temp` (Textured PEI Plate). Change only the one matching the plate selected in Orca; a value of 0 means "plate not supported by this filament". If the selected plate type does not match the physical plate, adhesion fails: tell the user to fix the plate selection first.

## Slicer fixes for common PLA problems
| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `hot_plate_temp` / `textured_plate_temp` (filament) | decrease when PLA clogs in an enclosed printer | -5 °C | stay ≥ 45 °C on PEI; max +10 °C per change, ≤ 120 °C | less adhesion; add brim if corners lift |
| `nozzle_temperature` (filament) | increase for under-melting at high speed or weak layers; decrease for stringing at low speed | ±5 °C | inside filament nozzle_temperature_range_low..high | hotter = more stringing; colder = weak layers |
| `close_fan_the_first_x_layers` (filament) | increase when the first layer lifts | 1 → 3 | 0-3 | none relevant for PLA |
| `brim_type` / `brim_width` (process) | `outer_only`, 8-10 mm for small footprints or lifting corners | +3 mm | 0-100 mm | brim removal marks |
| `filament_retraction_length` (filament) | increase for stringing (after drying) | +0.2 mm | 0..min(8, max(2, 2× printer retraction)) mm | clog risk if too long; nil = printer value |
| `filament_max_volumetric_speed` (filament) | decrease if fast PLA under-extrudes | -2 mm³/s | lower freely, raise ≤ +10% | longer print |
| `filament_flow_ratio` (filament) | tune with the flow calibration | ±0.02 | 0.8-1.2 | dimensions change |

## Variants
### Matte, PLA+, tough, high-speed PLA
- Print as standard PLA within the range printed on the spool. Matte and basic PLA usually need no drying out of the bag.
- High-speed PLA: speed and nozzle temperature go together. Raise `nozzle_temperature` toward the top of the range before raising speed, and run Calibration → Max flowrate to set `filament_max_volumetric_speed`.

### Silk PLA (pearlescent additive)
Shine depends on outer-wall speed and on keeping that speed constant.
- `outer_wall_speed` (process): 40-60 mm/s, start at 50. Fast walls look dull.
- `dont_slow_down_outer_wall` (filament) = `1`: layer-time slowdown no longer changes wall speed (removes bright/dull bands). Inner walls and infill get slowed more instead.
- `layer_height` (process) 0.16 mm on curved surfaces (≤ 75% of nozzle diameter).
- `top_surface_pattern` (process): `archimedeanchords` or `concentric` for shinier tops.
- `nozzle_temperature` / `nozzle_temperature_initial_layer` (filament): silk usually wants 210-240 °C; Bambu Silk is tuned around 235 °C (stay inside the filament range).
- Gloss bands from overhang slowdown or minimum layer time: check the Speed view in preview; print several parts together so layers last longer.
- Z strength is only about 65% of basic PLA: orient loads in XY, raise `wall_loops` and `sparse_infill_density` (process), slow down thin tall parts and add supports.
- Hardware: 0.2/0.4 mm nozzles recommended, 0.6/0.8 not; avoid the Cool Plate SuperTack. Dual-colour silk has an oval cross-section and can twist: not recommended on Bambu A-series.
- Orient the main display surface vertical: flat curved surfaces show steps and lose gloss.

### Translucent / transparent PLA
PLA is semi-crystalline, so it never gets as clear as PETG. Recipe (only with fully dry filament):
- 1 wall (`wall_loops` = 1), `top_shell_layers` = 0, `bottom_shell_layers` = 0, `sparse_infill_density` = `100%` (process). At 100% Orca prints the infill as internal solid infill, so the straight-line pattern goes in `internal_solid_infill_pattern` = `rectilinear` with `solid_infill_direction` 0 or 90 (process).
- `layer_height` 0.1 mm, `line_width` 0.5 mm, all speeds about 20 mm/s (process).
- Slightly higher `nozzle_temperature` and `filament_flow_ratio` (filament).
- Reduce part cooling (`fan_max_speed`, `fan_min_speed`, filament). Turning it fully off makes PLA warp: reduce moderately according to part thickness.
- A 0.8 mm nozzle (user hardware change) gives fewer line boundaries; sand afterwards.

### PLA Wood
Must be dried; wood powder absorbs water and causes stringing. Not for 0.2 mm nozzles; AMS lite not recommended. Noticeable wood smell: ventilate.

### LW-PLA / PLA Aero (active foaming)
Expansion grows with temperature (Prusa LW-PLA: up to about 3× near 240-250 °C; faster printing needs more heat for the same foaming). Retraction barely works because the melt keeps expanding: oozing on travel is normal.
- Prefer vase mode: `spiral_mode` = `1`, `wall_loops` 1, `top_shell_layers` 0, `sparse_infill_density` `0%`, `slicing_mode` = `even_odd`, `wall_generator` = `classic`, `print_sequence` = `by object` for several parts (process).
- Same speed for all features, `enable_overhang_speed` = `0`, moderate acceleration.
- Normal mode: low or zero `filament_retraction_length`, `filament_z_hop` 0, `seam_position` `nearest`; check the preview for unnecessary travel.
- Foaming needs flow ratio far below 1 (0.35-0.95 depending on temperature). The plugin cannot set `filament_flow_ratio` below 0.8: explain the value and let the user set it by hand (Filament → Filament → Flow ratio).
- Bambu PLA Aero: 0.4 mm nozzle only; disable the printer's dynamic flow calibration in the print dialog (user action).
- Damp foaming PLA leaks much more: dry deeply first.

### PLA-CF, PLA Glow, Marble, Sparkle
Abrasive or particle-filled: hardened nozzle, no 0.2 mm nozzle. See material-composites.

## Checks the user must do by hand
- Heat creep in enclosed printers (Bambu X1/P1S/P2S/H2, any printer in a closed enclosure): with the bed above about 45 °C, open the door and/or remove the top lid, or use a low-temperature plate. Prusa: in a closed Original Prusa Enclosure with the room above about 27 °C, PLA can under-extrude or clog. Room 10-30 °C is ideal; in summer also lower the bed 5-10 °C. Bambu groups PLA as low-temperature filament: never in a heated chamber (over about 45 °C).
- After ABS/PC/PETG, load PLA at the previous (hotter) material temperature so it pushes the residue out, or do a cold pull first.
- Clean the plate with warm water and dish soap (Bambu) or IPA (Prusa); no fingerprints. Let the plate cool before removing parts.
- Prusa sheets: satin or smooth PEI give the best PLA adhesion; on the textured sheet the first layer must be slightly lower (live-Z, printer calibration). Small PLA parts on textured/satin may need a brim.
- Ring-shaped bulges where a thick base meets thin walls (box or boat hull) come from internal bridges touching the walls: add an inner fillet/chamfer in CAD.
- PLA is not food-safe as printed (layer grooves trap bacteria).

## Drying
Standard PLA is barely hygroscopic (fine at 50-60% RH). Dry when stringing or popping appears, and always for silk, wood, Aero, translucent and CF:
- Standard PLA: 45-50 °C, 6-8 h.
- Silk / wood / Aero: 55 °C, 8 h (oven or dryer). Bambu AMS 2 Pro / AMS HT: 45 °C, 12 h. Heated-bed drying (enclosed Bambu, spool covered, flipped every 6 h): 60-75 °C, 12 h.
- Never let a dryer exceed the spool's rating; static drying of PLA can fuse the coils.

## Calibration in Orca
Calibration → Temperature (tower) for a new brand/colour, then Flow ratio, Pressure advance, Max flowrate, Retraction test (calibration-guide).

## Sources
- https://wiki.bambulab.com/en/filament/pla
- https://wiki.bambulab.com/en/x1/manual/printing-with-silk-filaments
- https://wiki.bambulab.com/en/general/filament-guide-material-table
- https://wiki.bambulab.com/en/knowledge-sharing/transparent-petg
- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament
- https://wiki.bambulab.com/en/filament-acc/filament/heat-creep
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/different-gloss
- https://wiki.bambulab.com/en/filament-acc/filament/slice-param
- https://wiki.bambulab.com/en/filament-acc/acc/plates
- https://wiki.bambulab.com/en/h2c/h2c-filament-printing-guide
- https://help.prusa3d.com/article/pla_2062
- https://help.prusa3d.com/article/lw-pla_304914
- https://help.prusa3d.com/article/drying-filament_332086
- https://help.prusa3d.com/article/under-extrusion-nextruder-printers_821253
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/warping-falling-off-collapsing
- https://help.prusa3d.com/article/satin-steel-sheet_196526
- https://help.prusa3d.com/article/textured-steel-sheet_196534
- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html
- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_infill.html
