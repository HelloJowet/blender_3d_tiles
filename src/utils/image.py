from bpy.types import Image, MeshUVLoopLayer, Object


def get_ideal_size(object: Object, image: Image, uv_layer: MeshUVLoopLayer) -> tuple[int, int]:
    """
    Calculate the ideal image size to cover only the UV-mapped area
    """

    min_u = min_v = float('inf')
    max_u = max_v = float('-inf')

    for loop in object.data.loops:
        uv = uv_layer.data[loop.index].uv
        min_u = min(min_u, uv.x)
        max_u = max(max_u, uv.x)
        min_v = min(min_v, uv.y)
        max_v = max(max_v, uv.y)

    uv_width = max_u - min_u
    uv_height = max_v - min_v

    current_image_width = image.size[0]
    current_image_height = image.size[1]
    ideal_image_width = int(current_image_width * uv_width)
    ideal_image_height = int(current_image_height * uv_height)

    return (ideal_image_width, ideal_image_height)
