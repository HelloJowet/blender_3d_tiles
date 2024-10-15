import importlib
import os
import sys

import bpy


def setup_blender_local_dev_environment():
    """
    Adds the script's directory to sys.path to allow Blender to locate modules.
    This is essential when working with external Python files for module imports in Blender's environment.
    """

    script_dir = os.path.dirname(bpy.data.filepath)
    if script_dir not in sys.path:
        sys.path.append(script_dir)


def reload_modules():
    """
    Reloads modules to ensure that the latest code changes are reflected without restarting Blender.
    This is useful during development to see updates in code without reloading the entire environment.
    """

    import src.chunk  # noqa
    import src.session  # noqa

    # Reload modules to apply the latest changes
    importlib.reload(src.chunk)
    importlib.reload(src.session)


setup_blender_local_dev_environment()
reload_modules()

from src.chunk import Chunk  # noqa
from src.session import Session  # noqa

# Initialize session, which automatically cleans up existing data in the scene
# session = Session()
# session.clean()

grid_x = 106
grid_y = 69
chunk = Chunk(grid_x, grid_y)
# chunk.load_3d_object(file_path=f'/Users/jonas.frei/Documents/Python/blender_01/data/data_2/Tile-{grid_x}-{grid_y}-1-1.obj', clean=False, combine_materials=False)
chunk.create_tiles(depth=3)
