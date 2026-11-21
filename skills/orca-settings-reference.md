---
name: orca-settings-reference
description: OrcaSlicer 2.5.1 settings reference - value formats (bool, %, mm-or-%, enums, lists, nil), which preset owns which key, plate temperature keys, filament retraction overrides, and PrusaSlicer / Simplify3D / Cura names translated to Orca keys. Read when the user quotes a setting from another slicer or a video ("extrusion multiplier", "perimeters", "fill density", "retraction distance", "coasting", "combing", "horizontal expansion"), when unsure of a key name, unit or allowed values, or when a change has no effect.
---
# OrcaSlicer settings reference (2.5.1)

## Which preset owns what
- **Process**: layers, walls, shells, infill, speeds, accelerations, jerk, line widths, per-feature flow ratios (`outer_wall_flow_ratio` etc., need `set_other_flow_ratios` = `1`; BY HAND: Process → Quality → Wall and surfaces → Surface flow ratio), seam, ironing, supports, brim/skirt/raft, XY compensation, prime tower.
- **Filament**: nozzle and plate temperatures, fans and layer-time slowdown, `filament_flow_ratio`, pressure advance, `filament_max_volumetric_speed`, retraction / z-hop / wipe overrides, ironing overrides.
- **Printer** (read-only for the plugin): nozzle, default retraction and z-hop, Z offset, layer height and machine limits, firmware.
- Per-object / modifier settings override the process preset: if a change has no effect, ask the user to check them.

## Value formats
- Boolean: `1` / `0`.
- Integer, float: plain number without unit (`0.2`, `45`); the unit is fixed per key.
- Percentage: write the `%` (`15%`).
- Float-or-percent (mm or %): a number is absolute, a `%` is relative to a base that differs per key:
  - line widths (`line_width`, `outer_wall_line_width`, `initial_layer_line_width`...): % of nozzle diameter; 0 = use `line_width`.
  - `small_perimeter_speed`: % of `outer_wall_speed`. `internal_bridge_speed`: % of `bridge_speed`. Overhang speeds `overhang_1_4_speed`...`overhang_4_4_speed`: mm/s or %.
  - `sparse_infill_acceleration`, `internal_solid_infill_acceleration`: % of `default_acceleration`. `bridge_acceleration`: % of `outer_wall_acceleration`. `initial_layer_travel_jerk`: % of `travel_jerk`.
  - `wipe_speed`: % of `travel_speed`. `seam_gap`: % of nozzle diameter. `infill_anchor`: % of infill width. `infill_wall_overlap` (percent only): % of inner wall width, 10-15 % recommended.
- Enum: the internal value below, not the GUI label.
- Lists: filament keys hold one value per filament; on multi-nozzle printers (H2D, H2C, X2D) many keys hold one value per nozzle or nozzle variant. Keep the entry count; change the entry in use.
- `nil` in a filament override = use the printer value.
- Special values: `top_shell_thickness` / `bottom_shell_thickness` 0 = off; `skirt_loops` 0 = no skirt; `adaptive_pressure_advance_bridges` 0 = off; `filament_ramming_volumetric_speed` -1 = use max volumetric speed.

