---
name: defect-triage
description: Start here for any print problem: maps what the user sees (strings, lifting corners, gaps, lines on walls, blobs, cracks, shifted layers, clogs, failed supports, wrong size) to the right defect skill and gives the diagnostic order and plugin limits. Read when the user describes a bad print but the defect is unclear, or several defects at once.
---
# Print defect triage

## Method (follow in this order)
1. **Pin down the symptom.** Ask for a photo if none was given. Locate the defect: first layer, walls, top surface, under overhangs, around supports, at layer changes, only on one object, only in one part of the plate.
2. **Ask what changed.** New spool or brand, filament left out for days, new or edited profile, new plate, different printer mode (silent/sport), hardware work. A defect that appeared suddenly on a profile that used to work points to hardware or material, not to the profile.
3. **Read the current settings** (process + filament) before proposing anything, and identify printer, nozzle diameter, plate type and material.
4. **Rule out hardware and material first** when the symptom points there (see "Hardware first" below). Explain these checks to the user; never try to compensate a mechanical fault with parameters.
5. **Calibrate before tuning.** If flow, pressure advance, temperature or max volumetric speed were never calibrated for this filament, recommend the matching calibration (see calibration-guide) instead of guessing values.
6. **Change few settings, in small steps**, most effective and least risky first. Say what each change costs (time, strength, surface). One defect per round; ask the user to reprint (ideally a small test) before the next round.

## Symptom → skill
| What the user sees or says | Skill |
|---|---|
| strings, hairs, cobwebs, wisps between parts; oozing during travel | defect-stringing |
| visible seam line, zits, pimples, blobs on walls, bumps where layers start | defect-seam-zits-blobs |
| nozzle not extruding, extrusion stops mid print, clicking extruder, ground filament, filament balled on the nozzle, heat creep | defect-clogs-heat-creep |
| corners lifting, part detaching, curling at the base, print knocked off | defect-warping |
| first layer not sticking, too squished, ridges or gaps in the first layer, elephant foot, part impossible to remove | defect-first-layer |
| layers splitting, cracks in tall parts, delamination, part breaks along layer lines | defect-layer-adhesion |
| gaps between lines or walls, thin weak walls, holes in walls, too much material, rough overfilled surfaces, uneven gloss | defect-extrusion |
| pillowing, holes or gaps on the top, scratches or lines on top surfaces, ironing problems | defect-top-surface |
| small parts or tips melted/deformed, thin walls or tiny features missing, gaps inside thin walls | defect-overheating-small-features |
| ghosting, ringing, echoes after corners, ripples, vertical bands/fine vertical artefacts (VFA), wobble, salmon skin | defect-ringing-ghosting |
| whole layers offset sideways, staircase shift | defect-layer-shift |
| spaghetti, print collapsed or turned into a tangle mid print | find what failed first: part came loose (defect-warping, defect-first-layer), support fell (defect-supports), extrusion stopped (defect-clogs-heat-creep) |
| part too big/small, holes too tight, pegs do not fit, shrinkage, warped dimensions | defect-dimensional-accuracy |
| drooping or curling overhangs, sagging or broken bridges | defect-overhangs-bridges |
| supports hard to remove, falling over, failing mid print, ugly surface above supports, too many or missing supports | defect-supports |
| AMS/MMU/multi-tool: colour bleeding, too much purge waste, prime tower problems, ooze from the idle nozzle | defect-multimaterial |
| which temperature/plate/fan for a material, drying, material choice | materials-overview, then material-pla, material-petg, material-abs-asa, material-tpu, material-pa-pc, material-composites, material-special |
| no defect, a goal: print faster / less filament; stronger or watertight part; smoother surface, finer detail, vase mode, fuzzy skin | goal-faster-prints, goal-stronger-parts, goal-surface-quality |
| which calibration to run and in which order | calibration-guide |
| exact key name, value format, enum values, PrusaSlicer/Cura name translation | orca-settings-reference |
| printer-specific behaviour (enclosure, AMS, Nextruder, limits) | printers-bambu, printers-prusa |

Combined symptoms: strings + blobs usually share a cause (too hot, wet filament, weak retraction): start with defect-stringing. Gaps on top + weak walls + rough sound from the extruder: start with defect-clogs-heat-creep, then defect-extrusion. Droopy overhangs + melted small tips: cooling problem, defect-overheating-small-features and defect-overhangs-bridges.

## Hardware first (explain, do not fix with settings)
- **Wet filament**: popping/hissing, steam, bubbles, rough surface, many strings, brittle filament (PETG, TPU, PA, PC, PVA most sensitive). → dry it (see materials-overview).
- **Plate**: fingerprints/grease, wrong side or wrong plate type selected, worn PEI, missing glue where required.
- **Z offset / levelling**: first layer uniformly too high or too squished, or only on one side.
- **Partial clog, worn nozzle, dirty extruder gears**: under-extrusion that appeared suddenly, clicking, inconsistent lines; abrasive (CF/GF) filament on a brass nozzle.
- **Part cooling fan not spinning or blocked**: sudden droopy overhangs and melted details.
- **Belts, pulleys, loose parts, collisions**: layer shifts, ringing that got worse over time.
- **Environment**: drafts, cold room, open door on an enclosed printer for ABS/ASA (or closed door for PLA on enclosed printers, which can soften PLA in the extruder).

