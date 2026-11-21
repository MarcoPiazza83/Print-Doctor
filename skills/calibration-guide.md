---
name: calibration-guide
description: Which OrcaSlicer calibration test (menu Calibration) fixes which defect, the order to run them, how to read each printed test and which Orca key receives the result. Read when the user asks how to calibrate or tune a new filament, or mentions a temperature tower, flow ratio / flow rate / extrusion multiplier test, pressure advance / K factor / linear advance / flow dynamics, retraction tower, max volumetric speed / max flowrate test, VFA, input shaping, jerk / cornering, tolerance test or adaptive PA.
---
# Calibration guide (OrcaSlicer 2.5.1)

## Rules for the AI
- The user runs every test from the **Calibration** menu in the top bar; each test opens a new project. Afterwards tell the user to start a new project to leave calibration mode.
- Calibrate with the same printer, filament and process presets that will be used. The flow ratio test starts from the value already in the filament preset.
- Choose the test, explain how to read it, do the arithmetic, propose the change. Printer/firmware results (input shaping, jerk, resonance avoidance) are entered by the user by hand.
- Rule out hardware first, or the numbers are meaningless: dry filament, clean nozzle without partial clog, clean extruder gears, clean plate, correct first layer.
- Bambu printers: when sending an Orca test, untick the flow (dynamics) calibration option in the send dialog, otherwise the printer measures its own value and the test is not what was printed.

## Symptom → test → key
| Symptom | Test | Result goes to |
|---|---|---|
| Stringing plus weak layers, saggy bridges, rough or dull walls | Temperature | `nozzle_temperature`, `nozzle_temperature_initial_layer` (filament) |
| Under-extrusion or matte, rough walls only at high speed; extruder clicks | Max volumetric speed | `filament_max_volumetric_speed` (filament) |
| Bulging or rounded corners, gaps right after corners, thin or blobby line ends, uneven seams | Pressure advance | `enable_pressure_advance`, `pressure_advance` (filament) |
| Gaps or ridges between top lines, general over/under-extrusion, walls too thick | Flow ratio | `filament_flow_ratio` (filament) |
| Strings and blobs once temperature is right | Retraction | `filament_retraction_length` (filament) |
| Holes too small, parts do not fit | Tolerance test | `xy_hole_compensation`, `xy_contour_compensation` (process) |
| Ringing / ghosting after sharp corners | Input shaping | printer firmware (by hand) |
| Fine vertical ripples at certain speeds | VFA | printer resonance avoidance (by hand) or `outer_wall_speed` (process) |
| Corners overshoot | Cornering | printer jerk / junction deviation (by hand) |
| PA right at one speed, wrong at another | Adaptive PA | `adaptive_pressure_advance_model` (filament) |

## Order
1. Filament calibration, repeat for each new filament: **Temperature → Max flowrate → Pressure advance → Flow ratio → Retraction**. If flow ratio moved a lot, rerun a quick PA test.
2. Advanced, mostly printer-related, only after hardware changes or moving the printer: Cornering → Input shaping → VFA → Adaptive PA.
3. Tolerance last, because it depends on everything above.

## Temperature (Calibration → Temperature)
- Tower of blocks, each block printed at a different nozzle temperature. Keep start and end inside the filament's recommended range.
- Read each block: stringing (cooler is usually better, too cold strings too), layer bonding (hotter is stronger), bridges/overhangs (too hot sags), finish.
- Several good blocks: take the middle. For fast or high-flow printing take the upper part of the good range.
- Save: `nozzle_temperature` (filament); `nozzle_temperature_initial_layer` equal or slightly higher. Safe limit: inside the filament's minimum..maximum range (enforced by the plugin). Never edit the range itself.

