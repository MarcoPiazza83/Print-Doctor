---
name: materials-overview
description: Quick comparison of all filament materials (PLA, PETG/PCTG, ABS/ASA, TPU, PA/nylon, PC, CF/GF composites, wood/metal fills, PVA/BVOH, HIPS, support filaments, PP, PVB, PPS, PEI) with nozzle and bed ranges, enclosure and hardened-nozzle needs, drying table, wet-filament signs, plate choice and the Orca plate-temperature keys; routes to the material-* skill. Read when the user asks which material, temperature, plate, glue or drying settings to use, whether filament is wet or must be dried, or mentions a material before a defect is clear.
---
# Materials overview

Values are start points for a 0.4 mm nozzle; the spool label and a temperature tower win. Detail and fixes live in the routed skill.

## Comparison table
| Material | Nozzle °C | Bed °C | Enclosure | Hardened nozzle | Skill |
|---|---|---|---|---|---|
| PLA (basic, matte, silk, PLA+) | 200-220 (family 190-240) | 45-65 PEI, 35-45 Cool Plate | no; open door if bed > 45 °C | no | material-pla |
| PETG, PETG-HF, PCTG, CPE | 230-250 | 70-80 | no; open door if bed > ~70 °C | no | material-petg |
| ABS / ASA | 240-265 | 90-110 | yes | no | material-abs-asa |
| TPU / flexibles | 220-240 | 30-45 | no | no | material-tpu |
| PA (nylon) | 240-285 | 100-110 + glue | yes | no (yes for filled) | material-pa-pc |
| PC, PC Blend, PC-ABS | 260-290 | 100-115 + glue | yes | no | material-pa-pc |
| PLA-CF / PETG-CF | 210-240 / 240-270 | as base | as base | yes | material-composites |
| ABS-GF, ASA-CF | 240-280 | 90-100 + glue | yes | yes | material-composites |
| PA-CF/GF, PAHT-CF, PET-CF | 260-300 | 80-110 + glue stick | yes | yes | material-composites |
| PPA-CF / PPS-CF | 285-320 / 310-340 | 100-120 + glue stick | yes (PPS-CF: Bambu X1E/H2 only) | yes | material-composites |
| Wood-filled | as base (190-240 PLA) | as base | no | no, but ≥ 0.6 mm nozzle for coarse fills | material-composites |
| Metal-powder, glow, magnetite, tungsten | as base | as base | no | yes | material-composites |
| PVA / BVOH | 190-215 | 45-60 | no | no | material-special |
| HIPS, Support for ABS | 225-255 | 100-110 | yes | no | material-special |
| Support for PLA, PLA/PETG | 190-240 | as model | as model | no | material-special |
| Support for PA/PET | 260-300 | as model | yes | yes | material-special |
| PP | 220-250 | 80-100, PP sheet/tape | recommended | no | material-special |
| PVB | 205-225 | ~75 | no | no | material-special |
| PPS, PEI/Ultem | 330-430 | 120-150 | heated chamber | - | material-special (beyond plugin limits) |

Material groups that must not share a print or a hot chamber (Bambu H2D/H2C enforce it; the chamber logic applies to any enclosed printer): low-temperature PLA, PETG, TPU, PVA, BVOH vs high-temperature ABS, ASA, PC, PA, PET-CF, PPS, PPA. Low-temperature filaments soften in the extruder above ~45 °C chamber and clog.

## Is the filament wet?
Signs: popping or hissing at the nozzle, steam, bubbles or holes in walls, rough or foamy surface, sudden heavy stringing or oozing, weak or brittle layers, blobs; damp PVA/BVOH turns soft and fails to feed. When unsure, dry it: no slicer setting compensates. Most sensitive: PVA, BVOH, PA, PC, TPU, Support for PA/PET, PPA/PPS, PEI, PVB, wood fills, PETG.

## Drying table (oven or filament dryer)
| Material | Temperature | Time | Need |
|---|---|---|---|
| PLA basic/matte | 45-50 °C | 6-8 h | only if symptoms |
| PLA silk, PLA-CF, Support for PLA | 50-55 °C | 8 h | recommended |
| PLA wood | 55-65 °C | 8 h | required |
| PVB | 45 °C | 8 h | required |
| PETG, PETG-CF, PCTG | 55-65 °C | 6-8 h | recommended |
| TPU | 60-70 °C | 4-8 h | required |
| PP-CF/GF | 70 °C | 2-4 h | recommended |
| ABS, ASA, ABS-GF, ASA-CF | 75-85 °C | 4-8 h | recommended |
| Support for PLA/PETG | 75 °C | 8 h | recommended |
| Support for ABS / HIPS | 80 °C | 4 h | optional |
| PC, PC Blend | 75-85 °C | 5-8 h | required |
| PA, PA-CF/GF, PAHT-CF, PET-CF | 80-85 °C | 8-12 h | required |
| PVA, Support for PA/PET | 75-85 °C | 8-12 h | required |
| PPA-CF | 100-140 °C | 8-12 h | required |
| PPS | 110 °C | ≥ 4 h | required |
| PEI 1010 | 150 °C | 6-8 h | required |

