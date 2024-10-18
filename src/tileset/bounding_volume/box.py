from bpy.types import Object
from pydantic import BaseModel

from src import utils


class Box(BaseModel):
    box: list[float]

    def __init__(self, object: Object):
        box = utils.tile.calculate_bounding_volume_box(object)
        super().__init__(box=box)