## What the plugin may change (keep proposals inside this)
- Only **process** and **filament** preset keys. Printer settings (printer retraction, Z offset, machine limits, nozzle diameter) are explained to the user, never changed.
- Never: custom G-code or post-processing scripts, material data (diameter, density, type, shrinkage), filament temperature ranges, chamber heating.
- Limits: nozzle temperature inside the filament range; plate temperature at most +10 °C over the current value (max 120 °C); `filament_flow_ratio` 0.8-1.2; `filament_max_volumetric_speed` at most +10%; `layer_height` and `initial_layer_print_height` ≤ 75% of the nozzle; `filament_retraction_length` 0 .. min(8 mm, max(2 mm, 2× printer retraction)); `filament_retraction_speed` and `filament_deretraction_speed` > 0 and ≤ max(1.5× printer value, 30 mm/s); `filament_z_hop` 0-2 mm; speeds, accelerations and jerk within the machine limits.
- If the right fix is outside these limits, say so and tell the user what to do by hand.

## Settings the plugin cannot check: the user changes them by hand
Never put these in a proposal: the plugin cannot verify a safe value for them. Explain the change and guide the user step by step, using the menu path and the Orca wiki page:
- Per-feature flow ratios (`first_layer_flow_ratio`, `outer_wall_flow_ratio`, `inner_wall_flow_ratio`, `top_solid_infill_flow_ratio`, `bottom_solid_infill_flow_ratio`, `sparse_infill_flow_ratio`, `internal_solid_infill_flow_ratio`, `overhang_flow_ratio`, `gap_fill_flow_ratio`, `support_flow_ratio`, `support_interface_flow_ratio`, switch `set_other_flow_ratios`): Process → Quality → Wall and surfaces → Surface flow ratio (per-feature ratios appear after enabling "Set other flow ratios"); https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html. Keep them 0.8-1.2; they multiply the filament flow ratio.
- Also by hand only, flow ratios in other sections: `brim_flow_ratio` (Process → Others → Brim), `scarf_joint_flow_ratio` (Process → Quality → Seam → Scarf joint seam), `spiral_starting_flow_ratio` and `spiral_finishing_flow_ratio` (Process → Others → Special mode → Spiral vase).
- Bridge flow (`bridge_flow`, `internal_bridge_flow`): Process → Quality → Bridging → Flow ratio; https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_bridging.html.
- Extra length on restart (`filament_retract_restart_extra`, `filament_retract_restart_extra_toolchange`): Filament → Setting overrides → Retraction → Extra length on restart; https://www.orcaslicer.com/wiki/material_settings/setting%20overrides/material_setting_overrides.html. Only tiny values (±0.1 mm).
- Air filtration and exhaust fan (`activate_air_filtration`, `activate_air_filtration_during_print`, `activate_air_filtration_on_completion`, `during_print_exhaust_fan_speed`, `complete_print_exhaust_fan_speed`): Filament → Cooling → Exhaust fan; https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html.
- Temperature keys other than nozzle and plate temperatures (the plugin blocks them), e.g. idle/standby nozzle temperature for multi-tool ooze prevention: Filament → Multimaterial and Process → Multimaterial → Ooze prevention.
- Values outside the plugin limits (e.g. flow ratio below 0.8 for foaming PLA/ASA, a bigger jump in max volumetric speed after a calibration): same approach, give the field name as shown in Orca and its tab.
- Printer settings (printer retraction, Z offset, machine limits, nozzle): Printer settings tab, see https://www.orcaslicer.com/wiki/printer_settings/extruder/printer_extruder_retraction.html and the other pages under https://www.orcaslicer.com/wiki/printer_settings/.
In each fixes table these rows are marked "BY HAND".

## Sources
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality
- https://wiki.bambulab.com/en/knowledge-sharing/troubleshooting-printing-issues
- https://wiki.bambulab.com/en/knowledge-sharing/common-print-quality-problem
- https://www.prusa3d.com/print-quality-troubleshooting
- https://www.simplify3d.com/resources/print-quality-troubleshooting/
- https://www.obico.io/blog/3d-print-troubleshooting-guide/
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_bridging.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_seam.html
- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_brim.html
- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_special_mode.html
- https://www.orcaslicer.com/wiki/material_settings/setting%20overrides/material_setting_overrides.html
- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html
- https://www.orcaslicer.com/wiki/printer_settings/extruder/printer_extruder_retraction.html
