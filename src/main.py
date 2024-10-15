import os
import sys

import bpy

# Add the script's directory to sys.path for Blender to locate modules correctly
script_dir = os.path.dirname(bpy.data.filepath)
if script_dir not in sys.path:
    sys.path.append(script_dir)


from src.chunk import Chunk  # noqa
from src.session import Session  # noqa

session = Session()
session.clean()

grid_x = 106
grid_y = 69
chunk = Chunk(grid_x, grid_y)
chunk.load_3d_object(file_path=f'/Users/jonas.frei/Documents/Python/blender_01/data/data_2/Tile-{grid_x}-{grid_y}-1-1.obj', clean=True, combine_materials=True)
# chunk.create_tiles(depth=3)
