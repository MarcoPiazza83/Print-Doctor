---
name: printers-prusa
description: Prusa printers (MK4/MK4S, MK3.9, CORE One / CORE One+, CORE One L, XL single and multi-tool, MINI/MINI+, MK3.5/S) and MMU3 / INDX - kinematics, enclosure, extruder type, LoadCell vs Live Z, nozzle system and options, HF profiles and Orca profile limits that change print advice. Read when the user has a Prusa printer or mentions Nextruder, LoadCell, Live Z, CHT or ObXidian nozzle, HF profile, MMU3, INDX, XL toolchanger, CORE One chamber or ventilation grille, Prusa steel sheet.
---
# Prusa printers: differences that change advice

## Overview (Orca 2.5.1 profiles, 0.4 nozzle; Prusa KB)
| Model | Motion | Enclosure | Extruder / nozzle system | Build volume (mm) | Profile limits: XY speed, accel (normal / stealth) |
|---|---|---|---|---|---|
| MK4 / MK3.9 | Cartesian bed-slinger | open (optional Original Prusa Enclosure) | Nextruder direct drive, LoadCell, Prusa Nozzle | 250×210×220 | 300 / 200 mm/s, 4000 mm/s² |
| MK4S / MK3.9S | bed-slinger | open (optional enclosure) | Nextruder, LoadCell | 250×210×220 | 300 / 160, 4000 / 2500 |
| CORE One / CORE One+ | CoreXY | **enclosed**: door, top ventilation grilles, chamber fans, optional HEPA | Nextruder, LoadCell, stock CHT 0.4 nozzle | 250×220×270 | 350 / 160; 10000 (X/Y), 7000 extruding |
| CORE One L | CoreXY | **enclosed**, chamber temperature item in the menu, integrated accelerometer | Nextruder, LoadCell | 300×300×331 | 350 / 160; 10000, 7000 extruding, 6000 travel |
| XL (1, 2 or 5 heads) | CoreXY | open (optional enclosure with HEPA) | Nextruder toolchanger heads, LoadCell, integrated accelerometer | 360×360×360 | 400 mm/s; 7000 X/Y, 4000 extruding, 5000 travel |
| MK3.5 / MK3.5S | bed-slinger | open | direct drive with E3D V6 hotend, no LoadCell | 250×210×210 | 300 mm/s, 4000 |
| MINI / MINI+ | bed-slinger | open | **Bowden**, E3D V6 hotend, no LoadCell | 180×180×180 | MINI profile 180 mm/s, 1250 extruding; MINI IS profile 400 mm/s, 4000 |
- None of these has an active chamber heater in the sources read; the CORE One family warms its chamber with the bed and controls it with fans and grilles. The plugin never touches chamber settings.
- Printer retraction in profiles (0.4 nozzle): MK4S, MK4 MMU3, CORE One family 0.7 mm (MK4S 35 mm/s, CORE One 45 mm/s) with 0.2 mm z-hop (Slope Lift on MK4S and CORE One); MK4, XL, MK3.5 0.8 mm at 30-35 mm/s; MINI 3.2 mm at 70 mm/s (MINI IS 2.5-2.8 mm) because of the Bowden tube; 0.8 nozzles use 0.6 mm and lower retraction speeds on MK4S, CORE One and XL.
- Layer height limits (0.4 nozzle): 0.07-0.30 mm on MK4S, CORE One/L and XL (MK4 MMU3: 0.25 max), 0.08-0.30 on MK4, MK3.5 and MINI. Keep `layer_height` (process) within the printer maximum.
- Profile variants matter: "HF" printer presets (MK4S HF, CORE One HF, CORE One L HF) are for high-flow nozzles (CHT / E3D High Flow) and allow higher flow; the plain CORE One preset in Orca inherits from CORE One HF, and the CORE One ships with a CHT 0.4 nozzle. MMU3, INDX 4T/8T and XL 5T are separate printer presets.

