---
name: material-petg
description: PETG family (PETG basic, PETG-HF high-flow, matte, translucent/transparent PETG, PETG V0, CPE, PCTG): temperatures, plate choice and bed keys, cooling trade-off, flow ratio window, stringing and nozzle build-up, wet-filament printing, transparency recipe. Read when the user prints PETG, PETG HF, CPE or PCTG and asks for settings or reports PETG stringing, oozing, blobs or filament sticking to the nozzle, PETG stuck too hard to the plate or tearing PEI, clogging, cloudy transparent PETG, poor PETG bridges or supports that will not come off.
---
# PETG, PETG-HF, CPE, PCTG

Tough, heat-resistant to about 70-80 °C, good layer adhesion, low warping, glossy. Weak points: stringing and oozing, poor bridges/overhangs, bonds very hard to smooth PEI and to its own supports, scratches easily, fairly hygroscopic. Good for mechanical, outdoor and water-exposed parts.

## Baseline (start from the vendor preset)
| Item | Typical value | Notes |
|---|---|---|
| `nozzle_temperature` (filament) | PETG 230-250 °C (Prusa 240, first layer 230; Bambu PETG range 240-270) | PETG-HF and translucent 230-260; PETG V0 220-240; CPE about 275 °C. |
| Bed, PEI (smooth/textured) or Engineering plate | 70-80 °C (Bambu range 60-80, Prusa 85-90) | Smooth PEI only with a glue-stick separation layer. |
| Bed, Cool Plate SuperTack | 55-65 °C | Original (non-SuperTack) Bambu Cool Plate: not recommended. |
| `filament_flow_ratio` (filament) | 0.93-0.96 (Bambu PETG default 0.95) | Below 0.93 weak/gappy; above 0.96 oozing and nozzle build-up. |
| Cooling | moderate | First few layers no fan (`close_fan_the_first_x_layers`), then partial fan; more fan = detail, less fan = stronger part. |

Bed keys per plate (filament preset, each with an "_initial_layer" twin): `supertack_plate_temp`, `cool_plate_temp`, `textured_cool_plate_temp`, `eng_plate_temp`, `hot_plate_temp` (Smooth PEI / High Temp), `textured_plate_temp`. Change only the one matching the plate selected in Orca.

## Slicer fixes for PETG problems (dry the filament first: most PETG stringing is moisture)
| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `filament_flow_ratio` (filament) | decrease for oozing, blobs, material on the nozzle | to 0.93-0.94 | 0.8-1.2; do not go below 0.93 for PETG | under-extrusion, weaker layers |
| `nozzle_temperature` (filament) | decrease when printing slowly or stringing | -5 °C (up to -10) | inside nozzle_temperature_range_low..high | weaker layers if too cold |
| `filament_max_volumetric_speed` (filament) | decrease for build-up, clogs, wet PETG-HF | -4 mm³/s | lower freely, raise ≤ +10% | slower print; lower temperature with it |
| `fan_max_speed` (filament) | increase for nozzle build-up and stringing | +10-20% | 0-100% | less layer strength, more warping |
| `filament_retraction_length` (filament) | increase for strings on travel | +0.2 mm, typical 1.2-1.6 mm | 0..min(8, max(2, 2× printer retraction)) mm; keep < 2 mm on direct drive | too long = clog; nil = printer value |
| `filament_retraction_speed` (filament) | increase with the length | 40-60 mm/s | > 0, ≤ max(1.5× printer value, 30 mm/s) | grinding if excessive |
| `line_width` / `inner_wall_line_width` (process) | decrease if material collects on the nozzle | 0.36-0.40 mm on a 0.4 nozzle | 0.75-1.5× nozzle diameter | slightly weaker part |
| `outer_wall_speed` (process) | decrease for bumps/dips after overhangs or speed changes | about 90 mm/s | ≤ printer limits | longer print |
| `max_volumetric_extrusion_rate_slope` (process) | enable (non-zero) to smooth flow changes | 35-50 mm³/s² at 1000 mm/s² outer-wall acceleration, 70-100 at 2000, 145-200 at 4000 (0.42 mm line, 0.16 mm layer) | 0 = off; above those values it has no effect | turns off arc fitting; slightly longer print |
| `brim_type` / `brim_width` (process) | `outer_only` for lifting corners or large parts | +3 mm | 0-100 mm | removal marks |
| `wall_loops` (process) | increase for strength instead of more infill | +1 | ≤ 6 walls, infill ≤ 50% | more shrinkage stress/warping |

- Seam on an overhang ruins that surface: move it with `seam_position` (process) or seam painting.
- Strength: walls give more than infill; orient so the load is not across layers.
- Wet PETG-HF with no dryer available: print slower and cooler (Bambu "Generic PETG HF" uses about 220 °C and 16 mm³/s); do not speed up at that temperature. Dry it as soon as possible.

