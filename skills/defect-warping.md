---
name: defect-warping
description: Warping and lifting of the part: corners or edges curling up off the plate, a curved bottom, the base peeling during the print, parts coming loose or popping off mid print, the ripple left where the nozzle hits a lifted corner. Read when the user reports warping, corners lifting, edges curling, the print detaching or falling off the bed mid print, or a bent bottom face.
---
# Warping, lifting corners, part detaching mid print

## How to recognize it
- Corners or edges rise off the plate during the print, mostly on large, flat or long parts with sharp corners; after removal the bottom face is curved.
- A horizontal ridge a few mm above the plate on the side walls: the nozzle hit a corner that had already lifted. Slight lifting can mimic flow or top-surface defects: check that the base is flat before tuning extrusion.
- The whole part slides or pops off mid print: grip problem (plate, plate type, Z) or the nozzle knocking over a tall thin part.
- Only the first layer peels or never sticks: use defect-first-layer. Curling tips or overhangs high in the part: defect-overhangs-bridges / defect-overheating-small-features. Horizontal cracks between layers on ABS/ASA/PC: same thermal stress, see defect-layer-adhesion.

## Likely causes, most common first
1. Dirty plate (skin oil from fingers is the top cause).
2. Plate type selected in Orca does not match the physical plate: the bed is heated to the wrong plate temperature. Bambu: on a Textured PEI plate the printer lowers the nozzle 0.04 mm only if Textured PEI is the selected plate type.
3. Material shrinkage vs. cold surroundings: risk order PC > PA-CF > PA > ABS > ASA > PETG > PLA. Drafts (window, AC, desk fan) and rooms below about 20 °C make even PLA/PETG lift; large ABS/ASA/PC/PA parts warp on open-frame printers.
4. Bed temperature too low for material and plate.
5. Too much part cooling: fan running in the first layers, strong auxiliary fan, high fan on ABS/ASA/PC.
6. First layer not squished enough (Z offset, levelling): see defect-first-layer.
7. Small contact area or sharp corners and no brim.
8. Large part with dense infill (above ~50%) or straight-line infill (grid, triangles): more internal shrink tension.
9. High speed: more stress in the part and more shear from the nozzle.

## Questions worth asking (only when the answer changes the fix)
- Which plate is physically on the printer, which plate type is selected in Orca, glue or not?
- Open-frame or enclosed printer, doors/lid closed, room temperature, draft sources nearby?
- Does it lift in the first few layers (grip) or after several mm (shrink stress, environment)?
- When was the plate last washed with soap? Was it touched?
- Part size, infill density and pattern; one object or several?

## Slicer fixes
Change the plate temperature pair that matches the plate in use: `textured_plate_temp`/`textured_plate_temp_initial_layer` (Textured PEI), `hot_plate_temp`/`hot_plate_temp_initial_layer` (Smooth PEI / High Temp), `cool_plate_temp`/`cool_plate_temp_initial_layer`, `textured_cool_plate_temp`/`textured_cool_plate_temp_initial_layer`, `eng_plate_temp`/`eng_plate_temp_initial_layer`, `supertack_plate_temp`/`supertack_plate_temp_initial_layer`.

