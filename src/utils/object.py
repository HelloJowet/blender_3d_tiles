import math

import bmesh
import bpy
from bmesh.types import BMFace
from bpy.types import DecimateModifier, Object, ShaderNodeTexImage
from mathutils import Vector

from src import utils


def clean():
    """
    Clean up the selected mesh.
    """

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.dissolve_degenerate()  # Remove redundant geometry
    bpy.ops.mesh.remove_doubles()  # Merge duplicate vertices
    bpy.ops.object.mode_set(mode='OBJECT')


def duplicate(object: Object, new_object_name: str) -> Object:
    """
    Creates a duplicate of the specified object and links it to the current collection.
    """

    new_object = object.copy()
    new_object.data = object.data.copy()  # Duplicate mesh data
    new_object.name = new_object_name
    bpy.context.collection.objects.link(new_object)  # Link to current collection
    return new_object


def get_image_nodes(object: Object) -> list[ShaderNodeTexImage]:
    """
    Finds and returns all image texture nodes in the object's materials.
    """

    image_nodes = []

    for material in object.data.materials:
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    image_nodes.append(node)

    return image_nodes


def separate_by_materials(object: Object) -> list[Object]:
    """
    Separates the object into individual objects by material assignment and renames each.
    """

    seperated_objects = []

    bpy.ops.object.mode_set(mode='EDIT')

    for material_index, material in enumerate(object.data.materials):
        bpy.ops.mesh.select_all(action='DESELECT')
        object.active_material_index = material_index
        bpy.ops.object.material_slot_select()  # Select faces with the current material
        bpy.ops.mesh.separate(type='SELECTED')  # Separate selected faces

        new_separated_object = bpy.data.objects.get(f'{object.name}.001')
        new_separated_object.name = f'tile_106_69__1__material_{material_index}'
        new_separated_object.data.materials.clear()  # Clear all old materials
        new_separated_object.data.materials.append(material)  # Assign new material

        seperated_objects.append(new_separated_object)

    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='DESELECT')
    object.select_set(True)
    bpy.ops.object.delete()  # Delete the original object

    return seperated_objects


def merge_images(object: Object, resolution: int, new_uv_layer_name: str):
    """
    Creates a new UV layer and image for the object, bakes combined textures, and links them.
    """

    uv_layer = object.data.uv_layers.new(name=new_uv_layer_name)
    object.data.uv_layers.active = uv_layer

    utils.uv.pack_islands(scale=True, margin=0, calculate_average_islands_scale=True)

    # Create a new transparent image for baking
    image = bpy.data.images.new(name=object.name, width=resolution, height=resolution, alpha=True)
    image.generated_color = (0, 0, 0, 0)

    # Link the new image to each material of the object
    for material in object.data.materials:
        nodes = material.node_tree.nodes
        utils.material.add_empty_image(material, name=object.name, width=None, height=None, image=image)

    bpy.ops.object.bake(type='DIFFUSE')  # Bake old images into the new image

    # Create a new material and assign the baked image to it
    material = bpy.data.materials.new(name='material_01')
    material.use_nodes = True
    nodes = material.node_tree.nodes
    node_image: ShaderNodeTexImage = nodes.new(type='ShaderNodeTexImage')
    node_image.name = object.name
    node_image.image = image

    # Add baked image to material
    node_principled_bsdf = nodes.get('Principled BSDF')
    material.node_tree.links.new(node_image.outputs['Color'], node_principled_bsdf.inputs['Base Color'])

    # Assign the new material to the object and set UV layer for rendering
    object.data.materials.clear()
    object.data.materials.append(material)
    object.data.uv_layers.active.active_render = True


def combine_materials(object: Object):
    """
    Combines materials of the object by separating, re-baking, and merging all materials into one.
    """

    object_name = object.name
    seperated_objects = utils.object.separate_by_materials(object)

    # Process each separated object, ensure it has a single material and remove unused pixels
    for seperated_object in seperated_objects:
        bpy.context.view_layer.objects.active = seperated_object
        bpy.ops.object.select_all(action='DESELECT')
        seperated_object.select_set(True)

        if len(seperated_object.data.materials) != 1:
            raise Exception('Object should only have one material assigned')
        material = seperated_object.data.materials[0]

        image_nodes = [node for node in material.node_tree.nodes if node.type == 'TEX_IMAGE']
        if len(image_nodes) != 1:
            raise Exception('Material should only have one image assigned')
        image_node = image_nodes[0]

        utils.image.remove_unused_pixels(image_node, material, seperated_object, new_uv_layer_name='uv_layer_01')

    # Join separated objects into a single combined object
    for seperated_object in seperated_objects:
        seperated_object.select_set(True)
        bpy.context.view_layer.objects.active = seperated_object
    bpy.ops.object.join()
    combined_object = bpy.context.view_layer.objects.active
    combined_object.name = object_name

    # Calculate resolution for the merged image and combine textures
    image_nodes = utils.object.get_image_nodes(combined_object)
    total_pixel_count = sum(image_node.image.size[0] * image_node.image.size[1] for image_node in image_nodes)
    image_resolution = int(math.sqrt(total_pixel_count))
    merge_images(combined_object, image_resolution, new_uv_layer_name='uv_layer_02')


