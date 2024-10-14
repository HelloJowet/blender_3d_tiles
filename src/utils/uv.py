import bpy


def pack_islands(scale: bool, margin: int, calculate_average_islands_scale: bool = False):
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    if calculate_average_islands_scale:
        bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(scale=scale, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')
