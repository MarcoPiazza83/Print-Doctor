---
name: defect-multimaterial
description: Multi-material and multi-colour printing with AMS, MMU or multi-tool/dual-nozzle printers - flushing (purge) volumes, prime/wipe tower stability, colour bleeding and contamination, ooze from idle nozzles, weak bonds between materials, and reducing purge waste. Read when the user reports colours mixing or bleeding, wrong colour streaks after a filament change, a prime tower that falls, wobbles or collects blobs, drips or strings from the idle nozzle, too much purge/poop or a huge tower, or parts of different materials coming apart.
---
# Multi-material: flushing, prime tower, colour bleeding, ooze, waste

## How to recognize it
- Colour bleeding: the new colour starts tinted with the previous one (worst from dark to light), streaks in light areas, or infill colour showing through thin or translucent walls.
- Contaminated supported surfaces: strings or gaps under supports printed with a support filament (support material mixed with model material or vice versa).
- Prime tower trouble: tower leans, topples or detaches, blobs build up on it, the nozzle scrapes or knocks it.
- Idle-nozzle ooze (dual nozzle, tool changer, IDEX): drips, strings or blobs on the part from the parked nozzle, or ooze dropped where the tool change or heat-up happens.
- Bubbles or pits right after filament changes (air in the re-melted tip).
- Waste: big purge per change, heavy tower, long print time.
- Material boundaries split apart (e.g. TPU on PLA/PETG, PLA on PETG).

## Likely causes, most common first
1. Flushing volume too low for that colour pair (dark -> light, silk/glitter, support or soluble filaments need more).
2. Flush into infill/objects with few walls or light/translucent outer colour.
3. Prime tower too tall and thin, no brim, poor plate adhesion, or walls printed in a filament that does not bond to the others.
4. Wet filament (main cause of ooze from preheated idle nozzles and of bubbles after changes).
5. Idle nozzle kept at full temperature, or the heat-up wait happening above the part.
6. Materials that do not bond chemically at the boundary.
7. Many filament changes per layer (orientation, thin layers) multiplying waste.

## Questions worth asking (only when the answer changes the fix)
- Printer type: single nozzle with AMS/MMU (flush volumes) or dual nozzle / tool changer (ooze, prime volume)? Bambu printers always use the Type 1 tower; most others use Type 2.
- Which colour/material pairs show the problem, and in which direction?
- Is the goal quality (no bleeding) or saving filament/time?
- Flush into infill/objects enabled? Light or translucent walls? Filament dried recently?