| Key (preset) | Direction | Typical step | Safe limit | Side effects |
|---|---|---|---|---|
| `brim_type` (process) | `outer_only` (or `auto_brim`); for corners only `brim_ears` (mouse-ears value of `brim_type`) or `painted` | - | - | brim to trim off the bottom edge |
| `brim_width` (process) | increase | to 5 mm; PLA corners 8-10 mm | ≤ 18 mm | more material; ear radius when **brim_ears** |
| `brim_object_gap` (process) | decrease | to 0-0.05 mm | 0..2 mm | brim harder to remove |
| plate temp pair for the plate in use (filament) | increase | +5 °C (open printer in a cold room: +10 °C) | ≤ +10 °C over current, never above 120 °C | PLA/PETG: elephant foot, heat creep in enclosed printers |
| `close_fan_the_first_x_layers` (filament) | increase | to 3 | 1-5 layers | weaker overhangs/bridges in those layers |
| `additional_cooling_fan_speed` (filament) | decrease | -20-30 points (PLA: 40-50%) | 0-100%; only printers with an auxiliary fan | small details cool less |
| `fan_max_speed` / `fan_min_speed` (filament) | decrease (ABS/ASA/PC/PA) | -10-20 points; ABS about 30-40% max | keep enough cooling for PLA/PETG | overhangs droop |
| `reduce_fan_stop_start_freq` (filament) | `0` for ABS/ASA/PC | - | - | fan stops on long layers |
| `internal_bridge_fan_speed` (filament) | set below the normal fan speed | - | -1 = use overhang fan; needs `enable_overhang_bridge_fan` = `1` | rougher internal bridges |
| `sparse_infill_pattern` (process) | `gyroid` on large flat parts | - | - | slower slicing |
| `sparse_infill_density` (process) | decrease on large parts | to 15-25% | avoid > 50% on large parts | lower strength |
| `draft_shield` (process) | `enabled` (ABS/ASA/PC, open frame) | with `skirt_loops` ≥ 1 | - | more filament and time |
| `raft_layers` (process) | from 0 to 2-4 | +1 | 2-4 usual | rough bottom, time; disables elephant foot compensation |
| `initial_layer_speed` / `initial_layer_infill_speed` (process) | decrease | -20-30% | never above printer limits | longer first layer |
| `slow_down_layers` (process) | increase | to 2-3 | - | slightly longer print |
| `outer_wall_speed`, `inner_wall_speed`, `sparse_infill_speed`, `default_acceleration` (process) | decrease (high-warp material, tall thin parts) | -20-30% | never above printer machine limits | longer print |
| `brim_use_efc_outline` (process) | `1` when `elefant_foot_compensation` > 0 leaves a gap between brim and part | - | - | brim may fuse with upper layers |
| `enable_support` (process) | `1` for tall thin parts knocked over | - | - | support marks |

Notes for the AI:
- Brim first: least risk, fixes most corner lifting. `auto_brim` sizes the brim from height, footprint, speed and material and can produce no brim on small parts; set `outer_only` + `brim_width` when the user needs it to hold.
- **brim_ears**: ears at corners sharper than `brim_ears_max_angle` (default 125); `painted`: the user paints ears in the Prepare tab (Brim ears painting tool); `brim_ears_outer_only` = `1` skips ears inside holes.
- With `elefant_foot_compensation` > 0 the preview shows a gap between brim and part; it is normally filled by squish. If the printed brim does not touch the part, reduce the compensation or enable `brim_use_efc_outline`.
- Do not stack several fan reductions on PLA/PETG at once: overhangs and small parts depend on cooling.

## Checks the user must do by hand (hardware, material, printer settings)
- Wash the plate: warm water + dish soap (no lotion-type soaps), rinse, dry, hold by the edges. Clean plate test (Bambu): water spreads as a film; beads and streams mean residue. Textured PEI: soap and sponge/brush, never acetone. Prusa smooth PEI: IPA 90%+ when cold, acetone only occasionally; never acetone on textured/satin sheets or SuperTack.
- Select the plate type in Orca (Prepare tab plate selector) that matches the plate on the printer. The AI cannot change it; tell the user.
- Glue: thin, even layer. Often needed for ABS/ASA/PA/PC on PEI, always on the Bambu Engineering Plate, on smooth PEI for everything except PLA (also protects the sheet). Bambu Cool Plate (old) needs glue even for PLA.
- Re-run bed levelling (always after moving the printer); first layer must be slightly squished (defect-first-layer).
- Enclosure: close doors and top cover; Bambu suggests 40 °C+ inside for ABS/ASA. The plugin never changes chamber heating: on printers with active chamber heating the user sets it by hand.
- Remove drafts: windows, AC vents, fans. Ventilate the room for ABS/ASA without blowing on the printer.
- Place warp-prone parts near the plate centre; printing several objects together keeps more heat around them (Prusa).
- Open-frame printers (Bambu A1, MK4 without enclosure): large ABS/ASA/PC parts almost always warp; suggest PLA, PETG, PLA-CF or PETG-CF.
- Design: rounded corners warp less than sharp ones; small discs at corners (a few layers tall) act like ears.
- Wet filament (crackling, bubbly surface): dry it.
- Bambu: nozzle clips fastened correctly. Tall parts collapsing: check belt tension.

