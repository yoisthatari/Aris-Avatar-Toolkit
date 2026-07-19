from __future__ import annotations

import re

import bpy
from bpy.types import Context, Material, Operator

from ..core import common

_SUFFIX = re.compile(r"\.\d{3}$")


def _base_image(material: Material):
    if not material.node_tree:
        return None
    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            return node.image
    return None


class AAT_OT_merge_duplicate_materials(Operator):
    bl_idname = "aat.merge_duplicate_materials"
    bl_label = "Merge Duplicate Materials"
    bl_description = (
        "Merge materials that are copies of each other (same base name and same "
        "main texture), e.g. 'Skin', 'Skin.001', 'Skin.002'"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def execute(self, context: Context):
        armature = common.get_armature(context)
        meshes = common.get_armature_meshes(context, armature)

        groups: dict[tuple[str, str], Material] = {}
        replacements: dict[Material, Material] = {}
        for mesh in meshes:
            for slot in mesh.material_slots:
                material = slot.material
                if material is None:
                    continue
                base_name = _SUFFIX.sub("", material.name)
                image = _base_image(material)
                key = (base_name, image.name if image else "")
                canonical = groups.setdefault(key, material)
                if canonical is not material:
                    replacements[material] = canonical

        merged = 0
        for mesh in meshes:
            for slot in mesh.material_slots:
                if slot.material in replacements:
                    slot.material = replacements[slot.material]
                    merged += 1

        for (base_name, _), material in groups.items():
            if material.name != base_name and base_name not in bpy.data.materials:
                material.name = base_name

        self.report(
            {'INFO'},
            f"Merged {len(set(replacements))} duplicate materials across {merged} slots",
        )
        return {'FINISHED'}


class AAT_OT_remove_unused_material_slots(Operator):
    bl_idname = "aat.remove_unused_material_slots"
    bl_label = "Remove Unused Material Slots"
    bl_description = "Remove material slots that no face uses, on all meshes of the model"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def execute(self, context: Context):
        armature = common.get_armature(context)
        meshes = common.get_armature_meshes(context, armature)
        common.ensure_object_mode(context)
        for mesh in meshes:
            with context.temp_override(object=mesh, active_object=mesh, selected_objects=[mesh]):
                bpy.ops.object.material_slot_remove_unused()
        self.report({'INFO'}, "Removed unused material slots")
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_merge_duplicate_materials,
    AAT_OT_remove_unused_material_slots,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
