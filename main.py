import math

import bmesh
import bpy
from bmesh.types import BMFace
from bpy.types import DecimateModifier, Image, Object, ShaderNodeBsdfPrincipled, ShaderNodeTexImage


class BlenderSession:
    def clean():
        for mesh in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)

        for material in bpy.data.materials:
            bpy.data.materials.remove(material)

        for image in bpy.data.images:
            bpy.data.images.remove(image)


class BlenderUtils:
    def duplicate_object(object: Object, new_object_name: str) -> Object:
        new_object = object.copy()
        new_object.data = object.data.copy()
        new_object.name = new_object_name
        bpy.context.collection.objects.link(new_object)
        return new_object


class Chunk:
    grid_x: int
    grid_y: int
    tiles: list['Tile']

    def __init__(self, grid_x: int, grid_y: int):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.tiles = []

    def load_3d_object(self, file_path: str):
        bpy.ops.wm.obj_import(filepath=file_path, up_axis='Z')

        selected_object = bpy.context.active_object
        selected_object.scale = (0.1, 0.1, 0.1)
        selected_object.name = f'tile_{self.grid_x}_{self.grid_y}__1'

        self._clean()
        if len(selected_object.data.materials) > 1:
            self._combine_materials(selected_object)

    def _clean(self):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')

        bpy.ops.mesh.dissolve_degenerate()
        bpy.ops.mesh.remove_doubles()

        bpy.ops.object.mode_set(mode='OBJECT')

    def _combine_materials(self, selected_object: Object):
        # Create a new UV layer for the object
        new_uv_layer = selected_object.data.uv_layers.new(name='uv_layer_01', do_init=True)
        selected_object.data.uv_layers.active = new_uv_layer

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        # Use smart UV projection to create UV islands
        bpy.ops.uv.smart_project()
        bpy.ops.object.mode_set(mode='OBJECT')

        # Calculate total pixel count of all images
        new_image_texture_pixel_count = 0
        for material in selected_object.data.materials:
            if material.use_nodes:
                for node in material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        image: Image = node.image
                        if image:
                            new_image_texture_pixel_count += image.size[0] * image.size[1]
        # Calculate the resolution for the new image texture
        new_image_texture_resolution = int(math.sqrt(new_image_texture_pixel_count))

        # Set the rendering engine to Cycles (required for baking)
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.device = 'GPU'

        # Prepare the Principled Baker for baking operations
        bpy.ops.principled_baker_bakelist.detect()  # Detect baking options
        # Get the index of the 'Color' bake option
        bake_index = next((index for index, bake_option in enumerate(bpy.context.scene.principled_baker_bakelist) if bake_option.name == 'Color'), None)
        if bake_index is None:
            raise ValueError('Color bake option not found in the Principled Baker')

        bpy.context.scene.principled_baker_bakelist_index = bake_index
        bake_settings = bpy.context.scene.principled_baker_settings
        bake_settings.bake_mode = 'BATCH'
        bake_settings.resolution = 'CUSTOM'
        bake_settings.file_format = 'JPEG'
        bake_settings.color_mode = 'RGB'
        bake_settings.use_overwrite = True
        bake_settings.custom_resolution = new_image_texture_resolution

        bpy.ops.object.principled_baker_bake()

        # Delete old UV maps, keeping only the newly created one
        uv_layers = selected_object.data.uv_layers
        for uv_layer in uv_layers:
            if uv_layer.name != 'uv_layer_01':
                uv_layers.remove(uv_layer)

        # Clear all materials from the object
        selected_object.data.materials.clear()

        # Create and assign a new material with the baked texture
        new_material = bpy.data.materials.new(name='material_01')
        new_material.use_nodes = True

        # Create a new image texture node and assign the baked image
        image_texture_node: ShaderNodeTexImage = new_material.node_tree.nodes.new(type='ShaderNodeTexImage')
        image_texture_node.image = bpy.data.images.get(f'{selected_object.name}_color.jpg')
        # Get the Principled BSDF node and link the texture to it
        principled_bsdf_node: ShaderNodeBsdfPrincipled = new_material.node_tree.nodes.get('Principled BSDF')
        new_material.node_tree.links.new(image_texture_node.outputs['Color'], principled_bsdf_node.inputs['Base Color'])
        # Append the new material to the object's material slots
        selected_object.data.materials.append(new_material)

    def create_tiles(self, depth: int):
        root_tile_object = bpy.data.objects.get(f'tile_{self.grid_x}_{self.grid_y}__1')
        if not root_tile_object:
            raise Exception('Root tile could not be found')

        root_tile = Tile(object=root_tile_object)
        self.tiles = self._create_tile_children(tile=root_tile, current_depth=1, max_depth=depth)

    def _create_tile_children(self, tile: 'Tile', current_depth: int, max_depth: int) -> 'Tile':
        tile.subdivide()

        ratio = 1 / (4 ** (max_depth - current_depth))
        tile.reduce_mesh_vertices(decimate_ratio=ratio)
        tile.reduce_texture_resolution(texture_scale=ratio)

        current_depth += 1
        if current_depth < max_depth:
            tile.childrens = [self._create_tile_children(tile_child, current_depth, max_depth) for tile_child in tile.childrens[:1]]

        return tile