## Max volumetric speed (Calibration → Max flowrate)
- Default start 5, end 20 mm³/s, step 0.5. If it reaches the top intact, reprint with a higher end.
- Read three heights from the bottom: (1) gloss lost / finish rougher, (2) quality lost: walls deform, first at curves, (3) failure: heavy deformation and under-extrusion.
- Flow at a height = start + height_mm × step, or read it in Preview with the "Flow" colour scheme at that layer.
- Save `filament_max_volumetric_speed` (filament) below point (2) with a 10-20 % margin, never at point (3). The plugin allows lowering freely but raising by at most +10 % per change; if the test shows a much higher limit, raise in steps or let the user set it by hand.
- Point (1) is meant for a separate "max external volumetric speed" limit that is not a key in Orca 2.5.1; to keep visible surfaces glossy, lower `outer_wall_speed` and `top_surface_speed` (process) instead.
- Faster flow needs the upper part of the temperature range. Bambu 0.2 mm nozzle: about 2 mm³/s.

## Pressure advance (Calibration → Pressure advance)
- Use the direct-drive or Bowden version matching the extruder. Marlin needs Linear Advance enabled (M900).
- **Tower**: does not depend on the first layer. PA rises one step per mm of height: PA = start + step × height_mm (example 0 + 0.002 × 8 = 0.016).
- **Pattern**: chevrons with printed values; pick the corner that is sharp and fully extruded, no bulge, no gap.
- **Line**: fastest, depends on the first layer (enable bed mesh). Pick the most even line.
- Too low PA: corners bulge and round off. Too high: gaps, thin or missing extrusion at corners and line starts.
- Save: `enable_pressure_advance` = `1` and `pressure_advance` (filament). Direct-drive results are usually a few hundredths (examples 0.015-0.036).
- Bambu Lab: the printer stores a K value per filament (Flow Dynamics calibration: automatic on X1, A1, H2 and P2S series, manual only on P1). When `enable_pressure_advance` is `1` the slicer value overrides the stored one. Expect about 10 % scatter between runs; automatic K on eddy-sensor printers (A1, H2D) is intentionally higher than a manual pattern result. With 0.2 mm nozzles automatic K is unreliable: use the manual pattern.
- Prusa (MK4/S, MK3.9/S, XL, MINI/+): firmware Pressure Advance; the stock start G-code sets a tuned value per nozzle size and Prusa recommends keeping it. Override only when a test is clearly better.

## Flow ratio (Calibration → Flow ratio)
- **YOLO (recommended)**, Archimedean-chords blocks: range -0.05..+0.05, step 0.01 ("perfectionist": -0.04..+0.035, step 0.005). New = old + modifier (0.98 + 0.01 = 0.99).
- **Pass 1 / Pass 2** (legacy, monotonic lines): new = old × (100 + modifier) / 100; Pass 2 covers -9..0 around the Pass 1 result.
- Read the top surface under low-angle light: smoothest surface, no gaps between lines, little or no ridge where the inner spiral meets the outer arcs. Reject blocks with faint gaps.
- Save `filament_flow_ratio` (filament). Plugin limit 0.8-1.2; typical results 0.95-1.05. Leave `print_flow_ratio` (process) at `1`: it multiplies the filament value.
- Foaming filaments (LW-PLA, PLA Aero, LW-ASA) need ratios far below 0.8 (Bambu starts near 0.6): outside the plugin limit, the user sets it by hand.
- Bambu X1 lidar auto flow: not for transparent, silk, sparkle, marble, metal-look or TPU; use the manual test.

## Retraction (Calibration → Retraction test)
- Tower with notches at increasing retraction length. Defaults 0 → 2 mm, step 0.1 (direct drive); Bowden 1 → 6 mm, step 0.2.
- Choose the shortest length that gives a clean section. Read the length from the retraction-tower comment in the G-code preview at that height.
- PLA and ABS are often clean from the bottom: 0.2-0.4 mm is then enough. Still stringy at the top: dry the filament and check that the nozzle is seated and not leaking; more retraction will not fix it.
- Save `filament_retraction_length` (filament; `nil` = use the printer value). Limit 0..min(8 mm, max(2 mm, 2 × printer retraction)). Speed: `filament_retraction_speed`.

