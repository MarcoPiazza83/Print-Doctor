---
name: material-pa-pc
description: Printing nylon (PA6, PA11, PA12/PAHT) and polycarbonate (PC, PC Blend, PC FR) in Orca: temperatures, plates and glue, drying, enclosure, warping and layer cracking, and which filament/process keys to adjust. Read when the user prints nylon, PA or PC/polycarbonate and reports warping, corners lifting, cracks between layers, bubbles, popping or foamy surface, weak or brittle parts, poor bed adhesion or a damaged plate.
---
# PA (nylon) and PC (polycarbonate)

Scope: unfilled PA and PC and their blends. Fibre-filled grades (PA-CF, PA6-GF, PAHT-CF, PC-CF): read material-composites as well (hardened nozzle, clog risk, speed caps); warping and drying advice here still applies.

## Material profile (start values; the spool label wins)
| | PA (nylon) | PC and PC blends |
|---|---|---|
| Nozzle | 240-285 °C (pure PA often ~285 °C) | 260-290 °C (PC Blend ~275 °C) |
| Bed | 100-110 °C, with glue | 100-115 °C (first layer ~110, then ~115), with glue |
| Enclosure | required for pure PA; CF-filled PA warps far less | required for anything larger than small parts |
| Drying (oven/dryer) | 80-85 °C, 8-12 h (stay below 90 °C) | 75-85 °C, 5-8 h |
| Moisture | extreme: can absorb up to ~10% of its weight | pure PC extreme; PC Blend absorbs much less |
| Plate | Prusa Special PA Nylon sheet (no glue), or textured/satin/engineering/smooth PEI with glue stick | textured or satin PEI with glue stick; Bambu engineering/smooth/textured with glue stick |
| Fumes | strong odour, ultrafine particles: ventilate | moderate odour |

- PA6-based parts lose a large share of stiffness and strength when they take up water; PA12-based grades (PAHT) absorb roughly half as much as standard PA.
- Bambu: PA and PC need an enclosed printer (not P1P or A-series), are not for AMS lite, and want glue stick (liquid glue is not recommended for PA/PC). PC is not recommended with a 0.2 mm nozzle.
- Pure PA is a good cleaning filament for cold pulls.

## How to recognize material-specific problems
- **Wet filament**: popping/hissing, steam at the nozzle, bubbles and voids in walls, foamy or rough surface, uneven layers, strings, weak parts. Most common root cause with PA and PC: check before touching any setting.
- **Warping / lifting / part detaching**: shrinkage on cooling; worst on large flat parts, sharp corners, dense infill, cold room or open door.
- **Cracks between layers** (tall walls splitting): internal cooling stress larger than layer bond. Causes: too much fan, cold chamber, filament not fully melted (too cold or too fast), clogged nozzle.
- **Plate damage / part ripped PEI**: PC bonds too strongly to bare smooth PEI; PA sheet damaged by IPA or acetone.
- **Sagging bridges**: hot material cools slowly; add supports under long bridges.

## Diagnostic order
1. Filament dry? (when in doubt, dry it: see table above; materials-overview for methods).
2. Door and lid closed, no drafts; room not cold (Prusa: below ~18 °C the bed may fail to hold PC temperatures).
3. Right plate, clean (dish soap and water), glue applied where required.
4. Only then change slicer values, one or two per round.

