from __future__ import annotations

import bpy
from bpy.types import Context, Panel

from ..core import common

CATEGORY = "Ari's Toolkit"


class _BasePanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY


class AAT_PT_main(_BasePanel, Panel):
    bl_idname = "AAT_PT_main"
    bl_label = "Model"

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat

        layout.prop(settings, "armature")

        armature = common.get_armature(context)
        if armature is None:
            box = layout.box()
            box.label(text="No armature in the scene", icon='INFO')
            box.label(text="Import a model to get started")
            return

        col = layout.column()
        col.scale_y = 1.4
        col.operator("aat.fix_model", icon='TOOL_SETTINGS')

        layout.separator()
        row = layout.row(align=True)
        if armature.mode == 'POSE':
            row.operator("aat.stop_pose_mode", icon='POSE_HLT')
        else:
            row.operator("aat.start_pose_mode", icon='POSE_HLT')
        layout.operator("aat.apply_as_rest_pose", icon='ARMATURE_DATA')


class AAT_PT_fix_options(_BasePanel, Panel):
    bl_idname = "AAT_PT_fix_options"
    bl_parent_id = "AAT_PT_main"
    bl_label = "Fix Model Options"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        col = layout.column(heading="Names")
        col.prop(settings, "fix_translate_names")
        col.prop(settings, "fix_standardize_names")
        col = layout.column(heading="Bones")
        col.prop(settings, "fix_reparent_bones")
        col.prop(settings, "fix_remove_zero_weight")
        col.prop(settings, "fix_keep_twist_bones")
        col.prop(settings, "fix_connect_bones")
        col.prop(settings, "fix_remove_constraints")
        col = layout.column(heading="Scene")
        col.prop(settings, "fix_join_meshes")
        col.prop(settings, "fix_remove_rigidbodies")


class AAT_PT_translation(_BasePanel, Panel):
    bl_idname = "AAT_PT_translation"
    bl_label = "Translation"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        layout.label(text="Offline dictionary, no internet needed", icon='WORLD')
        col = layout.column(align=True)
        col.operator("aat.translate_all", icon='FILE_TEXT')
        col.separator()
        row = col.row(align=True)
        row.operator("aat.translate_bones", text="Bones")
        row.operator("aat.translate_shapekeys", text="Shape Keys")
        row = col.row(align=True)
        row.operator("aat.translate_materials", text="Materials")
        row.operator("aat.translate_objects", text="Objects")


class AAT_PT_armature_tools(_BasePanel, Panel):
    bl_idname = "AAT_PT_armature_tools"
    bl_label = "Armature"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        col = layout.column(align=True)
        col.operator("aat.merge_weights_to_parent", icon='BONE_DATA')
        col.operator("aat.remove_zero_weight_bones", icon='GROUP_BONE')
        col.operator("aat.delete_bone_pattern", icon='VIEWZOOM')
        col.operator("aat.remove_constraints", icon='CONSTRAINT_BONE')
        layout.prop(settings, "merge_weights_threshold")


class AAT_PT_visemes(_BasePanel, Panel):
    bl_idname = "AAT_PT_visemes"
    bl_label = "Visemes"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        layout.prop(settings, "viseme_mesh")
        layout.prop(settings, "viseme_ah")
        layout.prop(settings, "viseme_oh")
        layout.prop(settings, "viseme_ch")
        layout.prop(settings, "viseme_intensity")
        col = layout.column()
        col.scale_y = 1.2
        col.operator("aat.create_visemes", icon='RESTRICT_VIEW_OFF')
        layout.operator("aat.remove_visemes", icon='X')


class AAT_PT_eye_tracking(_BasePanel, Panel):
    bl_idname = "AAT_PT_eye_tracking"
    bl_label = "Eye Tracking"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        layout.prop(settings, "eye_left_bone")
        layout.prop(settings, "eye_right_bone")
        layout.prop(settings, "eye_reparent_to_head")
        layout.prop(settings, "eye_straighten")
        col = layout.column()
        col.scale_y = 1.2
        col.operator("aat.setup_eye_bones", icon='HIDE_OFF')
        row = layout.row(align=True)
        row.operator("aat.test_eye_rotation", text="Test")
        row.operator("aat.reset_eye_rotation", text="Reset")


