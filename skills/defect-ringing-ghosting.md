---
name: defect-ringing-ghosting
description: Ringing/ghosting (fading echoes after corners, edges, holes or letters), vertical fine artifacts (VFA, salmon skin), vertical ribs and wobble on walls, with Orca acceleration/speed/jerk fixes and the Input Shaping, Cornering and VFA tests. Read when the user reports ghosting, ringing, echoes, ripples or waves after corners, a shadow of a feature repeated on the wall, vertical lines or ribs on walls, salmon skin, wavy or wobbly walls.
---
# Ringing, ghosting and VFA

## How to recognize it
- **Ringing / ghosting**: a short train of ripples right after a sharp corner, edge, hole or embossed text, evenly spaced and fading with distance. They sit on the wall printed *after* the corner, in the direction of travel.- **Axis clue**: ripples on only some faces point to one axis (X or Y): check that axis's belt, pulley and bearings first. On bed-slinger printers (Prusa MK/MINI, Bambu A1/A1 mini) the Y axis moves the bed.
- **VFA (vertical fine artifacts) / salmon skin**: very fine, regular vertical lines over whole walls, also on curved walls and far from corners. They appear or vanish in specific speed bands. A common subtype is motor resonance rippling (MRR) from the stepper motors.
- **Look-alikes, route elsewhere**:
  - Horizontal bands repeating every few layers (Z wobble, temperature swings, filament diameter): see the hand checks below and defect-extrusion.
  - One horizontal line or bulge where a bridge, roof or overhang starts (the Benchy hull line): shrinkage of the bridge pulls the wall, plus a sudden flow change. Covered by the last rows of the fixes table.
  - Random irregular layer lines: often a loose hotend (hand checks).
  - Rough texture on purpose: `fuzzy_skin` (process) is not `disabled_fuzzy`.

## Likely causes, most common first
1. Outer wall acceleration and speed too high for the frame: the toolhead's inertia at a direction change excites the frame and the belts.
2. The printer's own resonance compensation (input shaper / vibration compensation) is missing or out of date: printer moved to another surface, belts re-tensioned, firmware update, new parts.
3. Mechanics: loose or uneven belts, loose pulley set screws or frame screws, dry or dirty rods and bearings, a table or shelf that wobbles.
4. Cornering limits (jerk, junction deviation) too permissive.
5. VFA: stepper motor resonance at certain speeds, motor-to-motor variance.
6. Very tall, slender parts swaying as they grow (wobble rising with height).

## Questions worth asking (only when the answer changes the fix)
- Ripples after corners, or fine lines everywhere? (ringing vs VFA)
- Which faces show it? (axis, belt to check)
- Printer and firmware: Bambu, Prusa (input shaper firmware), Klipper, Marlin 2 (junction deviation or classic jerk)? Decides which jerk key the printer actually uses.
- Was the printer moved, belts adjusted or parts changed since the last good print? If yes, recalibrate the printer before changing presets.
- Was a speed mode raised on the printer screen (Bambu Sport/Ludicrous, Prusa Tune → Speed)? That overrides the slicer.

