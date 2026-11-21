---
name: defect-overhangs-bridges
description: Drooping, sagging or curling overhangs and bridges (unsupported walls, ceilings, hole tops, spans between two points) and the Orca overhang/bridge speed, flow, cooling and support-threshold settings that fix them. Read when the user reports droopy or saggy overhangs, curled-up overhang edges, a messy underside, bridge strings that sag, break or leave gaps, or a rough ceiling over a hole or gap.
---
# Overhangs and bridges: drooping, curling, sagging

## How to recognize it
- Overhang droop: walls that lean outward look ragged, wavy or melted on the underside; layers sag and stack unevenly. Gets worse as the angle approaches horizontal.
- Overhang curl: the edge of an overhang lifts up (often at sharp corners like a boat bow) and the nozzle may hit it on following layers.
- Bridge sag: lines spanning a gap hang down in the middle, droop as loose strings or break.
- Bridge gaps: bridge lines stay round and do not touch each other, leaving a see-through or ribbed ceiling.
- Ask which side of the part and which feature (wall, hole top, flat ceiling); check the Preview with the "Line type" view to see whether Orca actually printed the area as bridge or overhang wall.

## Likely causes, most common first
1. Geometry beyond what the material can do: overhang angle (measured from the bed) below about 45° needs support; very long bridges sag no matter what.
2. Not enough cooling on overhangs and bridges (fan too low, overhang fan threshold too high, enclosed chamber too warm for PLA/PETG/TPU).
3. Overhang walls or bridges printed too fast (overhang slowdown off or not slow enough, high outer wall speed).
4. Nozzle temperature at the top of the range: hot plastic stays soft longer and droops.
5. Bridge flow/density/thickness not matched to the span: too little material makes lines that do not touch or snap; too much makes them hang.
6. Bridge direction not across the shortest span (Orca normally picks it automatically).
7. Thick layers: each layer steps out further over the one below.
8. Hardware: part cooling fan weak, dirty or obstructed duct, wet filament.

## Questions worth asking (only when the answer changes the fix)
- Material and printer (enclosed or open)? Decides how much fan and whether to open the door.
- Overhang or bridge, and roughly how long is the span / what angle? Long spans and angles below ~45° go to supports first.
- Sagging lines or gaps between lines? Opposite bridge-flow directions.
- Does the overhang curl upward or droop downward? Curl -> cooling + curled-perimeter slowdown; droop -> speed/temperature/cooling.
- Are supports acceptable? If not, use the no-support levers (speed, cooling, angle limit, geometry change).

## Slicer fixes
Check first that `detect_overhang_wall` (process) is `1`; most overhang features depend on it. Change one or two things at a time and reprint a small test.

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `enable_overhang_bridge_fan` (filament) | set `1` | on | boolean | none for PLA; more warping risk on ABS/ASA/PA/PC |
| `overhang_fan_speed` (filament) | increase | +10-20 % | max 100 %; ABS/ASA/PA/PC raise cautiously | cooling can weaken layer bonding and warp high-temp materials |
| `overhang_fan_threshold` (filament) | lower | one enum step (e.g. `50%` -> `25%` -> `10%`) | enum `0%`,`10%`,`25%`,`50%`,`75%`,`95%` | `0%` forces the overhang fan on all outer walls |
| `enable_overhang_speed` (process) | set `1` | on | boolean | longer print time |
| `overhang_3_4_speed` / `overhang_4_4_speed` (process) | decrease | -5 to -10 mm/s (or a lower % of wall speed) | about 10 mm/s minimum; 0 = no slowdown | time; big speed jumps can leave wall marks if PA is off |
| `overhang_1_4_speed` / `overhang_2_4_speed` (process) | decrease if mild overhangs are rough | -10 mm/s | typical overhang range 10-60 mm/s | time |
| `slowdown_for_curled_perimeters` (process) | set `1` for curling at corners | on | boolean | possible wall artifacts at high speeds; needs good PA |
| `bridge_speed` (process) | decrease when bridges sag | -5 mm/s | about 10 mm/s minimum; test 10-50 mm/s | slower is not always better: test per filament |
| `nozzle_temperature` (filament) | decrease | -5 °C | inside nozzle_temperature_range_low..high | under-extrusion, weaker layers if too low |
| `bridge_flow` (process) — BY HAND | lower if lines sag/hang; raise if lines do not touch | ±0.05 | by hand only (plugin cannot check it), keep 0.7-1.5: Process → Quality → Bridging → Flow ratio | low: thin, breaking lines; high: hanging bulges |
| `bridge_density` (process) | raise if gaps between bridge lines | +5 % | 100-125 % | over-extruded bridge surface |
| `thick_bridges` (process) | `1` for long spans; `0` for short spans and nicer look | toggle | boolean | on: stronger but rougher, can sag on short bridges; off: thin lines can snap on long or low-layer bridges |
| `enable_extra_bridge_layer` (process) | set `external_bridge_only` | enum | `disabled`, `external_bridge_only`, `internal_bridge_only`, `apply_to_all` | slightly more time |
| `bridge_angle` (process) | set to the direction of the shortest span if auto picks badly | degrees | 0 = auto (default), 0-180 | wrong angle makes spans longer |
| `extra_perimeters_on_overhangs` (process) | set `1` for steep overhangs and unanchored bridges | on | boolean; needs `detect_overhang_wall` | more time |
| `overhang_reverse` (process) | set `1` for steep overhangs and curling | on | boolean | texture on outer wall; add `overhang_reverse_internal_only` = `1` to keep the outer wall smooth |
| `outer_wall_speed` (process) | decrease when all overhangs are rough | -10-20 % | never above printer limits | time |
| `layer_height` (process) | decrease | -0.04 mm | ≤ 75 % of nozzle diameter, min 0.04 mm | longer print |
| `enable_support` (process) + `support_threshold_angle` (process) | enable for angles below ~45° or long bridges; raise threshold to support more | +5° | 0-90; Orca default 30 | material, removal marks (see defect-supports) |
| `max_bridge_length` (process, tree support) / `bridge_no_support` (process, normal support) | lower length / set `0` so long bridges get supported | -5 mm | 0 = support all bridges | more support |
| `make_overhang_printable` (process) + `make_overhang_printable_angle` (process) | enable, angle 45-60° | on | changes the model shape (adds cone material) | only when shape change is acceptable |
| `counterbore_hole_bridging` (process) | `partiallybridge` or `sacrificiallayer` for counterbores | enum | `none`,`partiallybridge`,`sacrificiallayer` | sacrificial layer must be broken out |

