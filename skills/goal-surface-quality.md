---
name: goal-surface-quality
description: Goal skill for the best-looking surfaces and finest detail - finer layer height, variable layer height, outer wall speed and acceleration, wall order, wall generator (Arachne vs classic), line widths and small details, even gloss, top surfaces and ironing, seam, spiral vase mode and its limits, fuzzy skin. Read when the user asks "smoother", "better quality", "finer detail", "hide layer lines", "nicer surface", "shiny or matte bands", "small text", "vase mode", "fuzzy skin", "miniatures".
---
# Best surface quality and fine detail

The user wants a better look and pays with time. Ask which surface matters; a real defect goes to its own skill (ringing, seam, zits, pillowing, supports, overhangs).

## What to ask first
- Which surface: vertical walls, curved or sloped tops (stair-steps), flat top, underside or supported areas, small text and details?
- What bothers them: layer lines, the seam, shiny/dull bands, roughness, missing or rounded details?
- Material (silk, glossy and translucent filaments show every speed change), printer, nozzle diameter.
- How much extra time is acceptable: halving the layer height roughly doubles the time.
- Vase mode: is the model one closed outline per layer (vase, pot, lampshade), or does it have handles, islands, inner structures?
- Was the filament dried and calibrated (flow, pressure advance)?

## Levers, biggest gain first
| Key (preset) | Change | Typical step | Safe limit | What it costs |
|---|---|---|---|---|
| `layer_height` (process) | decrease | 0.2 → 0.16 → 0.12 on a 0.4 mm nozzle | ≥ 20% of nozzle (0.08 on 0.4 mm), plugin min 0.04; little visible gain below 0.10 | time grows almost in proportion; no gain in XY detail; very thin layers printed fast look scaly |
| `outer_wall_speed` (process) | decrease, keep it uniform | -20-30%; silk or glossy filaments 40-60 mm/s | - | time |
| `dont_slow_down_outer_wall` (filament) | `1` | - | not on tiny or pointed parts that overheat | even gloss, but short layers cool less and inner features slow down more |
| `outer_wall_acceleration` (process) | decrease | -25-40% | ≤ printer limit; ignored when `default_acceleration` is 0 | time; details in defect-ringing-ghosting |
| `wall_sequence` (process) | `inner-outer-inner wall` | needs `wall_loops` ≥ 3 | models without steep overhangs | best outer surface and accuracy; worse overhangs |
| `precise_outer_wall` (process) | `1` when the order stays `inner wall/outer wall` | - | ignored with the other orders | none known; more even layers |
| `infill_wall_overlap` (process) | decrease (infill pattern visible outside) | 15% → 10% | ≥ 0% | weaker infill-to-wall bond |
| `top_surface_pattern` (process) | `monotonicline` or `monotonic`; round or silk tops: `concentric`, `archimedeanchords` | - | - | spiral patterns are slower |
| `top_surface_speed` (process) | decrease | -20-30% | - | time |
| `only_one_wall_top` (process) | `1` | - | - | cleaner flat tops and small lettering |
| `ironing_type` (process) | `top` or `topmost`, flat tops only | defaults first | see defect-top-surface | much more time; heat-creep risk; edges a little less sharp |
| `seam_position` (process) | `aligned` or `back` | - | see defect-seam-zits-blobs | seam concentrated on one line |
| `reduce_crossing_wall` (process) | `1` | - | - | fewer travel marks and strings on walls; slightly longer print |
| `outer_wall_line_width` (process) | 105-120% of nozzle normally; narrower for tiny text | e.g. 0.45 → 0.40 on a 0.4 mm nozzle | 75-150% of nozzle; below 100% bonding suffers | thinner, weaker walls |
| `min_feature_size` (process) | decrease (Arachne, thin details missing in the preview) | 25% → 15-10% | ≥ 0% | tiny moves, blobs or strings on tiny features |
| `wall_generator` (process) | `arachne` for thin walls, text, logos; `classic` if Arachne gives uneven walls or odd seams | - | - | `classic` drops features thinner than two lines |
| `nozzle_temperature` (filament) | increase for more gloss, silk filaments | +5 °C | inside the filament's temperature range | stringing, softer overhangs |
| `fuzzy_skin` (process) | `external` (contour), `all` (contour and holes), `allwalls` | `fuzzy_skin_thickness` (process) 0.1-0.3, `fuzzy_skin_point_distance` (process) 0.3-0.8 | thickness below the outer wall line width; keep `fuzzy_skin_first_layer` (process) `0` | rough matte texture on walls only; slower; sizes and fits change |
| `spiral_mode` (process) | `1` for vases | see the vase section | one closed outline per layer | single wall, no infill, no top |

