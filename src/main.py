import importlib
import os
import sys
from typing import Optional

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
    Reloads all modules in the current project directory to ensure the latest code changes are reflected without restarting Blender.
    This is especially useful during development to see updates without reloading the entire environment.
    """

    # Get the current project directory path
    project_directory = os.getcwd()
    module_names = list(sys.modules.keys())

    for module_name in module_names:
        module = sys.modules[module_name]
        module_path: Optional[str] = getattr(module, '__file__', None)

        if module_path and module_path.startswith(project_directory):
            if getattr(module, '__spec__', None) is None:
                # Skipping module due to missing spec
                continue
            try:
                # Reload the module to apply any recent code changes
                importlib.reload(module)
            except Exception as e:
                print(f'Failed to reload module: {module_path} - {e}')


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
print('yess')
