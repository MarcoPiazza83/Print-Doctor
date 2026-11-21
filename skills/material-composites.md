---
name: material-composites
description: Fibre- and particle-filled filaments (PLA-CF, PETG-CF, PA-CF/GF, PAHT-CF, PA6-CF/GF, PET-CF, ASA-CF, ABS-GF, PC-CF, PP-CF, PPA-CF, PPS-CF, wood, metal, magnetite, tungsten, glow): hardened nozzles and nozzle wear, clog prevention, speed and flow caps, drying, plates and the Orca keys to adjust. Read when the user prints carbon fibre, glass fibre, wood, metal-filled or glow filament and reports clogs, under-extrusion that gets worse over time, a worn nozzle, brittle or breaking filament, rough or matte-uneven surfaces, weak layers or AMS feeding problems.
---
# Composite filaments (CF, GF, wood, metal, other particles)

## What changes versus the base polymer
- Fibres (carbon, glass, aramid) make parts stiffer, more heat resistant and dimensionally stable, and cut warping a lot (PA-CF, PP-CF, ASA-CF, ABS-GF warp far less than the unfilled grade).
- The price: lower impact strength and weaker layer-to-layer bond, brittle filament, higher clog risk, abrasive wear on nozzle, extruder gears and PTFE tubes.
- Printing temperature is usually the base polymer's, sometimes slightly higher. Plate, enclosure and drying rules of the base polymer still apply (material-pla, material-petg, material-abs-asa, material-pa-pc, material-special).
- Wood fills: mostly cosmetic, weaker, clog-prone (large particles), very hygroscopic. Metal-powder fills (copper, steel, magnetite, tungsten): heavy, abrasive, weaker layers; can be sanded and polished. "Metallic-look" PLA with pigment only is not abrasive.
- Cheap composites more often clog, ooze and snap: brand quality matters.

## Nozzle rules (hardware: explain, never "fix" with settings)
- **Hardened steel (or tungsten carbide, ObXidian-type, diamond-tipped) nozzle required** for CF/GF, metal powder, glow-in-the-dark and other hard particles. Brass and stainless wear quickly: the bore widens, flow and precision drift and extrusion becomes inconsistent.
- **Diameter**: never 0.2 mm (very high clog risk); prefer **0.6 mm** for CF/GF and wood with large particles; 0.4 mm hardened works for most (layer 0.15-0.3 mm, ~100 mm/s max), and is the first choice for Bambu PLA-CF, PETG-CF and particle PLAs. 0.4 mm high-flow nozzles are not recommended for PLA-CF, PETG-CF, PA-CF and PET-CF.
- Orca checks hardness: the nozzle type and nozzle HRC in the printer settings (see the hand checks below) must match the installed nozzle (brass 2, stainless 20, hardened steel 55, tungsten carbide 85). If Orca warns about nozzle hardness, the fix is the real nozzle, not the filament profile.
- Worn nozzle suspected (flow and precision drifting after abrasive spools): inspect or replace the nozzle; do not compensate with flow settings.

## Feeding and AMS (Bambu)
- Brittle or rough filaments can snap or wear tubes: PET-CF, PPA-CF and PPS-CF are not AMS-compatible (external spool, short smooth path, no tight bends); PA-CF/PAHT-CF only for Bambu grades; PETG-CF fine in AMS but not AMS lite; most CF/GF not for AMS lite. Rough filaments slowly grind AMS PTFE tubes.
- H2D: print PET-CF/PPA-CF/PPS-CF from the left hotend to avoid a sharp tube bend on the right.

## Start values (spool label wins)
| Material | Nozzle °C | Bed °C | Glue | Max volumetric speed | Notes |
|---|---|---|---|---|---|
| PLA-CF | 210-240 | 45-65 | optional | as PLA, lower if clogs | dry 50-60 °C, 8 h recommended |
| PETG-CF | 240-270 | 60-80 | release layer on smooth PEI | as PETG | Bambu default flow ratio 0.95 |
| ASA-CF | 240-280 | 90-100 | glue stick | 18 mm³/s | enclosure; speed < 250 mm/s |
| ABS-GF | 240-280 | 90-100 | liquid glue | 12 mm³/s | enclosure; speed < 180 mm/s |
| PA6-GF | 260-300 | 100-110 | glue stick | 10.5 mm³/s | enclosure; speed < 130 mm/s |
| PA-CF / PAHT-CF / PA6-CF | 260-300 | 100-110 | glue stick | 8 mm³/s | enclosure; speed < 100 mm/s |
| PET-CF | 260-300 | 80-110 | glue stick | 8 mm³/s | not AMS; speed < 100 mm/s |
| PPA-CF | 285-320 | 100-120 | glue stick | 8 mm³/s | enclosure; oven-dry hot |
| PPS-CF | 310-340 | 100-120 | glue stick | 6 mm³/s | Bambu X1E/H2 only |
| Wood (PLA) | 190-240 | as PLA | - | as PLA | ≥ 0.6 mm nozzle for coarse fills; must be dried |
| PETG Magnetite 40% | 270 ±5 | 100 ±10 | textured/satin sheet | - | hardened; do not clean the sheet with IPA |
| PETG Tungsten 75% | 260 ±10 | 80 ±10 | glue on smooth PEI | - | hardened; no part cooling |

