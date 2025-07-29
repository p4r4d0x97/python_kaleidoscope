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

# Derived
gear_radius = outer_diameter / 2
tooth_depth = 2

# Gear body (cylinder without teeth)
gear_body = (
    cq.Workplane("XY")
    .circle(gear_radius - tooth_depth)
    .extrude(gear_height)
)

# Create teeth directly on the Workplane using polarArray
teeth = (
    cq.Workplane("XY")
    .moveTo(0, gear_radius - tooth_depth)
    .lineTo(tooth_top_length / 2, gear_radius + tooth_depth)
    .lineTo(-tooth_top_length / 2, gear_radius + tooth_depth)
    .close()
    .extrude(gear_height)
    .faces(">Z")
    .workplane(centerOption="CenterOfMass")
    .polarArray(0, 0, 360, num_teeth)
)

# Combine gear and teeth
gear_with_teeth = gear_body.union(teeth)

# Pipe on top
pipe = (
    cq.Workplane("XY")
    .circle(inner_diameter / 2)
    .extrude(pipe_height)
    .translate((0, 0, gear_height))
)

# Base under the gear
base = (
    cq.Workplane("XY")
    .circle(base_diameter / 2)
    .extrude(-base_height)
)

# Combine all parts
full_model = base.union(gear_with_teeth).union(pipe)

# Drill a hole through everything
hole = (
    cq.Workplane("XY")
    .circle(inner_diameter / 2)
    .extrude(pipe_height + gear_height + base_height)
)

final_model = full_model.cut(hole)

# Export as STL
cq.exporters.export(final_model, "custom_gear_correct.stl")

print("✅ Exported: custom_gear_correct.stl")
