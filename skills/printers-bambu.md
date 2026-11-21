---
name: printers-bambu
description: Bambu Lab printers (X1C, X1E, P1P, P1S, P2S, A1, A1 mini, H2D, H2S, H2C, plus X2D/A2L/H2D Pro profiles) and AMS / AMS 2 Pro / AMS HT / AMS lite - kinematics, enclosure and chamber heating, hotend and bed limits, nozzle options, dual-nozzle rules and Orca profile limits that change print advice. Read when the user has a Bambu Lab printer or AMS, or mentions X1, P1, P2S, A1, H2D, H2S, H2C, Bambu plates, flow dynamics / K value, hardened or high-flow nozzle, left/right nozzle.
---
# Bambu Lab printers: differences that change advice

## Overview (Orca 2.5.1 profiles, 0.4 mm nozzle, plus Bambu wiki)
| Model | Motion | Enclosure / chamber | Build volume (mm) | Hotend max | Bed max | Profile limits: XY speed, accel |
|---|---|---|---|---|---|---|
| X1C | CoreXY | enclosed, no heater; exhaust fan, filter, aux fan | 256×256×250 | 320 °C | 110 °C | 500 mm/s, 20000 mm/s² |
| X1E | CoreXY | enclosed, **active heater up to 60 °C**, HEPA + carbon | 256×256×250 | - | - | 500, 20000 |
| P1P | CoreXY | **open frame**, no aux fan | 256×256×250 | 320 °C | 100 °C | 500, 20000 |
| P1S | CoreXY | enclosed, no heater; aux fan, filter | 256×256×250 | 320 °C | 100 °C | 500, 20000 |
| P2S | CoreXY | enclosed, no heater; adaptive airflow (draws outside air for PLA, recirculates through filter for hot materials) | 256×256×256 | 300 °C | 110 °C | 1000, 20000 |
| A1 | bed-slinger (Cartesian) | **open** | 256×256×256 | - | 100 °C | 500, 12000 |
| A1 mini | bed-slinger | **open** | 180×180×180 | - | **80 °C** | 500, 20000 |
| H2D | CoreXY, **two nozzles** (left lifts) | enclosed, **active PTC heater** (H2D Pro: 65 °C max) | 350×320×325 | 350 °C | 120 °C | 1000, 20000 |
| H2S | CoreXY, one nozzle | enclosed, active PTC heater | 340×320×340 | 350 °C | 120 °C | 1000, 20000 |
| H2C | CoreXY, left nozzle + right Vortek induction hotend changer (rack of 6) | enclosed, active PTC heater | 330×320×325 | 350 °C | - | 1000, 20000 |
- All are direct drive. Orca also ships X2D (dual nozzle, second extruder Bowden: printer retraction 2 mm at 20 mm/s), A2L (bed-slinger 330×320×325, 12000 mm/s²) and H2D Pro profiles.
- Travel acceleration in the profiles is 9000 mm/s² (P2S 10000). Never set process speeds, accelerations or jerk above these machine limits.
- Printer retraction in profiles: 0.8 mm at 30 mm/s for 0.4 nozzles; 0.2 → 0.4 mm, 0.6 → 1.4 mm, 0.8 → 3 mm (A1 keeps 0.8 mm for every nozzle). Printer z-hop 0.4 mm.
- Layer height limits in profiles: 0.2 nozzle 0.04-0.14, 0.4: 0.08-0.28, 0.6: 0.12-0.42, 0.8: 0.16-0.56 mm. Keep `layer_height` (process) within the printer maximum even where the plugin's 75 % rule would allow more.

