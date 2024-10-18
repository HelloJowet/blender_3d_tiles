from bpy.types import Object

from src import utils
from src.utils.pydantic import BaseSchema


class Box(BaseSchema):
    box: list[float]

    def __init__(self, object: Object):
        box = self.calculate_box(object)
        super().__init__(box=box)

    def calculate_box(self, object: Object) -> list[float]:
        (center_x, center_y, center_z) = utils.object.get_bounding_box_center(object)
        (length_x, length_y, length_z) = utils.object.get_axis_lengths(object)

        return [center_x, center_y, center_z, length_x / 2, 0, 0, 0, length_y / 2, 0, 0, 0, length_z / 2]
