"""
run_in_blender.py — paste-and-run launcher for Blender's Text Editor.

Use this if you don't want to install the add-on: open this file in
Blender's Text Editor (or paste it), fix REPO_ROOT below if needed, and
press Run Script. It puts the repo on sys.path, (re)loads every module so
edits are picked up between runs, and builds the full scene.

Headless build + reel render:
    blender -b -P run_in_blender.py -- --render-reel
Headless stills:
    blender -b -P run_in_blender.py -- --render-stills
"""

import sys
import os
import importlib

# repo root = the folder containing the hermes_miata/ package.
# When run from the Text Editor on a saved file this resolves itself;
# otherwise hard-code it, e.g. r"C:\dev\Hermes" or "/home/you/Hermes".
try:
    REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
except NameError:
    REPO_ROOT = os.path.dirname(bpy.data.filepath) or os.getcwd()  # noqa

if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

import hermes_miata
from hermes_miata import (utils, materials, body, wheels, interior,
                          drivetrain, animation, scene_setup, photoreal,
                          main_miata)

# hot-reload so repeated runs pick up source edits
for mod in (utils, materials, body, wheels, interior, drivetrain,
            animation, scene_setup, photoreal, main_miata, hermes_miata):
    importlib.reload(mod)

handles = main_miata.build(with_animation=True, with_scene=True, samples=512)

# optional headless render flags (after the '--' separator)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if "--render-reel" in argv:
    main_miata.render_reel()
if "--render-stills" in argv:
    main_miata.render_stills()