## How the machine type changes advice
- **Bed-slingers (A1, A1 mini, A2L)**: the bed moves in Y, so tall thin or heavy parts wobble and ring more; prefer lower `outer_wall_acceleration` and `default_acceleration` (process) for tall parts, brim for narrow bases. Open frame: ABS/ASA/PC/PA warp and crack from drafts; suggest `draft_shield` (process) = `enabled` and a brim, but recommend an enclosed printer for large parts.
- **A1 mini bed max 80 °C**, A1/P1 100 °C: never propose plate temperatures above the printer's bed maximum even if the plugin cap (120 °C) allows it.
- **Enclosed without heater (X1C, P1S, P2S)**: good for ABS/ASA; for PLA, PETG and TPU heat builds up and causes heat creep and soft, clogging filament. Hardware advice: open the front door and remove or lift the top glass when the bed is at or above the filament's softening point (about 45 °C PLA, 70 °C PETG).
- **Heated chamber (X1E, H2D, H2S, H2C)**: chamber heating is only for ABS/ASA (optional), PC, PA, PA-CF, PET-CF, PPA, PPS. The plugin never changes chamber settings; if relevant, tell the user. PLA, PETG, TPU, PVA, BVOH, PCTG, PLA-CF and PETG-CF must not see a chamber above about 45 °C. H2C classifies third-party filaments with heat deflection below 80 °C (ISO 75, 1.8 MPa) as low-temperature. High- and low-temperature filaments cannot share one print.
- **P1P** is open and has no auxiliary fan: same draft advice as bed-slingers for warping materials; for PLA bridges and overhangs rely on `overhang_fan_speed` and `fan_max_speed` (filament).

## Nozzles and hotends
- Sizes 0.2 / 0.4 / 0.6 / 0.8 mm. Stock: X1C 0.4 hardened steel; P1P/P1S and A series 0.4 stainless steel (hardened optional). Stainless is fine for PLA, PETG, ABS, ASA, TPU, PVA; abrasive filaments (CF, GF, glow-in-the-dark, wood, metal) need hardened steel or tungsten carbide.
- 0.2 mm nozzles are stainless and not abrasion resistant; avoid CF/GF, glow, sparkle and galaxy filaments (particles clog). Use about 2 mm³/s for `filament_max_volumetric_speed` (filament); layers are weaker than with 0.4/0.6.
- High-flow hotends (H2 series / P2S / X2D) raise the maximum flow considerably; the E3D High Flow ObXidian hotend for X1C/P1 adds about 60 % flow but is limited to 300 °C. Tungsten carbide nozzles (H2D, H2S, H2C left, P2S, X2D) resist abrasion best, 350 °C max.
- H2D TPU high-flow hotend: right side only, flexible filaments only (hard filaments damage its coating), no cutter and no AMS feeding on that side.
- H2C Vortek induction hotends (right side, 0.2-0.8 mm, hardened or stainless) heat in about 8 s, which cuts colour-change time and purge waste.
- Orca printer variants list the hotend type (Standard, High Flow, E3D High Flow, TPU High Flow): the selected printer preset must match the installed hotend, otherwise flow limits in the filament profiles are wrong.

## Dual-nozzle rules (H2D, H2C; X2D similar)
- TPU only on the right nozzle (H2D: higher clog risk on the left; H2C left does not support TPU 85A yet).
- PPS-CF and PPA-CF (H2C also PET-CF) only on the left nozzle: the right filament path bends sharply at homing and brittle filament snaps.
- H2C: never PVA on one hotend and PETG on the other at the same time (PETG bed heat softens PVA, clogs). PVA with a 0.2 mm standard hotend is not supported.
- Soft + hard multi-material: hard filament on the left, TPU on the right.
- For two-colour prints use both nozzles: switching nozzles avoids AMS unload/reload and is faster.

