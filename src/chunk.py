import bpy

from src import utils
from src.tile import Tile


class Chunk:
    grid_x: int
    grid_y: int
    tiles: list[Tile]

    def __init__(self, grid_x: int, grid_y: int):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.tiles = []

    def load_3d_object(self, file_path: str, clean: bool = True, combine_materials: bool = True):
        bpy.ops.wm.obj_import(filepath=file_path, up_axis='Z')

        selected_object = bpy.context.active_object
        selected_object.scale = (0.1, 0.1, 0.1)
        selected_object.name = f'tile_{self.grid_x}_{self.grid_y}__1'

        if clean:
            utils.object.clean()
        if combine_materials and len(selected_object.data.materials) > 1:
            utils.object.combine_materials(selected_object)

    def create_tiles(self, depth: int):
        root_tile_object = bpy.data.objects.get(f'tile_{self.grid_x}_{self.grid_y}__1')
        if not root_tile_object:
            raise Exception('Root tile could not be found')

        root_tile = Tile(object=root_tile_object)
        self.tiles = self._create_tile_children(tile=root_tile, current_depth=1, max_depth=depth)

    def _create_tile_children(self, tile: Tile, current_depth: int, max_depth: int) -> Tile:
        tile.subdivide()

        ratio = 1 / (4 ** (max_depth - current_depth))
        tile.reduce_mesh_vertices(decimate_ratio=ratio)
        tile.reduce_texture_resolution(texture_scale=ratio)

        current_depth += 1
        if current_depth < max_depth:
            tile.childrens = [self._create_tile_children(tile_child, current_depth, max_depth) for tile_child in tile.childrens[:1]]

        return tile
