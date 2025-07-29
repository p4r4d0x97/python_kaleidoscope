import cadquery as cq
import math

# Parameters (edit as needed)
gear_height = 10
num_teeth = 20
tooth_top_length = 2  # approx tip-to-tip length
outer_diameter = 40
inner_diameter = 10
pipe_height = 15
base_height = 5
base_diameter = 50

# Derived values
gear_radius = outer_diameter / 2
tooth_angle = 360 / num_teeth
tooth_depth = 2  # how much the tooth sticks out from gear radius

# Create base gear body
gear_body = (
    cq.Workplane("XY")
    .circle(gear_radius - tooth_depth)
    .extrude(gear_height)
)

# Create one custom tooth shape (rounded triangle-style)
tooth = (
    cq.Workplane("XY")
    .moveTo(0, gear_radius - tooth_depth)
    .lineTo(tooth_top_length / 2, gear_radius + tooth_depth)
    .lineTo(-tooth_top_length / 2, gear_radius + tooth_depth)
    .close()
    .extrude(gear_height)
)

# Pattern the teeth around the gear
teeth = tooth.pattern(circle=gear_radius - tooth_depth, count=num_teeth, angle=360)

# Combine teeth and gear
gear_with_teeth = gear_body.union(teeth)

# Add the pipe on top
pipe = (
    cq.Workplane("XY")
    .circle(inner_diameter / 2)
    .extrude(pipe_height)
)

# Add the base underneath
base = (
    cq.Workplane("XY")
    .circle(base_diameter / 2)
    .extrude(-base_height)
)

# Combine all parts
model = base.union(gear_with_teeth).union(pipe.translate((0, 0, gear_height)))

# Drill hole through everything
hole = (
    cq.Workplane("XY")
    .circle(inner_diameter / 2)
    .extrude(pipe_height + gear_height + base_height)
)

final_model = model.cut(hole)

# Export to STL
cq.exporters.export(final_model, "custom_gear_fixed.stl")
