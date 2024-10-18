import math

from bpy.types import Object
from mathutils import Vector


def calculate_transformation_matrix(object: Object) -> list[float]:
    bounding_box = [object.matrix_world @ Vector(corner) for corner in object.bound_box]

    # Calculate minimum and maximum bounds
    min_bound = [min(coordinate[i] for coordinate in bounding_box) for i in range(3)]
    max_bound = [max(coordinate[i] for coordinate in bounding_box) for i in range(3)]

    # Calculate the center of the bounding box
    center_x = (max_bound[0] + min_bound[0]) / 2
    center_y = (max_bound[1] + min_bound[1]) / 2
    center_z = (max_bound[2] + min_bound[2]) / 2
    center = [center_x, center_y, center_z]

    # Calculate the half-lengths for each axis
    half_length_x = (max_bound[0] - min_bound[0]) / 2
    half_length_y = (max_bound[1] - min_bound[1]) / 2
    half_length_z = (max_bound[2] - min_bound[2]) / 2

    # Construct the 3x4 oriented bounding box matrix
    transformation_matrix = [center[0], center[1], center[2], half_length_x, 0, 0, 0, half_length_y, 0, 0, 0, half_length_z]

    return transformation_matrix


def calculate_geometric_error(transformation_matrix: list[float]) -> float:
    # Extract the half-lengths from the transformation matrix
    half_length_x = transformation_matrix[3]
    half_length_y = transformation_matrix[7]
    half_length_z = transformation_matrix[11]

    # Calculate the full diagonal of the bounding box
    diagonal = math.sqrt((2 * half_length_x) ** 2 + (2 * half_length_y) ** 2 + (2 * half_length_z) ** 2)

    geometric_error = diagonal / 2

    return geometric_error
