import math
from typing import Optional

import bmesh
import bpy
from bmesh.types import BMFace
from bpy.types import DecimateModifier, Image, Material, MeshUVLoopLayer, Object, ShaderNodeTexImage


class BlenderSession:
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


class BlenderObjectUtils:
    def duplicate(object: Object, new_object_name: str) -> Object:
        new_object = object.copy()
        new_object.data = object.data.copy()
        new_object.name = new_object_name
        bpy.context.collection.objects.link(new_object)
        return new_object

    def get_image_nodes(object: Object) -> list[ShaderNodeTexImage]:
        image_nodes = []

        for material in object.data.materials:
            if material and material.use_nodes:
                for node in material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        image_nodes.append(node)

        return image_nodes

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
    def add_empty_image(material: Material, name: str, width: Optional[int], height: Optional[int], image: Optional[Image] = None) -> ShaderNodeTexImage:
        if image is None:
            if width is None or height is None:
                raise Exception('image width and heigh needs to be specified when creating a new image')
            image = bpy.data.images.new(name, width, height, alpha=True)
            image.generated_color = (0, 0, 0, 0)
        nodes = material.node_tree.nodes
        image_texture_node: ShaderNodeTexImage = nodes.new(type='ShaderNodeTexImage')
        image_texture_node.name = name
        image_texture_node.image = image
        image_texture_node.select = True
        nodes.active = image_texture_node
        return image_texture_node


class BlenderUVUtils:
    def pack_islands(scale: bool, margin: int, calculate_average_islands_scale: bool = False):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        if calculate_average_islands_scale:
            bpy.ops.uv.average_islands_scale()
        bpy.ops.uv.pack_islands(scale=scale, margin=margin)
        bpy.ops.object.mode_set(mode='OBJECT')


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
        object_name = object.name
        seperated_objects: list[Object] = BlenderObjectUtils.separate_by_materials(object)
        for seperated_object in seperated_objects:
            bpy.context.view_layer.objects.active = seperated_object
            bpy.ops.object.select_all(action='DESELECT')
            seperated_object.select_set(True)

            # Create a new UV layer for the object
            new_uv_layer = seperated_object.data.uv_layers.new(name='uv_map_01', do_init=True)
            seperated_object.data.uv_layers.active = new_uv_layer

            BlenderUVUtils.pack_islands(scale=False, margin=0)

            image_nodes = BlenderObjectUtils.get_image_nodes(seperated_object)
            if len(seperated_object.data.materials) != 1:
                raise Exception('Object should only have one material assigned')
            if len(image_nodes) != 1:
                raise Exception('Object should only have one image assigned')
            material = seperated_object.data.materials[0]
            node_image: ShaderNodeTexImage = image_nodes[0]
            ideal_texture_width, ideal_texture_height = BlenderImageUtils.get_ideal_size(seperated_object, node_image.image, uv_layer=seperated_object.data.uv_layers.active)
            node_new_image: ShaderNodeTexImage = BlenderMaterialUtils.add_empty_image(
                material,
                name=f'{seperated_object.name}_texture',
                width=ideal_texture_width,
                height=ideal_texture_height,
            )

            BlenderUVUtils.pack_islands(scale=True, margin=0)

            bpy.ops.object.bake(type='DIFFUSE')

            node_tree = seperated_object.data.materials[0].node_tree
            nodes = node_tree.nodes

            node_principled_bsdf = nodes.get('Principled BSDF')
            node_tree.links.new(node_new_image.outputs['Color'], node_principled_bsdf.inputs['Base Color'])

            # remove old image from material
            material.node_tree.nodes.remove(node_image)

            seperated_object.data.uv_layers.active.active_render = True

        for seperated_object in seperated_objects:
            seperated_object.select_set(True)
            bpy.context.view_layer.objects.active = seperated_object

        bpy.ops.object.join()
        combined_object = bpy.context.view_layer.objects.active
        combined_object.name = object_name

        uv_layer = combined_object.data.uv_layers.new(name='uv_map_02')
        combined_object.data.uv_layers.active = uv_layer

        BlenderUVUtils.pack_islands(scale=True, margin=0, calculate_average_islands_scale=True)

        image_nodes: list[ShaderNodeTexImage] = BlenderObjectUtils.get_image_nodes(combined_object)
        total_pixel_count = sum(image_node.image.size[0] * image_node.image.size[1] for image_node in image_nodes)
        image_resolution = int(math.sqrt(total_pixel_count))
        image = bpy.data.images.new(name=f'{object_name}_texture', width=image_resolution, height=image_resolution, alpha=True)
        image.generated_color = (0, 0, 0, 0)

        for material in combined_object.data.materials:
            nodes = material.node_tree.nodes
            BlenderMaterialUtils.add_empty_image(material, name=f'{object_name}_texture', width=None, height=None, image=image)

        bpy.ops.object.bake(type='DIFFUSE')

        material = bpy.data.materials.new(name='material_01')
        material.use_nodes = True

        nodes = material.node_tree.nodes
        node_image: ShaderNodeTexImage = nodes.new(type='ShaderNodeTexImage')
        node_image.name = f'{object_name}_texture'
        node_image.image = image
        node_principled_bsdf = nodes.get('Principled BSDF')
        material.node_tree.links.new(node_image.outputs['Color'], node_principled_bsdf.inputs['Base Color'])

        combined_object = bpy.data.objects.get(object_name)
        combined_object.data.materials.clear()
        combined_object.data.materials.append(material)

        combined_object.data.uv_layers.active.active_render = True

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
blender_session.clean()

grid_x = 106
grid_y = 69
chunk = Chunk(grid_x, grid_y)
chunk.load_3d_object(file_path=f'/Users/jonas.frei/Documents/Python/blender_01/data/data_2/Tile-{grid_x}-{grid_y}-1-1.obj', clean=True, combine_materials=True)
# # chunk.create_tiles(depth=3)