## Slicer fixes
| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| plate keys for the plate in use: `textured_plate_temp`, `hot_plate_temp`, `eng_plate_temp` and their _initial_layer variants, e.g. `textured_plate_temp_initial_layer` (filament) | increase against warping/lifting | +5 °C | at most +10 °C over current, never above 120 °C | elephant foot, part harder to remove |
| `fan_max_speed` (filament) | decrease against layer cracks/warping | -10 points | ≥ 0; keep some fan for bridges | droopier overhangs and bridges |
| `fan_min_speed` (filament) | decrease | -5 to -10 points | ≤ `fan_max_speed` | as above |
| `close_fan_the_first_x_layers` (filament) | increase | +1 to +2 layers | 1-5 layers | first overhangs above the base less cooled |
| `nozzle_temperature` (filament) | increase for weak layers/cracks/under-melting; decrease for oozing | ±5 °C | inside the filament's recommended range (plugin-checked) | hotter = more stringing and oozing |
| `brim_type` (process) = `outer_only` with `brim_width` (process) | enable for small footprints, corners, any PC/PA part that lifts | 5-10 mm | 10 mm usually enough | brim removal, slight mark on the edge |
| `sparse_infill_density` (process) | decrease on large parts | -5 to -10% | keep ≤ 50% | weaker part |
| `wall_loops` (process) | fewer on large warping PC parts; more for strength on small parts | ±1 | ≤ 6 | more walls = more shrink stress |
| `outer_wall_speed`, `inner_wall_speed` (process) | decrease if layers crack or look under-melted | -10 to -20% | never above machine limits | longer print |
| `filament_max_volumetric_speed` (filament) | decrease when fast sections under-extrude or crack | -10 to -20% | may be lowered freely, raised at most +10% | longer print |
| `draft_shield` (process) = `enabled` | open-frame printer or draughty room | - | - | extra material and time |
| `enable_support` (process) under long bridges | add | - | - | support marks |
| `activate_air_filtration` (filament) = 1 — BY HAND | odour control on printers with a filter fan | - | by hand only (plugin cannot check it): Filament → Cooling → Exhaust fan; only if the printer has one | none |

Strength without warping: `sparse_infill_pattern` = `gyroid`, infill ≤ 50%, ≤ 6 walls; orient the part so the main load runs along the layers, not across them (a ~45° tilt is a compromise between warping and Z strength). For warping in depth see defect-warping; for cracks see defect-layer-adhesion.

## Checks the user must do by hand
- **Dry** the spool, then print from a sealed box or AMS with fresh desiccant. Check spool heat rating before drying (Bambu low-temp spools ~70 °C max; old black Prusament spools only ~45 °C unless screwed together).
- **Chamber**: keep door and lid closed. Bambu X1C/P1S: preheat the bed at maximum for ~15 min before starting to warm the chamber. Chamber heating (H2 series, X1E) is a printer/filament option the plugin does not change: tell the user to check it.
- **Plate**: clean with dish soap and hot water (no acetone on Bambu plates); glue stick for PA and PC; never PC on bare smooth PEI. Prusa Special PA Nylon sheet: water and dish soap only, never IPA, acetone or alcohol cleaners.
- **Model**: rounded corners warp less than sharp ones; split or shrink full-bed parts.
- **Nozzle**: filled grades need hardened steel; set the correct nozzle type in printer settings (`nozzle_type`, printer setting, changed by hand).
- **Next filament**: before switching to PLA/PETG, purge at the PA/PC temperature first, then cool down while extruding, or the old residue clogs.
- **Bambu H2D/H2C**: PA/PC belong to the high-temperature group and cannot share a job with PLA/PETG/TPU/PVA.

## Calibration in Orca
Dry the filament first, then: Calibration → Temperature (temp tower inside the range), Flow Rate, Pressure Advance, Max Volumetric Speed. Results go to `nozzle_temperature`, `filament_flow_ratio`, `pressure_advance` and `filament_max_volumetric_speed` (filament). See calibration-guide.

## Material notes
- PA-CF/PAHT-CF/PA6-GF: much less warping, hardened nozzle, lower volumetric caps (material-composites).
- PC FR and PC Blend: easier than pure PC; same plate and drying rules.
- Prusa PC Blend on satin sheet can print without glue occasionally; regular use still benefits from glue as protection.

## Sources
- https://wiki.bambulab.com/en/filament/abs_asa_pc
- https://wiki.bambulab.com/en/filament/absgf_pa6gf
- https://wiki.bambulab.com/en/filament/asacf_pahtcf
- https://wiki.bambulab.com/en/filament/petcf_ppacf
- https://wiki.bambulab.com/en/general/filament-guide-material-table
- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament
- https://wiki.bambulab.com/en/filament-acc/filament/slice-param
- https://wiki.bambulab.com/en/filament-acc/filament/h2d-filament-config-limit
- https://wiki.bambulab.com/en/knowledge-sharing/how_to_avoid_nozzle_clogs
- https://help.prusa3d.com/article/polyamide-nylon_167188
- https://help.prusa3d.com/article/polycarbonate-pc_165812
- https://help.prusa3d.com/article/special-pa-nylon-steel-sheet_341570
- https://help.prusa3d.com/article/drying-filament_332086
- https://help.prusa3d.com/filament-material-guide
- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html
- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html
