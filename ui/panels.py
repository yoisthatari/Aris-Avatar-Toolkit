from __future__ import annotations

import bpy
from bpy.types import Context, Panel

from ..core import common
from ..operators import (
    avatar_analyzer,
    health_check,
    import_export,
    shapekey_ops,
    texturing_ops,
)

CATEGORY = "Ari's Toolkit"

_LEVEL_ICONS = {'ERROR': 'CANCEL', 'WARNING': 'ERROR', 'INFO': 'INFO'}


class _BasePanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = CATEGORY


class _Section(_BasePanel):
    bl_options = {'DEFAULT_CLOSED'}


def _wrap(text: str, width: int) -> list:
    words = text.split()
    lines: list = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _settings_column(layout):
    column = layout.column()
    column.use_property_split = True
    column.use_property_decorate = False
    return column


def _count(number: int, singular: str, plural: str = "") -> str:
    word = singular if number == 1 else (plural or singular + "s")
    return f"{number} {word}"


def _toggle_column(layout, heading: str = ""):
    column = layout.column(align=True)
    if heading:
        column.label(text=heading)
    return column


def _selection_hint(layout, text: str = "Acts on the selected meshes") -> None:
    row = layout.row()
    row.alignment = 'LEFT'
    row.label(text=text, icon='RESTRICT_SELECT_OFF')


class AAT_PT_main(_BasePanel, Panel):
    bl_idname = "AAT_PT_main"
    bl_label = "Model"
    bl_order = 0

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat

        row = layout.row(align=True)
        row.scale_y = 1.2
        row.operator("aat.import_model", text="Import", icon='IMPORT')
        row.operator("aat.export_model", text="Export", icon='EXPORT')
        if not import_export.mmd_tools_available():
            layout.operator("aat.install_mmd_tools", icon='PLUGIN')

        layout.separator()
        layout.prop(settings, "armature", text="")

        armature = common.get_armature(context)
        if armature is None:
            box = layout.box()
            box.label(text="No armature in the scene", icon='INFO')
            box.label(text="Import a model to get started")
            return

        meshes = common.get_armature_meshes(context, armature)
        bones = len(armature.data.bones)
        row = layout.row(align=True)
        row.label(text=_count(len(meshes), "mesh", "meshes"), icon='MESH_DATA')
        row.label(text=_count(bones, "bone"), icon='BONE_DATA')

        layout.separator()
        col = layout.column()
        col.scale_y = 1.5
        col.operator("aat.fix_model", icon='TOOL_SETTINGS')


class AAT_PT_fix_options(_Section, Panel):
    bl_idname = "AAT_PT_fix_options"
    bl_parent_id = "AAT_PT_main"
    bl_label = "Fix Model Options"
    bl_order = 0

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        col = _toggle_column(layout, "Names")
        col.prop(settings, "fix_translate_names")
        col.prop(settings, "fix_standardize_names")
        layout.separator()
        col = _toggle_column(layout, "Bones")
        col.prop(settings, "fix_reparent_bones")
        col.prop(settings, "fix_remove_zero_weight")
        col.prop(settings, "fix_keep_twist_bones")
        col.prop(settings, "fix_connect_bones")
        col.prop(settings, "fix_remove_constraints")
        layout.separator()
        col = _toggle_column(layout, "Scene")
        col.prop(settings, "fix_join_meshes")
        col.prop(settings, "fix_remove_rigidbodies")


class AAT_PT_translation(_Section, Panel):
    bl_idname = "AAT_PT_translation"
    bl_parent_id = "AAT_PT_main"
    bl_label = "Translation"
    bl_order = 1

    def draw(self, context: Context) -> None:
        layout = self.layout
        layout.label(text="Offline dictionary, no internet needed", icon='WORLD')
        col = layout.column(align=True)
        col.scale_y = 1.2
        col.operator("aat.translate_all", icon='FILE_TEXT')
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("aat.translate_bones", text="Bones")
        row.operator("aat.translate_shapekeys", text="Shape Keys")
        row = col.row(align=True)
        row.operator("aat.translate_materials", text="Materials")
        row.operator("aat.translate_objects", text="Objects")