## Enum values (internal)
| Key (preset) | Values |
|---|---|
| `seam_position` (process) | `nearest`, `aligned`, `aligned_back`, `back`, `random` |
| `seam_slope_type` (process) | `none`, `external`, `all` (scarf seam) |
| `wall_sequence` (process) | `inner wall/outer wall`, `outer wall/inner wall`, `inner-outer-inner wall` |
| `wall_generator` (process) | `classic`, `arachne` |
| `top_surface_pattern`, `bottom_surface_pattern`, `internal_solid_infill_pattern` (process) | `monotonic`, `monotonicline`, `rectilinear`, `alignedrectilinear`, `concentric`, `spiralinset`, `hilbertcurve`, `archimedeanchords`, `octagramspiral` |
| `sparse_infill_pattern` (process) | `rectilinear`, `alignedrectilinear`, `zigzag`, `crosszag`, `lockedzag`, `line`, `grid`, `triangles`, `tri-hexagon`, `cubic`, `adaptivecubic`, `quartercubic`, `supportcubic`, `lightning`, `honeycomb`, `3dhoneycomb`, `lateral-honeycomb`, `lateral-lattice`, `crosshatch`, `tpmsd`, `tpmsfk`, `gyroid`, `concentric`, `hilbertcurve`, `archimedeanchords`, `octagramspiral` |
| `support_type` (process) | `normal(auto)`, `tree(auto)`, `normal(manual)`, `tree(manual)` |
| `support_style` (process) | `default`, `grid`, `snug`, `organic`, `tree_slim`, `tree_strong`, `tree_hybrid` |
| `brim_type` (process) | `auto_brim`, brim_ears, `painted`, `outer_only`, `inner_only`, `outer_and_inner`, `no_brim`, `leading_edge_only` |
| `ironing_type` (process) | `no ironing`, `top`, `topmost`, `solid` |
| `gap_fill_target` (process) | `everywhere`, `topbottom`, `nowhere` |
| `ensure_vertical_shell_thickness` (process) | `none`, `ensure_critical_only`, `ensure_moderate`, `ensure_all` |
| `print_sequence` (process) | `by layer`, `by object` |
| `filament_z_hop_types` (filament) | `Auto Lift`, `Normal Lift`, `Slope Lift`, `Spiral Lift` |
| `filament_retract_lift_enforce` (filament) | `All Surfaces`, `Top Only`, `Bottom Only`, `Top and Bottom` |
| `overhang_fan_threshold` (filament) | `0%`, `10%`, `25%`, `50%`, `75%`, `95%` |

## Plate temperature keys (filament)
Change only the pair for the plate in use (max +10 °C per change, never above 120 °C):
| Plate (Orca bed type) | Other layers | First layer |
|---|---|---|
| Smooth Cool Plate | `cool_plate_temp` | `cool_plate_temp_initial_layer` |
| Textured Cool Plate | `textured_cool_plate_temp` | `textured_cool_plate_temp_initial_layer` |
| Smooth High Temp Plate (smooth PEI) | `hot_plate_temp` | `hot_plate_temp_initial_layer` |
| Textured PEI Plate | `textured_plate_temp` | `textured_plate_temp_initial_layer` |
| Engineering Plate | `eng_plate_temp` | `eng_plate_temp_initial_layer` |
| Cool Plate (SuperTack) | `supertack_plate_temp` | `supertack_plate_temp_initial_layer` |
- Bambu printers and printers with "Support multi bed types" let the user pick the plate; others (most Prusa profiles) use the profile default (Textured PEI on Prusa MMU3/INDX). If unsure, ask which plate is selected.

## Filament overrides of printer settings
`filament_retraction_length`, `filament_retraction_speed`, `filament_deretraction_speed`, `filament_retraction_minimum_travel`, `filament_retract_when_changing_layer`, `filament_retract_before_wipe`, `filament_retract_after_wipe`, `filament_retract_restart_extra` (BY HAND), `filament_wipe`, `filament_wipe_distance`, `filament_z_hop`, `filament_z_hop_types`, `filament_retract_lift_above`, `filament_retract_lift_below`, `filament_retract_lift_enforce`, `filament_long_retractions_when_cut`, `filament_retraction_distances_when_cut`, `filament_retract_length_toolchange`.
Ironing overrides: `filament_ironing_flow`, `filament_ironing_spacing`, `filament_ironing_speed`, `filament_ironing_inset`.
Plugin limits: length 0..min(8, max(2, 2 × printer value)) mm; (de)retraction speed ≤ max(1.5 × printer value, 30 mm/s); z-hop 0-2 mm.

