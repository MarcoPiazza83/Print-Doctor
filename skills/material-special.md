---
name: material-special
description: Support and soluble filaments (PVA, BVOH, HIPS, Bambu Support for ABS, Support for PLA, PLA/PETG and PA/PET), polypropylene (PP, PP-CF), PVB and high-temperature niche materials (PPS, PEI/Ultem): pairing rules, drying, plates, support and purge settings in Orca. Read when the user prints soluble or break-away supports, PVA that clogs or will not stick, supports that do not dissolve, PP that will not stick or warps, PVB for smoothing, or asks about PPS or PEI/Ultem.
---
# Special materials: soluble and support filaments, PP, PVB, PPS, PEI

## Support filaments: pairing (wrong pairs clog or do not bond)
| Support filament | Use with | Removal | Moisture |
|---|---|---|---|
| PVA | PLA (incl. PLA-CF/GF). Not with PETG | dissolves in water | extreme |
| BVOH | PLA and PETG; stiffer, prints more reliably than PVA | dissolves in water | extreme |
| HIPS / Bambu Support for ABS (HIPS based) | ABS (also PETG) | break-away, or d-limonene | low |
| Bambu Support for PLA | PLA (not PLA Aero) | break-away | low |
| Bambu Support for PLA/PETG | PLA and PETG | break-away | moderate |
| Bambu Support for PA/PET | PA, PA-CF, PET-CF | break-away; remove within ~2 h of print end | high |
| PVB | PLA-like temperatures | dissolves in IPA | high |

Needs a multi-material system (AMS, MMU, XL, H2D/H2C dual nozzle). Bambu: PVA not recommended on A-series/AMS lite (open spools re-absorb water; keep prints with PVA on AMS lite under ~1 h); H2D must not print PVA in one hotend and PETG in the other at the same time.

## PVA / BVOH
- Nozzle: PVA ~190-215 °C, BVOH ~215 °C; bed ~45-60 °C. Bonds poorly to PEI: avoid PVA directly on the plate where possible.
- Moisture is the main failure: wet PVA turns soft and sticky, will not feed, tangles in gears, clogs the hotend and does not stick. Freshly dried PVA in a ~55% RH room is degraded within 1-3 h; keep it in a sealed box below 20% RH. Dried PVA bends stiffer than PLA: a quick dryness test.
- Drying: 75-85 °C, 8-12 h in an oven or dryer; AMS HT 85 °C ~18 h; an AMS 2 Pro (65 °C) cannot dry it completely. Put it in the dry box right after drying, without letting it cool in room air.
- Low flow: about 4 mm³/s versus ~15 mm³/s for PLA, so long print times.
- Dissolve in warm water (max ~45 °C for PLA parts), hours to overnight, then brush. Porous parts can take water inside.

## Slicer settings for soluble and break-away supports
| Key (preset) | Direction | Typical value | Safe limit | Side effects |
|---|---|---|---|---|
| `support_interface_filament` and `support_filament` (process) | select the support filament slot | full soluble: both = PVA/BVOH; interface-only: base = model filament | slot must hold the support filament | full soluble costs more material and time |
| `support_top_z_distance` (process) | 0 for soluble interfaces | 0 | - | supported surface fused if the support filament is wrong |
| `support_type` = `normal(auto)`, `support_style` = `grid` (process) | prefer over tree when PVA is the body | - | - | more material |
| `support_interface_not_for_body` (process) | 1 with break-away/soluble interface over a default base | 1 | - | none |
| `flush_into_support`, `flush_into_infill` (process) | 0 for soluble supports and for Support for ABS (mixed-in model filament stops PVA dissolving and weakens HIPS supports) | 0 | - | more purge on the tower |
| `prime_volume` (process) / `filament_minimal_purge_on_wipe_tower` (filament) | increase if supported faces show strings, gaps or residue | x1.5-2 | - | more waste |
| `filament_max_volumetric_speed` (filament, PVA/BVOH) | keep low | ~4 mm³/s | lower freely, raise max +10% | slower supports |
| `support_interface_top_layers` (process) | increase for easier removal of break-away supports | +1 | 0-3 | more material |
| `support_interface_speed` (process) | increase slightly if break-away supports are hard to remove; decrease if the part does not stick to the interface | ±10-20% | machine limits | too fast can lift or warp |
| `support_top_z_distance` (process, break-away only) | decrease if the model will not bond onto the interface | -0.05 mm | ≥ 0 | harder removal |
| `bridge_speed` (process) | increase if break-away supports bond too hard (Bambu: 100-150 mm/s) | +20 mm/s | machine limits | bridge sag |

Purge between model and support filament happens in the flushing-volumes dialog (not a preset key): tell the user to raise it; for changes to/from PVA or BVOH ~200-240 mm³ or more, doubling the default if residue shows; Support for ABS → ABS needs a very large value (Bambu uses 800). Bambu H2D with ABS + Support for ABS: `filament_prime_volume` (filament, ABS) 90 mm³ and `fan_min_speed` (filament, ABS) 50%. Do not use the adaptive (variable) layer height tool with Support for ABS. With ABS + Support for ABS, model layers at the height of support swaps are weaker (overcooling during swaps, residue): orient so loads do not cross those layers. Prime tower note: with a prime tower, independent support layer height is ignored.

