import bpy
from bpy.types import Object

from src import utils
from src.utils.pydantic import BaseSchema

from .tile import Tile


class Tileset(BaseSchema):
    asset: dict = {'version': '1.0'}
    geometric_error: float
    root: Tile

    @classmethod
    def get(cls, grid_x: int, grid_y: int, max_depth: int) -> 'Tileset':
        object_name = f'chunk_{grid_x}_{grid_y}__1'
        object = bpy.data.objects.get(object_name)
        if object is None:
            raise Exception(f'Tileset root tile {object_name} could not be found')

        tile = Tile.get(object, current_depth=1, max_depth=max_depth)
        tile.transform = [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1]

        return cls(geometric_error=1, root=tile)

    @classmethod
    def create(cls, object: Object, max_depth: int) -> 'Tileset':
        if len(object.data.materials) != 1:
            raise Exception('Tileset can only be created with an object that only has one material assigned')
        image_nodes = utils.object.get_image_nodes(object)
        if len(image_nodes) != 1:
            raise Exception('Tileset can only be created with an object that only has one image assigned')

        object.name += '__1'
        object.data.materials[0].name = object.name

        tile = Tile.create(object, current_depth=1, max_depth=max_depth)
        tile.transform = [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1]

        return cls(geometric_error=1, root=tile)

    def save(self, folder_path: str):
        self.root.save(folder_path)

        with open(f'{folder_path}/tileset.json', 'w') as json_file:
            json_file.write(self.model_dump_json(exclude_none=True, by_alias=True))