class AAT_PT_pose(_Section, Panel):
    bl_idname = "AAT_PT_pose"
    bl_parent_id = "AAT_PT_main"
    bl_label = "Pose"
    bl_order = 2

    def draw(self, context: Context) -> None:
        layout = self.layout
        armature = common.get_armature(context)
        col = layout.column(align=True)
        col.scale_y = 1.2
        if armature is not None and armature.mode == 'POSE':
            col.operator("aat.stop_pose_mode", icon='POSE_HLT')
        else:
            col.operator("aat.start_pose_mode", icon='POSE_HLT')
        col.operator("aat.apply_as_rest_pose", icon='ARMATURE_DATA')

        layout.separator()
        col = layout.column(align=True)
        col.label(text="Save a pose to come back to")
        row = col.row(align=True)
        row.operator("aat.store_pose", text="Store", icon='FILE_TICK')
        row.operator("aat.restore_pose", text="Restore", icon='FILE_REFRESH')
        row.operator("aat.reset_pose", text="Reset", icon='LOOP_BACK')


class AAT_PT_health(_Section, Panel):
    bl_idname = "AAT_PT_health"
    bl_label = "Avatar Doctor"
    bl_order = 1

    def draw(self, context: Context) -> None:
        layout = self.layout
        layout.label(text="A full check-up before Unity", icon='INFO')
        col = layout.column()
        col.scale_y = 1.4
        col.operator("aat.health_check", icon='VIEWZOOM')

        report = health_check.get_last_report()
        if report is None:
            layout.label(text="Run the check-up to see results")
            return

        errors = [i for i in report.issues if i.level == 'ERROR']
        warnings = [i for i in report.issues if i.level == 'WARNING']
        infos = [i for i in report.issues if i.level == 'INFO']

        box = layout.box()
        if errors:
            box.label(
                text=f"{len(errors)} to fix, {len(warnings)} to look at",
                icon='CANCEL',
            )
        elif warnings:
            box.label(text=f"No blockers, {len(warnings)} to look at", icon='ERROR')
        else:
            box.label(text="Everything passed", icon='CHECKMARK')
        box.label(text=report.avatar_name, icon='ARMATURE_DATA')

        for group in (errors, warnings, infos):
            for issue in group:
                box = layout.box()
                box.label(text=issue.label, icon=_LEVEL_ICONS.get(issue.level, 'INFO'))
                sub = box.column(align=True)
                sub.scale_y = 0.8
                for line in _wrap(issue.detail, 42):
                    sub.label(text=line)
                if issue.fix:
                    row = box.row()
                    row.scale_y = 1.1
                    row.operator(issue.fix, icon='PLAY')

        if report.passed:
            box = layout.box()
            box.label(text=f"{len(report.passed)} checks passed", icon='CHECKMARK')
            sub = box.column(align=True)
            sub.scale_y = 0.8
            for line in report.passed:
                sub.label(text=line, icon='DOT')


class AAT_PT_weight_tools(_Section, Panel):
    bl_idname = "AAT_PT_weight_tools"
    bl_parent_id = "AAT_PT_health"
    bl_label = "Weight Tools"
    bl_order = 0

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        _selection_hint(layout, "Selected meshes, or the whole model")
        _settings_column(layout).prop(settings, "health_max_influences")

        col = layout.column()
        col.scale_y = 1.4
        col.operator("aat.fix_all_weights", icon='SHADERFX')

        layout.separator()
        col = layout.column(align=True)
        col.operator("aat.fix_unweighted_vertices", icon='GROUP_VERTEX')
        col.operator("aat.limit_bone_influences", icon='BONE_DATA')
        col.operator("aat.normalize_weights", icon='NORMALIZE_FCURVES')
        col.separator()
        col.operator("aat.select_unweighted_vertices", icon='VERTEXSEL')
        col.operator("aat.remove_loose_geometry", icon='TRASH')