## HIPS and limonene
- Nozzle 225-255 °C, bed 100-110 °C; ABS-like, lighter, lower shrink; sticks to PEI sheets, use a brim for small contact areas. Not hygroscopic (drying optional, ~80 °C 4 h).
- d-Limonene also attacks some ABS/ASA grades: soak briefly to loosen the HIPS, then pull it off, instead of dissolving fully. Limonene: flash point ~48 °C (no flames, no hot bed nearby), ventilated room, fluororubber or laminated gloves (not latex).

## PP (polypropylene)
- Nozzle 220-270 °C (brand dependent), bed 80-100 °C. Very low adhesion to PEI: use a PP sheet, PP tape on smooth PEI, or a PP-specific adhesive. Prusa PP sheet: clean cold with ~90% IPA, never acetone; it also works for PLA, PETG and TPU.
- Strong warping: enclosure, `brim_type` `outer_only` with `brim_width` 5-10 mm (process), sparse infill. Prints better with a hotter `nozzle_temperature` for layer bond and a cooler `nozzle_temperature_initial_layer` (filament), both inside the filament range.
- PP-CF/PP-GF warp almost not at all (hardened nozzle: material-composites). Dry PP-CF/GF ~70 °C 2-4 h.

## PVB
- Nozzle 205-225 °C, bed ~75 °C, PLA-like and low warping; smooth PEI or satin sheet (poor on powder-coated textured). Smoothed with IPA (vapour, bath, brush).
- Clear parts: `spiral_mode` = 1 (process) with a 0.8 mm nozzle; extra walls stay visible after smoothing. Weak layer bond, PLA-like heat resistance: not for mechanical parts.
- Hygroscopic: dry 45 °C, 8 h.

## PPS and PEI (Ultem): specialist printers only
- PPS: nozzle 330-370 °C, bed 120-150 °C, actively heated chamber ≥ 65 °C, dry ≥ 4 h at 110 °C, HT adhesive in several layers. PPS-CF (Bambu, X1E/H2 only): 310-340 °C, bed 100-120 °C, brittle (no tight tube bends, external dry box), hardened nozzle.
- PEI 9085/1010: nozzle 370-420 °C, bed 150-155 °C, chamber 85-90 °C, dry 130-150 °C (1010: 150 °C, 6-8 h; regains moisture within tens of minutes), thin HT adhesive layer, always a brim, round compact bases, slow speed, remove supports while warm. Wet PEI gives a foamy base, bubbles and strings.
- These bed and chamber values exceed what the plugin may set (bed max 120 °C, no chamber control): explain to the user that a high-temperature printer and its vendor profile are required.

## Checks the user must do by hand
- Dry and store soluble/PA support filaments sealed; replace saturated desiccant (silica beads turn purple).
- Load the support filament in the slot the profile expects; the printer cannot detect it.
- Set flushing volumes in the flushing dialog; calibrate the MMU/AMS feeding for soft PVA.
- Choose the plate (PP sheet/tape for PP; smooth PEI or satin for PVB).

## Calibration in Orca
Calibration → Flow ratio and Max flowrate for PVA/BVOH and PP after drying; Temperature tower for PP and PVB. See calibration-guide; purge tuning in defect-multimaterial, support geometry in defect-supports.

## Sources
- https://wiki.bambulab.com/en/filament/support
- https://wiki.bambulab.com/en/filament-acc/filament/pva-printing-guide
- https://wiki.bambulab.com/en/filament-acc/filament/support-for-abs
- https://wiki.bambulab.com/en/filament-acc/filament/h2d-filament-config-limit
- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament
- https://wiki.bambulab.com/en/knowledge-sharing/desiccant-status
- https://wiki.bambulab.com/en/filament/petcf_ppacf
- https://wiki.bambulab.com/en/h2/manual/PPA-PPS-printing-guide
- https://wiki.bambulab.com/en/general/filament-guide-material-table
- https://help.prusa3d.com/article/water-soluble-bvoh-pva_167012
- https://help.prusa3d.com/article/water-soluble-materials-pva-bvoh_162860
- https://help.prusa3d.com/article/hips_167118
- https://help.prusa3d.com/article/polypropylene-pp_167126
- https://help.prusa3d.com/article/pp-steel-sheet_815373
- https://help.prusa3d.com/article/pvb_196708
- https://help.prusa3d.com/article/pps-polyphenylene-sulfide_788028
- https://help.prusa3d.com/article/pei-ultem_725809
- https://help.prusa3d.com/article/how-to-print-with-pei-1010_794930
- https://help.prusa3d.com/article/drying-filament_332086
- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_filament.html
- https://www.orcaslicer.com/wiki/print_settings/multimaterial/multimaterial_settings_flush_options.html