Notes for the AI:
- Bridge flow logic in Orca: values below 1.0 reduce material per line and tighten spacing (less sag); above 1.0 add material at the same spacing (better line contact). Internal bridges over infill use `internal_bridge_flow` (process, by hand, same menu) and `thick_internal_bridges` (process) - see defect-top-surface for pillowing.
- Overhang speeds as % are taken from outer/inner wall speed. When overhangs are 100 % unsupported Orca treats them as bridges and `bridge_speed` applies.
- For long bridges the most reliable fix is a support enforcer (painted support) in the middle of the span, which splits it into two short bridges.

## Checks the user must do by hand (hardware, material, printer settings)
- Part cooling fan: spins at full speed, duct clean and not cracked or blocked. Bambu printers with an auxiliary fan: check that it works; whether the printer has one is a printer setting (`auxiliary_fan`) the user changes by hand only if wrong.
- PLA, PETG, TPU on enclosed printers: open the front door and/or top lid for overhang-heavy prints. Do not do this for ABS, ASA, PA, PC (warping, weak layers).
- Filament dry (wet filament oozes and makes bubbly, weak bridges).
- Orientation: rotate the part so overhangs face up or bridges become shorter; split with the Cut tool; chamfer instead of flat overhangs in CAD.
- Paint support enforcers under the worst overhang or in the middle of a long bridge (Prepare -> Support painting).
- Nozzle not partially clogged (inconsistent flow ruins bridges first).

## Calibration in Orca (menu Calibration → ...)
- Temperature: pick the tower block with the cleanest overhangs and bridges that still bonds well (if several look good, take the middle of that range); too hot causes sagging. Value goes to `nozzle_temperature`.
- Flow ratio and Pressure advance first, so overhang slowdowns do not create blobs at speed transitions.
- Max flowrate (max volumetric speed) if you also raise other speeds.
- Bridges: no dedicated Orca test; print a bridge test model several times with per-object `bridge_flow` (by hand) / `bridge_speed` overrides and keep the best (see calibration-guide).

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- PLA: best overhangs of all; overhang fan 100 %, slightly lower temperature (e.g. Bambu PLA around 205 °C on later layers) and slow overhang speeds. Open the enclosure.
- PETG: droops and strings more; lower temperature 5-10 °C within range, strong overhang fan, slower bridges; open the enclosure.
- ABS/ASA: keep the enclosure closed; use moderate overhang fan and slower speeds rather than full cooling; rely on supports earlier.
- TPU: slow everything; cooling helps; open the enclosure.
- PA/PC: like ABS - limited cooling, enclosure closed, support earlier.
- CF/GF filled: similar to the base polymer; fibres make lines stiffer but rougher.
- See the material-* skills for full profiles.

## Sources
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/overhang
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/bridging
- https://wiki.bambulab.com/en/software/bambu-studio/parameter/bridge
- https://wiki.bambulab.com/en/software/bambu-studio/slow-down-for-overhang
- https://wiki.bambulab.com/en/software/bambu-studio/support
- https://help.prusa3d.com/article/poor-bridging_1802
- https://help.prusa3d.com/article/support-material_1698
- https://www.simplify3d.com/resources/print-quality-troubleshooting/poor-bridging/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/poor-surface-above-supports/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/curling-or-rough-corners/
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_overhangs.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_bridging.html
- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_overhang_speed.html
- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_advanced.html
- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html
- https://www.orcaslicer.com/wiki/calibration/temp_calib.html
