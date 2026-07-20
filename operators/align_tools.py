import bpy
from bpy.props import EnumProperty
from bpy.types import Context, Operator
from mathutils import Vector

from ..core import common


class AAT_OT_align_to_element(Operator):
    bl_idname = "aat.align_to_element"
    bl_label = "Align by Vertex/Face"
    bl_description = (
        "Perfectly aligns the selected mesh objects onto a vertex or face "
        "center you picked in edit mode on the active object"
    )
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(
        name="Mode",
        description="What the objects align to on the active object",
        items=(
            ('VERTEX', "Vertex", "Align to the selected vertex (median when several are selected)"),
            ('FACE', "Face", "Align to the center of the selected face (median when several are selected)"),
        ),
        default='VERTEX',
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def invoke(self, context: Context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context: Context):
        active = context.active_object
        if active is None or active.type != 'MESH':
            self.report({'ERROR'}, "The active object must be a mesh")
            return {'CANCELLED'}

        common.ensure_object_mode(context)

        movers = [
            obj for obj in context.selected_objects
            if obj is not active and obj.type == 'MESH'
        ]
        skipped = [
            obj for obj in context.selected_objects
            if obj is not active and obj.type != 'MESH'
        ]
        if not movers:
            self.report({'ERROR'}, "Select at least one other mesh object to align")
            return {'CANCELLED'}

        mesh = active.data
        if self.mode == 'VERTEX':
            points = [v.co for v in mesh.vertices if v.select]
            if not points:
                self.report(
                    {'ERROR'},
                    "No vertex selected. Enter edit mode on the active object and "
                    "select the vertex to align to",
                )
                return {'CANCELLED'}
        else:
            points = [p.center for p in mesh.polygons if p.select]
            if not points:
                self.report(
                    {'ERROR'},
                    "No face selected. Enter edit mode on the active object and "
                    "select the face to align to",
                )
                return {'CANCELLED'}

        local = Vector((0.0, 0.0, 0.0))
        for point in points:
            local += point
        local /= len(points)
        world = active.matrix_world @ local

        for obj in movers:
            obj.matrix_world.translation = world

        message = f"Aligned {len(movers)} objects to the selected {self.mode.lower()}"
        if len(points) > 1:
            message += f" (median of {len(points)})"
        if skipped:
            message += f", skipped {len(skipped)} non-mesh objects"
            self.report({'WARNING'}, message)
        else:
            self.report({'INFO'}, message)
        return {'FINISHED'}


_CLASSES = (AAT_OT_align_to_element,)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