class AAT_PT_clothing(_BasePanel, Panel):
    bl_idname = "AAT_PT_clothing"
    bl_label = "Clothing & Weights"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        layout.prop(settings, "cloth_body_mesh")
        layout.label(text="Acts on the selected meshes", icon='RESTRICT_SELECT_OFF')

        box = layout.box()
        box.label(text="Elastic Fit", icon='MOD_CLOTH')
        box.prop(settings, "cloth_offset")
        box.prop(settings, "cloth_smooth_factor")
        box.prop(settings, "cloth_smooth_iterations")
        obj = context.active_object
        if obj and obj.type == 'MESH':
            box.prop_search(settings, "cloth_offset_group", obj, "vertex_groups")
            box.prop(settings, "cloth_extra_offset")
            box.prop_search(settings, "cloth_pin_group", obj, "vertex_groups")
        col = box.column()
        col.scale_y = 1.2
        col.operator("aat.fit_clothing")

        box = layout.box()
        box.label(text="Weight Transfer", icon='MOD_VERTEX_WEIGHT')
        box.prop(settings, "wt_max_distance")
        box.prop(settings, "wt_max_angle")
        box.prop(settings, "wt_smooth_iterations")
        col = box.column()
        col.scale_y = 1.2
        col.operator("aat.transfer_weights")


class AAT_PT_decimation(_BasePanel, Panel):
    bl_idname = "AAT_PT_decimation"
    bl_label = "Decimation"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat

        armature = common.get_armature(context)
        if armature:
            tris = sum(
                common.triangle_count(m)
                for m in common.get_armature_meshes(context, armature)
            )
            layout.label(text=f"Current: {tris:,} triangles", icon='MESH_DATA')

        layout.prop(settings, "decimate_mode", expand=True)
        layout.prop(settings, "decimate_max_tris")
        layout.prop(settings, "decimate_remove_doubles")
        col = layout.column()
        col.scale_y = 1.2
        col.operator("aat.decimate", icon='MOD_DECIM')


class AAT_PT_shapekeys(_BasePanel, Panel):
    bl_idname = "AAT_PT_shapekeys"
    bl_label = "Shape Keys"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        col = layout.column(align=True)
        col.operator("aat.shapekey_to_basis", icon='SHAPEKEY_DATA')
        col.operator("aat.smooth_shapekeys", icon='MOD_SMOOTH')
        col.operator("aat.remove_empty_shapekeys", icon='TRASH')
        col.operator("aat.sort_shapekeys", icon='SORTALPHA')


class AAT_PT_mesh_materials(_BasePanel, Panel):
    bl_idname = "AAT_PT_mesh_materials"
    bl_label = "Mesh & Materials"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        col = layout.column(align=True)
        col.operator("aat.join_meshes", icon='OBJECT_DATA')
        col.operator("aat.separate_by_materials", icon='MATERIAL')
        col.operator("aat.separate_loose_parts", icon='MOD_EXPLODE')
        col.operator("aat.remove_doubles", icon='AUTOMERGE_ON')
        layout.separator()
        col = layout.column(align=True)
        col.operator("aat.merge_duplicate_materials", icon='MATERIAL_DATA')
        col.operator("aat.remove_unused_material_slots", icon='NODE_MATERIAL')


class AAT_PT_credits(_BasePanel, Panel):
    bl_idname = "AAT_PT_credits"
    bl_label = "Info"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Ari's Avatar Toolkit 1.1.0")
        col.label(text="Made for Blender 5.2 LTS")
        op = layout.operator("wm.url_open", text="GitHub", icon='URL')
        op.url = "https://github.com/yoisthatari/Ari-s-Avatar-Toolkit"


_CLASSES = (
    AAT_PT_main,
    AAT_PT_fix_options,
    AAT_PT_translation,
    AAT_PT_armature_tools,
    AAT_PT_visemes,
    AAT_PT_eye_tracking,
    AAT_PT_clothing,
    AAT_PT_decimation,
    AAT_PT_shapekeys,
    AAT_PT_mesh_materials,
    AAT_PT_credits,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
