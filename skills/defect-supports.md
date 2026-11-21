---
name: defect-supports
description: Support problems - hard to remove or fused supports, supports falling or breaking mid print, rough or scarred surfaces above supports, too many or too few supports, dedicated and soluble support filaments. Read when the user reports supports that won't come off, broken or toppled supports or tree branches, an ugly, droopy or stringy underside above supports, support marks on the model, or supports appearing where they are not wanted or missing where needed.
---
# Supports: removal, failure, scars, amount

## How to recognize it
- Hard to remove: support or interface welds to the part, breaks into pieces, leaves residue; walls fused to supports at the sides.
- Bad surface above supports: underside droopy, stringy or rippled, gaps between lines, or marks where the support touched.
- Failing supports: towers or tree branches topple, detach from the plate, snap mid print; the overhang above then prints into air (spaghetti).
- Too many: supports on the model surface, in holes, under small overhangs or short bridges. Too few: islands start in mid-air, sagging where support was expected.
- Check the Preview to see where supports touch the model.

## Likely causes, most common first
1. Z/XY gap and interface density not balanced (small gap: good surface but welded; large gap: easy removal but droop).
2. Same material for model and support with a top Z distance of 0 (only works with dedicated support or soluble interface filament).
3. Thin, tall or sparse supports (tree tips too thin, small footprint) with poor plate adhesion or too much speed.
4. Wrong type: tree under large flat overhangs (rough), normal grid on organic shapes (hard-to-reach support).
5. Threshold angle and "everywhere" placement generating supports on the model.
6. Mismatched or wet support filament (PVA, Support for PA/PET), or supports left too long on hygroscopic parts.

## Questions worth asking (only when the answer changes the fix)
- Same filament for support, or a dedicated/soluble support filament (which one)? Decides whether top Z distance 0 is allowed.
- Problem is removal, surface quality, falling, or amount? Pick the matching table below.
- Normal or tree support (separate keys)?
- Do supports stand on the plate or on the model?
- Multi-material printer (AMS/MMU/tool changer)? Enables support-interface filament options.

## Slicer fixes
Change one or two values, reslice, check Preview. Distances are rounded to layer height multiples unless `independent_support_layer_height` (process) is `1`.

### A. Supports hard to remove / fused to the part
| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `support_top_z_distance` (process) | increase | +0.05 mm | same material: about 0.1-0.25 mm (Orca default 0.2); 0 only with support/soluble interface filament | rougher, droopier underside |
| `support_object_xy_distance` (process) | increase | +0.1 mm | 0.2-0.5 mm typical (key 0-10) | support reaches less of the overhang edge |
| `support_interface_spacing` (process) | increase | +0.1 mm | 0 = solid interface | rougher underside |
| `support_interface_pattern` (process) | `concentric` (peels in one piece) or `rectilinear` | enum | auto, rectilinear, concentric, spiralinset, `rectilinear_interlaced`, grid | interlaced and grid are stiffer and harder to remove |
| `support_material_interface_fan_speed` (filament) | increase above normal fan | +20 % | 0-100; -1 = off | weaker bond is the goal; too much can warp ABS/ASA |
| `support_base_pattern` (process) | `rectilinear` | enum | default, rectilinear, rectilinear-grid, honeycomb, lightning, hollow | rectilinear is the easiest to remove but least sturdy |
| `support_interface_speed` (process) | increase (dedicated support filament) | +10 mm/s | never above printer limits | less stable interface; warping risk on ABS |
| `support_style` (process) | `snug` when normal supports spread along walls | enum | default, grid, snug, organic, `tree_slim`, `tree_strong`, `tree_hybrid` | tall snug towers less stable |
| `tree_support_branch_distance_organic` / `tree_support_branch_distance` (process) | increase | +1 mm | 1-10 mm | fewer contact points, rougher underside |

### B. Rough or droopy surface above supports
| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `support_interface_top_layers` (process) | increase | +1 | 2-4 | more material, harder to peel |
| `support_interface_spacing` (process) | decrease | -0.1 mm | 0 = solid | harder removal |
| `support_top_z_distance` (process) | decrease | -0.05 mm | see table A | harder removal |
| `support_type` (process) | `normal(auto)` or `support_style` = `tree_hybrid` for big flat overhangs | enum | `normal(auto)`, `tree(auto)`, `normal(manual)`, `tree(manual)` | more material than tree |
| `support_ironing` (process) | set `1` (needs top interface layers or raft) | on | `support_ironing_flow` default 10 % | more time; top interface printed solid |
| `layer_height` (process) | decrease | -0.04 mm | ≤ 75 % of nozzle diameter, min 0.04 mm | longer print |
| `tree_support_top_rate` (process, organic) | increase only if interface layers are not enough | +10 % | default 30 % | harder removal; interface layers are preferred |
| `support_interface_filament` (process) | dedicated support filament slot, then `support_top_z_distance` = 0 | filament index | matching support material only | tool changes, purge (see defect-multimaterial) |
| `support_bottom_z_distance` / `support_interface_bottom_layers` (process) | adjust where support stands on the model: more bottom layers protect that surface | +1 layer / +0.05 mm | -1 = same as top | harder removal there |

