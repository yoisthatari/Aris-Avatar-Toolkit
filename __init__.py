from . import core
from .core import properties
from .operators import (
    armature_ops,
    decimation,
    eye_tracking,
    fix_model,
    material_ops,
    mesh_ops,
    pose_ops,
    shapekey_ops,
    translate_ops,
    visemes,
)
from .ui import panels

_MODULES = (
    properties,
    fix_model,
    armature_ops,
    pose_ops,
    visemes,
    eye_tracking,
    shapekey_ops,
    mesh_ops,
    material_ops,
    decimation,
    translate_ops,
    panels,
)


def register() -> None:
    for module in _MODULES:
        module.register()


def unregister() -> None:
    for module in reversed(_MODULES):
        module.unregister()
