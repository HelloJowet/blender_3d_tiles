import bpy
from bpy.types import Object, ShaderNodeTexImage


def duplicate(object: Object, new_object_name: str) -> Object:
    new_object = object.copy()
    new_object.data = object.data.copy()
    new_object.name = new_object_name
    bpy.context.collection.objects.link(new_object)
    return new_object


def get_image_nodes(object: Object) -> list[ShaderNodeTexImage]:
    image_nodes = []

    for material in object.data.materials:
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    image_nodes.append(node)

    return image_nodes


def separate_by_materials(object: Object) -> list[Object]:
    seperated_objects = []

    bpy.ops.object.mode_set(mode='EDIT')

    for material_index, material in enumerate(object.data.materials):
        bpy.ops.mesh.select_all(action='DESELECT')
        object.active_material_index = material_index
        bpy.ops.object.material_slot_select()
        bpy.ops.mesh.separate(type='SELECTED')

        new_separated_object = bpy.data.objects.get(f'{object.name}.001')
        new_separated_object.name = f'tile_106_69__1__material_{material_index}'
        new_separated_object.data.materials.clear()
        new_separated_object.data.materials.append(material)

        seperated_objects.append(new_separated_object)

    bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='DESELECT')
    object.select_set(True)
    bpy.ops.object.delete()

    return seperated_objects
