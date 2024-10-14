from typing import Optional

import bpy
from bpy.types import Image, Material, ShaderNodeTexImage


def add_empty_image(material: Material, name: str, width: Optional[int], height: Optional[int], image: Optional[Image] = None) -> ShaderNodeTexImage:
    if image is None:
        if width is None or height is None:
            raise Exception('image width and heigh needs to be specified when creating a new image')
        image = bpy.data.images.new(name, width, height, alpha=True)
        image.generated_color = (0, 0, 0, 0)
    nodes = material.node_tree.nodes
    image_texture_node: ShaderNodeTexImage = nodes.new(type='ShaderNodeTexImage')
    image_texture_node.name = name
    image_texture_node.image = image
    image_texture_node.select = True
    nodes.active = image_texture_node
    return image_texture_node
