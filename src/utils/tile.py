import math

from bpy.types import Object

from src import utils


def calculate_transformation_matrix(object: Object) -> list[float]:
    (center_x, center_y, center_z) = utils.object.get_bounding_box_center(object)
    (length_x, length_y, length_z) = utils.object.get_axis_lengths(object)

    # Construct the 3x4 oriented bounding box matrix
    return [center_x, center_y, center_z, length_x / 2, 0, 0, 0, length_y / 2, 0, 0, 0, length_z / 2]


def calculate_geometric_error(object: Object) -> float:
    (length_x, length_y, length_z) = utils.object.get_axis_lengths(object)

    # Calculate the full diagonal of the bounding box
    diagonal = math.sqrt(length_x**2 + length_y**2 + length_z**2)

    return diagonal / 2


def calculate_bounding_volume_box(object: Object) -> list[float]:
    (center_x, center_y, center_z) = utils.object.get_bounding_box_center(object)
    (length_x, length_y, length_z) = utils.object.get_axis_lengths(object)

    return [center_x, center_y, center_z, length_x / 2, 0, 0, 0, length_y / 2, 0, 0, 0, length_z / 2]