## Slicer fixes
Read the current values first. Change one or two rows per round and reprint a small test (a box with sharp corners and embossed text).

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `outer_wall_acceleration` (process) | decrease | -25 to -40% (e.g. 5000 → 3000) | never above the printer's max acceleration; ≥ 500 | longer print; ignored if `default_acceleration` is 0 (Orca then sends no acceleration commands) |
| `outer_wall_speed` (process) | decrease (ringing); move out of a bad band (VFA) | -20%, or the nearest clean speed from the VFA test | within machine limits; also capped by `filament_max_volumetric_speed` | longer print; a lower speed can land in another VFA band |
| `default_acceleration` (process) | decrease | -20% | within machine limits; 0 = printer firmware value | slows every feature; only if ringing also shows on inner features |
| `outer_wall_jerk` (process) | decrease | -2 mm/s (e.g. 9 → 7) | ≤ printer max jerk; 0 = use `default_jerk`; no effect while `default_jerk` (process) is 0 (printer's own jerk) | slower corners; used by classic-jerk Marlin, RepRap and Klipper (as corner velocity); Marlin 2 with junction deviation ignores it |
| `default_junction_deviation` (process) | decrease | -0.002 to -0.005 mm | 0.01-0.3 mm accepted by Marlin 2; ≤ printer max junction deviation | Marlin 2 only; slower corners |
| `max_volumetric_extrusion_rate_slope` (process) | set (bulge line where speed drops, not true ringing) | 35-50 mm³/s² at 1000 mm/s² accel, 70-100 at 2000, 145-200 at 4000 (0.42 mm line, 0.16 mm layer; +25% at 0.2 mm layer) | 0 = off; stay below those maxima or it has no effect | longer print, larger G-code, turns off arc fitting; use `extrusion_rate_smoothing_external_perimeter_only` = `1` to limit it to visible walls |
| `overhang_fan_speed` (filament) | decrease (Benchy-hull line under bridges) | -10 to -20 points | keep enough for the overhangs you have | droopier overhangs |
| `infill_wall_overlap` (process) | decrease (same line) | 15% → 5% | ≥ 0% | weaker infill-to-wall bond |

Notes:
- Vibration grows with print speed and with abrupt direction changes: lower outer wall acceleration and speed first, before touching other features.
- Every speed, acceleration and jerk is clamped by the printer's Motion ability limits. If the preset already sits above them, changing it does nothing: check the printer limits first.
- Slowing the outer wall to the bridge speed also hides the hull line, at a time cost.

## Checks the user must do by hand (hardware, material, printer settings)
- **Belts**: equal, correct tension on both axes; a loose belt lowers the resonance frequency and makes vibration compensation less effective.
  - Bambu X1/P1/H2/P2S: printer off, loosen the 4 tensioner screws 1-2 turns (do not remove), move the toolhead back and forth, park it at the rear, retighten without over-torquing; the spring sets the tension. Bambu A1: loosen the X/Y screws about one turn, move the axis by hand three times, retighten.
  - Prusa: plucked belt should give a low bass tone; MK3S+ Support → Belt Status, about 240-300 is fine (lower number = tighter).
- **Recalibrate the printer's resonance compensation** after moving it, belt work or firmware updates: Bambu screen → Calibration → Vibration compensation (and motor noise cancellation where offered); Prusa input shaper is factory calibrated, recalibrate with the accelerometer only after hardware changes (CORE One L and XL have it built in).
- **Prusa phase stepping** (CORE One, CORE One L, XL) targets VFA and motor noise; calibrate from the printer menu, never next to another printer that is moving. On the XL, enabling it disables crash detection.
- **Mechanics**: pulley set screws, frame/PSU/display/bed screws, rubber or foam feet in place, rods and bearings clean and lubricated (Bambu X1/P1: clean the carbon rods), belt not rubbing on plastic parts.
- **Surface**: firm, non-wobbling table; a heavy tile under the printer helps; avoid very soft padding under light printers (Prusa MINI).
- **Printer settings (the user changes them by hand, the plugin never does)**: Printer settings → Motion ability → Resonance Compensation: `input_shaping_emit`, `input_shaping_type`, `input_shaping_freq_x`, `input_shaping_freq_y`, `input_shaping_damp_x`, `input_shaping_damp_y`; Resonance avoidance `resonance_avoidance` with `min_resonance_avoidance_speed` / `max_resonance_avoidance_speed` (outer wall speed inside the band is pushed to its edges; good fix for a VFA band); limits `machine_max_acceleration_x`, `machine_max_acceleration_y`, `machine_max_jerk_x`, `machine_max_jerk_y`, `machine_max_junction_deviation`.
- **Horizontal banding / wobble**: Z lead screw or Z belt (clean, straight, aligned, not binding), hotend temperature stable within about ±2 °C (PID tune), filament with consistent diameter, hotend firmly seated (Bambu H2/P2S/A1: clip and magnet; X1/P1: hotend screws).
- **Tall slender parts**: add a brim, reorient, or split the model.

## Calibration in Orca (menu Calibration → ...)
Run the filament calibrations first (see calibration-guide).
- **Calibration → Input Shaping**: only for printers without automatic accelerometer calibration (Bambu and recent Prusa do it themselves, use that). Opaque glossy filament; frequency test on the Ringing Tower (Fast Tower if ringing is heavy), 15-110 Hz to start, measure the height where ripples are least per axis and read the frequency; then the damping test (start 0.1-0.2). The test raises speed and acceleration on purpose. The user saves results in firmware and/or the printer settings by hand.
- **Calibration → Cornering**: finds the highest jerk / junction deviation that keeps corners sharp. Mostly useful to raise cornering speed; the firmware may cap the value.
- **Calibration → VFA**: speed tower covering every outer wall speed you use (e.g. 20-200 mm/s, step 10). Find speeds where walls get rough, then set `outer_wall_speed` outside that band or have the user enable resonance avoidance by hand. Run it after input shaping.

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- Opaque, glossy filaments make ringing most visible (Orca recommends them for its tests). Judge fixes on the same filament.
- PLA: usually printed with the fastest profiles; lower outer wall acceleration and speed first.
- PETG, ABS/ASA: normally slower profiles; if ringing appears, check printer mode and belts before presets.
- TPU and other soft materials: printed slowly, ringing is rare; bulges at speed changes are more likely (soft filament lags), smoothing helps.
- PA/PC and CF: low max volumetric speed often caps outer wall speed already; focus on acceleration and mechanics.

## Sources
- https://help.prusa3d.com/article/ghosting_1801
- https://help.prusa3d.com/article/input-shaper-core-one-mk4-s-mk3-9-s-mk3-5-s-xl-mini_451816
- https://help.prusa3d.com/article/phase-stepping-core-one-l-core-one_914247
- https://help.prusa3d.com/article/phase-stepping-xl_681760
- https://help.prusa3d.com/article/vibration-when-printing-mk3s-mk2-5s_2177
- https://help.prusa3d.com/article/vibration-noise-when-printing-mini-mini_264110
- https://wiki.bambulab.com/en/general/printer-calibration
- https://wiki.bambulab.com/en/x1/maintenance/belt-tension
- https://wiki.bambulab.com/en/a1/maintenance/belt_tension
- https://wiki.bambulab.com/en/p2s/maintenance/belt-tension
- https://wiki.bambulab.com/en/h2/maintenance/belt-tension
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/severe-layer-artifacts
- https://wiki.bambulab.com/en/bambu-studio/manual/3d-print-large-files
- https://wiki.bambulab.com/en/knowledge-sharing/layer-shifts
- https://help.prusa3d.com/article/layer-shifting_2020
- https://www.orcaslicer.com/wiki/calibration/input_shaping_calib.html
- https://www.orcaslicer.com/wiki/calibration/vfa_calib.html
- https://www.orcaslicer.com/wiki/calibration/cornering_calib.html
- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_acceleration.html
- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_jerk_xy.html
- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_advanced.html
- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_other_layers_speed.html
- https://www.orcaslicer.com/wiki/printer_settings/motion%20ability/printer_motion_ability.html
- https://www.simplify3d.com/resources/print-quality-troubleshooting/vibrations-and-ringing/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/lines-on-the-side-of-print/
- https://www.obico.io/blog/3d-print-troubleshooting-guide/
