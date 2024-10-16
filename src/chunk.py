import bpy

from src import logger, utils
from src.tile import Tile


class Chunk:
    """
    Represents a chunk in a grid with 3D tiles.
    """

    grid_x: int
    grid_y: int
    tiles: list[Tile]

    def __init__(self, grid_x: int, grid_y: int):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.tiles = []

    def load_3d_object(self, file_path: str, clean: bool = True, combine_materials: bool = True):
        bpy.ops.wm.obj_import(filepath=file_path)

        # Access the imported object and assign a unique name based on grid coordinates
        selected_object = bpy.context.active_object
        selected_object.name = f'tile_{self.grid_x}_{self.grid_y}__1'
        selected_object.rotation_euler = (0, 0, 0)

        # Center the view on the imported object
        bpy.ops.view3d.view_selected()

        if clean:
            utils.object.clean()
        if combine_materials and len(selected_object.data.materials) > 1:
            utils.object.combine_materials(selected_object)

        logger.debug(f'Successfully imported a 3d object from the following file path: {file_path}')

    def create_tiles(self, depth: int):
        """
        Generates a hierarchical tile structure for the chunk, subdividing the root tile based on the specified depth.
        """

        root_tile_object = bpy.data.objects.get(f'tile_{self.grid_x}_{self.grid_y}__1')
        if not root_tile_object:
            raise Exception('Root tile could not be found')

        root_tile = Tile(object=root_tile_object)
        self.tiles = self._get_tile_childrens(tile=root_tile, current_depth=1, max_depth=depth)

    def _get_tile_childrens(self, tile: Tile, current_depth: int, max_depth: int) -> list[Tile]:
        """
        Recursively subdivides a tile, simplifies its geometry and texture, and creates children tiles.
        """

        # Subdivide the tile into smaller tiles
        tile.subdivide()

        # Simplify geometry based on the tileset depth
        tile.simplify(ratio=1 / (4 ** (max_depth - current_depth)))

        tile_childrens = []

        # Increment the depth and recurse if not yet at maximum depth
        current_depth += 1
        if current_depth < max_depth:
            # Recursively create child tiles for further subdivision
            for tile_child in tile.childrens[:1]:
                tile_child.remove_unused_texture_pixels()
                tile_child.reduce_texture_resolution(texture_scale=0.25)
                tile_child.childrens = self._get_tile_childrens(tile_child, current_depth, max_depth)
                tile_childrens.append(tile_child)

        return tile_childrens
