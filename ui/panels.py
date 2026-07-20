from __future__ import annotations

import bpy
from bpy.types import Context, Panel

from ..core import common
from ..operators import avatar_analyzer, import_export, shapekey_ops

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

        row = layout.row(align=True)
        row.scale_y = 1.2
        row.operator("aat.import_model", icon='IMPORT')
        row.operator("aat.export_model", icon='EXPORT')
        if not import_export.mmd_tools_available():
            layout.operator("aat.install_mmd_tools", icon='PLUGIN')

        layout.separator()
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
        col.operator("aat.attach_mesh_auto_weights", icon='OUTLINER_OB_ARMATURE')
        col.separator()
        col.operator("aat.merge_weights_to_parent", icon='BONE_DATA')
        col.operator("aat.remove_zero_weight_bones", icon='GROUP_BONE')
        col.operator("aat.remove_end_bones", icon='TRASH')
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


class AAT_PT_blendshape(_BasePanel, Panel):
    bl_idname = "AAT_PT_blendshape"
    bl_label = "Blendshape"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        layout.prop(settings, "bst_source")
        layout.prop(settings, "bst_target")

        box = layout.box()
        box.label(text="Pre-Processing Modifiers", icon='MODIFIER')
        row = box.row(align=True)
        row.prop(settings, "bst_use_subsurf")
        if settings.bst_use_subsurf:
            sub = box.row(align=True)
            sub.prop(settings, "bst_subsurf_levels")
            sub.prop(settings, "bst_preview_subsurf", toggle=True, icon='HIDE_OFF')
        row = box.row(align=True)
        row.prop(settings, "bst_use_displace")
        if settings.bst_use_displace:
            sub = box.row(align=True)
            sub.prop(settings, "bst_displace_strength")
            sub.prop(settings, "bst_preview_displace", toggle=True, icon='HIDE_OFF')

        box = layout.box()
        box.label(text="Transfer Mask", icon='BRUSH_DATA')
        box.label(text="Red transfers fully, blue not at all")
        painting = (
            context.mode == 'PAINT_WEIGHT'
            and settings.bst_target is not None
            and context.active_object is settings.bst_target
        )
        box.operator(
            "aat.draw_transfer_mask",
            text="Finish Painting" if painting else "Draw Transfer Mask",
            icon='CHECKMARK' if painting else 'BRUSH_DATA',
            depress=painting,
        )
        row = box.row(align=True)
        row.operator("aat.reset_transfer_mask")
        row.operator("aat.invert_transfer_mask")

        col = layout.column()
        col.scale_y = 1.4
        col.operator("aat.transfer_blendshapes", icon='SHAPEKEY_DATA')


class AAT_PT_blendshape_sync(_BasePanel, Panel):
    bl_idname = "AAT_PT_blendshape_sync"
    bl_label = "Blendshape Sync"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        layout.label(text="Shape key list comes from the active object", icon='INFO')
        layout.prop(settings, "sync_auxiliary")
        layout.prop(settings, "sync_shapekey")

        col = layout.column(align=True)
        col.operator("aat.sync_blendshape", icon='UV_SYNC_SELECT')
        col.operator("aat.sculpt_shapekey_mode", icon='SCULPTMODE_HLT')
        col.operator("aat.reset_synced_shapekeys", icon='LOOP_BACK')


