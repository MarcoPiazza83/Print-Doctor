---
name: material-tpu
description: TPU and other flexible filaments (TPU 95A, 90A, 85A and softer, TPE/TPEE, "TPU for AMS"): feeding path and hardware limits, slow speed and volumetric limit, low retraction, temperatures and plate/bed keys, drying, supports and part removal. Read when the user prints TPU, flexible or rubber-like filament and asks for settings or reports TPU not feeding, tangling in the extruder gears, under-extrusion or holes in TPU walls, stringing or oozing with TPU, TPU stuck too hard to the plate, or TPU failing in the AMS.
---
# TPU and flexible filaments

Elastic, wear and impact resistant, low shrinkage and almost no warping, excellent layer adhesion. Hardness is given in Shore A: lower number = softer = harder to print (95A is the easiest; 85A and below need special feeding). Typical uses: tyres, gaskets, bumpers, watch bands, phone cases, shoe soles. Weak points: feeding (the filament buckles), stringing, very poor bridges/overhangs, supports hard to remove, hygroscopic.

## Baseline (start from the vendor preset)
| Item | Typical value | Notes |
|---|---|---|
| `nozzle_temperature` (filament) | 220-240 °C (Bambu 85A/90A: 225 °C; Prusa TPU 95A 220-240) | +5 °C lowers flow resistance; too hot gives bubbles and stringing. |
| Bed (PEI, Engineering, satin/textured) | 30-45 °C on Bambu plates; up to 55-75 °C on Prusa sheets for large parts | Adhesion is rarely the problem: removal is. |
| Cool Plate SuperTack | never | Bonds too strongly. |
| Speed | slow: about 20 mm/s typical, 30-40 mm/s max for soft grades | Bambu: keep the preset's volumetric limit, do not raise speed. |
| Retraction | short or off | Long retractions cause holes and jams. |
| Part cooling | low or off | Lower fan if the nozzle clogs (Prusa). |

Bed keys per plate (filament preset, each with an "_initial_layer" twin): `textured_plate_temp`, `hot_plate_temp` (Smooth PEI / High Temp), `eng_plate_temp`, `cool_plate_temp`, `textured_cool_plate_temp`. Change only the one matching the plate selected in Orca.

## Slicer fixes
| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `filament_max_volumetric_speed` (filament) | decrease for under-extrusion, skipping, tangling | -1 mm³/s | lower freely, raise ≤ +10% | longer print |
| `filament_retraction_length` (filament) | decrease for holes / brief gaps after travel | -0.2 mm (0 is acceptable) | 0..min(8, max(2, 2× printer retraction)) mm | more stringing; nil = printer value |
| `filament_retraction_length` (filament) | increase only for heavy oozing, after drying | +0.1-0.2 mm | same | jams in the gears |
| `print_sequence` (process) — BY HAND | `by object` when many parts are on the plate | n/a | by hand only: Process → Others → Special mode → Print sequence; gantry clearance | fewer long travels = fewer strings |
| `nozzle_temperature` (filament) | +5 °C for under-extrusion/clogs; -5 °C for bubbles and strings | ±5 °C | inside nozzle_temperature_range_low..high | see left |
| `fan_max_speed` (filament) | decrease when the nozzle clogs | -10-20% | 0-100% | worse overhangs |
| `wall_loops`, `top_shell_layers`, `bottom_shell_layers`, `sparse_infill_density` (process) | lower for a softer part, higher for a stiffer/stronger one | ±1 wall, ±10% | n/a | softness/strength trade-off |
| `brim_type` / `brim_width` (process) | add a brim (`outer_only`) for large parts on satin sheets | +3 mm | 0-100 mm | removal effort |

Supports:
- Best: PLA as support material for TPU (multi-material): removes more easily and avoids tangled support surfaces. Pick a PLA colour close to the TPU to avoid staining.
- TPU-only supports: `support_type` `normal(auto)`, `support_base_pattern` `rectilinear-grid` (Bambu, single nozzle). Bigger gaps: `support_top_z_distance` about 0.3 mm and `support_object_xy_distance` at least one line width (process).
- Avoid tall thin TPU parts: they wobble and fail. Bridges and overhangs are poor: orient or design them out.

