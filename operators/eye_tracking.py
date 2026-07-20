import bpy
from bpy.types import Context, Operator

from ..core import common


class AAT_OT_setup_eye_bones(Operator):
    bl_idname = "aat.setup_eye_bones"
    bl_label = "Setup Eye Bones"
    bl_description = (
        "Renames the chosen bones to Eye_L / Eye_R, optionally parents them to "
        "the Head bone, and straightens them upright for bright, modern eye "
        "tracking"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        settings = getattr(context.scene, "aat", None)
        return (
            settings is not None
            and common.get_armature(context) is not None
            and settings.eye_left_bone != "NONE"
            and settings.eye_right_bone != "NONE"
        )

    def execute(self, context: Context):
        settings = context.scene.aat
        armature = common.get_armature(context)

        if settings.eye_left_bone == settings.eye_right_bone:
            self.report({'ERROR'}, "Left and right eye must be different bones")
            return {'CANCELLED'}

        common.switch_mode(context, armature, 'EDIT')
        edit_bones = armature.data.edit_bones

        left = edit_bones.get(settings.eye_left_bone)
        right = edit_bones.get(settings.eye_right_bone)
        if left is None or right is None:
            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'ERROR'}, "Selected eye bones no longer exist")
            return {'CANCELLED'}

        meshes = common.get_armature_meshes(context, armature)
        renames = []
        for bone, standard in ((left, "Eye_L"), (right, "Eye_R")):
            if bone.name != standard:
                if standard in edit_bones and edit_bones[standard] not in (left, right):
                    old = edit_bones[standard]
                    old.name = standard + ".old"
                renames.append((bone.name, standard))
                bone.name = standard

        head = edit_bones.get("Head")
        if settings.eye_reparent_to_head and head:
            for bone in (left, right):
                bone.parent = head
                bone.use_connect = False

        if settings.eye_straighten:
            for bone in (left, right):
                length = max(bone.length, 0.01)
                bone.tail = bone.head.copy()
                bone.tail.z += length
                bone.roll = 0.0

        bpy.ops.object.mode_set(mode='OBJECT')

        for mesh in meshes:
            for old_name, new_name in renames:
                if mesh.vertex_groups.get(old_name) and mesh.vertex_groups.get(new_name):
                    common.merge_vertex_group(mesh, old_name, new_name)

        self.report({'INFO'}, "Eye bones set up (Eye_L / Eye_R)")
        return {'FINISHED'}


class AAT_OT_test_eye_rotation(Operator):
    bl_idname = "aat.test_eye_rotation"
    bl_label = "Test Eye Rotation"
    bl_description = "Rotate both eye bones in pose mode so you can see them sparkle and move correctly"
    bl_options = {'REGISTER', 'UNDO'}

    angle: bpy.props.FloatProperty(
        name="Angle",
        description="Test rotation in degrees around the X axis",
        default=15.0,
        min=-45.0,
        max=45.0,
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = common.get_armature(context)
        return (
            armature is not None
            and "Eye_L" in armature.data.bones
            and "Eye_R" in armature.data.bones
        )

    def execute(self, context: Context):
        import math

        armature = common.get_armature(context)
        common.switch_mode(context, armature, 'POSE')
        for name in ("Eye_L", "Eye_R"):
            pose_bone = armature.pose.bones[name]
            pose_bone.rotation_mode = 'XYZ'
            pose_bone.rotation_euler = (math.radians(self.angle), 0.0, 0.0)
        return {'FINISHED'}


class AAT_OT_reset_eye_rotation(Operator):
    bl_idname = "aat.reset_eye_rotation"
    bl_label = "Reset Eye Rotation"
    bl_description = "Clears the test rotation from the eye bones"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        armature = common.get_armature(context)
        return (
            armature is not None
            and "Eye_L" in armature.data.bones
            and "Eye_R" in armature.data.bones
        )

    def execute(self, context: Context):
        armature = common.get_armature(context)
        for name in ("Eye_L", "Eye_R"):
            pose_bone = armature.pose.bones.get(name)
            if pose_bone:
                pose_bone.matrix_basis.identity()
        if armature.mode == 'POSE':
            bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_setup_eye_bones,
    AAT_OT_test_eye_rotation,
    AAT_OT_reset_eye_rotation,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