class AAT_PT_shapekeys(_BasePanel, Panel):
    bl_idname = "AAT_PT_shapekeys"
    bl_label = "Shape Keys"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        col = layout.column(align=True)
        col.operator("aat.shapekey_to_basis", icon='SHAPEKEY_DATA')
        col.operator("aat.smooth_shapekeys", icon='MOD_SMOOTH')
        col.operator("aat.remove_empty_shapekeys", icon='TRASH')
        col.operator("aat.sort_shapekeys", icon='SORTALPHA')

        box = layout.box()
        box.label(text="Batch Creator", icon='PRESET_NEW')
        box.prop(settings, "batch_shapekey_names", text="")
        box.operator("aat.batch_create_shapekeys", icon='ADD')

        obj = context.active_object
        if obj is not None and common.has_shapekeys(obj):
            header = box.row()
            icon = 'TRIA_DOWN' if settings.batch_expanded else 'TRIA_RIGHT'
            header.prop(settings, "batch_expanded", text="Shape Key List", icon=icon, emboss=False)
            if settings.batch_expanded:
                names = [kb.name for kb in obj.data.shape_keys.key_blocks[1:]]
                page_size = shapekey_ops.PAGE_SIZE
                max_page = max((len(names) - 1) // page_size, 0)
                page = min(settings.batch_page, max_page)
                start = page * page_size
                for offset, name in enumerate(names[start:start + page_size]):
                    row = box.row(align=True)
                    op = row.operator("aat.batch_jump_to_shapekey", text=name, icon='SHAPEKEY_DATA')
                    op.index = start + offset + 1
                nav = box.row(align=True)
                nav.operator("aat.batch_page_prev", text="<")
                nav.label(text=f"Page {page + 1} / {max_page + 1}")
                nav.operator("aat.batch_page_next", text=">")


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


class AAT_PT_vertex_tools(_BasePanel, Panel):
    bl_idname = "AAT_PT_vertex_tools"
    bl_label = "Vertex Error Selector"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        layout.label(text="Paste vertex indices from a Unity error message", icon='INFO')
        layout.prop(settings, "vertex_error_input", text="")
        layout.operator("aat.select_error_vertices", icon='VIEWZOOM')


class AAT_PT_align_tools(_BasePanel, Panel):
    bl_idname = "AAT_PT_align_tools"
    bl_label = "Align Tools"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        layout.label(text="Select a vertex/face on the active object in edit mode")
        layout.operator("aat.align_to_element", icon='SNAP_VERTEX')


def _rank_icon(rank: str) -> str:
    return 'CHECKMARK' if rank in ('EXCELLENT', 'GOOD', 'MEDIUM') else 'CANCEL'


class AAT_PT_avatar_analyzer(_BasePanel, Panel):
    bl_idname = "AAT_PT_avatar_analyzer"
    bl_label = "Avatar Analyzer"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        layout.label(text="Scores the avatar against VRChat's performance ranks", icon='INFO')
        layout.prop(settings, "analyzer_armature")
        layout.prop(settings, "analyzer_platform")
        row = layout.row(align=True)
        row.scale_y = 1.2
        row.operator("aat.analyze_avatar", icon='VIEWZOOM')
        row.operator("aat.export_analysis_report", text="Export Report JSON", icon='EXPORT')


class AAT_PT_analyzer_tools(_BasePanel, Panel):
    bl_idname = "AAT_PT_analyzer_tools"
    bl_parent_id = "AAT_PT_avatar_analyzer"
    bl_label = "Creator Tools"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        layout.prop(settings, "analyzer_max_texture")
        layout.prop(settings, "analyzer_force_pot")
        layout.prop(settings, "analyzer_auto_decimate")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("aat.optimize_textures", text="Texture Optimizer", icon='TEXTURE')
        row.operator("aat.toggle_mesh_heatmap", text="Mesh Heatmap", icon='MOD_TRIANGULATE')
        col.separator()
        col.operator("aat.auto_fix_avatar", icon='TOOL_SETTINGS')
        row = col.row(align=True)
        row.operator("aat.undo_auto_fix_session", text="Undo Auto Fix Session", icon='LOOP_BACK')
        col.operator("aat.restore_texture_backup", icon='FILE_REFRESH')
        col.separator()
        col.operator("aat.batch_report_scene", icon='PRESET')


class AAT_PT_analyzer_results(_BasePanel, Panel):
    bl_idname = "AAT_PT_analyzer_results"
    bl_parent_id = "AAT_PT_avatar_analyzer"
    bl_label = "Results"

    def draw(self, context: Context) -> None:
        layout = self.layout
        result = avatar_analyzer.get_last_result()
        if result is None:
            layout.label(text="Click Analyze Avatar to see results", icon='INFO')
        else:
            box = layout.box()
            box.label(
                text=f"Status: {result.overall_rank.title()} | {round(result.score)}/100",
                icon=_rank_icon(result.overall_rank),
            )
            box.label(text=f"Avatar: {result.avatar_name}", icon='ARMATURE_DATA')
            box.label(text=f"Platform: {result.platform}")

            col = layout.column(align=True)
            for category in result.categories:
                row = col.row(align=True)
                row.label(text=category.label)
                row.label(text=f"{category.value:,.0f}")
                row.label(text=category.rank.title(), icon=_rank_icon(category.rank))
            col.separator()
            col.label(text=f"Blend Shapes: {result.blendshape_count:,} (informational, not an official VRChat limit)")

            if result.fix_first:
                box = layout.box()
                box.label(text="Fix First", icon='ERROR')
                for index, suggestion in enumerate(result.fix_first, start=1):
                    box.label(text=f"{index}. {suggestion}")

            if result.heavy_meshes:
                box = layout.box()
                box.label(text="Heavy Meshes", icon='MESH_DATA')
                for name, tris in result.heavy_meshes:
                    row = box.row(align=True)
                    row.label(text=name)
                    row.label(text=f"{tris:,} tris")

            box = layout.box()
            box.label(text="Texture Hotspots", icon='TEXTURE')
            if result.texture_hotspots:
                for name, size, mb in result.texture_hotspots:
                    row = box.row(align=True)
                    row.label(text=name)
                    row.label(text=f"{size}, {mb:.1f} MB")
            else:
                box.label(text="No texture data")

        batch = avatar_analyzer.get_last_batch()
        if batch:
            box = layout.box()
            box.label(text="Batch Report", icon='SCENE_DATA')
            for entry in batch:
                row = box.row(align=True)
                row.label(text=entry.avatar_name)
                row.label(text=entry.overall_rank.title(), icon=_rank_icon(entry.overall_rank))
                row.label(text=f"{round(entry.score)}/100")


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
    AAT_PT_blendshape,
    AAT_PT_decimation,
    AAT_PT_blendshape_sync,
    AAT_PT_shapekeys,
    AAT_PT_mesh_materials,
    AAT_PT_vertex_tools,
    AAT_PT_align_tools,
    AAT_PT_avatar_analyzer,
    AAT_PT_analyzer_tools,
    AAT_PT_analyzer_results,
    AAT_PT_credits,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