class AAT_PT_armature_tools(_Section, Panel):
    bl_idname = "AAT_PT_armature_tools"
    bl_label = "Armature"
    bl_order = 2

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        col = layout.column()
        col.scale_y = 1.2
        col.operator("aat.attach_mesh_auto_weights", icon='OUTLINER_OB_ARMATURE')

        layout.separator()
        col = layout.column(align=True)
        col.operator("aat.merge_weights_to_parent", icon='BONE_DATA')
        col.operator("aat.remove_zero_weight_bones", icon='GROUP_BONE')
        col.operator("aat.remove_end_bones", icon='TRASH')
        col.operator("aat.delete_bone_pattern", icon='VIEWZOOM')
        col.operator("aat.remove_constraints", icon='CONSTRAINT_BONE')
        _settings_column(layout).prop(settings, "merge_weights_threshold")


class AAT_PT_visemes(_Section, Panel):
    bl_idname = "AAT_PT_visemes"
    bl_parent_id = "AAT_PT_armature_tools"
    bl_label = "Visemes"
    bl_order = 0

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        col = _settings_column(layout)
        col.prop(settings, "viseme_mesh")
        col.separator()
        col.prop(settings, "viseme_ah")
        col.prop(settings, "viseme_oh")
        col.prop(settings, "viseme_ch")
        col.separator()
        col.prop(settings, "viseme_intensity")

        col = layout.column()
        col.scale_y = 1.3
        col.operator("aat.create_visemes", icon='RESTRICT_VIEW_OFF')
        layout.operator("aat.remove_visemes", icon='X')


class AAT_PT_eye_tracking(_Section, Panel):
    bl_idname = "AAT_PT_eye_tracking"
    bl_parent_id = "AAT_PT_armature_tools"
    bl_label = "Eye Tracking"
    bl_order = 1

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        col = _settings_column(layout)
        col.prop(settings, "eye_left_bone")
        col.prop(settings, "eye_right_bone")
        col.separator()
        col = _toggle_column(layout)
        col.prop(settings, "eye_reparent_to_head")
        col.prop(settings, "eye_straighten")

        col = layout.column()
        col.scale_y = 1.3
        col.operator("aat.setup_eye_bones", icon='HIDE_OFF')
        row = layout.row(align=True)
        row.operator("aat.test_eye_rotation", text="Test")
        row.operator("aat.reset_eye_rotation", text="Reset")


class AAT_PT_clothing(_Section, Panel):
    bl_idname = "AAT_PT_clothing"
    bl_label = "Clothing & Weights"
    bl_order = 3

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        _settings_column(layout).prop(settings, "cloth_body_mesh")
        _selection_hint(layout)

        box = layout.box()
        box.label(text="Elastic Fit", icon='MOD_CLOTH')
        col = _settings_column(box)
        col.prop(settings, "cloth_offset")
        col.prop(settings, "cloth_smooth_factor")
        col.prop(settings, "cloth_smooth_iterations")
        col.prop(settings, "cloth_passes")
        col.prop(settings, "cloth_max_distance")
        obj = context.active_object
        if obj and obj.type == 'MESH':
            col.separator()
            col.prop_search(settings, "cloth_offset_group", obj, "vertex_groups")
            col.prop(settings, "cloth_extra_offset")
            col.prop_search(settings, "cloth_pin_group", obj, "vertex_groups")
        col = box.column()
        col.scale_y = 1.3
        col.operator("aat.fit_clothing", icon='MOD_CLOTH')

        box = layout.box()
        box.label(text="Hide Body Under Clothing", icon='MOD_MASK')
        box.label(text="Stops poke-through and saves polygons")
        _settings_column(box).prop(settings, "cloth_hide_threshold")
        col = box.column(align=True)
        col.scale_y = 1.3
        col.operator("aat.hide_body_under_clothing", icon='HIDE_ON')
        col.operator("aat.show_body_under_clothing", icon='HIDE_OFF')

        box = layout.box()
        box.label(text="Weight Transfer", icon='MOD_VERTEX_WEIGHT')
        col = _settings_column(box)
        col.prop(settings, "wt_max_distance")
        col.prop(settings, "wt_max_angle")
        col.prop(settings, "wt_smooth_iterations")
        col = box.column()
        col.scale_y = 1.3
        col.operator("aat.transfer_weights", icon='MOD_VERTEX_WEIGHT')


