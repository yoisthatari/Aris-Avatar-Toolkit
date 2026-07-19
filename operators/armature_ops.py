import re

import bpy
from bpy.types import Context, Operator

from ..core import common


class AAT_OT_merge_weights_to_parent(Operator):
    bl_idname = "aat.merge_weights_to_parent"
    bl_label = "Merge Weights to Parent"
    bl_description = (
        "Delete the selected bones and merge their vertex weights into their parents"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        obj = context.active_object
        return obj is not None and obj.type == 'ARMATURE' and obj.mode in {'EDIT', 'POSE'}

    def execute(self, context: Context):
        armature = context.active_object
        meshes = common.get_armature_meshes(context, armature)

        if armature.mode == 'POSE':
            selected = [pb.name for pb in armature.pose.bones if pb.select]
        else:
            selected = [eb.name for eb in armature.data.edit_bones if eb.select]

        if not selected:
            self.report({'ERROR'}, "No bones selected")
            return {'CANCELLED'}

        previous_mode = armature.mode
        common.switch_mode(context, armature, 'EDIT')
        edit_bones = armature.data.edit_bones
        selected_set = set(selected)

        merge_targets: dict[str, str] = {}
        deletable: list[str] = []
        for name in selected:
            bone = edit_bones.get(name)
            if bone is None:
                continue
            ancestor = bone.parent
            while ancestor is not None and ancestor.name in selected_set:
                ancestor = ancestor.parent
            if ancestor is None:
                continue
            merge_targets[name] = ancestor.name
            deletable.append(name)

        for name in deletable:
            bone = edit_bones.get(name)
            if bone is not None:
                for child in bone.children:
                    child.parent = bone.parent
                edit_bones.remove(bone)

        bpy.ops.object.mode_set(mode='OBJECT')

        for mesh in meshes:
            for source, target in merge_targets.items():
                common.merge_vertex_group(mesh, source, target)

        common.switch_mode(context, armature, previous_mode)
        self.report({'INFO'}, f"Merged {len(deletable)} bones into their parents")
        return {'FINISHED'}


class AAT_OT_remove_zero_weight_bones(Operator):
    bl_idname = "aat.remove_zero_weight_bones"
    bl_label = "Remove Zero-Weight Bones"
    bl_description = (
        "Delete bones that carry no vertex weights (their weighted descendants are kept)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def execute(self, context: Context):
        settings = context.scene.aat
        armature = common.get_armature(context)
        meshes = common.get_armature_meshes(context, armature)
        weighted = common.collect_weighted_bone_names(
            meshes, threshold=settings.merge_weights_threshold)

        common.switch_mode(context, armature, 'EDIT')
        edit_bones = armature.data.edit_bones

        keep: set[str] = set()

        def mark(bone) -> bool:
            keep_this = bone.name in weighted
            for child in bone.children:
                if mark(child):
                    keep_this = True
            if keep_this:
                keep.add(bone.name)
            return keep_this

        for root in [b for b in edit_bones if b.parent is None]:
            mark(root)

        removed = 0
        for bone in list(edit_bones):
            if bone.name not in keep:
                edit_bones.remove(bone)
                removed += 1

        bpy.ops.object.mode_set(mode='OBJECT')
        common.remove_empty_vertex_groups(meshes, armature)
        self.report({'INFO'}, f"Removed {removed} zero-weight bones")
        return {'FINISHED'}


class AAT_OT_remove_constraints(Operator):
    bl_idname = "aat.remove_constraints"
    bl_label = "Remove Constraints"
    bl_description = "Remove all bone constraints from the armature"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def execute(self, context: Context):
        armature = common.get_armature(context)
        removed = 0
        for pose_bone in armature.pose.bones:
            for constraint in list(pose_bone.constraints):
                pose_bone.constraints.remove(constraint)
                removed += 1
        self.report({'INFO'}, f"Removed {removed} constraints")
        return {'FINISHED'}


class AAT_OT_delete_bone_pattern(Operator):
    bl_idname = "aat.delete_bone_pattern"
    bl_label = "Delete Bones by Pattern"
    bl_description = "Delete all bones whose names match a regular expression, merging weights upward"
    bl_options = {'REGISTER', 'UNDO'}

    pattern: bpy.props.StringProperty(
        name="Pattern",
        description="Case-insensitive regular expression, e.g. 'twist|physics'",
        default="",
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def invoke(self, context: Context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context: Context):
        if not self.pattern.strip():
            self.report({'ERROR'}, "No pattern given")
            return {'CANCELLED'}
        try:
            regex = re.compile(self.pattern, re.IGNORECASE)
        except re.error as exc:
            self.report({'ERROR'}, f"Invalid pattern: {exc}")
            return {'CANCELLED'}

        armature = common.get_armature(context)
        meshes = common.get_armature_meshes(context, armature)

        common.switch_mode(context, armature, 'EDIT')
        edit_bones = armature.data.edit_bones
        matched = {b.name for b in edit_bones if regex.search(b.name)}

        merge_targets: dict[str, str] = {}
        for name in matched:
            bone = edit_bones.get(name)
            ancestor = bone.parent
            while ancestor is not None and ancestor.name in matched:
                ancestor = ancestor.parent
            if ancestor is not None:
                merge_targets[name] = ancestor.name

        for name in matched:
            bone = edit_bones.get(name)
            if bone is not None:
                edit_bones.remove(bone)

        bpy.ops.object.mode_set(mode='OBJECT')
        for mesh in meshes:
            for source, target in merge_targets.items():
                common.merge_vertex_group(mesh, source, target)

        self.report({'INFO'}, f"Deleted {len(matched)} bones matching '{self.pattern}'")
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_merge_weights_to_parent,
    AAT_OT_remove_zero_weight_bones,
    AAT_OT_remove_constraints,
    AAT_OT_delete_bone_pattern,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
