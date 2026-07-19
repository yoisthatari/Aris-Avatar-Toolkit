import bpy
from bpy.types import Context, Operator

from ..core import common


class AAT_OT_join_meshes(Operator):
    bl_idname = "aat.join_meshes"
    bl_label = "Join Meshes"
    bl_description = "Join all meshes bound to the armature into one 'Body' mesh"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = common.get_armature(context)
        return armature is not None and len(common.get_armature_meshes(context, armature)) > 1

    def execute(self, context: Context):
        armature = common.get_armature(context)
        meshes = common.get_armature_meshes(context, armature)
        common.ensure_object_mode(context)
        common.unhide_everything(context)

        for obj in context.view_layer.objects:
            obj.select_set(False)
        for mesh in meshes:
            mesh.select_set(True)
        context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()

        body = context.view_layer.objects.active
        body.name = "Body"
        self.report({'INFO'}, f"Joined {len(meshes)} meshes into '{body.name}'")
        return {'FINISHED'}


class AAT_OT_separate_by_materials(Operator):
    bl_idname = "aat.separate_by_materials"
    bl_label = "Separate by Materials"
    bl_description = "Split the active mesh into one object per material"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context: Context):
        obj = context.active_object
        common.switch_mode(context, obj, 'EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='MATERIAL')
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}


class AAT_OT_separate_loose_parts(Operator):
    bl_idname = "aat.separate_loose_parts"
    bl_label = "Separate Loose Parts"
    bl_description = "Split the active mesh into its disconnected pieces"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context: Context):
        obj = context.active_object
        common.switch_mode(context, obj, 'EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}


class AAT_OT_remove_doubles(Operator):
    bl_idname = "aat.remove_doubles"
    bl_label = "Merge Doubles"
    bl_description = (
        "Merge duplicate vertices on the active mesh. Skipped automatically on "
        "meshes with shape keys unless forced, since merging can break them"
    )
    bl_options = {'REGISTER', 'UNDO'}

    threshold: bpy.props.FloatProperty(
        name="Merge Distance",
        default=0.0001,
        min=0.0,
        precision=5,
    )
    force_on_shapekeys: bpy.props.BoolProperty(
        name="Allow on Meshes With Shape Keys",
        description="Merge even when the mesh has shape keys (may distort them)",
        default=False,
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context: Context):
        obj = context.active_object
        if common.has_shapekeys(obj) and not self.force_on_shapekeys:
            self.report({'WARNING'}, "Mesh has shape keys; enable the override to merge anyway")
            return {'CANCELLED'}
        before = len(obj.data.vertices)
        common.switch_mode(context, obj, 'EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=self.threshold)
        bpy.ops.object.mode_set(mode='OBJECT')
        removed = before - len(obj.data.vertices)
        self.report({'INFO'}, f"Merged {removed} vertices")
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_join_meshes,
    AAT_OT_separate_by_materials,
    AAT_OT_separate_loose_parts,
    AAT_OT_remove_doubles,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