## Supports
PETG fuses strongly to PETG supports. Options:
- Larger `support_top_z_distance` and `support_object_xy_distance` (process); see defect-supports.
- Multi-material: PLA as support interface for PETG (and PETG for PLA) separates cleanly. Use the other material only for the interface (`support_interface_filament`, process), not the whole base; Bambu tested only PLA Basic with PETG Basic/HF. Both on Smooth or Textured PEI at about 60 °C, door open on enclosed printers. When PETG is the support for PLA, Bambu limits PETG `filament_max_volumetric_speed` to about 10 mm³/s.

## Translucent / transparent PETG
PETG is amorphous and clears better than PLA. Only with fully dried filament:
- `wall_loops` 1, `top_shell_layers` 0, `bottom_shell_layers` 0, `sparse_infill_density` `100%` (process). At 100% Orca prints the infill as internal solid infill: set `internal_solid_infill_pattern` `rectilinear` and `solid_infill_direction` 0 or 90 (process).
- `layer_height` 0.1 mm, `line_width` 0.5 mm, all speeds about 20 mm/s.
- Moderately higher `nozzle_temperature` and `filament_flow_ratio` (fills gaps between lines).
- Part cooling off (`fan_min_speed` and `fan_max_speed` 0, filament) for slow, even cooling.
- 0.8 mm nozzle recommended (hardware, user); sand the surface afterwards. Complex geometry limits clarity regardless of settings.

## Variants
- PETG-HF: high-flow PETG tuned for speed; same temperature logic (faster = hotter). Very sensitive to moisture.
- PETG matte (Bambu): Textured PEI, Smooth PEI or Cool Plate SuperTack.
- PETG V0 (Prusament, self-extinguishing): more hygroscopic than PETG; dry 6 h at 55 °C before use if not stored dry; satin/textured sheet.
- CPE: copolyester between PETG and ABS, prints like PETG at about 275 °C nozzle / 90 °C bed; same smooth-PEI warning.
- PCTG: Bambu lists it with PLA/PETG as low-temperature filament (no heated chamber). Use the vendor's ranges.
- PETG-CF, glow/Ultraglow PETG: abrasive, hardened nozzle, prefer 0.6 mm: see material-composites.

## Checks the user must do by hand
- Dry PETG: oven 55-65 °C for 6-8 h (Prusa 55 °C / 6 h; Bambu 65 °C / 8 h); Bambu AMS 2 Pro/HT 65 °C, 8 h; heated-bed drying on enclosed Bambu printers 75-85 °C, 12 h, spool covered and flipped every 6 h. Store below 20% RH with desiccant. Popping, bubbles, heavy stringing = wet.
- Plate: Prusa satin or textured sheet. Never bare smooth PEI: PETG can tear the surface; apply a thin glue-stick layer. Bambu: glue helps on Engineering plate; brim for large parts.
- Enclosed printers: PETG softens at 60-80 °C. With the bed above about 70 °C, open the door or lift the lid to avoid heat creep; in a cold room an enclosure helps layer strength. Never heated-chamber temperatures (above about 45 °C).
- Material building up on the nozzle with dry filament: check the nozzle for wear and replace it; check the nozzle wiper (Bambu) for wear or a loose mount.
- Many long travel moves (plate layout) increase oozing: arrange parts closer.
- Ring-shaped bulges where a thick base meets thin walls: add an inner fillet/chamfer in CAD.

## Calibration in Orca
Calibration → Temperature, Flow ratio (expect 0.93-0.96), Pressure advance, Retraction test, Max flowrate. On Bambu printers do not tick the printer's own flow calibration in the send dialog for these tests (calibration-guide).

## Sources
- https://wiki.bambulab.com/en/filament/petg
- https://wiki.bambulab.com/en/filament-acc/filament/petg-hf-unfinished-drying
- https://wiki.bambulab.com/en/knowledge-sharing/transparent-petg
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/filament-sticks-to-nozzle
- https://wiki.bambulab.com/en/filament-acc/filament/h2d-pla-and-petg-mutual-support
- https://wiki.bambulab.com/en/general/filament-guide-material-table
- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament
- https://wiki.bambulab.com/en/filament-acc/acc/plates
- https://wiki.bambulab.com/en/h2c/h2c-filament-printing-guide
- https://help.prusa3d.com/article/petg_2059
- https://help.prusa3d.com/article/petg-v0_1050343
- https://help.prusa3d.com/article/cpe_166877
- https://help.prusa3d.com/article/prusament-petg-ultraglow-troubleshooting_1043965
- https://help.prusa3d.com/article/smooth-steel-sheet_196550
- https://help.prusa3d.com/article/drying-filament_332086
- https://www.orcaslicer.com/wiki/material_settings/filament/material_flow_ratio_and_pressure_advance.html
- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_advanced.html
- https://www.orcaslicer.com/wiki/calibration/flow_ratio_calib.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_infill.html
