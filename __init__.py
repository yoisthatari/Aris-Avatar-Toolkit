from . import core
from .core import properties
from .operators import (
    align_tools,
    armature_ops,
    attach_ops,
    avatar_analyzer,
    blendshape_sync,
    blendshape_transfer,
    clothing_fit,
    decimation,
    eye_tracking,
    fix_model,
    health_check,
    import_export,
    material_ops,
    mesh_ops,
    pose_ops,
    shapekey_ops,
    texturing_ops,
    translate_ops,
    vertex_tools,
    visemes,
    weight_transfer,
)
from .ui import panels

_MODULES = (
    properties,
    import_export,
    fix_model,
    health_check,
    armature_ops,
    pose_ops,
    visemes,
    eye_tracking,
    clothing_fit,
    weight_transfer,
    attach_ops,
    blendshape_transfer,
    blendshape_sync,
    shapekey_ops,
    mesh_ops,
    vertex_tools,
    material_ops,
    decimation,
    translate_ops,
    texturing_ops,
    align_tools,
    avatar_analyzer,
    panels,
)


def register() -> None:
    for module in _MODULES:
        module.register()


def unregister() -> None:
    for module in reversed(_MODULES):
        module.unregister()