class AAT_PT_attach(_Section, Panel):
    bl_idname = "AAT_PT_attach"
    bl_parent_id = "AAT_PT_clothing"
    bl_label = "Attach & Merge Parts"
    bl_order = 0

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        layout.label(text="Heads, outfits and other parts", icon='INFO')
        col = layout.column()
        col.scale_y = 1.2
        col.operator("aat.import_model", text="Import Attachment", icon='IMPORT')

        box = layout.box()
        box.label(text="Has Its Own Armature", icon='OUTLINER_OB_ARMATURE')
        box.label(text="Heads or rigged clothing sold separately")
        col = _settings_column(box)
        col.prop(settings, "attach_incoming_armature", text="Armature")
        _toggle_column(box).prop(settings, "attach_keep_new_bones")
        col = box.column()
        col.scale_y = 1.3
        col.operator("aat.merge_armatures", icon='GROUP_BONE')

        box = layout.box()
        box.label(text="Mesh Only, No Armature", icon='MOD_CLOTH')
        box.label(text="Uses the body mesh set above")
        _selection_hint(box)
        _toggle_column(box).prop(settings, "attach_meshonly_fit")
        col = box.column()
        col.scale_y = 1.3
        col.operator("aat.attach_mesh_only", icon='CHECKMARK')


class AAT_PT_shapekeys(_Section, Panel):
    bl_idname = "AAT_PT_shapekeys"
    bl_label = "Shape Keys"
    bl_order = 4

    def draw(self, context: Context) -> None:
        layout = self.layout
        obj = context.active_object
        if obj is not None and common.has_shapekeys(obj):
            count = len(obj.data.shape_keys.key_blocks) - 1
            layout.label(text=f"{obj.name}: {count} shape keys", icon='SHAPEKEY_DATA')
        else:
            layout.label(text="Active object has no shape keys", icon='INFO')

        col = layout.column(align=True)
        col.operator("aat.shapekey_to_basis", icon='SHAPEKEY_DATA')
        col.operator("aat.smooth_shapekeys", icon='MOD_SMOOTH')
        col.operator("aat.remove_empty_shapekeys", icon='TRASH')
        col.operator("aat.sort_shapekeys", icon='SORTALPHA')


class AAT_PT_blendshape(_Section, Panel):
    bl_idname = "AAT_PT_blendshape"
    bl_parent_id = "AAT_PT_shapekeys"
    bl_label = "Transfer Between Meshes"
    bl_order = 0

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        col = _settings_column(layout)
        col.prop(settings, "bst_source")
        col.prop(settings, "bst_target")

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


class AAT_PT_blendshape_sync(_Section, Panel):
    bl_idname = "AAT_PT_blendshape_sync"
    bl_parent_id = "AAT_PT_shapekeys"
    bl_label = "Sync Across Meshes"
    bl_order = 1

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        layout.label(text="Shape key list comes from the active object", icon='INFO')
        col = _settings_column(layout)
        col.prop(settings, "sync_auxiliary")
        col.prop(settings, "sync_shapekey")

        col = layout.column(align=True)
        col.operator("aat.sync_blendshape", icon='UV_SYNC_SELECT')
        col.operator("aat.sculpt_shapekey_mode", icon='SCULPTMODE_HLT')
        col.operator("aat.reset_synced_shapekeys", icon='LOOP_BACK')