def subdivide(object: Object):
    """
    Subdivides an object into four quadrants.
    """

    # Duplicate the original object to work with a temporary copy
    object_duplicated = duplicate(object=object, new_object_name=f'{object.name}_temp')
    bpy.context.view_layer.objects.active = object_duplicated

    # Switch to Edit mode to work with vertices and faces
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(object_duplicated.data)

    # Calculate the bounding box center along the x and y axes
    min_x = min(vertex.co.x for vertex in bm.verts)
    max_x = max(vertex.co.x for vertex in bm.verts)
    min_y = min(vertex.co.y for vertex in bm.verts)
    max_y = max(vertex.co.y for vertex in bm.verts)
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    # Initialize four lists to hold faces for each quadrant
    quadrants: list[list[BMFace]] = [[], [], [], []]

    # Sort faces into quadrants based on face centroid positions
    for face in bm.faces:
        face_center = face.calc_center_median()
        if face_center.x < center_x and face_center.y < center_y:
            quadrants[0].append(face)  # Lower-left quadrant
        elif face_center.x >= center_x and face_center.y < center_y:
            quadrants[1].append(face)  # Lower-right quadrant
        elif face_center.x < center_x and face_center.y >= center_y:
            quadrants[2].append(face)  # Upper-left quadrant
        elif face_center.x >= center_x and face_center.y >= center_y:
            quadrants[3].append(face)  # Upper-right quadrant

    # Separate faces in each quadrant into a new object
    for faces in quadrants:
        bpy.ops.mesh.select_all(action='DESELECT')

        # Select all faces in the current quadrant
        for face in faces:
            face.select = True

        # Separate the selected faces into a new object
        bpy.ops.mesh.separate(type='SELECTED')

    # Update mesh and free bmesh data
    bmesh.update_edit_mesh(object_duplicated.data)
    bm.free()

    # Switch back to Object mode and remove the temporary duplicate object
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects.remove(object_duplicated, do_unlink=True)


def reduce_vertices(object: Object, decimate_ratio: float):
    """
    Reduces the vertex count of an object.
    """

    # Create a Decimate modifier for the object
    decimate_modifier: DecimateModifier = object.modifiers.new(name='Decimate', type='DECIMATE')
    decimate_modifier.ratio = decimate_ratio  # Set decimation ratio to reduce vertices

    # Ensure no unnecessary triangles are created and keep UV symmetry consistent
    decimate_modifier.use_collapse_triangulate = False
    decimate_modifier.use_symmetry = True


def change_vertices_center(object: Object, new_center: Vector):
    """
    Center the vertex coordinates of the specified mesh object around a given center.
    """

    # Create a bmesh from the object
    bm = bmesh.new()
    bm.from_mesh(object.data)

    # Move all vertices to be centered around the new_center
    for v in bm.verts:
        v.co -= new_center

    # Update the mesh with the new vertex positions
    bm.to_mesh(object.data)
    bm.free()

    # Remove artifacts in texture
    bpy.ops.mesh.customdata_custom_splitnormals_clear()


def get_minimum_and_maximum_bounds(object: Object) -> tuple[float, float]:
    # Get the object's bounding box in world coordinates
    bounding_box_world = [object.matrix_world @ Vector(corner) for corner in object.bound_box]

    # Calculate the minimum and maximum bounds in each axis
    min_bound = [min(coordinate[i] for coordinate in bounding_box_world) for i in range(3)]
    max_bound = [max(coordinate[i] for coordinate in bounding_box_world) for i in range(3)]

    return (min_bound, max_bound)


def get_bounding_box_center(object: Object) -> tuple[float, float, float]:
    (min_bound, max_bound) = get_minimum_and_maximum_bounds(object)

    # Calculate the center of the bounding box
    center_x = (max_bound[0] + min_bound[0]) / 2
    center_y = (max_bound[1] + min_bound[1]) / 2
    center_z = (max_bound[2] + min_bound[2]) / 2

    return (center_x, center_y, center_z)


def get_axis_lengths(object: Object) -> tuple[float, float, float]:
    (min_bound, max_bound) = get_minimum_and_maximum_bounds(object)

    # Calculate lengths along each axis (X, Y, Z)
    length_x = max_bound[0] - min_bound[0]
    length_y = max_bound[1] - min_bound[1]
    length_z = max_bound[2] - min_bound[2]

    return (length_x, length_y, length_z)


def remove_inactive_uv_layers(object: Object):
    mesh = object.data

    # Iterate over the UV layers in reverse to avoid index shifting issues
    for uv_layer in reversed(mesh.uv_layers):
        # If it's not the active UV layer, remove it
        if not uv_layer.active:
            mesh.uv_layers.remove(uv_layer)