## Slicer fixes
Flushing volumes are not a preset key: they live in the Flushing volumes dialog (button next to the project filament list) as a from/to matrix plus a multiplier. The plugin cannot change them; tell the user to edit them by hand (see Checks). Raise the cell of the pair that bleeds (or the multiplier) in small steps until the tint is gone; lower the multiplier to 0.8-0.9 only after a test print shows no tint.

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `enable_prime_tower` (process) | set `1` for multi-colour | on | not available with by-object printing | material, plate space |
| `flush_into_infill` (process) | `0` if colour shows through walls; `1` to save waste | toggle | needs prime tower | mixed-colour infill visible through light/translucent walls |
| `wall_loops` (process) | increase when flushed infill shows through | +1 | | more time |
| `flush_into_support` (process) | `0` with support filaments that must stay pure (e.g. Support for ABS), else `1` | toggle | needs prime tower | slightly weaker support when on |
| `filament_prime_volume` (filament) | increase on bubbles/tint right after changes (Type 1 tower, e.g. Bambu) | +10-15 mm³ | PC: 45 mm³ or more; Bambu H2D ABS with Support for ABS: 90 mm³ | bigger tower |
| `prime_volume` (process) | increase (Type 2 tower, fixed purge per change) | +10 mm³ | default 45 mm³ | bigger tower |
| `prime_tower_brim_width` (process) | increase if the tower detaches or wobbles | +2 mm | -1 = auto from height | plate area |
| `wipe_tower_wall_type` (process) | rib (default); cone on Type 2 towers for tall thin towers | enum | rectangle, cone, rib | cone has a wider base |
| `prime_tower_width` (process) | increase (not possible with rib wall type) | +10 mm | | more material |
| `prime_tower_enable_framework` (process) | set `1` (Type 1) if the tower has hollow zones | on | boolean | more material |
| `wipe_tower_max_purge_speed` (process) | decrease (Type 2) if blobs get knocked or the tower shakes | -10-20 mm/s | default 90 mm/s, min 10 | slower changes |
| `prime_tower_infill_gap` (process) | increase (Type 1) if material piles up on the tower | +25 % | 100-200 % (default 150 %) | larger tower |
| `wipe_tower_filament` (process) | set one filament (not soluble/flexible) for tower walls when mixing material types | filament index | 0 = any | that filament used on every tower layer |
| `ooze_prevention` (process) | set `1` on multi-tool printers with idle-nozzle ooze | on | boolean | slower tool changes (reheat) |
| `filament_change_length` (filament) — BY HAND | increase if the outgoing nozzle oozes (dual nozzle) | +5 mm | by hand only (plugin cannot check it): Filament → Multimaterial; 0 = no ramming | more waste |
| `filament_ramming_travel_time` (filament) — BY HAND | increase for runny filaments like TPU | +1 s | by hand only: Filament → Multimaterial; 0 = off | longer change |
| `filament_multitool_ramming` (filament) — BY HAND | enable on tool changers with a wipe tower | on | by hand only: Filament → Multimaterial | small extra waste |
| `interlocking_beam` (process) | set `1` where materials do not bond (TPU + rigid, PLA + PETG) | on | width default 0.8 mm, layers 2, depth 2 | more changes |
| `mmu_segmented_region_max_width` / `mmu_segmented_region_interlocking_depth` (process) | set for painted parts whose colours separate | +1 mm | 0 = off; ignored with beams | colour boundary less sharp inside |
| `interface_shells` (process) | set `1` for translucent multi-material parts | on | boolean | more material |
| `wipe_tower_no_sparse_layers` (process) | `1` to cut waste/time | on | collision risk; Orca rejects unsafe layouts | timelapse/clumping detection disable it |
| `wipe_tower_sparse_layers_combination` (process) | `1` (safe alternative) | on | only at low layer heights | less saving |
| `layer_height` (process) | increase to cut the number of changes | +0.04 mm | ≤ 75 % of nozzle diameter | coarser surface |

Notes for the AI:
- With a prime tower, `independent_support_layer_height` (process) is ignored and all objects must use the same raft layers.
- Type 2 towers use `prime_volume` per change unless the printer is a single-extruder MMU with purge in prime tower (then the flush matrix is used). Type 1 uses `filament_prime_volume` per filament (and `filament_prime_volume_nc` for hotend changes).
- Infill colour bleeding is fixed by more walls or turning flush into infill off, not by more flush.

## Checks the user must do by hand (hardware, material, printer settings)
- Flushing volumes dialog: raise the cells for the bleeding pairs. Guide values: Prusa MMU soluble supports at least 200-240 mm³ per change (240+ when coming from PVA/BVOH); Bambu Support for ABS -> ABS up to 800; stringy surfaces above support filament: about double the original. Recalculate restores auto values.
- Dry the filament, especially PVA, BVOH, PETG, PC, TPU; keep AMS/dry box below about 20 % RH for PVA.
- Temperature of idle tools (filament Idle temperature, process Temperature variation under Ooze prevention): the plugin cannot change temperature keys; the user lowers them by hand if idle nozzles ooze.
- Printer settings (by hand, Type 2 multi-tool only): Wait for temperature on wipe tower (`wait_for_temp_on_wipe_tower`) parks the heat-up ooze beside the tower; Tool change on wipe tower (`tool_change_on_wipe_tower`) issues the change over the tower, not over the part. Check that firmware macros do not already wait for temperature.
- Tower on a clean plate area, away from tall parts when no-sparse-layers is used.
- Clean nozzle wiper, purge chute and nozzle tip; check AMS/MMU cutter and PTFE path if changes fail.
- Reduce waste by layout: put colour changes low in the part (tower stops at the last change), print several copies per plate, add "Flush into this object" parts of similar height, rotate tall multi-colour parts only if their colours run vertically. Compare by slicing.
- Prusa XL: the purge tower can be turned off only with well-dried filament; check the print regularly.
- Bambu H2D/H2C: grouping the filaments with the largest mutual flush on different nozzles removes that flush.

