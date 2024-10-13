from typing import Optional

import bmesh
import bpy
from bmesh.types import BMFace
from bpy.types import DecimateModifier, Image, Material, MeshUVLoopLayer, Object, ShaderNodeTexImage


class BlenderSession:
    def configure_renderer(self):
        # required for baking textures
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.device = 'GPU'

    def clean(self):
        for mesh in bpy.data.meshes:
            bpy.data.meshes.remove(mesh)

        for material in bpy.data.materials:
            bpy.data.materials.remove(material)

        for image in bpy.data.images:
            bpy.data.images.remove(image)


class BlenderObjectUtils:
    def duplicate(object: Object, new_object_name: str) -> Object:
        new_object = object.copy()
        new_object.data = object.data.copy()
        new_object.name = new_object_name
        bpy.context.collection.objects.link(new_object)
        return new_object

    def get_image(object: Object) -> Optional[Image]:
        nodes = object.data.materials[0].node_tree.nodes
        return next((node.image for node in nodes if node.type == 'TEX_IMAGE'), None)

    def separate_by_materials(object: Object) -> list[Object]:
        seperated_objects = []

        bpy.ops.object.mode_set(mode='EDIT')

        for material_index, material in enumerate(object.data.materials):
            bpy.ops.mesh.select_all(action='DESELECT')
            object.active_material_index = material_index
            bpy.ops.object.material_slot_select()
            bpy.ops.mesh.separate(type='SELECTED')

            new_separated_object = bpy.data.objects.get(f'{object.name}.001')
            new_separated_object.name = f'tile_106_69__1__material_{material_index}'
            new_separated_object.data.materials.clear()
            new_separated_object.data.materials.append(material)

            seperated_objects.append(new_separated_object)

        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        object.select_set(True)
        bpy.ops.object.delete()

        return seperated_objects


class BlenderImageUtils:
    def get_ideal_size(object: Object, image: Image, uv_layer: MeshUVLoopLayer) -> tuple[int, int]:
        """
        Calculate the ideal image size to cover only the UV-mapped area
        """

        min_u = min_v = float('inf')
        max_u = max_v = float('-inf')

        for loop in object.data.loops:
            uv = uv_layer.data[loop.index].uv
            min_u = min(min_u, uv.x)
            max_u = max(max_u, uv.x)
            min_v = min(min_v, uv.y)
            max_v = max(max_v, uv.y)

        uv_width = max_u - min_u
        uv_height = max_v - min_v

        current_image_width = image.size[0]
        current_image_height = image.size[1]
        ideal_image_width = int(current_image_width * uv_width)
        ideal_image_height = int(current_image_height * uv_height)

        return (ideal_image_width, ideal_image_height)


class BlenderMaterialUtils:
    def add_empty_image(material: Material, image: Image, name: str, width: int, height: int):
        nodes = material.node_tree.nodes
        if image is None:
            raise Exception('Material has no Image assigned. TODO: This case needs to be handled')
        new_image = bpy.data.images.new(name, width, height, alpha=True)
        new_image.generated_color = (0, 0, 0, 0)
        image_texture_node: ShaderNodeTexImage = nodes.new(type='ShaderNodeTexImage')
        image_texture_node.name = name
        image_texture_node.image = new_image
        image_texture_node.select = True
        nodes.active = image_texture_node


class Chunk:
    grid_x: int
    grid_y: int
    tiles: list['Tile']

    def __init__(self, grid_x: int, grid_y: int):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.tiles = []

    def load_3d_object(self, file_path: str, clean: bool = True, combine_materials: bool = True):
        bpy.ops.wm.obj_import(filepath=file_path, up_axis='Z')

        selected_object = bpy.context.active_object
        selected_object.scale = (0.1, 0.1, 0.1)
        selected_object.name = f'tile_{self.grid_x}_{self.grid_y}__1'

        if clean:
            self._clean()
        if combine_materials and len(selected_object.data.materials) > 1:
            self._combine_materials(selected_object)

    def _clean(self):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')

        bpy.ops.mesh.dissolve_degenerate()
        bpy.ops.mesh.remove_doubles()

        bpy.ops.object.mode_set(mode='OBJECT')

    def _combine_materials(self, object: Object):
        seperated_objects: list[Object] = BlenderObjectUtils.separate_by_materials(object)
        for seperated_object in seperated_objects:
            bpy.context.view_layer.objects.active = seperated_object

            # Create a new UV layer for the object
            new_uv_layer = seperated_object.data.uv_layers.new(name='baked', do_init=True)
            seperated_object.data.uv_layers.active = new_uv_layer

            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.pack_islands(scale=False, margin=0)
            bpy.ops.object.mode_set(mode='OBJECT')

            image = BlenderObjectUtils.get_image(seperated_object)
            material = seperated_object.data.materials[0]
            ideal_texture_width, ideal_texture_height = BlenderImageUtils.get_ideal_size(seperated_object, image, uv_layer=seperated_object.data.uv_layers.active)
            BlenderMaterialUtils.add_empty_image(material, image, name=f'{seperated_object}_texture', width=ideal_texture_width, height=ideal_texture_height)

            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.pack_islands(scale=True, margin=0)
            bpy.ops.object.mode_set(mode='OBJECT')

            bpy.ops.object.select_all(action='DESELECT')
            seperated_object.select_set(True)
            bpy.context.scene.render.bake.use_pass_direct = False
            bpy.context.scene.render.bake.use_pass_indirect = False
            bpy.context.scene.render.bake.use_pass_color = True
            bpy.ops.object.bake(type='DIFFUSE')

            node_tree = seperated_object.data.materials[0].node_tree
            nodes = node_tree.nodes

            node_principled_bsdf = nodes.get('Principled BSDF')
            node_material_1_texture = nodes.get(f'{seperated_object}_texture')
            node_tree.links.new(node_material_1_texture.outputs['Color'], node_principled_bsdf.inputs['Base Color'])

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
        object_duplicated: Object = BlenderObjectUtils.duplicate(object=self.object, new_object_name=f'{self.object.name}_temp')
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


blender_session = BlenderSession()
blender_session.configure_renderer()
blender_session.clean()

grid_x = 106
grid_y = 69
chunk = Chunk(grid_x, grid_y)
chunk.load_3d_object(file_path=f'/Users/jonas.frei/Documents/Python/blender_01/data/data_2/Tile-{grid_x}-{grid_y}-1-1.obj', clean=True, combine_materials=True)
# chunk.create_tiles(depth=3)
