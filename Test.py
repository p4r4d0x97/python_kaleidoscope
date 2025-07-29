import cadquery as cq

# Parameters
gear_height = 10
num_teeth = 20
tooth_top_length = 2
outer_diameter = 40
inner_diameter = 10
pipe_height = 15
base_height = 5
base_diameter = 50
tooth_depth = 2
pipe_outer_diameter = 15  # Added: outer diameter for the hollow pipe

# Derived
gear_radius = outer_diameter / 2
tooth_base_length = tooth_top_length * 1.5  # Wider base for trapezoidal teeth

# Validate parameters
if inner_diameter >= outer_diameter or outer_diameter >= base_diameter or inner_diameter >= pipe_outer_diameter:
    raise ValueError("Invalid dimensions: ensure inner_diameter < pipe_outer_diameter < outer_diameter < base_diameter")

# Gear body (cylinder without teeth)
gear_body = (
    cq.Workplane("XY")
    .circle(gear_radius - tooth_depth)
    .extrude(gear_height)
)

# Create a single trapezoidal tooth
tooth = (
    cq.Workplane("XY")
    .moveTo(-tooth_base_length / 2, gear_radius - tooth_depth)
    .lineTo(tooth_base_length / 2, gear_radius - tooth_depth)
    .lineTo(tooth_top_length / 2, gear_radius + tooth_depth)
    .lineTo(-tooth_top_length / 2, gear_radius + tooth_depth)
    .close()
    .extrude(gear_height)
)

# Distribute teeth around the gear using polarArray
teeth = (
    cq.Workplane("XY")
    .union(tooth)
    .polarArray(radius=0, startAngle=0, angle=360, count=num_teeth)
)

# Combine gear body and teeth
gear_with_teeth = gear_body.union(teeth)

# Base under the gear
base = (
    cq.Workplane("XY")
    .circle(base_diameter / 2)
    .extrude(base_height)  # Positive extrusion (base is at z=0 to z=base_height)
)

# Hollow pipe on top of gear
pipe = (
    cq.Workplane("XY")
    .circle(pipe_outer_diameter / 2)
    .circle(inner_diameter / 2)
    .extrude(pipe_height)
    .translate((0, 0, gear_height))  # Place pipe on top of gear
)

# Combine all parts
full_model = base.union(gear_with_teeth).union(pipe)

# Drill a hole through everything
total_height = base_height + gear_height + pipe_height
hole = (
    cq.Workplane("XY")
    .circle(inner_diameter / 2)
    .extrude(total_height, both=True)  # Extrude in both directions to ensure full cut
    .translate((0, 0, -base_height))  # Shift to start at bottom of base
)

# Cut the hole from the full model
final_model = full_model.cut(hole)

# Export as STL
cq.exporters.export(final_model, "custom_gear_correct.stl")

print("✅ Exported: custom_gear_correct.stl")