### C. Supports falling, breaking or detaching
| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `support_speed` (process) | decrease | -10-20 % | never above printer limits | time |
| `support_base_pattern_spacing` (process) | decrease | -0.5 mm | default 2.5 mm | more material, harder removal |
| `support_base_pattern` (process) | `rectilinear-grid` or `honeycomb` | enum | see table A | harder removal |
| `tree_support_branch_diameter_organic` / `tree_support_branch_diameter` (process) | increase | +1 mm | 1-10 mm | more material |
| `tree_support_branch_diameter_angle` (process, organic) | increase | +2° | 0-15° | wider bases |
| `tree_support_angle_slow` (process, organic) | decrease (more vertical branches) | -5° | 10-85° | less reach around the model |
| `tree_support_wall_count` (process) | set 2 | +1 | 0-2 (0 = auto) | harder removal |
| `tree_support_auto_brim` / `tree_support_brim_width` (process; slim/strong/hybrid) | on, or wider brim | +2 mm | 0 = no brim | more plate area |
| `raft_first_layer_expansion` / `raft_first_layer_density` (process) | increase for normal supports on the plate | +1 mm / +10 % | density 10-100 % | more material |
| `support_style` (process) | `grid` (stable) or `tree_strong` instead of slim/snug | enum | see table A | more material |

### D. Too many or too few supports
| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `support_threshold_angle` (process) | lower = fewer supports; raise = more | ±5° | 1-90, default 30; 0 = special (overlap threshold) | too low: drooping overhangs |
| `support_on_build_plate_only` (process) | set `1` to stop supports on the model | on | check unsupported areas in Preview | some overhangs left unsupported |
| `support_remove_small_overhang` (process) | set `1` | on | boolean | rare tiny droops |
| `support_critical_regions_only` (process) | set `1` (tree(auto) only) | on | boolean | only sharp tails/cantilevers supported |
| `bridge_no_support` (process, normal) / `max_bridge_length` (process, tree) | on / raise length | +5 mm | default 10 mm | long bridges may sag |
| `support_type` (process) | `normal(manual)` / `tree(manual)` + painted enforcers | enum | | only painted areas supported |
| `enable_support` (process) | `1` if overhangs are missing support | on | | see too-many rows |

## Checks the user must do by hand (hardware, material, printer settings)
- Support painting (Prepare -> Support painting, or add a Support blocker / enforcer shape): block supports on cosmetic faces and inside holes, enforce under critical islands or mid-span of long bridges.
- Orientation or cutting the model so fewer, shorter supports are needed.
- Clean plate, good first layer: small support footprints detach first.
- Match support filament to the model material: Support for PLA only with PLA, Support for PA/PET only with PA/PET; PVA is not for PETG. Mismatched pairs can clog the nozzle.
- Dry support filaments (PVA, BVOH, Support for PA/PET) and keep them below ~20 % RH while printing; wet PVA clogs and strings.
- Remove supports within about 2 h on PA/PA-CF parts and with PVA or Support for PA/PET; if they have absorbed moisture, dry the part, let it cool, then remove.
- Pliers/knife and eye protection: snapped pieces can fly.
- Dissolving: PVA/BVOH in warm water (max about 45 °C for PLA parts), hours to overnight, brush off residue. Support for ABS (HIPS) can be dissolved in d-limonene: ventilation, FKM gloves, no open flames or hot surfaces.

## Calibration in Orca (menu Calibration -> ...)
- No support test. Run Temperature and Flow rate first; then print a small overhang test with 2-3 `support_top_z_distance` values as per-object overrides. See calibration-guide.

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- PLA: same-material top Z about 0.2 mm; best interface: Support for PLA, PVA or BVOH (top Z 0). PETG works as interface-only support for PLA.
- PETG: welds to PETG supports; PLA as interface-only works well (PLA and PETG bond poorly). Use BVOH, not PVA, as soluble support.
- ABS/ASA: Support for ABS (HIPS; listed for ABS) as interface; grid style for normal supports; more interface layers ease removal. Purge between them matters (see defect-multimaterial).
- TPU: bonds strongly to TPU supports; larger Z/XY distance or orientation without supports.
- PA/PC and CF/GF: ABS or ASA can support PA6-CF, PAHT-CF, PET-CF; ASA bonds weakly to PA-CF, so use it for interface and body. Remove supports promptly (moisture).
- PVA: base + interface for internal supports, interface only when supports start on the plate (poor plate adhesion); normal supports, not tree.

## Sources
- https://wiki.bambulab.com/en/software/bambu-studio/support
- https://wiki.bambulab.com/en/filament/support
- https://wiki.bambulab.com/en/filament-acc/filament/support-for-abs
- https://wiki.bambulab.com/en/filament-acc/filament/h2d-pla-and-petg-mutual-support
- https://wiki.bambulab.com/en/filament-acc/filament/pva-printing-guide
- https://wiki.bambulab.com/en/software/bambu-studio/support-painting
- https://help.prusa3d.com/article/support-material_1698
- https://help.prusa3d.com/article/failing-supports_1807
- https://help.prusa3d.com/article/bad-looking-surface-above-supports_1803
- https://help.prusa3d.com/article/organic-supports_480131
- https://help.prusa3d.com/article/paint-on-supports_168584
- https://help.prusa3d.com/article/water-soluble-materials-pva-bvoh_162860
- https://help.prusa3d.com/article/water-soluble-bvoh-pva_167012
- https://help.prusa3d.com/article/flexible-materials_2057
- https://www.simplify3d.com/resources/print-quality-troubleshooting/poor-surface-above-supports/
- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_support.html
- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_advanced.html
- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_tree.html
- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_filament.html
- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_raft.html
- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_ironing.html
