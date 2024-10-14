import bpy


class Session:
    def __init__(self) -> None:
        # required for baking textures
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.device = 'GPU'

        # default bake settings
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False
        bpy.context.scene.render.bake.use_pass_color = True

        # required by uv operations like pack_islands
        bpy.context.scene.tool_settings.use_uv_select_sync = True

    def clean(self):
        for mesh in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)

        for material in bpy.data.materials:
            bpy.data.materials.remove(material)

        for image in bpy.data.images:
            bpy.data.images.remove(image)
