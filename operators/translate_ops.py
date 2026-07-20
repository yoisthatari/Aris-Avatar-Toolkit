from __future__ import annotations

import bpy
from bpy.types import Context, Operator

from ..core import common, translations


class _TranslateBase(Operator):
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None


class AAT_OT_translate_bones(_TranslateBase):
    bl_idname = "aat.translate_bones"
    bl_label = "Translate Bones"
    bl_description = "Sweetly translates Japanese bone names to English (offline dictionary)"

    def execute(self, context: Context):
        armature = common.get_armature(context)
        count = 0
        for bone in armature.data.bones:
            translated = translations.translate(common.sanitize_name(bone.name))
            if translated != bone.name and translated not in armature.data.bones:
                bone.name = translated
                count += 1
        self.report({'INFO'}, f"Translated {count} bone names")
        return {'FINISHED'}


class AAT_OT_translate_shapekeys(_TranslateBase):
    bl_idname = "aat.translate_shapekeys"
    bl_label = "Translate Shape Keys"
    bl_description = "Sweetly translates Japanese shape key names to English (offline dictionary)"

    def execute(self, context: Context):
        armature = common.get_armature(context)
        count = 0
        for mesh in common.get_armature_meshes(context, armature):
            if not mesh.data.shape_keys:
                continue
            for kb in mesh.data.shape_keys.key_blocks:
                translated = translations.translate(common.sanitize_name(kb.name))
                if translated != kb.name:
                    kb.name = translated
                    count += 1
        self.report({'INFO'}, f"Translated {count} shape keys")
        return {'FINISHED'}


class AAT_OT_translate_materials(_TranslateBase):
    bl_idname = "aat.translate_materials"
    bl_label = "Translate Materials"
    bl_description = "Sweetly translates Japanese material names to English (offline dictionary)"

    def execute(self, context: Context):
        armature = common.get_armature(context)
        count = 0
        seen: set[str] = set()
        for mesh in common.get_armature_meshes(context, armature):
            for slot in mesh.material_slots:
                material = slot.material
                if material is None or material.name in seen:
                    continue
                seen.add(material.name)
                translated = translations.translate(common.sanitize_name(material.name))
                if translated != material.name:
                    material.name = translated
                    count += 1
        self.report({'INFO'}, f"Translated {count} materials")
        return {'FINISHED'}


class AAT_OT_translate_objects(_TranslateBase):
    bl_idname = "aat.translate_objects"
    bl_label = "Translate Objects"
    bl_description = "Sweetly translates Japanese object and mesh names to English (offline dictionary)"

    def execute(self, context: Context):
        count = 0
        for obj in context.scene.objects:
            translated = translations.translate(common.sanitize_name(obj.name))
            if translated != obj.name:
                obj.name = translated
                count += 1
            if obj.data and obj.data.name:
                translated = translations.translate(common.sanitize_name(obj.data.name))
                if translated != obj.data.name:
                    obj.data.name = translated
        self.report({'INFO'}, f"Translated {count} objects")
        return {'FINISHED'}


class AAT_OT_translate_all(_TranslateBase):
    bl_idname = "aat.translate_all"
    bl_label = "Translate Everything"
    bl_description = "Translates bones, shape keys, materials and objects in one lovely go"

    def execute(self, context: Context):
        bpy.ops.aat.translate_bones()
        bpy.ops.aat.translate_shapekeys()
        bpy.ops.aat.translate_materials()
        bpy.ops.aat.translate_objects()
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_translate_bones,
    AAT_OT_translate_shapekeys,
    AAT_OT_translate_materials,
    AAT_OT_translate_objects,
    AAT_OT_translate_all,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