## How the machine type changes advice
- **Bed-slingers (MK4/S, MK3.9/S, MK3.5, MINI)**: tall thin or heavy parts wobble and ring; lower `outer_wall_acceleration` / `default_acceleration` (process) for tall parts and add a brim for narrow bases. Open frame: ABS, ASA, PC, PA warp; suggest `draft_shield` (process) = `enabled` plus brim, or an enclosure for large parts.
- **CORE One family (enclosed)**: open the top ventilation grilles for PLA and PETG; a closed, warm chamber causes heat creep and under-extrusion with PLA. With high-flow nozzles in a closed chamber Prusa suggests opening the grille (or the door on other enclosures). For ABS, ASA and PC keep the chamber closed to hold heat.
- **Original Prusa Enclosure on MK/MINI**: with the doors closed and room temperature above about 27 °C the inside can get too hot for PLA (under-extrusion, clogs). Advise opening it.
- **MINI (Bowden)**: needs longer retraction and the Bowden version of the PA test. Soft filament can be hard to push through the PTFE tube on XL and CORE One (see material-tpu).
- **XL multi-tool**: idle tools ooze; the purge (wipe) tower is on by default when mixing materials. Turning `enable_prime_tower` (process) off works only with well-dried filament. `ooze_prevention` (process) = `1` cools idle tools; its temperature values are blocked by the plugin, so the user sets them BY HAND: `standby_temperature_delta` at Process → Multimaterial → Ooze prevention → Temperature variation, or `idle_temperature` at Filament → Basic information → Idle temperature. After a nozzle change the user must run tool offset calibration.
- **Pressure advance**: Prusa firmware takes PA from an M572 command (old M900 K values are converted 1:1). PrusaSlicer's default start G-code sets it; the Orca 2.5.1 Prusa machine profiles only reset it, so the value comes from the filament preset (`enable_pressure_advance`, `pressure_advance`); see calibration-guide.
- **Input shaper** is standard on all current models (crash detection is not used with it). Phase stepping (XL, CORE One/L) reduces VFA but disables crash detection on the XL.

## Nozzles
- Nextruder printers (MK4/S, MK3.9/S, CORE One/L, XL) use the Prusa Nozzle: heatbreak integrated, cold tool-free swap. MK3.5, MINI and older use E3D V6 nozzles, which must be tightened hot. A Nextruder V6 adapter lets Nextruder printers take V6 nozzles.
- Options: brass (stock, non-abrasive only); brass CHT and E3D High Flow brass (split melt channels, more flow, can print a bit cooler, need HF profiles); ObXidian (hardened, coated: for CF and other abrasives; no cold pulls, no needles or brass brushes); hardened nickel-plated; High Flow ObXidian; ObXiDian 500 (standard and HF); DiamondBack (diamond tip, most wear resistant).
- With the MMU3 use the standard Prusa Nozzle, not CHT: CHT holds more material and needs much larger purge volumes, or colours bleed.
- Diameter rules (Prusa): 0.25 mm: no composites (CF, GF, Kevlar, wood/metal fill), no flexibles, no PVA/BVOH; very long print times. ≥0.6 mm: stronger parts, less detail, more warping for ASA/PC. Metal-filled: hardened nozzle; wood-filled and large-particle composites: at least 0.6 mm.

## Multi-material
- **MMU3**: one nozzle, up to five filaments, purge tower required. Works with MK3S+, MK3.5/S, MK3.9/S, MK4/S and CORE One (CORE One L as a community mod). Printer and MMU firmware must match; MMU3 G-code for MK4/CORE is not interchangeable with older MMU profiles. Select the MMU3 printer preset in Orca.
- **INDX** (CORE One toolchanger, 4 or 8 tools) and **XL 5T** are true multi-tool printers: ooze and idle temperature matter more than purge volume. See defect-multimaterial.