## Checks the user must do by hand (most TPU failures are feeding hardware)
- Feeding path: as short and straight as possible, spool rotating freely and raised above the extruder inlet. Soft TPU (95A and below) must not go through the AMS, AMS lite or AMS 2 Pro; only "TPU for AMS" can. AMS HT works as a sealed box with its rear TPU outlet; AMS 3H via the bypass port. A 5.8 L dry box with a side opening is preferred (TPU spools widen when dried).
- Bambu A1/A1 mini: TPU 90A or harder (not 85A). H2D/H2C: TPU on the right hotend only; 85A fed directly into the extruder, or with the top-feed rack. P-series: place the part toward the front centre of the bed to reduce tube friction. The optional TPU Feeding Assist Module (H2/X/P) reduces resistance.
- Nozzle: no 0.2 mm. TPU 85A needs 0.6 mm or larger (or the TPU high-flow hotend) on Bambu; standard high-flow nozzles are not recommended for 85A/90A. Use a new or cold-pulled nozzle; never one that printed CF/GF filament.
- Extruder: Prusa: loosen the idler (about 1.5 turns) so the gears grip gently; CORE One+/L have a switch to loosen the filament sensor lever; on the XL and CORE One feed through the tube manually. Bambu: clean the extruder gears, replace worn ones. Load slowly with short extrude clicks so the TPU does not wrap around the gears; if it tangles, the extruder must be opened and cleared.
- Bambu A1 TPU 90A: disable dynamic flow calibration in the print dialog. Automatic filament change and runout sensors may not work with flexibles.
- Dry before printing (Bambu: required). Oven 60-70 °C for 4-8 h (Prusa TPU 60 °C / 4-6 h; Bambu 70 °C / 8 h); AMS HT 75 °C, 18 h; heated bed of enclosed Bambu printers 80-90 °C, 12-16 h. AMS 2 Pro (max 65 °C) does not dry it fully. Store below 20% RH.
- TPU left loaded for a long time between prints can deform in the extruder: unload and reload.
- Plates: Bambu Textured PEI without glue (glue makes it stick too much); other Bambu plates with glue. Prusa: textured sheet without glue, satin and smooth PEI only with a glue-stick separation layer (bare smooth PEI gets damaged). Removal: let the plate cool (Prusa textured: warm to about 40 °C), lift a corner and spray alcohol into the gap, never force it.
- Enclosed printers: TPU softens below 60 °C; keep the chamber cool (door open if the bed is above about 45 °C).

## Calibration in Orca
Calibration → Temperature and Max flowrate (start from a low range); Retraction test with the default 0-2 mm range and 0.1 mm steps, choosing the shortest clean length; then Flow ratio and Pressure advance as for other filaments (calibration-guide). Bambu A1 series with TPU 90A: leave the printer-side dynamic flow calibration off.

## Sources
- https://wiki.bambulab.com/en/knowledge-sharing/tpu-printing-guide
- https://wiki.bambulab.com/en/filament-acc/filament/tpu-85a-90a-printing-guide-for-a-series
- https://wiki.bambulab.com/en/filament-acc/filament/tpu-85a-90a-printing-guide-for-p-series
- https://wiki.bambulab.com/en/h2/h2d-tpu-printing-guide
- https://wiki.bambulab.com/en/h2/troubleshooting/tpu-clogging
- https://wiki.bambulab.com/en/h2c/h2c-filament-printing-guide
- https://wiki.bambulab.com/en/general/filament-guide-material-table
- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament
- https://help.prusa3d.com/article/flexible-materials_2057
- https://help.prusa3d.com/article/prusament-tpu-95a-material-guide_899653
- https://help.prusa3d.com/article/satin-steel-sheet_196526
- https://help.prusa3d.com/article/textured-steel-sheet_196534
- https://help.prusa3d.com/article/smooth-steel-sheet_196550
- https://help.prusa3d.com/article/drying-filament_332086
- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html
- https://www.orcaslicer.com/wiki/calibration/retraction_calib.html
