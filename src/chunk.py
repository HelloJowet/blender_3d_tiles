import bpy
from bpy.types import Object
from pydantic import BaseModel, PrivateAttr

from src import Tileset, logger, utils


class Chunk(BaseModel):
    _object: Object = PrivateAttr()

    def __init__(self, object: Object):
        super().__init__()
        self._object = object

    def __post_init__(self):
        # Center the view on the chunk
        bpy.ops.view3d.view_selected()

    @classmethod
    def load(cls, grid_x: int, grid_y: int) -> 'Chunk':
        object_name = f'chunk_{grid_x}_{grid_y}'
        object = bpy.data.objects.get(object_name)

        if object is None:
            raise Exception(f'Object {object_name} could not be found')

        return cls(object)

    @classmethod
    def create(cls, grid_x: int, grid_y: int, file_path: str) -> 'Chunk':
        bpy.ops.wm.obj_import(filepath=file_path)

        # Access the imported object and assign a unique name based on grid coordinates
        object = bpy.context.active_object
        object.name = f'chunk_{grid_x}_{grid_y}'
        object.rotation_euler = (0, 0, 0)

        logger.debug(f'Successfully created chunk {grid_x}_{grid_y}')

        return cls(object)

    def clean(self):
        utils.object.clean()

    def combine_materials(self):
        if len(self._object.data.materials) > 1:
            utils.object.combine_materials(self._object)

    def create_tileset(self, max_depth: int) -> Tileset:
        return Tileset.create(self._object, max_depth)