## Plates and bed temperature keys
- Most Prusa Orca profiles do not enable multiple bed types: the filament's bed temperature comes from one global plate type. The MK4 MMU3 and CORE One INDX profiles default to Textured PEI (`textured_plate_temp` pair); otherwise check with the user which plate type Orca shows before changing a plate key (see orca-settings-reference).
- Prusa steel sheets (smooth, textured, satin, special PA) differ in thickness. On LoadCell printers the first layer is calibrated automatically and Live Z resets after each print; on MK3.5 and MINI every sheet needs its own Live Z value (steel sheet profiles).

## Checks the user must do by hand (hardware, printer settings)
- In the printer menu (Settings → Hardware) nozzle diameter, "hardened", "high-flow" and the Nextruder silicone sock option must match the installed parts; G-code checks warn when the sliced profile does not match.
- Select the Orca printer preset that matches nozzle size, HF nozzle, MMU3 or toolchanger. Printer settings `nozzle_diameter`, `retraction_length`, `retraction_speed`, `z_hop` and machine limits are changed only by the user; per-material retraction goes into filament overrides (`filament_retraction_length`, filament).
- Before input shaper / phase stepping: tight belts, healthy nozzle, clean rods. A failed phase stepping calibration usually means wrong belt tension. CORE One needs the accessory accelerometer for phase stepping; CORE One L and XL have one built in.
- MK3.5 / MINI: run first layer calibration and set Live Z per sheet. Fit the silicone sock (and enable it in the menu) for high-temperature filaments and to keep the heater block clean.

## Sources
- https://github.com/OrcaSlicer/OrcaSlicer/tree/v2.5.1/resources/profiles/Prusa/machine
- https://help.prusa3d.com/article/types-of-printers-and-their-differences_112464
- https://help.prusa3d.com/article/core-one-glossary_980046
- https://help.prusa3d.com/article/lcd-menu-core-one-l_970140
- https://help.prusa3d.com/article/lcd-menu-core-one_829752
- https://help.prusa3d.com/article/advanced-filtration-system-for-prusa-core-one_887189
- https://help.prusa3d.com/article/prusa-printer-upgrades_796284
- https://help.prusa3d.com/article/core-one-upgrade-paths_1253002
- https://help.prusa3d.com/article/input-shaper-core-one-mk4-s-mk3-9-s-mk3-5-s-xl-mini_451816
- https://help.prusa3d.com/article/phase-stepping-core-one-l-core-one_914247
- https://help.prusa3d.com/article/phase-stepping-xl_681760
- https://help.prusa3d.com/article/pressure-advance_814986
- https://help.prusa3d.com/article/prusa-nozzle-types-for-nextruder-printers_928993
- https://help.prusa3d.com/article/different-nozzle-types_2193
- https://help.prusa3d.com/article/mmu3-compatibility_470808
- https://help.prusa3d.com/article/mmu3-prusa-nozzle-vs-cht-nozzle_779168
- https://help.prusa3d.com/article/printing-without-purge-tower-on-the-xl-multi-tool_649633
- https://help.prusa3d.com/article/nextruder-silicone-sock-core-one-core-one-l-xl-mk4-s-mk3-9-s_641415
- https://help.prusa3d.com/article/under-extrusion-nextruder-printers_821253
- https://help.prusa3d.com/article/clogged-nozzle-core-one-core-one-l-xl-mk4-s-mk3-9-s_411823
- https://help.prusa3d.com/article/composite-materials-with-metal-or-wood-particles_166863
- https://help.prusa3d.com/article/mutliple-extruders-settings-interlocking-advanced-bonding_867124
- https://help.prusa3d.com/article/experimental-printing-with-different-nozzle-diameters_821176
- https://help.prusa3d.com/article/e3d-v6-nozzles_920168
- https://help.prusa3d.com/article/flexible-steel-sheets-guidepost_2195
- https://help.prusa3d.com/article/stringing-and-oozing_1805
- https://help.prusa3d.com/article/prusament-tpu-95a-material-guide_899653