## Calibration in Orca (menu Calibration → ...)
No calibration measures warping. Fix the first layer first (defect-first-layer). Calibration → Temperature only if the filament runs outside its usual range. See calibration-guide.

## Material notes (PLA / PETG / ABS-ASA / TPU / PA-PC / CF)
- PLA: low shrink. Bambu Textured PEI 55-65 °C; Cool Plate / SuperTack 35-45 °C. Room below 20 °C or open printer: +10 °C bed. Enclosed printers with bed > 45 °C: open door/lid to avoid heat creep.
- PETG: low warping. Bambu PEI plates 60-80 °C; SuperTack gen 2 about 55-60 °C (X/P series profiles may use 65 °C). Bonds too strongly to smooth PEI: use glue as release layer.
- ABS/ASA: high shrink. Bed 90-100 °C (Bambu); Prusa ABS 100 °C (80-110 by part size), ASA 105/110 °C. Enclosure, low or no fan, glue on PEI, draft shield if open frame. ASA warps less than ABS.
- TPU: hardly warps; never on SuperTack.
- PA/PC: highest shrink. Bed 100-120 °C (Bambu), enclosure, glue, dry filament. PC: fewer walls and lower infill on large parts reduce lifting; avoid parts covering the whole plate. PA: Prusa recommends its PA Nylon sheet.
- CF/GF: PA-CF stays high-warp (enclosure, glue); PLA-CF and PETG-CF suit large flat parts. `auto_brim` gives PLA-CF/PET-CF/PA-CF wider brims. Bambu: glue stick for PA-CF/GF, PET-CF, ASA-CF.

## Sources
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/warping-falling-off-collapsing
- https://wiki.bambulab.com/en/knowledge-sharing/printed-model-warping
- https://wiki.bambulab.com/en/software/bambu-studio/use-disc-to-avoid-warping
- https://wiki.bambulab.com/en/software/bambu-studio/brim-ears
- https://wiki.bambulab.com/en/software/bambu-studio/auto-brim
- https://wiki.bambulab.com/en/filament-acc/acc/plates
- https://wiki.bambulab.com/en/filament-acc/acc/pei-plate-clean-guide
- https://wiki.bambulab.com/en/general/how-to-use-bbl-liquid-glue
- https://wiki.bambulab.com/en/general/filament-guide-material-table
- https://wiki.bambulab.com/en/general/engineering-plate-not-working-as-expected
- https://wiki.bambulab.com/en/filament-acc/acc/bambu-cool-plate-supertack
- https://help.prusa3d.com/article/warping_2011
- https://help.prusa3d.com/article/first-layer-issues_1804
- https://help.prusa3d.com/article/print-surface-preparation_686951
- https://help.prusa3d.com/article/skirt-and-brim_133969
- https://help.prusa3d.com/article/abs_2058
- https://help.prusa3d.com/article/asa_1809
- https://help.prusa3d.com/article/polycarbonate-pc_165812
- https://help.prusa3d.com/article/polyamide-nylon_167188
- https://www.simplify3d.com/resources/print-quality-troubleshooting/warping/
- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_brim.html
- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_skirt.html
- https://www.orcaslicer.com/wiki/print_settings/support/support_settings_raft.html
- https://www.orcaslicer.com/wiki/print_prepare/prepare_brim_ears_painting.html
- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html
- https://www.orcaslicer.com/wiki/print_settings/strength/strength_settings_patterns.html
