import bpy
from bpy.types import Context, Operator

from ..core import common


class AAT_OT_start_pose_mode(Operator):
    bl_idname = "aat.start_pose_mode"
    bl_label = "Start Pose Mode"
    bl_description = "Enter pose mode on the model's armature"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = common.get_armature(context)
        return armature is not None and armature.mode != 'POSE'

    def execute(self, context: Context):
        armature = common.get_armature(context)
        common.unhide_everything(context)
        common.switch_mode(context, armature, 'POSE')
        for pose_bone in armature.pose.bones:
            pose_bone.select = True
        return {'FINISHED'}


class AAT_OT_stop_pose_mode(Operator):
    bl_idname = "aat.stop_pose_mode"
    bl_label = "Stop Pose Mode"
    bl_description = "Reset the pose and return to object mode"
    bl_options = {'REGISTER', 'UNDO'}

    reset_pose: bpy.props.BoolProperty(
        name="Reset Pose",
        description="Clear all pose bone transforms before leaving pose mode",
        default=True,
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = common.get_armature(context)
        return armature is not None and armature.mode == 'POSE'

    def execute(self, context: Context):
        armature = common.get_armature(context)
        if self.reset_pose:
            for pose_bone in armature.pose.bones:
                pose_bone.matrix_basis.identity()
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}


class AAT_OT_apply_as_rest_pose(Operator):
    bl_idname = "aat.apply_as_rest_pose"
    bl_label = "Apply as Rest Pose"
    bl_description = (
        "Make the current pose the new rest pose. Meshes are updated to match, "
        "including meshes with shape keys (which Blender cannot do on its own)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def execute(self, context: Context):
        armature = common.get_armature(context)
        meshes = common.get_armature_meshes(context, armature)

        common.ensure_object_mode(context)

        for mesh in meshes:
            armature_mods = [m for m in mesh.modifiers if m.type == 'ARMATURE' and m.object == armature]
            if not armature_mods:
                continue
            mod = armature_mods[0]
            mod_name = mod.name
            show_states = (mod.show_viewport, mod.show_render)
            mod.show_viewport = True
            try:
                common.apply_modifier_with_shapekeys(context, mesh, mod_name)
            except RuntimeError as exc:
                self.report({'WARNING'}, f"Could not apply pose on '{mesh.name}': {exc}")
                mod.show_viewport, mod.show_render = show_states
                continue
            new_mod = mesh.modifiers.new(name="Armature", type='ARMATURE')
            new_mod.object = armature
            new_mod.show_in_editmode = True
            new_mod.show_on_cage = True

        common.switch_mode(context, armature, 'POSE')
        bpy.ops.pose.armature_apply(selected=False)
        bpy.ops.object.mode_set(mode='OBJECT')

        self.report({'INFO'}, "Pose applied as new rest pose")
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_start_pose_mode,
    AAT_OT_stop_pose_mode,
    AAT_OT_apply_as_rest_pose,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