class Tile:
    object: Object
    childrens: list['Tile'] = []

    def __init__(self, object: Object):
        self.object = object
        self.childrens = []

    def subdivide(self):
        object_duplicated: Object = BlenderUtils.duplicate_object(object=self.object, new_object_name=f'{self.object.name}_temp')
        bpy.context.view_layer.objects.active = object_duplicated

        bpy.ops.object.mode_set(mode='EDIT')

        bm = bmesh.from_edit_mesh(object_duplicated.data)

        min_x = min(vertex.co.x for vertex in bm.verts)
        max_x = max(vertex.co.x for vertex in bm.verts)
        min_y = min(vertex.co.y for vertex in bm.verts)
        max_y = max(vertex.co.y for vertex in bm.verts)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # Create four lists to hold face groups for each quadrant
        quadrants: list[list[BMFace]] = [[], [], [], []]
        # Sort faces into quadrants based on face centroids
        for face in bm.faces:
            face_center = face.calc_center_median()
            if face_center.x < center_x and face_center.y < center_y:
                quadrants[0].append(face)
            elif face_center.x >= center_x and face_center.y < center_y:
                quadrants[1].append(face)
            elif face_center.x < center_x and face_center.y >= center_y:
                quadrants[2].append(face)
            elif face_center.x >= center_x and face_center.y >= center_y:
                quadrants[3].append(face)

        for faces in quadrants:
            bpy.ops.mesh.select_all(action='DESELECT')

            # Select the faces in the current quadrant
            for face in faces:
                face.select = True

            # Separate the selected faces of quadrant into a new object
            bpy.ops.mesh.separate(type='SELECTED')

        bmesh.update_edit_mesh(object_duplicated.data)
        bm.free()

        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.data.objects.remove(object_duplicated, do_unlink=True)

        children_tile_objects = [object for object in bpy.context.selectable_objects if object.name.startswith(self.object.name) and object.name != self.object.name]
        for index, children_tile_object in enumerate(children_tile_objects):
            children_tile_object.name = f'{self.object.name}_{index}'
            self.childrens.append(Tile(object=children_tile_object))
            print(f'{children_tile_object.name} tile successfully created')

    def reduce_mesh_vertices(self, decimate_ratio: float):
        decimate_modifier: DecimateModifier = self.object.modifiers.new(name='Decimate', type='DECIMATE')
        decimate_modifier.ratio = decimate_ratio
        decimate_modifier.use_collapse_triangulate = False  # Avoids extra triangles if not needed
        decimate_modifier.use_symmetry = True  # Helps keep UVs more consistent

    def reduce_texture_resolution(self, texture_scale: float):
        for index, material in enumerate(self.object.data.materials):
            new_material = material.copy()
            self.object.data.materials[index] = new_material

            if new_material.use_nodes:
                for node in new_material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        new_image: Image = node.image.copy()
                        if new_image:
                            new_width = int(new_image.size[0] * texture_scale)
                            new_height = int(new_image.size[1] * texture_scale)
                            new_image.scale(new_width, new_height)
                            node.image = new_image


# BlenderSession.clean()

grid_x = 106
grid_y = 69
chunk = Chunk(grid_x, grid_y)
# chunk.load_3d_object(file_path=f'/Users/jonas.frei/Documents/Python/blender_01/data/data_2/Tile-{grid_x}-{grid_y}-1-1.obj')
chunk.create_tiles(depth=3)
