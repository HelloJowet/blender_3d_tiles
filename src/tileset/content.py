import uuid
from typing import Optional

import bpy
from bpy.types import Object
from pydantic import PrivateAttr

from src import utils
from src.utils.pydantic import BaseSchema


class Content(BaseSchema):
    uri: Optional[str]

    _object: Object = PrivateAttr()

    def __init__(self, object: Object):
        super().__init__(uri=None)
        self._object = object

    def get_object(self) -> Object:
        return self._object

    def subdivide(self) -> list[Object]:
        """
        Subdivides the tile into smaller child tiles.
        """

        utils.object.subdivide(self._object)

        children_objects = [object for object in bpy.context.selectable_objects if object.name.startswith(self._object.name) and object.name != self._object.name]
        for index, child_object in enumerate(children_objects):
            child_object.name = f'{self._object.name}_{index}'

            material = child_object.data.materials[0].copy()
            material.name = child_object.name
            child_object.data.materials.clear()
            child_object.data.materials.append(material)

        return children_objects

    def simplify(self, ratio: float):
        """
        Simplifies the tile's geometry.
        """

        utils.object.reduce_vertices(self._object, decimate_ratio=ratio)

    def reduce_texture_resolution(self, texture_scale: float):
        """
        Adjusts the texture resolution of the tile's material by the specified scale.
        """

        if len(self._object.data.materials) != 1:
            raise Exception('Tile object should only contain one material')

        material = self._object.data.materials[0]
        self._object.data.materials[0] = utils.material.change_texture_resolution(material, texture_scale, new_image_name=f'{self._object.name}__low_resolution')

    def remove_unused_texture_pixels(self):
        images_nodes = utils.object.get_image_nodes(self._object)
        image_node = images_nodes[0]
        material = self._object.data.materials[0]

        utils.image.remove_unused_pixels(image_node, material, self._object, new_uv_layer_name=str(uuid.uuid4()))

    def save(self, folder_path: str):
        # Deselect all objects
        bpy.ops.object.select_all(action='DESELECT')

        # Select the specified object
        self._object.select_set(True)
        bpy.context.view_layer.objects.active = self._object

        self.uri = f'{self._object.name}.glb'

        # bpy.ops.export_scene.gltf(
        #     filepath=f'{folder_path}/{self._object.name}',
        #     use_selection=True,
        #     export_format='GLB',
        #     export_apply=True,
        #     export_materials='EXPORT',
        #     export_image_format='WEBP',
        #     export_draco_mesh_compression_enable=True,
        # )