## Calibration in Orca (menu Calibration -> ...)
- Flow rate and Pressure advance per filament (each filament keeps its own values), Temperature and Max volumetric speed for each material.
- Flush volumes: no built-in test; print a small two-colour cube with the worst pair (dark -> light) and adjust the matrix cell. See calibration-guide.

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- PLA: easiest; glossy/silk and glitter variants need more flush. PLA + PETG bond poorly: good as support pair, use beam interlocking for mixed parts.
- PETG: dry first; keep the prime volume generous; PVA is not compatible, use BVOH or PLA interfaces.
- ABS/ASA: Support for ABS is hard to flush out; high flush from support to ABS, flush into infill/support off, more prime volume (Bambu H2D: about 90 mm³). Long changes overcool layers: keep the enclosure closed.
- TPU: dry thoroughly; oozes from a parked nozzle; use ramming and travel time after ramming; beam interlocking against rigid parts. Bambu H2D: TPU on the left nozzle blocks the right one.
- PA/PC: very hygroscopic and runny when hot; PC needs about 45 mm³ or more prime volume.
- CF/GF: check AMS and nozzle compatibility in the vendor filament guide before loading.

## Sources
- https://wiki.bambulab.com/en/software/bambu-studio/reduce-wasting-during-filament-change
- https://wiki.bambulab.com/en/software/bambu-studio/parameter/prime-tower
- https://wiki.bambulab.com/en/software/bambu-studio/multi-color-printing
- https://wiki.bambulab.com/en/software/bambu-studio/h2c-purge-mode
- https://wiki.bambulab.com/en/software/bambu-studio/manual/dual-nozzles-slicing-filament-grouping
- https://wiki.bambulab.com/en/software/bambu-studio/beam-interlocking
- https://wiki.bambulab.com/en/h2/manual/soft-and-hard-filament-multi-material-printing-guide
- https://wiki.bambulab.com/en/filament/support
- https://wiki.bambulab.com/en/filament-acc/filament/support-for-abs
- https://wiki.bambulab.com/en/filament-acc/filament/pva-printing-guide
- https://help.prusa3d.com/article/wipe-tower_125010
- https://help.prusa3d.com/article/purging-volumes-mmu_125097
- https://help.prusa3d.com/article/multi-material-painting_262620
- https://help.prusa3d.com/article/mutliple-extruders-settings-interlocking-advanced-bonding_867124
- https://help.prusa3d.com/article/water-soluble-materials-pva-bvoh_162860
- https://help.prusa3d.com/article/water-soluble-bvoh-pva_167012
- https://help.prusa3d.com/article/printing-without-purge-tower-on-the-xl-multi-tool_649633
- https://help.prusa3d.com/article/support-settings-for-the-xl_681927
- https://www.orcaslicer.com/wiki/print_settings/multimaterial/multimaterial_settings_prime_tower.html
- https://www.orcaslicer.com/wiki/print_settings/multimaterial/multimaterial_settings_flush_options.html
- https://www.orcaslicer.com/wiki/print_settings/multimaterial/multimaterial_settings_ooze_prevention.html
- https://www.orcaslicer.com/wiki/print_settings/multimaterial/multimaterial_settings_advanced.html
- https://www.orcaslicer.com/wiki/material_settings/multimaterial/material_multimaterial.html
- https://www.orcaslicer.com/wiki/printer_settings/multimaterial/printer_multimaterial_wipe_tower.html