Notes for the AI:
- **Layer height sets vertical resolution only**: XY detail comes from line width and nozzle. Thinner layers also improve overhangs. With thin layers leave `top_shell_thickness` (process) on: it keeps the top solid.
- **Gloss follows speed and flow**: slow, hot plastic is glossy, fast plastic matte. Bands appear where the outer wall slows down (overhangs, minimum layer time). Remedies: `outer_wall_speed` close to the slowest wall speed shown in the Preview "Speed" view, `dont_slow_down_outer_wall`, a 0.16 mm layer, several parts on the plate (by hand).
- **Wall order.** `inner-outer-inner wall` prints the outer wall undisturbed. `outer wall/inner wall` gives similar walls but less consistent seams. `inner wall/outer wall` stays best for overhangs. Keep `is_infill_first` (process) `0`.
- **Arachne.** `wall_distribution_count` (process) 1 keeps width changes in the innermost wall, so outer walls stay even.
- **Bulge or line where speed changes** (start of an overhang or bridge): `max_volumetric_extrusion_rate_slope` (process), values in defect-ringing-ghosting.
- **Top surfaces**: `top_surface_line_width` (process) 100-105% of nozzle; ironing only helps flat tops parallel to the bed (defect-top-surface).
- **Fuzzy skin** hides layer lines, ringing and seams and adds grip; it acts on walls only, never on top and bottom faces. `fuzzy_skin_mode` (process): `displacement` is the classic look but weakens the shell and slows the print; `extrusion` (needs `arachne`) keeps speed and strength with a milder texture; `combined` sits between. `fuzzy_skin` `none` = only areas painted by the user; `disabled_fuzzy` = off. Keep it off mating faces and holes that must fit.

### Spiral vase
- Propose `spiral_mode` `1` together with `wall_loops` 1, `top_shell_layers` 0, `sparse_infill_density` `0%`, `enable_support` `0` (all process). When the user ticks Spiral vase by hand (Process → Others → Special mode), Orca offers to apply these itself: usually the simpler route.
- Result: one continuous wall rising in a spiral, no seam above the bottom layers; `bottom_shell_layers` (process) still applies.
- `spiral_mode_smooth` (process) `1` also smooths XY moves: no seam on slanted walls, but it can leave bumps on vases with sharp edges; best on smooth shapes. `spiral_mode_max_xy_smoothing` (process) default `200%` of nozzle.
- Stronger or tighter vase: `outer_wall_line_width` up to 0.6 mm on a 0.4 mm nozzle (≤ 150% of nozzle); for leaks see goal-stronger-parts.
- Limits: the model must be a solid with one closed outline per layer; handles, islands and inner walls come out floating or missing. One object per plate, or `print_sequence` (process) `by object`. Timelapse must be traditional; Bambu A1 / A1 mini make no timelapse in vase mode. A single wall is fragile.

