from __future__ import annotations

import bpy
from bpy.types import Context, Operator

from ..core import common

VISEME_TABLE: dict[str, list[tuple[str, float]]] = {
    "vrc.v_aa": [("A", 0.9998)],
    "vrc.v_ch": [("CH", 0.9996)],
    "vrc.v_dd": [("A", 0.3), ("CH", 0.7)],
    "vrc.v_e":  [("CH", 0.7), ("O", 0.3)],
    "vrc.v_ff": [("A", 0.2), ("CH", 0.4)],
    "vrc.v_ih": [("A", 0.5), ("CH", 0.2)],
    "vrc.v_kk": [("A", 0.7), ("CH", 0.4)],
    "vrc.v_nn": [("A", 0.2), ("CH", 0.7)],
    "vrc.v_oh": [("A", 0.2), ("O", 0.8)],
    "vrc.v_ou": [("O", 0.9994)],
    "vrc.v_pp": [("A", 0.0004), ("O", 0.0004)],
    "vrc.v_rr": [("CH", 0.5), ("O", 0.3)],
    "vrc.v_sil": [("A", 0.0002), ("CH", 0.0002)],
    "vrc.v_ss": [("CH", 0.8)],
    "vrc.v_th": [("A", 0.4), ("O", 0.15)],
}


class AAT_OT_create_visemes(Operator):
    bl_idname = "aat.create_visemes"
    bl_label = "Create Visemes"
    bl_description = (
        "Generate the 15 standard visemes (vrc.v_aa ... vrc.v_th) from the "
        "selected A, O and CH mouth shape keys"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        settings = getattr(context.scene, "aat", None)
        return settings is not None and settings.viseme_mesh != "NONE"

    def execute(self, context: Context):
        settings = context.scene.aat
        mesh = bpy.data.objects.get(settings.viseme_mesh)
        if mesh is None or mesh.type != 'MESH' or not mesh.data.shape_keys:
            self.report({'ERROR'}, "Selected mesh has no shape keys")
            return {'CANCELLED'}

        sources = {
            "A": settings.viseme_ah,
            "O": settings.viseme_oh,
            "CH": settings.viseme_ch,
        }
        key_blocks = mesh.data.shape_keys.key_blocks
        for label, name in sources.items():
            if name == "NONE" or name not in key_blocks:
                self.report({'ERROR'}, f"Shape {label} is not set")
                return {'CANCELLED'}

        common.ensure_object_mode(context)
        common.set_active(context, mesh)

        saved_values = {kb.name: kb.value for kb in key_blocks}
        saved_mutes = {kb.name: kb.mute for kb in key_blocks}
        for kb in key_blocks:
            kb.value = 0.0
            kb.mute = False

        intensity = settings.viseme_intensity
        created = 0
        for viseme_name, mix in VISEME_TABLE.items():
            existing = key_blocks.get(viseme_name)
            if existing:
                mesh.shape_key_remove(existing)

            for source_label, ratio in mix:
                key_blocks[sources[source_label]].value = min(ratio * intensity, 1.0)

            new_key = mesh.shape_key_add(name=viseme_name, from_mix=True)
            new_key.value = 0.0

            for source_label, _ in mix:
                key_blocks[sources[source_label]].value = 0.0
            created += 1

        for kb in key_blocks:
            if kb.name in saved_values:
                kb.value = saved_values[kb.name]
                kb.mute = saved_mutes[kb.name]

        self.report({'INFO'}, f"Created {created} visemes on '{mesh.name}'")
        return {'FINISHED'}


class AAT_OT_remove_visemes(Operator):
    bl_idname = "aat.remove_visemes"
    bl_label = "Remove Visemes"
    bl_description = "Delete all vrc.v_* shape keys from the selected mesh"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        settings = getattr(context.scene, "aat", None)
        return settings is not None and settings.viseme_mesh != "NONE"

    def execute(self, context: Context):
        settings = context.scene.aat
        mesh = bpy.data.objects.get(settings.viseme_mesh)
        if mesh is None or not mesh.data.shape_keys:
            return {'CANCELLED'}
        removed = 0
        for kb in list(mesh.data.shape_keys.key_blocks):
            if kb.name.startswith("vrc.v_"):
                mesh.shape_key_remove(kb)
                removed += 1
        self.report({'INFO'}, f"Removed {removed} visemes")
        return {'FINISHED'}


_CLASSES = (AAT_OT_create_visemes, AAT_OT_remove_visemes)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
