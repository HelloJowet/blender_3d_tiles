import re
from typing import Optional

import bpy
from bpy.types import Object
from pydantic import BaseModel

from src import enums, logger

from . import bounding_volume
from .content import Content


class Tile(BaseModel):
    transform: Optional[list[list[int]]]
    bounding_volume: bounding_volume.Box
    geometric_error: float
    refine: enums.Refine = enums.Refine.replace
    content: Content
    children: list['Tile']

    @classmethod
    def get(cls, object: Object, current_depth: int, max_depth: int) -> 'Tile':
        tile = cls(transform=None, bounding_volume=bounding_volume.Box(), geometric_error=1, content=Content(object), children=[])
        tile.children = tile.get_children(current_depth, max_depth, parent_object_name=object.name)
        return tile

    @classmethod
    def create(cls, object: Object, current_depth: int, max_depth: int) -> 'Tile':
        tile = cls(transform=None, bounding_volume=bounding_volume.Box(), geometric_error=1, content=Content(object), children=[])

        if current_depth != 1:
            tile.content.remove_unused_texture_pixels()

        tile.children = tile.create_children(current_depth, max_depth)

        if current_depth < max_depth:
            # Simplify geometry and texture based on the tileset depth
            simplification_ratio = 1 / 4 ** (max_depth - current_depth)
            tile.content.simplify(simplification_ratio if simplification_ratio > 0.03 else 0.03)
            texture_scale = 1 / 2 ** (max_depth - current_depth)
            tile.content.reduce_texture_resolution(texture_scale)

        logger.debug(f'Successfully created the tile {tile.content.get_object().name}')

        return tile

    def get_children(self, current_depth: int, max_depth: int, parent_object_name: Object) -> list['Tile']:
        if current_depth >= max_depth:
            return

        regex_pattern = rf'^{re.escape(parent_object_name)}_([0-3])$'
        children_objects = [object for object in bpy.data.objects if re.match(regex_pattern, object.name)]

        return [Tile.get(child_object, current_depth, max_depth) for child_object in children_objects]

    def create_children(self, current_depth: int, max_depth: int) -> list['Tile']:
        """
        Recursively subdivides a tile, simplifies its geometry and texture, and creates children tiles.
        """

        if current_depth >= max_depth:
            return

        # Subdivide the tile into smaller tiles
        children_objects = self.content.subdivide()

        current_depth += 1

        # Recursively create child tiles for further subdivision
        return [Tile.create(child_object, current_depth, max_depth) for child_object in children_objects]
