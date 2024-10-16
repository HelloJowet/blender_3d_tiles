from typing import Optional

import bpy
from bpy.types import Image, Material, ShaderNodeTexImage


def add_empty_image(material: Material, name: str, width: Optional[int], height: Optional[int], image: Optional[Image] = None) -> ShaderNodeTexImage:
    """
    Add an empty image texture node to the given material, creating a new image if one isn't provided.
    """

    # Create a new blank image if none is provided, with a transparent background color
    if image is None:
        if width is None or height is None:
            raise Exception('image width and heigh needs to be specified when creating a new image')
        image = bpy.data.images.new(name, width, height, alpha=True)
        image.generated_color = (0, 0, 0, 0)

    # Add an image texture node to the material's node tree
    nodes = material.node_tree.nodes
    image_texture_node: ShaderNodeTexImage = nodes.new(type='ShaderNodeTexImage')
    image_texture_node.name = name
    image_texture_node.image = image

    # Make this node the active selection in the node editor (required for baking)
    image_texture_node.select = True
    nodes.active = image_texture_node

    return image_texture_node


def change_texture_resolution(material: Material, texture_scale: float):
    """
    Changes the resolution of all image textures in the specified material by scaling them according to the provided resolution multiplier.
    """

    # Check if the material uses nodes (needed to access image textures within the node tree)
    if material.use_nodes:
        # Loop through all nodes in the material's node tree
        for node in material.node_tree.nodes:
            # Identify image texture nodes specifically
            if node.type == 'TEX_IMAGE' and node.image:
                # Copy the image to avoid modifying the original image file
                new_image = node.image.copy()
                if new_image:
                    # Calculate new dimensions based on the texture scaling factor
                    new_width = int(new_image.size[0] * texture_scale)
                    new_height = int(new_image.size[1] * texture_scale)

                    # Apply the new dimensions to the copied image
                    new_image.scale(new_width, new_height)

                    # Assign the scaled image back to the texture node
                    node.image = new_image
