import bpy


def pack_islands(
    scale: bool,  # whether to scale islands to fit within the UV space
    margin: int,  # margin in pixels between UV islands.
    calculate_average_islands_scale: bool = False,  # if True, scales islands to a consistent average size.
):
    """
    Organizes UV islands to prevent overlap, with options to resize and set spacing.
    """

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    if calculate_average_islands_scale:
        bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(scale=scale, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')