## Limits you cannot tune past (explain to the user)
- **Layer lines never disappear**, and shallow slopes always show stair-steps: orientation and variable layer height reduce them more than any global setting.
- **XY detail is bounded by the nozzle**: features thinner than about one line are thinned, widened or skipped. Finer needs a smaller nozzle.
- **Every layer has a start and an end** except in vase mode: the seam can be hidden, not removed.
- **Ringing and fine vertical ripples are mechanical**: lower acceleration hides them, printer calibration fixes them (defect-ringing-ghosting).
- **Supported and steeply overhanging faces stay rougher** than the rest (defect-supports, defect-overhangs-bridges).
- **Material**: wet filament prints rough with uneven gloss whatever the profile.

## Checks and choices the user makes by hand
- **Orientation**: put the display face upright rather than as a shallow curved top; a face printed on the plate copies the plate's finish (smooth or textured).
- **Variable layer height** (Prepare toolbar, object selected): Adaptive with the slider toward Quality, then Smooth (repeat if needed). Thin layers go only on curved tops and shallow slopes. Abrupt layer-height changes show as horizontal lines: always smooth. The range is the min/max layer height of the printer's extruder settings. Restrictions (Bambu documentation): a prime tower needs the same profile on all objects; not with organic tree supports. The plugin cannot apply this tool.
- **Painted fuzzy skin and seam**: paint tools in the Prepare toolbar (painted fuzzy skin needs `fuzzy_skin` `none`, not `disabled_fuzzy`).
- **Spiral start/end flow** (`spiral_starting_flow_ratio`, `spiral_finishing_flow_ratio`, process): BY HAND only, Process → Others → Special mode → Spiral vase; the plugin cannot check them.
- **Smaller nozzle** (hardware plus the matching printer preset): 0.2 mm for miniatures and tiny text; very low flow limit (about 2 mm³/s on Bambu), no filled, glow or sparkle filaments, weaker parts.
- **More parts on the plate** lengthen each layer: fewer cooling slowdowns on small parts.
- **Dry the filament; run Flow ratio and Pressure advance calibrations** (calibration-guide) before judging the surface.

## Related skills
- defect-seam-zits-blobs, defect-top-surface, defect-ringing-ghosting, defect-overhangs-bridges, defect-supports, defect-overheating-small-features, defect-extrusion (uneven gloss).
- material-pla (silk, matte), calibration-guide, goal-faster-prints, goal-stronger-parts.

## Sources
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_layer_height.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_line_width.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_and_surfaces.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_wall_generator.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_precision.html
- https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_ironing.html
- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_special_mode.html
- https://www.orcaslicer.com/wiki/print_settings/others/others_settings_fuzzy_skin.html
- https://www.orcaslicer.com/wiki/print_prepare/prepare_variable_layer_height.html
- https://www.orcaslicer.com/wiki/material_settings/cooling/material_cooling.html
- https://wiki.bambulab.com/en/software/bambu-studio/layer-height
- https://wiki.bambulab.com/en/software/bambu-studio/adaptive-layer-height
- https://wiki.bambulab.com/en/software/bambu-studio/spiral-vase
- https://wiki.bambulab.com/en/software/bambu-studio/parameter/fuzzy-skin
- https://wiki.bambulab.com/en/software/bambu-studio/parameter/quality-advance-settings
- https://wiki.bambulab.com/en/software/bambu-studio/wall-generator
- https://wiki.bambulab.com/en/software/bambu-studio/WallGenerator
- https://wiki.bambulab.com/en/software/bambu-studio/parameter/line-width
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/different-gloss
- https://wiki.bambulab.com/en/filament-acc/filament/print-quality/severe-layer-artifacts
- https://wiki.bambulab.com/en/x1/manual/printing-with-silk-filaments
- https://wiki.bambulab.com/en/knowledge-sharing/02-mm-nozzle-FAQ
- https://help.prusa3d.com/article/layers-and-perimeters_1748
- https://help.prusa3d.com/article/arachne-perimeter-generator_352769
- https://help.prusa3d.com/article/fuzzy-skin_246186
- https://help.prusa3d.com/article/ironing_177488