## Names from other slicers → Orca key
Cura names: for recognition only.
| PrusaSlicer | Simplify3D | Cura | Orca key (preset) |
|---|---|---|---|
| Extrusion multiplier | Extrusion Multiplier | Flow | `filament_flow_ratio` (filament) |
| Perimeters | - | Wall Line Count | `wall_loops` (process) |
| Solid layers top / bottom | Top / Bottom Solid Layers | Top / Bottom Layers | `top_shell_layers` / `bottom_shell_layers` (process) |
| Fill density / Fill pattern | Infill Percentage | Infill Density / Pattern | `sparse_infill_density` / `sparse_infill_pattern` (process) |
| First layer height | - | Initial Layer Height | `initial_layer_print_height` (process) |
| Extrusion width | Extrusion Width | Line Width | `line_width` and per-feature widths (process) |
| Infill/perimeters overlap | Outline Overlap | Infill Overlap | `infill_wall_overlap` (process) |
| Retraction length | Retraction Distance | Retraction Distance | `filament_retraction_length` (filament) |
| Retraction speed | Retraction Speed | Retraction Speed | `filament_retraction_speed` (filament) |
| Lift Z | Retraction Vertical Lift | Z Hop When Retracted | `filament_z_hop` (filament) |
| Extra length on restart | Extra restart distance | Retraction Extra Prime Amount | `filament_retract_restart_extra` (filament) — BY HAND: Filament → Setting overrides → Retraction |
| Minimum travel after retraction | Minimum travel for retraction | Retraction Minimum Travel | `filament_retraction_minimum_travel` (filament) |
| Wipe while retracting | Wipe Nozzle | - | `filament_wipe`, `filament_wipe_distance` (filament) |
| Only retract when crossing perimeters | Only retract when crossing open spaces | Combing (partly) | `reduce_infill_retraction` (process) |
| Avoid crossing perimeters | Avoid crossing outline for travel movement | Combing Mode | `reduce_crossing_wall` (process) |
| - | Coasting | Coasting | none; use PA and retraction |
| Temperature / First layer | - | Printing Temperature / Initial Layer | `nozzle_temperature` / `nozzle_temperature_initial_layer` (filament) |
| XY Size Compensation | Horizontal size compensation | Horizontal Expansion | `xy_contour_compensation` (process) |
| - | - | Hole Horizontal Expansion | `xy_hole_compensation` (process) |
| Elephant foot compensation | - | Initial Layer Horizontal Expansion (negative) | `elefant_foot_compensation` (process, positive mm) |
| Seam position (rear = `back`) | - | Z Seam Alignment | `seam_position` (process) |
| External perimeters first | - | Wall Ordering | `wall_sequence` (process) |
| Bridge flow ratio | Bridging extrusion multiplier | Bridge Skin Flow | `bridge_flow` (process) — BY HAND: Process → Quality → Bridging → Flow ratio |
| Slow down if layer print time is below | - | Minimum Layer Time | `slow_down_layer_time` (filament) |
| Disable fan for the first N layers | - | Initial Fan Speed | `close_fan_the_first_x_layers` (filament) |
| Contact Z distance | Upper Vertical Separation | Support Top Distance | `support_top_z_distance` (process) |
| Interface layers | Dense Support | Support Interface | `support_interface_top_layers` (process) |
| Skirt loops / distance / height | - | Skirt Line Count / Distance | `skirt_loops` / `skirt_distance` / `skirt_height` (process) |
Speeds (process): perimeters `inner_wall_speed`, external perimeters `outer_wall_speed`, infill `sparse_infill_speed`, solid infill `internal_solid_infill_speed`, top solid `top_surface_speed`, gap fill `gap_infill_speed`, first layer `initial_layer_speed`, travel / S3D X/Y Axis Movement Speed `travel_speed`.

## Checks the user must do by hand (printer settings, never changed by the plugin)
Printer settings tab: `retraction_length`, `retraction_speed`, `z_hop` (override them in the filament instead), `z_offset`, `nozzle_diameter`, `nozzle_type`, layer height limits, machine limits (`machine_max_speed_x`, `machine_max_acceleration_extruding`, `machine_max_jerk_x` ...), input shaping, `resonance_avoidance`, firmware flavour, `extruder_type`. Process speeds/accel/jerk ≤ machine limits.

## Sources
- https://www.orcaslicer.com/wiki/general_settings/option_type.html
- https://www.orcaslicer.com/wiki/material_settings/setting%20overrides/material_setting_overrides.html
- https://www.orcaslicer.com/wiki/material_settings/filament/material_temperatures.html
- https://www.orcaslicer.com/wiki/printer_settings/basic%20information/printer_basic_information_printable_space.html
- https://help.prusa3d.com/article/layers-and-perimeters_1748
- https://help.prusa3d.com/article/stringing-and-oozing_1805
- https://help.prusa3d.com/article/infill_42
- https://help.prusa3d.com/article/cooling_127569
- https://help.prusa3d.com/article/poor-bridging_1802
- https://www.simplify3d.com/resources/print-quality-troubleshooting/stringing-or-oozing/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/blobs-and-zits/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/dimensional-accuracy/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/poor-surface-above-supports/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/gaps-between-infill-and-outline/
- https://www.simplify3d.com/resources/print-quality-troubleshooting/gaps-in-top-layers/
