import math

import bpy
from bpy.types import Object, ShaderNodeTexImage

from src import utils
from src.tile import Tile


class Chunk:
    grid_x: int
    grid_y: int
    tiles: list[Tile]

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
        seperated_objects: list[Object] = utils.object.separate_by_materials(object)
        for seperated_object in seperated_objects:
            bpy.context.view_layer.objects.active = seperated_object
            bpy.ops.object.select_all(action='DESELECT')
            seperated_object.select_set(True)

            # Create a new UV layer for the object
            new_uv_layer = seperated_object.data.uv_layers.new(name='uv_map_01', do_init=True)
            seperated_object.data.uv_layers.active = new_uv_layer

            utils.uv.pack_islands(scale=False, margin=0)

            image_nodes = utils.object.get_image_nodes(seperated_object)
            if len(seperated_object.data.materials) != 1:
                raise Exception('Object should only have one material assigned')
            if len(image_nodes) != 1:
                raise Exception('Object should only have one image assigned')
            material = seperated_object.data.materials[0]
            node_image: ShaderNodeTexImage = image_nodes[0]
            ideal_texture_width, ideal_texture_height = utils.image.get_ideal_size(seperated_object, node_image.image, uv_layer=seperated_object.data.uv_layers.active)
            node_new_image: ShaderNodeTexImage = utils.material.add_empty_image(
                material,
                name=f'{seperated_object.name}_texture',
                width=ideal_texture_width,
                height=ideal_texture_height,
            )

            utils.uv.pack_islands(scale=True, margin=0)

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

        utils.uv.pack_islands(scale=True, margin=0, calculate_average_islands_scale=True)

        image_nodes: list[ShaderNodeTexImage] = utils.object.get_image_nodes(combined_object)
        total_pixel_count = sum(image_node.image.size[0] * image_node.image.size[1] for image_node in image_nodes)
        image_resolution = int(math.sqrt(total_pixel_count))
        image = bpy.data.images.new(name=f'{object_name}_texture', width=image_resolution, height=image_resolution, alpha=True)
        image.generated_color = (0, 0, 0, 0)

        for material in combined_object.data.materials:
            nodes = material.node_tree.nodes
            utils.material.add_empty_image(material, name=f'{object_name}_texture', width=None, height=None, image=image)

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

    def _create_tile_children(self, tile: Tile, current_depth: int, max_depth: int) -> Tile:
        tile.subdivide()

        ratio = 1 / (4 ** (max_depth - current_depth))
        tile.reduce_mesh_vertices(decimate_ratio=ratio)
        tile.reduce_texture_resolution(texture_scale=ratio)

        current_depth += 1
        if current_depth < max_depth:
            tile.childrens = [self._create_tile_children(tile_child, current_depth, max_depth) for tile_child in tile.childrens[:1]]

        return tile
