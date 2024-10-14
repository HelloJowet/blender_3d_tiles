import bmesh
import bpy
from bmesh.types import BMFace
from bpy.types import DecimateModifier, Image, Object

from src import utils


class Tile:
    object: Object
    childrens: list['Tile'] = []

    def __init__(self, object: Object):
        self.object = object
        self.childrens = []

    def subdivide(self):
        object_duplicated: Object = utils.object.duplicate(object=self.object, new_object_name=f'{self.object.name}_temp')
        bpy.context.view_layer.objects.active = object_duplicated

        bpy.ops.object.mode_set(mode='EDIT')

        bm = bmesh.from_edit_mesh(object_duplicated.data)

        min_x = min(vertex.co.x for vertex in bm.verts)
        max_x = max(vertex.co.x for vertex in bm.verts)
        min_y = min(vertex.co.y for vertex in bm.verts)
        max_y = max(vertex.co.y for vertex in bm.verts)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # Create four lists to hold face groups for each quadrant
        quadrants: list[list[BMFace]] = [[], [], [], []]
        # Sort faces into quadrants based on face centroids
        for face in bm.faces:
            face_center = face.calc_center_median()
            if face_center.x < center_x and face_center.y < center_y:
                quadrants[0].append(face)
            elif face_center.x >= center_x and face_center.y < center_y:
                quadrants[1].append(face)
            elif face_center.x < center_x and face_center.y >= center_y:
                quadrants[2].append(face)
            elif face_center.x >= center_x and face_center.y >= center_y:
                quadrants[3].append(face)

        for faces in quadrants:
            bpy.ops.mesh.select_all(action='DESELECT')

            # Select the faces in the current quadrant
            for face in faces:
                face.select = True

            # Separate the selected faces of quadrant into a new object
            bpy.ops.mesh.separate(type='SELECTED')

        bmesh.update_edit_mesh(object_duplicated.data)
        bm.free()

        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.data.objects.remove(object_duplicated, do_unlink=True)

        children_tile_objects = [object for object in bpy.context.selectable_objects if object.name.startswith(self.object.name) and object.name != self.object.name]
        for index, children_tile_object in enumerate(children_tile_objects):
            children_tile_object.name = f'{self.object.name}_{index}'
            self.childrens.append(Tile(object=children_tile_object))
            print(f'{children_tile_object.name} tile successfully created')

    def reduce_mesh_vertices(self, decimate_ratio: float):
        decimate_modifier: DecimateModifier = self.object.modifiers.new(name='Decimate', type='DECIMATE')
        decimate_modifier.ratio = decimate_ratio
        decimate_modifier.use_collapse_triangulate = False  # Avoids extra triangles if not needed
        decimate_modifier.use_symmetry = True  # Helps keep UVs more consistent

    def reduce_texture_resolution(self, texture_scale: float):
        for index, material in enumerate(self.object.data.materials):
            new_material = material.copy()
            self.object.data.materials[index] = new_material

            if new_material.use_nodes:
                for node in new_material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        new_image: Image = node.image.copy()
                        if new_image:
                            new_width = int(new_image.size[0] * texture_scale)
                            new_height = int(new_image.size[1] * texture_scale)
                            new_image.scale(new_width, new_height)
                            node.image = new_image
