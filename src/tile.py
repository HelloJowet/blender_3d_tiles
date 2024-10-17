import uuid

import bpy
from bpy.types import Object

from src import utils


class Tile:
    """
    Represents a single tile in a 3D tileset.
    """

    object: Object
    childrens: list['Tile'] = []

    def __init__(self, object: Object):
        self.object = object
        self.childrens = []

    def subdivide(self):
        """
        Subdivides the tile into smaller child tiles.
        """

        utils.object.subdivide(self.object)

        children_tile_objects = [object for object in bpy.context.selectable_objects if object.name.startswith(self.object.name) and object.name != self.object.name]
        for index, children_tile_object in enumerate(children_tile_objects):
            children_tile_object.name = f'{self.object.name}_{index}'

            material = children_tile_object.data.materials[0].copy()
            material.name = children_tile_object.name
            children_tile_object.data.materials.clear()
            children_tile_object.data.materials.append(material)

            self.childrens.append(Tile(object=children_tile_object))

    def simplify(self, ratio: float):
        """
        Simplifies the tile's geometry.
        """

        utils.object.reduce_vertices(self.object, decimate_ratio=ratio)

    def reduce_texture_resolution(self, texture_scale: float):
        """
        Adjusts the texture resolution of the tile's material by the specified scale.
        """

        if len(self.object.data.materials) != 1:
            raise Exception('Tile object should only contain one material')

        material = self.object.data.materials[0]
        self.object.data.materials[0] = utils.material.change_texture_resolution(material, texture_scale, new_image_name=f'{self.object.name}_texture_low_resolution')

    def remove_unused_texture_pixels(self, texture_scale: float = 1):
        images_nodes = utils.object.get_image_nodes(self.object)
        image_node = images_nodes[0]
        material = self.object.data.materials[0]

        utils.image.remove_unused_pixels(image_node, material, self.object, new_uv_layer_name=str(uuid.uuid4()), texture_scale=texture_scale)