## AMS family
- AMS (1st gen), AMS 2 Pro (drying), AMS HT (single spool, drying up to 85 °C, needs its own power for drying): X1/P1 need a filament buffer (one unit) or AMS hub (several), up to 4 units; P2S up to 4 AMS 2 Pro + 4 AMS HT; H2 series up to 4 AMS 2 Pro + 8 AMS HT with built-in buffer; A1 up to 4 via the A1 AMS hub.
- AMS lite: A series only, one unit, 4 slots, single-stage feed; long or sharply bent PTFE tubes cause feed failures (max feed length 1.2 m).
- Soft TPU cannot be fed automatically by an AMS (Bambu's "TPU for AMS" is the exception). AMS HT has a dedicated TPU outlet: feed manually; it still works as a dry box.
- Purge, prime tower and colour bleed: see defect-multimaterial.

## Plates (Orca bed type → filament keys)
- Textured PEI (stock): `textured_plate_temp` / `textured_plate_temp_initial_layer`; PLA, PETG, TPU without glue, glue may be needed for PC, PA, ABS, ASA.
- Smooth PEI / High Temp Plate: `hot_plate_temp` pair; only PLA without glue, use glue for everything else to protect the sheet.
- Engineering Plate: `eng_plate_temp` pair; always with glue. Cool Plate: `cool_plate_temp` pair. Cool Plate SuperTack: `supertack_plate_temp` pair.
- Remove parts once the plate is at about 35 °C or less. Second-generation plates are auto-detected only on P2S/X2D.

## Calibration differences
- Flow Dynamics (K): automatic on X1 (lidar lines), A1, H2 and P2S (eddy sensor at the purge wiper); P1 manual only. H2 series offer Auto / On / Off before each print; Off uses the stored K profile for that slot. With `enable_pressure_advance` (filament) = `1` the Orca filament value overrides the printer. Eddy-sensor auto K reads higher than manual by design; third-party hotends make A1/H2D auto K inaccurate. See calibration-guide.
- Automatic flow rate (lidar) exists only on X1.

## Checks the user must do by hand (hardware, printer settings)
- Select the printer preset that matches nozzle size and hotend type; printer settings `nozzle_diameter`, `retraction_length`, `z_hop` and machine limits are changed only by the user. Use filament overrides (`filament_retraction_length`, `filament_z_hop`) for per-material changes.
- Rerun the printer's automatic calibration (vibration compensation, bed levelling, motor noise) after moving the printer, firmware updates, belt work or part replacement, or when quality suddenly drops.
- Keep the silicone sock fitted (P2S warns when missing), clean the nozzle wiper and purge chute, check PTFE routing to the AMS, and keep the build plate clean and grease-free.

## Sources
- https://github.com/OrcaSlicer/OrcaSlicer/tree/v2.5.1/resources/profiles/BBL/machine
- https://wiki.bambulab.com/en/x1/manual/intro-x1
- https://wiki.bambulab.com/en/x1/manual/x1e-faq
- https://wiki.bambulab.com/en/x1/manual/X1E-chamber-temp-guide
- https://wiki.bambulab.com/en/p1/manual/intro-p1p
- https://wiki.bambulab.com/en/a1/manual/intro-a1
- https://wiki.bambulab.com/en/a1-mini/manual/intro-a1-mini
- https://wiki.bambulab.com/en/h2/manual/h2d-intro
- https://wiki.bambulab.com/en/h2/manual/h2d-pro-faq
- https://wiki.bambulab.com/en/h2s/manual/h2s-intro
- https://wiki.bambulab.com/en/h2c/manual/h2c-intro
- https://wiki.bambulab.com/en/h2c/manual/induction-hotend-system-workflow
- https://wiki.bambulab.com/en/p2s/manual/p2s-intro
- https://wiki.bambulab.com/en/h2/h2d-filament-printing-guide
- https://wiki.bambulab.com/en/h2c/h2c-filament-printing-guide
- https://wiki.bambulab.com/en/filament-acc/acc/nozzles
- https://wiki.bambulab.com/en/filament-acc/acc/plates
- https://wiki.bambulab.com/en/knowledge-sharing/02-mm-nozzle-FAQ
- https://wiki.bambulab.com/en/ams/manual/multi-model-AMS-compatibility-guide
- https://wiki.bambulab.com/en/ams-lite/manual/intro-ams-lite
- https://wiki.bambulab.com/en/ams-ht/manual/intro-and-connection-guide
- https://wiki.bambulab.com/en/software/bambu-studio/calibration_pa
- https://wiki.bambulab.com/en/general/printer-calibration
