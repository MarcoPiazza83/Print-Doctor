---
name: defect-layer-shift
description: Layer shifts (diagnosis and prevention only): whole layers offset in X or Y, staircase shifts, leaning prints; mostly hardware (belts, pulleys, obstructions, collisions, overheated drivers) with a few preventive slicer changes. Read when the user reports shifted layers, layers moved sideways, a step or offset in the print, a staircase or leaning print, or the printer clicking/knocking and the print continuing misaligned.
---
# Layer shift

Layer shift is a **hardware or collision problem**. Most printers are open loop: if the toolhead loses steps it keeps printing at the wrong place. The slicer cannot correct a shift; it can only lower the risk. Explain the hand checks first; propose preset changes only as prevention.

## How to recognize it
- Everything above a certain height is offset sideways in X or Y; the print continues normally on top of the offset.
- **Single shift**: usually one event (nozzle hit a curled edge or blob, cable or object caught, a bump to the printer).
- **Staircase** (several shifts in the same direction): typically a loose or misaligned motor pulley or a slipping belt.
- **Leaning print**: many small shifts in one direction.
- A clicking or thumping noise from a motor at the moment of the shift means skipped steps.
- Not a layer shift: elephant foot (defect-first-layer), corners lifting (defect-warping), seam line (defect-seam-zits-blobs), ripples after corners (defect-ringing-ghosting), wrong overall size (defect-dimensional-accuracy).

## Likely causes, most common first
1. **Nozzle collides with the print**: curled overhangs, warped corners, blobs from sticky filament (PETG) collecting on the nozzle, very sparse infill under top layers.
2. **Belts and pulleys**: belt too loose (slips) or too tight (friction), pulley set screws loose or not on the flat of the motor shaft.
3. **Obstruction of the motion**: filament scraps around a belt or pulley, cable bundle or cable chain catching, PTFE tube or cables snagging (Bambu A series), purge waste piling up at the chute (Bambu), dirty or dry rods and bearings.
4. **Too fast for the motors**: speed or acceleration above what the axes can hold, especially when a faster speed mode is selected on the printer screen mid-print (Bambu Ludicrous), or stealth/silent mode on large prints (Prusa).
5. **Electronics too hot or underpowered**: motor drivers overheating (e.g. Bambu P1P fully enclosed without an MC board fan), insufficient motor current.
6. Non-original hotends that are taller than stock (Bambu), external bumps, unstable table.

## Questions worth asking (only when the answer changes the fix)
- One shift or several in the same direction? Which axis?
- At what height, and what was printing then (travel over a top surface, an overhang, a filament change, a tall thin section)?
- Any clicking or grinding noise? Was the speed mode changed on the printer?
- Is the printer enclosed and hot (long ABS/ASA prints, P1P with an enclosure)?
- Does the same file shift at the same height every time? (repeatable = geometry/collision; random = mechanics/electronics)

## Slicer fixes
Prevention only, after the hand checks. All values must stay within the printer's machine limits.

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `filament_z_hop` (filament) | increase | set 0.2-0.4 mm | 0-2 mm; nil = printer value | slightly longer travel, a bit more stringing |
| `filament_retract_lift_enforce` (filament) | set | `All Surfaces` | nil = printer value | more lifts, more time |
| `travel_acceleration` (process) | decrease | -25% | within machine max acceleration | longer print |
| `default_acceleration` (process) | decrease | -20% | within machine limits; 0 = printer value | longer print |
| `travel_speed` (process) | decrease | -20 to -30% | within machine max speed | longer print, slightly more oozing |
| `enable_prime_tower` (process) | enable for PETG blobs on the nozzle | `1` | needs space on the plate | extra filament and time |
| `sparse_infill_density` (process) | increase if top layers sag and get hit | +5 points (e.g. 15% → 20%) | | more material and time |

For collisions with curled or warped areas, treat the cause: overhang cooling and slowdown (`enable_overhang_speed` (process), `slowdown_for_curled_perimeters` (process), `overhang_fan_speed` (filament); see defect-overhangs-bridges) and adhesion/warping (see defect-warping).

