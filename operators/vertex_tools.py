import re

import bpy
from bpy.types import Context, Operator

from ..core import common

_INDEX_PATTERN = re.compile(r"\d+")


class AAT_OT_select_error_vertices(Operator):
    bl_idname = "aat.select_error_vertices"
    bl_label = "Select Error Vertices"
    bl_description = (
        "Select the pasted vertex index numbers on the active mesh and enter "
        "Edit Mode, so you can fix a Unity unweighted-vertex error"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        obj = context.active_object
        settings = getattr(context.scene, "aat", None)
        return (
            obj is not None and obj.type == 'MESH'
            and settings is not None and settings.vertex_error_input.strip() != ""
        )

    def execute(self, context: Context):
        obj = context.active_object
        settings = context.scene.aat
        indices = sorted({int(match) for match in _INDEX_PATTERN.findall(settings.vertex_error_input)})
        if not indices:
            self.report({'ERROR'}, "No vertex indices found in the pasted text")
            return {'CANCELLED'}

        mesh = obj.data
        vertex_count = len(mesh.vertices)
        valid = [i for i in indices if 0 <= i < vertex_count]
        invalid_count = len(indices) - len(valid)

        common.ensure_object_mode(context)
        mesh.vertices.foreach_set("select", [False] * vertex_count)
        mesh.edges.foreach_set("select", [False] * len(mesh.edges))
        mesh.polygons.foreach_set("select", [False] * len(mesh.polygons))
        for i in valid:
            mesh.vertices[i].select = True
        mesh.update()

        common.switch_mode(context, obj, 'EDIT')
        bpy.ops.mesh.select_mode(type='VERT')

        message = f"Selected {len(valid)} vertices"
        if invalid_count:
            message += f", {invalid_count} indices were out of range"
            self.report({'WARNING'}, message)
        else:
            self.report({'INFO'}, message)
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_select_error_vertices,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
