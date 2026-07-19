from __future__ import annotations

import re

import bpy
from bpy.types import Context, Object, Operator

from ..core import bone_names, common, translations

_KEEP_BONES = {
    "Hips", "Spine", "Chest", "Upper Chest", "Neck", "Head",
    "Eye_L", "Eye_R",
    "Left shoulder", "Right shoulder",
    "Left arm", "Right arm",
    "Left elbow", "Right elbow",
    "Left wrist", "Right wrist",
    "Left leg", "Right leg",
    "Left knee", "Right knee",
    "Left ankle", "Right ankle",
    "Left toe", "Right toe",
}

_SPINE_CHAIN = ("Hips", "Spine", "Chest", "Upper Chest", "Neck", "Head")

_RIGIDBODY_PATTERN = re.compile(r"(?i)^(rigidbodies|joints|rigid ?body|物理演算)")


class AAT_OT_fix_model(Operator):
    bl_idname = "aat.fix_model"
    bl_label = "Fix Model"
    bl_description = (
        "Fix the model in one click: translate and standardize bone names, "
        "clean the hierarchy, remove junk bones, apply transforms and join meshes"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def execute(self, context: Context):
        settings = context.scene.aat
        armature = common.get_armature(context)
        if armature is None:
            self.report({'ERROR'}, "No armature found in the scene")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        common.unhide_everything(context)

        if settings.fix_remove_rigidbodies:
            removed = self._remove_rigidbodies(context, armature)
            if removed:
                self.report({'INFO'}, f"Removed {removed} rigid body / joint helper objects")

        meshes = common.get_armature_meshes(context, armature)
        if not meshes:
            self.report({'ERROR'}, "The armature has no meshes bound to it")
            return {'CANCELLED'}

        self._clear_pose(context, armature)
        common.apply_transforms(context, [armature, *meshes])

        if settings.fix_translate_names:
            self._translate_names(armature, meshes)

        renamed = 0
        if settings.fix_standardize_names:
            renamed = self._standardize_bones(context, armature, meshes)

        if settings.fix_remove_constraints:
            self._remove_constraints(armature)

        deleted_bones = 0
        if settings.fix_remove_zero_weight:
            deleted_bones = self._remove_zero_weight_bones(
                context, armature, meshes, settings)

        if settings.fix_reparent_bones:
            self._fix_hierarchy(context, armature)

        if settings.fix_connect_bones:
            self._connect_bones(context, armature)

        self._fix_armature_modifiers(armature, meshes)
        common.remove_empty_vertex_groups(meshes, armature)

        if settings.fix_join_meshes and len(meshes) > 1:
            body = self._join_meshes(context, armature, meshes)
        else:
            body = meshes[0]

        armature.show_in_front = True
        armature.data.display_type = 'OCTAHEDRAL'
        common.set_active(context, armature)

        tris = sum(common.triangle_count(m) for m in common.get_armature_meshes(context, armature))
        self.report(
            {'INFO'},
            f"Model fixed: {renamed} bones standardized, {deleted_bones} junk bones "
            f"removed, {tris:,} triangles in '{body.name}'",
        )
        return {'FINISHED'}

    def _remove_rigidbodies(self, context: Context, armature: Object) -> int:
        removed = 0
        for obj in list(context.scene.objects):
            root_name = obj.name
            top = obj
            while top.parent is not None and top.parent != armature:
                top = top.parent
                root_name = top.name
            if _RIGIDBODY_PATTERN.match(root_name) and obj.type in {'EMPTY', 'MESH'} and not (
                obj.type == 'MESH' and any(
                    mod.type == 'ARMATURE' and mod.object == armature for mod in obj.modifiers
                )
            ):
                bpy.data.objects.remove(obj, do_unlink=True)
                removed += 1
        return removed

    def _clear_pose(self, context: Context, armature: Object) -> None:
        common.switch_mode(context, armature, 'POSE')
        for pose_bone in armature.pose.bones:
            pose_bone.matrix_basis.identity()
        bpy.ops.object.mode_set(mode='OBJECT')

    def _translate_names(self, armature: Object, meshes: list[Object]) -> None:
        for bone in armature.data.bones:
            translated = translations.translate(common.sanitize_name(bone.name))
            if translated != bone.name and translated not in armature.data.bones:
                bone.name = translated
        for mesh in meshes:
            new_name = translations.translate(common.sanitize_name(mesh.name))
            if new_name != mesh.name:
                mesh.name = new_name
            for slot in mesh.material_slots:
                if slot.material:
                    translated = translations.translate(slot.material.name)
                    if translated != slot.material.name:
                        slot.material.name = translated
            if mesh.data.shape_keys:
                for kb in mesh.data.shape_keys.key_blocks:
                    translated = translations.translate(kb.name)
                    if translated != kb.name:
                        kb.name = translated

    def _standardize_bones(self, context: Context, armature: Object, meshes: list[Object]) -> int:
        rename_map = bone_names.build_rename_map([b.name for b in armature.data.bones])
        for old, new in rename_map.items():
            bone = armature.data.bones.get(old)
            if bone:
                bone.name = new
        return len(rename_map)

    def _remove_constraints(self, armature: Object) -> None:
        for pose_bone in armature.pose.bones:
            for constraint in list(pose_bone.constraints):
                pose_bone.constraints.remove(constraint)

    def _remove_zero_weight_bones(
        self, context: Context, armature: Object, meshes: list[Object], settings
    ) -> int:
        weighted = common.collect_weighted_bone_names(
            meshes, threshold=settings.merge_weights_threshold)

        def is_protected(name: str) -> bool:
            if name in _KEEP_BONES:
                return True
            if settings.fix_keep_twist_bones and re.search(r"(?i)twist|捩", name):
                return True
            return False

        common.switch_mode(context, armature, 'EDIT')
        edit_bones = armature.data.edit_bones

        keep: set[str] = set()

        def mark(bone) -> bool:
            keep_this = bone.name in weighted or is_protected(bone.name)
            for child in bone.children:
                if mark(child):
                    keep_this = True
            if keep_this:
                keep.add(bone.name)
            return keep_this

        for root in [b for b in edit_bones if b.parent is None]:
            mark(root)

        to_delete = [b.name for b in edit_bones if b.name not in keep]

        merge_targets: dict[str, str] = {}
        for name in to_delete:
            bone = edit_bones.get(name)
            ancestor = bone.parent if bone else None
            while ancestor is not None and ancestor.name not in keep:
                ancestor = ancestor.parent
            if ancestor is not None:
                merge_targets[name] = ancestor.name

        for name in to_delete:
            bone = edit_bones.get(name)
            if bone is not None:
                edit_bones.remove(bone)

        bpy.ops.object.mode_set(mode='OBJECT')

        for mesh in meshes:
            for source, target in merge_targets.items():
                if mesh.vertex_groups.get(source):
                    common.merge_vertex_group(mesh, source, target)

        return len(to_delete)

    def _fix_hierarchy(self, context: Context, armature: Object) -> None:
        common.switch_mode(context, armature, 'EDIT')
        edit_bones = armature.data.edit_bones

        present = [edit_bones[name] for name in _SPINE_CHAIN if name in edit_bones]
        for parent, child in zip(present, present[1:]):
            child.parent = parent
            child.use_connect = False

        hips = edit_bones.get("Hips")
        if hips:
            hips.parent = None
            left_leg = edit_bones.get("Left leg")
            right_leg = edit_bones.get("Right leg")
            spine = edit_bones.get("Spine")
            if left_leg and right_leg:
                hips.head = (left_leg.head + right_leg.head) / 2
            if spine:
                hips.tail = spine.head.copy()
            if (hips.tail - hips.head).length < 1e-5:
                hips.tail = hips.head.copy()
                hips.tail.z += 0.1
            if hips.tail.z < hips.head.z:
                hips.head, hips.tail = hips.tail.copy(), hips.head.copy()
            hips.roll = 0.0

            for leg_name in ("Left leg", "Right leg"):
                leg = edit_bones.get(leg_name)
                if leg:
                    leg.parent = hips
                    leg.use_connect = False

        for side in ("Left", "Right"):
            shoulder = edit_bones.get(f"{side} shoulder")
            anchor = edit_bones.get("Upper Chest") or edit_bones.get("Chest") or edit_bones.get("Spine")
            if shoulder and anchor:
                shoulder.parent = anchor
                shoulder.use_connect = False
            for parent_name, child_name in (
                (f"{side} shoulder", f"{side} arm"),
                (f"{side} arm", f"{side} elbow"),
                (f"{side} elbow", f"{side} wrist"),
                (f"{side} leg", f"{side} knee"),
                (f"{side} knee", f"{side} ankle"),
                (f"{side} ankle", f"{side} toe"),
            ):
                parent = edit_bones.get(parent_name)
                child = edit_bones.get(child_name)
                if parent and child:
                    child.parent = parent
                    child.use_connect = False

        bpy.ops.object.mode_set(mode='OBJECT')

    def _connect_bones(self, context: Context, armature: Object) -> None:
        common.switch_mode(context, armature, 'EDIT')
        for bone in armature.data.edit_bones:
            children = bone.children
            if len(children) == 1:
                child = children[0]
                if (bone.tail - child.head).length > 1e-6 and (bone.head - child.head).length > 1e-3:
                    bone.tail = child.head.copy()
        bpy.ops.object.mode_set(mode='OBJECT')

    def _fix_armature_modifiers(self, armature: Object, meshes: list[Object]) -> None:
        for mesh in meshes:
            armature_mods = [m for m in mesh.modifiers if m.type == 'ARMATURE']
            for extra in armature_mods[1:]:
                mesh.modifiers.remove(extra)
            if armature_mods:
                mod = armature_mods[0]
            else:
                mod = mesh.modifiers.new(name="Armature", type='ARMATURE')
            mod.object = armature
            mod.name = "Armature"
            mod.show_in_editmode = True
            mod.show_on_cage = True
            if mesh.parent is None or mesh.parent != armature:
                mesh.parent = armature
                mesh.matrix_parent_inverse = armature.matrix_world.inverted()

    def _join_meshes(self, context: Context, armature: Object, meshes: list[Object]) -> Object:
        common.ensure_object_mode(context)

        for mesh in meshes:
            for mod in list(mesh.modifiers):
                if mod.type == 'ARMATURE':
                    continue
                if not mod.show_viewport:
                    mesh.modifiers.remove(mod)
                    continue
                if common.has_shapekeys(mesh) and mod.type not in {
                    'ARMATURE', 'DATA_TRANSFER', 'NORMAL_EDIT', 'SMOOTH', 'DISPLACE',
                }:
                    mesh.modifiers.remove(mod)
                    continue
                try:
                    common.apply_modifier_with_shapekeys(context, mesh, mod.name)
                except RuntimeError:
                    mesh.modifiers.remove(mod)

        for obj in context.view_layer.objects:
            obj.select_set(False)
        for mesh in meshes:
            mesh.select_set(True)
        context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()

        body = context.view_layer.objects.active
        body.name = "Body"
        return body


_CLASSES = (AAT_OT_fix_model,)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