class AAT_PT_shapekey_batch(_Section, Panel):
    bl_idname = "AAT_PT_shapekey_batch"
    bl_parent_id = "AAT_PT_shapekeys"
    bl_label = "Batch Creator"
    bl_order = 2

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        layout.label(text="Comma-separated, e.g. 'Blink, Smile, Angry'")
        layout.prop(settings, "batch_shapekey_names", text="")
        col = layout.column()
        col.scale_y = 1.2
        col.operator("aat.batch_create_shapekeys", icon='ADD')

        obj = context.active_object
        if obj is None or not common.has_shapekeys(obj):
            layout.label(text="Active object has no shape keys yet", icon='INFO')
            return

        key_blocks = obj.data.shape_keys.key_blocks
        names = [kb.name for kb in key_blocks[1:]]
        page_size = shapekey_ops.PAGE_SIZE
        max_page = max((len(names) - 1) // page_size, 0)
        page = min(settings.batch_page, max_page)
        start = page * page_size

        box = layout.box()
        row = box.row(align=True)
        row.operator("aat.batch_page_prev", text="", icon='TRIA_LEFT')
        row.label(text=f"{len(names)} keys | page {page + 1} of {max_page + 1}")
        row.operator("aat.batch_page_next", text="", icon='TRIA_RIGHT')

        col = box.column(align=True)
        for offset, name in enumerate(names[start:start + page_size]):
            index = start + offset + 1
            op = col.operator(
                "aat.batch_jump_to_shapekey",
                text=name,
                depress=(obj.active_shape_key_index == index),
            )
            op.index = index


class AAT_PT_texturing(_Section, Panel):
    bl_idname = "AAT_PT_texturing"
    bl_label = "Substance Painter & Unity"
    bl_order = 5

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        meshes = texturing_ops.target_meshes(context)
        materials = texturing_ops.collect_materials(meshes)
        if meshes:
            row = layout.row(align=True)
            row.label(text=_count(len(meshes), "mesh", "meshes"), icon='MESH_DATA')
            row.label(text=_count(len(materials), "texture set"), icon='TEXTURE')
        _selection_hint(layout, "Selection, or the whole model")

        box = layout.box()
        box.label(text="1. Send to Painter", icon='EXPORT')
        col = _toggle_column(box)
        col.prop(settings, "painter_reset_pose")
        col.prop(settings, "painter_triangulate")
        col.prop(settings, "painter_include_armature")
        col = box.column(align=True)
        col.scale_y = 1.3
        col.operator("aat.prep_for_painter", icon='CHECKMARK')
        col.operator("aat.export_for_painter", icon='EXPORT')

        no_uvs = [m.name for m in meshes if not m.data.uv_layers]
        if no_uvs:
            warn = box.box()
            warn.label(text=f"{len(no_uvs)} meshes have no UVs", icon='ERROR')
            for name in no_uvs[:3]:
                warn.label(text=name)

        box = layout.box()
        box.label(text="2. Bring the Textures Home", icon='IMPORT')
        col = box.column(align=True)
        col.scale_y = 1.3
        col.operator("aat.import_painted_textures", icon='NODE_TEXTURE')
        col.operator("aat.fix_colorspaces", icon='COLOR')


class AAT_PT_decimation(_Section, Panel):
    bl_idname = "AAT_PT_decimation"
    bl_label = "Decimation & Retopology"
    bl_order = 6

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

        box = layout.box()
        box.label(text="Triangle Budget", icon='MOD_DECIM')
        box.row(align=True).prop(settings, "decimate_mode", expand=True)
        _settings_column(box).prop(settings, "decimate_max_tris")
        _toggle_column(box).prop(settings, "decimate_remove_doubles")
        col = box.column()
        col.scale_y = 1.3
        col.operator("aat.decimate", icon='MOD_DECIM')

        box = layout.box()
        box.label(text="Quad Remesh", icon='MOD_REMESH')
        box.label(text="QuadriFlow, on the selected meshes")
        box.row(align=True).prop(settings, "remesh_mode", expand=True)
        col = _settings_column(box)
        if settings.remesh_mode == 'RATIO':
            col.prop(settings, "remesh_ratio")
        else:
            col.prop(settings, "remesh_target_faces")
        col = _toggle_column(box)
        col.prop(settings, "remesh_symmetry")
        col.prop(settings, "remesh_preserve_boundary")
        col.prop(settings, "remesh_preserve_sharp")
        col.prop(settings, "remesh_smooth_normals")
        col.separator()
        col.prop(settings, "remesh_transfer_weights")
        col.prop(settings, "remesh_force_shapekeys")
        if any(
            common.has_shapekeys(obj)
            for obj in context.selected_objects
            if obj.type == 'MESH'
        ):
            warn = box.box()
            warn.label(text="Selection has shape keys", icon='ERROR')
            warn.label(text="A remesh cannot keep them")
        col = box.column()
        col.scale_y = 1.3
        col.operator("aat.quad_remesh", icon='MOD_REMESH')


def _rank_icon(rank: str) -> str:
    return 'CHECKMARK' if rank in ('EXCELLENT', 'GOOD', 'MEDIUM') else 'CANCEL'


class AAT_PT_avatar_analyzer(_Section, Panel):
    bl_idname = "AAT_PT_avatar_analyzer"
    bl_label = "Avatar Analyzer"
    bl_order = 7

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        layout.label(text="Scores against VRChat's performance ranks", icon='INFO')
        col = _settings_column(layout)
        col.prop(settings, "analyzer_armature")
        col.prop(settings, "analyzer_platform")
        col = layout.column(align=True)
        col.scale_y = 1.3
        col.operator("aat.analyze_avatar", icon='VIEWZOOM')
        col.operator("aat.export_analysis_report", text="Export Report JSON", icon='EXPORT')


class AAT_PT_analyzer_results(_BasePanel, Panel):
    bl_idname = "AAT_PT_analyzer_results"
    bl_parent_id = "AAT_PT_avatar_analyzer"
    bl_label = "Results"
    bl_order = 0

    def draw(self, context: Context) -> None:
        layout = self.layout
        result = avatar_analyzer.get_last_result()
        if result is None:
            layout.label(text="Click Analyze Avatar to see results", icon='INFO')
        else:
            box = layout.box()
            box.label(
                text=f"{result.overall_rank.title()} | {round(result.score)}/100",
                icon=_rank_icon(result.overall_rank),
            )
            box.label(text=result.avatar_name, icon='ARMATURE_DATA')
            box.label(text=f"Platform: {result.platform}")

            col = layout.column(align=True)
            for category in result.categories:
                row = col.row(align=True)
                row.label(text=category.label)
                row.label(text=f"{category.value:,.0f}")
                row.label(text=category.rank.title(), icon=_rank_icon(category.rank))
            col.separator()
            sub = col.column(align=True)
            sub.scale_y = 0.8
            for line in _wrap(
                f"Blend Shapes: {result.blendshape_count:,} (informational, "
                "not an official VRChat limit)", 42
            ):
                sub.label(text=line)

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


class AAT_PT_analyzer_tools(_Section, Panel):
    bl_idname = "AAT_PT_analyzer_tools"
    bl_parent_id = "AAT_PT_avatar_analyzer"
    bl_label = "Creator Tools"
    bl_order = 1

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        _settings_column(layout).prop(settings, "analyzer_max_texture")
        col = _toggle_column(layout)
        col.prop(settings, "analyzer_force_pot")
        col.prop(settings, "analyzer_auto_decimate")

        col = layout.column(align=True)
        col.operator("aat.optimize_textures", text="Texture Optimizer", icon='TEXTURE')
        col.operator("aat.toggle_mesh_heatmap", text="Mesh Heatmap", icon='MOD_TRIANGULATE')
        col.separator()
        col.operator("aat.auto_fix_avatar", icon='TOOL_SETTINGS')
        col.operator("aat.undo_auto_fix_session", text="Undo Auto Fix Session", icon='LOOP_BACK')
        col.operator("aat.restore_texture_backup", icon='FILE_REFRESH')
        col.separator()
        col.operator("aat.batch_report_scene", icon='PRESET')


class AAT_PT_mesh_materials(_Section, Panel):
    bl_idname = "AAT_PT_mesh_materials"
    bl_label = "Mesh & Materials"
    bl_order = 8

    def draw(self, context: Context) -> None:
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Mesh")
        col.operator("aat.join_meshes", icon='OBJECT_DATA')
        col.operator("aat.separate_by_materials", icon='MATERIAL')
        col.operator("aat.separate_loose_parts", icon='MOD_EXPLODE')
        col.operator("aat.remove_doubles", icon='AUTOMERGE_ON')

        layout.separator()
        col = layout.column(align=True)
        col.label(text="Materials")
        col.operator("aat.merge_duplicate_materials", icon='MATERIAL_DATA')
        col.operator("aat.remove_unused_material_slots", icon='NODE_MATERIAL')


class AAT_PT_align_tools(_Section, Panel):
    bl_idname = "AAT_PT_align_tools"
    bl_parent_id = "AAT_PT_mesh_materials"
    bl_label = "Align Tools"
    bl_order = 0

    def draw(self, context: Context) -> None:
        layout = self.layout
        sub = layout.column(align=True)
        sub.scale_y = 0.8
        for line in _wrap(
            "Select a vertex or face on the active object in edit mode", 42
        ):
            sub.label(text=line)
        col = layout.column()
        col.scale_y = 1.2
        col.operator("aat.align_to_element", icon='SNAP_VERTEX')


class AAT_PT_vertex_tools(_Section, Panel):
    bl_idname = "AAT_PT_vertex_tools"
    bl_parent_id = "AAT_PT_mesh_materials"
    bl_label = "Vertex Error Selector"
    bl_order = 1

    def draw(self, context: Context) -> None:
        layout = self.layout
        settings = context.scene.aat
        sub = layout.column(align=True)
        sub.scale_y = 0.8
        for line in _wrap(
            "Paste Unity's unweighted vertex error; the numbers are picked out", 42
        ):
            sub.label(text=line)
        layout.prop(settings, "vertex_error_input", text="")
        col = layout.column()
        col.scale_y = 1.2
        col.operator("aat.select_error_vertices", icon='VERTEXSEL')


class AAT_PT_credits(_Section, Panel):
    bl_idname = "AAT_PT_credits"
    bl_label = "Info"
    bl_order = 9

    def draw(self, context: Context) -> None:
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Ari's Avatar Toolkit 1.6.1")
        col.label(text="Made for Blender 5.2 LTS")
        op = layout.operator("wm.url_open", text="GitHub", icon='URL')
        op.url = "https://github.com/yoisthatari/Ari-s-Avatar-Toolkit"


_CLASSES = (
    AAT_PT_main,
    AAT_PT_fix_options,
    AAT_PT_translation,
    AAT_PT_pose,
    AAT_PT_health,
    AAT_PT_weight_tools,
    AAT_PT_armature_tools,
    AAT_PT_visemes,
    AAT_PT_eye_tracking,
    AAT_PT_clothing,
    AAT_PT_attach,
    AAT_PT_shapekeys,
    AAT_PT_blendshape,
    AAT_PT_blendshape_sync,
    AAT_PT_shapekey_batch,
    AAT_PT_texturing,
    AAT_PT_decimation,
    AAT_PT_avatar_analyzer,
    AAT_PT_analyzer_results,
    AAT_PT_analyzer_tools,
    AAT_PT_mesh_materials,
    AAT_PT_align_tools,
    AAT_PT_vertex_tools,
    AAT_PT_credits,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