## Checks the user must do by hand (hardware, material, printer settings)
- **Move each axis by hand with the printer off**: smooth, no tight spots. On CoreXY (Bambu X1/P1/P2S/H2, Prusa CORE One, XL) also move along both diagonals: a rough diagonal points to the motor or pulley driving it.
- **Belt tension**:
  - Bambu X1/P1/H2/P2S: printer off, loosen the 4 tensioner screws 1-2 turns, move the toolhead around, park it at the rear, retighten (no over-torque); then run Vibration compensation. Bambu A1: loosen the tension screw(s) about one turn, move the axis three times, retighten, calibrate.
  - Prusa MK3S+: Support → Belt Status, best around 250 (X) and 275 (Y), ±15; near 240 loosen, near 290 tighten. Other Prusa: belt sounds like a low bass note and can be pinched with slight resistance. XL: inspect the belt clamps.
- **Pulleys**: both set screws tight, one on the flat of the shaft, pulley aligned so the belt runs straight. Test by holding the motor shaft and pushing the axis: no play allowed. Prusa MINI: the X pulley screw is reachable through a hole on top of the extruder (2 mm Allen key).
- **Obstructions**: filament around belts or pulleys, cable bundle or chain hitting the frame, purge waste at the chute, PTFE tubes. Watching a video of the print helps.
- **Rods and bearings**: clean and lubricate (Prusa lubricant or lithium grease); Bambu X1/P1: clean the carbon rods.
- **Printer options**: Bambu "Auto-recovery from step loss" (X1, A, H2, P2S, X2D: printer screen → Print options; P1: from Bambu Studio). Prusa: use normal mode instead of stealth for large or complex prints (stealth also disables crash detection). Do not raise the speed mode on the printer screen for large prints.
- **Electronics**: enclosed Bambu P1P needs the MC board fan; motors warm but not too hot to touch.
- **Machine limits (printer settings, the user changes them by hand, the plugin never does)**: `machine_max_acceleration_x`, `machine_max_acceleration_y`, `machine_max_speed_x`, `machine_max_speed_y`. If presets keep hitting these limits and shifts persist, the user can lower them.
- **Geometry**: tall slender parts are more prone to shifts and knock-overs: add a brim, reorient, or cut the model into parts.

## Calibration in Orca (menu Calibration → ...)
- No Orca test fixes a layer shift. After belt or pulley work, run the printer's own resonance calibration (Bambu Vibration compensation, Prusa input shaper with an accelerometer if hardware changed).
- Do not run Calibration → Input Shaping or Calibration → Cornering until shifts are solved: they push acceleration and speed high on purpose.

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- PLA: fast profiles plus curled overhangs are the usual collision; improve overhang cooling.
- PETG: sticks to the nozzle and builds blobs that catch the print; dry the filament, consider a prime tower and z-hop.
- ABS/ASA: warping and curling corners get hit; keep the enclosure closed, use a brim.
- TPU: printed slowly, shifts are rare; strings or blobs on the nozzle can still catch.
- PA/PC and CF composites: warping-prone; Bambu suggests the Smooth PEI plate with glue for PAHT-CF to avoid warp-related shifts.

## Sources
- https://wiki.bambulab.com/en/knowledge-sharing/layer-shifts
- https://wiki.bambulab.com/en/general/bambu-mods-to-avoid
- https://wiki.bambulab.com/en/software/bambu-studio/remote-control
- https://wiki.bambulab.com/en/x1/maintenance/belt-tension
- https://wiki.bambulab.com/en/a1/maintenance/belt_tension
- https://wiki.bambulab.com/en/p2s/maintenance/belt-tension
- https://wiki.bambulab.com/en/h2/maintenance/belt-tension
- https://wiki.bambulab.com/en/bambu-studio/manual/3d-print-large-files
- https://help.prusa3d.com/article/layer-shifting_2020
- https://www.orcaslicer.com/wiki/print_settings/speed/speed_settings_acceleration.html
- https://www.orcaslicer.com/wiki/printer_settings/motion%20ability/printer_motion_ability.html
- https://www.simplify3d.com/resources/print-quality-troubleshooting/layer-shifting/
- https://www.obico.io/blog/3d-print-troubleshooting-guide/
