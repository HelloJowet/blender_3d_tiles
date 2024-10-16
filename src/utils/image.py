import bpy
from bpy.types import Image, Material, MeshUVLoopLayer, Object, ShaderNodeTexImage

from src import utils


def get_ideal_size(object: Object, image: Image, uv_layer: MeshUVLoopLayer) -> tuple[int, int]:
    """
    Calculate the ideal size of an image to fit only the UV-mapped area of the given object.
    """

    # Initialize minimum and maximum UV bounds
    min_u = min_v = float('inf')
    max_u = max_v = float('-inf')

    # Loop through each UV coordinate, updating min/max bounds
    for loop in object.data.loops:
        uv = uv_layer.data[loop.index].uv
        min_u = min(min_u, uv.x)
        max_u = max(max_u, uv.x)
        min_v = min(min_v, uv.y)
        max_v = max(max_v, uv.y)

    # Calculate width and height based on UV bounds
    uv_width = max_u - min_u
    uv_height = max_v - min_v

    # Calculate ideal image dimensions to match the UV-mapped area
    current_image_width = image.size[0]
    current_image_height = image.size[1]
    ideal_image_width = int(current_image_width * uv_width)
    ideal_image_height = int(current_image_height * uv_height)

    return (ideal_image_width, ideal_image_height)


def remove_unused_pixels(image_node: ShaderNodeTexImage, material: Material, object: Object, new_uv_layer_name: str):
    """
    Create a trimmed version of an image texture by removing unused pixels that are not covered by the UV map.
    """

    bpy.ops.object.select_all(action='DESELECT')
    object.select_set(True)

    # Create a new UV layer
    new_uv_layer = object.data.uv_layers.new(name=new_uv_layer_name)
    object.data.uv_layers.active = new_uv_layer

    # Pack UV islands without scaling, to optimize texture space usage
    bpy.context.view_layer.objects.active = object
    utils.uv.pack_islands(scale=False, margin=0)

    # Calculate ideal image size based on UV-mapped area
    ideal_texture_width, ideal_texture_height = get_ideal_size(object, image_node.image, uv_layer=object.data.uv_layers.active)
    # Create a new empty image with the calculated size and add it to the material
    node_new_image = utils.material.add_empty_image(material, name=f'{object.name}_texture', width=ideal_texture_width, height=ideal_texture_height)

    # Re-pack UV islands with scaling to maximize space usage in the new texture
    utils.uv.pack_islands(scale=True, margin=0)

    # Bake the original texture's colors onto the new optimized image
    bpy.ops.object.bake(type='DIFFUSE')

    # Add baked image to material
    principled_bsdf_node = material.node_tree.nodes.get('Principled BSDF')
    material.node_tree.links.new(node_new_image.outputs['Color'], principled_bsdf_node.inputs['Base Color'])

    # Remove the old image node from the material to free up unused nodes
    material.node_tree.nodes.remove(image_node)

    # Set the new UV layer as the active render layer
    object.data.uv_layers.active.active_render = True