Rules (explain to the user, these are hand actions):
- Never exceed the spool's heat rating (Bambu low-temp spools ~70 °C, high-temp ~90 °C; old black Prusament spools ~45 °C unless screwed together; new Prusament black 90 °C, grey 150 °C). Too hot fuses the coils.
- Home ovens drift: check with a separate thermometer.
- Bambu AMS 2 Pro reaches 65 °C (cannot fully dry ABS/ASA/PC/PA/TPU/PVA); AMS HT and AMS 3H reach 85 °C (not enough for PPA-CF/PPS-CF). Remove PLA/TPU from the AMS before a hot drying cycle.
- Heated-bed drying (enclosed Bambu printers only): unload the filament, cover the spool with its box, flip every 6 h; roughly 10-15 °C above the oven value, ~12 h.
- After drying, move the spool straight into a sealed box or AMS with active desiccant (silica beads turning purple = saturated; regenerate at 80-90 °C, never above 100 °C). Keep PVA and similar below 20% RH.

## Plate choice and Orca bed keys
Bed temperature keys are filament keys, one per plate type, each with an _initial_layer twin. Change only the one matching the plate selected in Orca (a value of 0 means the filament does not support that plate). Plugin limit: at most +10 °C over the current value, never above 120 °C.
| Plate in Orca | Key | Good for |
|---|---|---|
| Cool Plate | `cool_plate_temp` | PLA, PVA |
| Cool Plate SuperTack | `supertack_plate_temp` | PLA, PETG only |
| Textured Cool Plate | `textured_cool_plate_temp` | follow the filament preset (0 = not supported) |
| Engineering Plate | `eng_plate_temp` | ABS, ASA, PC, PA, composites (glue); PLA needs glue |
| High Temp / Smooth PEI | `hot_plate_temp` | PLA without glue; ABS/ASA, PETG, PC, TPU only with a glue layer (it protects the PEI) |
| Textured PEI | `textured_plate_temp` | PLA, PETG, TPU (no glue); ABS/ASA, PC, PA with glue stick |

- Glue stick: PA, PC, ASA-CF, PA/PAHT/PA6-CF/GF, PET-CF, PPA-CF, PPS-CF; liquid glue suits ABS-GF but is not recommended for PA/PC.
- Prusa sheets: Special PA Nylon sheet for polyamides (clean with water and dish soap only); PP sheet for polypropylene (clean with ~90% IPA, no acetone); satin or textured for PC Blend, PETG Magnetite and Tungsten; smooth PEI for PVB.
- Clean plates with dish soap and hot water; no acetone on Bambu plates.

## Hardened nozzle
Required for CF/GF, metal powder, glow-in-the-dark and other hard particles; brass and stainless wear fast. Avoid 0.2 mm nozzles with any fill; prefer 0.6 mm for CF/GF. Details in material-composites.

## Sources
- https://wiki.bambulab.com/en/general/filament-guide-material-table
- https://wiki.bambulab.com/en/filament-acc/filament/dry-filament
- https://wiki.bambulab.com/en/knowledge-sharing/desiccant-status
- https://wiki.bambulab.com/en/filament-acc/filament/h2d-filament-config-limit
- https://wiki.bambulab.com/en/filament/beginner
- https://wiki.bambulab.com/en/filament/support
- https://wiki.bambulab.com/en/filament/petcf_ppacf
- https://help.prusa3d.com/filament-material-guide
- https://help.prusa3d.com/article/drying-filament_332086
- https://help.prusa3d.com/article/special-pa-nylon-steel-sheet_341570
- https://help.prusa3d.com/article/pp-steel-sheet_815373
- https://help.prusa3d.com/article/pps-polyphenylene-sulfide_788028
- https://help.prusa3d.com/article/how-to-print-with-pei-1010_794930
- https://help.prusa3d.com/article/composite-materials-with-metal-or-wood-particles_166863
- https://help.prusa3d.com/article/petg-magnetite-40_1078164
- https://help.prusa3d.com/article/petg-tungsten_1080996
- https://help.prusa3d.com/article/pvb_196708
- https://help.prusa3d.com/article/polycarbonate-pc_165812
- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html