## Tolerance (right-click plate → Add Handy Model → Orca Tolerance Test)
- Six hex holes (0-0.4 mm clearance) plus a hex tester; check with a 6 mm hex key and calipers.
- Holes too tight: increase `xy_hole_compensation` (positive = bigger holes). Outer size too big: negative `xy_contour_compensation`. Work in steps of 0.02-0.05 mm and reprint.
- Filament shrinkage compensation is material data: the plugin does not change it; the user may set it by hand. First-layer flare is `elefant_foot_compensation` (see defect-dimensional-accuracy).

## Cornering (Calibration → Cornering)
- Skip if corners look fine. The firmware (Klipper, Marlin JD/jerk, RepRap) caps the value and Orca cannot see the cap: if the whole tower looks the same, the limit is reached.
- Result goes to the printer profile (Motion ability → Jerk limitation) or firmware: by hand. In the process preset jerk keys (`default_jerk`, `outer_wall_jerk`) may only be lowered, never above the printer limits.

## Input shaping (Calibration → Input shaping)
- Prefer the printer's own automatic calibration when it has one (most recent printers; Prusa CORE One L and XL have integrated accelerometers, other Prusa models use an optional one).
- Orca test: glossy opaque filament, Ringing Tower, 15-110 Hz, damping 0.1-0.2; read X/Y frequency from the heights, then the damping test. The user stores the values in firmware/printer settings and restores normal acceleration afterwards.

## VFA (Calibration → VFA)
- After input shaping. Tower at rising speeds (e.g. 20-200 mm/s, step 10) covering the outer-wall speeds used; find bands where walls get rougher.
- Fix: printer resonance avoidance range (by hand), or keep `outer_wall_speed` (process) outside the bad band. Prusa CORE One/L and XL: run phase stepping calibration from the printer menu (a failed run usually means belt tension).

## Adaptive pressure advance
- Worth it on fast CoreXY printers with high-flow nozzles and a wide range of speeds and accelerations; useless with one speed and one acceleration. Validated on Klipper; on Marlin disable it if walls hesitate.
- Run PA pattern tests for each pair, e.g. accelerations 1k/2k/4k × speeds 50/100/150/200 mm/s, PA step 0.001, never above the maximum acceleration recommended by input shaping.
- Enter one line per test, "PA, flow mm³/s, acceleration", in `adaptive_pressure_advance_model`, set `adaptive_pressure_advance` = `1`, keep a median value in `pressure_advance` as fallback for tool changes and prime tower. `adaptive_pressure_advance_bridges`: about half the normal PA (0 disables). Leave `adaptive_pressure_advance_overhangs` at `0` until the model is proven.

## Sources
- https://www.orcaslicer.com/wiki/guides/calibration_guide.html
- https://www.orcaslicer.com/wiki/calibration/temp_calib.html
- https://www.orcaslicer.com/wiki/calibration/volumetric_speed_calib.html
- https://www.orcaslicer.com/wiki/calibration/pressure_advance_calib.html
- https://www.orcaslicer.com/wiki/calibration/flow_ratio_calib.html
- https://www.orcaslicer.com/wiki/calibration/retraction_calib.html
- https://www.orcaslicer.com/wiki/calibration/tolerance_calib.html
- https://www.orcaslicer.com/wiki/calibration/cornering_calib.html
- https://www.orcaslicer.com/wiki/calibration/input_shaping_calib.html
- https://www.orcaslicer.com/wiki/calibration/vfa_calib.html
- https://www.orcaslicer.com/wiki/calibration/adaptive_pressure_advance_calib.html
- https://wiki.bambulab.com/en/bambu-studio/Calibration
- https://wiki.bambulab.com/en/software/bambu-studio/calibration_pa
- https://wiki.bambulab.com/en/software/bambu-studio/calibration_flow_rate
- https://wiki.bambulab.com/en/knowledge-sharing/flowrate-calibration-by-microlidar
- https://help.prusa3d.com/article/pressure-advance_814986
- https://help.prusa3d.com/article/input-shaper-core-one-mk4-s-mk3-9-s-mk3-5-s-xl-mini_451816
- https://help.prusa3d.com/article/phase-stepping-core-one-l-core-one_914247
- https://help.prusa3d.com/article/phase-stepping-xl_681760
- https://wiki.bambulab.com/en/knowledge-sharing/02-mm-nozzle-FAQ