Drying (oven): PA6/PAHT/PET-CF 80 °C 8-12 h; ABS-GF/ASA-CF 80 °C 8 h; PETG-CF 60-65 °C 8 h; PPA-CF 100-140 °C 8-12 h (an AMS HT may not dry PPA-CF/PPS-CF fully). PA6-CF loses about a third of its strength when humid; PPS-CF barely changes. Wet composites string, ooze and leave a rough, uneven texture.

## Slicer fixes
| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `filament_max_volumetric_speed` (filament) | decrease to the cap in the table when clogs, skipping or under-extrusion appear at speed | to cap, then -10% | lower freely; raise at most +10% | longer print |
| `outer_wall_speed` (process) | decrease and keep it constant over the part for even gloss | to ≤ 100 mm/s on high-temp composites | machine limits | longer print |
| `layer_height` (process) | increase if a 0.4 mm nozzle clogs at fine layers | to 0.2 mm (0.4 nozzle) / 0.3 mm (0.6 nozzle) | ≤ 75% of nozzle diameter | coarser surface |
| `filament_flow_ratio` (filament) | lower slightly if dried filament still clogs or over-extrudes (PETG-CF: 0.93-0.94) | -0.01 to -0.02 | 0.8-1.2 | under-extrusion if overdone; run Flow Rate calibration |
| `nozzle_temperature` (filament) | increase for weak layers or poor melt at speed | +5 °C | inside the filament's recommended range | more oozing |
| `support_type` = `normal(auto)` with `support_style` = `grid`, or `support_type` = `tree(auto)` with `support_style` = `tree_hybrid` (process) | use for heavy or tall composite parts; tree supports alone can be unstable | - | - | harder removal |
| `enable_support` (process) under long bridges | add on PA/PET/PPS composites | - | - | support marks |
| `sparse_infill_pattern` = `gyroid`, `sparse_infill_density`, `wall_loops` (process) | for strength | +1 wall / +10% | ≤ 6 walls, ≤ 50% infill | more warping risk, more time |
| plate key of the plate in use (`textured_plate_temp`, `hot_plate_temp`, `eng_plate_temp`, `cool_plate_temp` and _initial_layer variants) (filament) | increase if PA/PET composites lift | +5 °C | +10 °C over current, ≤ 120 °C | harder removal |
| `fan_min_speed`, `fan_max_speed` (filament) | set to 0 only for PETG Tungsten; otherwise keep the base polymer's cooling | - | 0-100% | overhang quality |

## Checks the user must do by hand
- Install the right nozzle (hardened, 0.4 or 0.6 mm) and set it in printer settings (`nozzle_type`, `nozzle_hrc`: printer settings, by hand).
- Dry the filament and print from a dry box; check the desiccant.
- First layer must be correct (Z offset, clean plate): a squashed first layer is a common clog trigger with fibres.
- Clean the nozzle before long composite jobs (cold pull, not on coated ObXidian-type nozzles); avoid many short start/stop jobs that build residue.
- After high-temp composites, purge at the old temperature before loading PLA/PETG/TPU.
- Wear gloves and eye protection when handling, removing supports or sanding fibre parts (fine sharp fibres).
- Clean the extruder gears more often; abrasive dust accumulates.

## Calibration in Orca
Calibration → Flow ratio and Pressure Advance per spool; Calibration → Max flowrate after drying (keep the result at or below the vendor cap). Temperature tower if layers are weak. See calibration-guide.

## Related skills
defect-clogs-heat-creep (clogs), defect-extrusion (inconsistent extrusion), defect-layer-adhesion (weak layers), defect-multimaterial (AMS and purge).

## Sources
- https://wiki.bambulab.com/en/general/filament-guide-material-table
- https://wiki.bambulab.com/en/filament/absgf_pa6gf
- https://wiki.bambulab.com/en/filament/asacf_pahtcf
- https://wiki.bambulab.com/en/filament/petcf_ppacf
- https://wiki.bambulab.com/en/filament/petg
- https://wiki.bambulab.com/en/filament/pla
- https://wiki.bambulab.com/en/filament-acc/acc/nozzles
- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament
- https://wiki.bambulab.com/en/knowledge-sharing/how_to_avoid_nozzle_clogs
- https://help.prusa3d.com/article/composite-materials-filled-with-carbon-kevlar-or-glass_167387
- https://help.prusa3d.com/article/composite-materials-with-metal-or-wood-particles_166863
- https://help.prusa3d.com/article/petg-magnetite-40_1078164
- https://help.prusa3d.com/article/petg-tungsten_1080996
- https://help.prusa3d.com/article/prusa-nozzle-types-for-nextruder-printers_928993
- https://help.prusa3d.com/article/different-nozzle-types_2193
- https://www.orcaslicer.com/wiki/printer_settings/basic%20information/printer_basic_information_accessory.html
