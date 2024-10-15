import bpy


class Session:
    """
    Manages a Blender session.
    """

    def __init__(self) -> None:
        # Set the render engine to Cycles, which is required for texture baking
        bpy.context.scene.render.engine = 'CYCLES'
        # Use GPU for rendering, if available
        bpy.context.scene.cycles.device = 'GPU'

        # Set default bake settings to use only color information for baking
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False
        bpy.context.scene.render.bake.use_pass_color = True

        # Necessary for certain UV operations like pack_islands
        bpy.context.scene.tool_settings.use_uv_select_sync = True

    def clean(self):
        """
        Cleans up the current session by removing all meshes, materials, and images from the Blender data.
        """

        for mesh in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)

        for material in bpy.data.materials:
            bpy.data.materials.remove(material)

        for image in bpy.data.images:
            bpy.data.images.remove(image)
