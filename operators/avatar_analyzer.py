import json
import os
from dataclasses import dataclass

import bpy
import numpy as np
from bpy.props import StringProperty
from bpy.types import Context, Image, Object, Operator

from ..core import common
from ..core import vrchat_limits as limits

_BACKUP_PREFIX = "AAT_Backup_"
HEATMAP_GROUP = "AAT Heatmap"
DECIMATE_NAME = "AAT Auto Decimate"


@dataclass
class CategoryStat:
    key: str
    label: str
    value: float
    rank: str
    score: float
    thresholds: tuple


@dataclass
class AnalysisResult:
    avatar_name: str
    platform: str
    overall_rank: str
    score: float
    categories: list
    blendshape_count: int
    heavy_meshes: list
    texture_hotspots: list
    fix_first: list


_last_result = None
_last_batch = None


def get_last_result():
    return _last_result


def get_last_batch():
    return _last_batch


def _set_last_result(result) -> None:
    global _last_result
    _last_result = result


def _set_last_batch(results) -> None:
    global _last_batch
    _last_batch = results


def _resolve_armature(context: Context):
    settings = getattr(context.scene, "aat", None)
    if settings is not None:
        obj = bpy.data.objects.get(settings.analyzer_armature)
        if obj is not None and obj.type == 'ARMATURE':
            return obj
    return common.get_armature(context)


def _skinned_and_basic(meshes, armature: Object):
    skinned = []
    basic = []
    for mesh in meshes:
        if any(mod.type == 'ARMATURE' and mod.object == armature for mod in mesh.modifiers):
            skinned.append(mesh)
        else:
            basic.append(mesh)
    return skinned, basic


def _used_materials(meshes):
    materials = set()
    for mesh in meshes:
        for slot in mesh.material_slots:
            if slot.material:
                materials.add(slot.material)
    return materials


def _used_images(materials):
    images = set()
    for material in materials:
        if not material.node_tree:
            continue
        for node in material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                images.add(node.image)
    return images


def _image_mb(image: Image) -> float:
    width, height = image.size
    if width <= 0 or height <= 0:
        return 0.0
    channels = image.channels or 4
    return (width * height * channels * (4.0 / 3.0)) / (1024.0 * 1024.0)


def _blendshape_count(meshes) -> int:
    total = 0
    for mesh in meshes:
        if common.has_shapekeys(mesh):
            total += len(mesh.data.shape_keys.key_blocks) - 1
    return total


def analyze(context: Context, armature: Object, platform: str) -> AnalysisResult:
    thresholds = limits.LIMITS_BY_PLATFORM[platform]
    meshes = common.get_armature_meshes(context, armature)
    skinned, basic = _skinned_and_basic(meshes, armature)
    materials = _used_materials(meshes)
    images = _used_images(materials)

    raw_values = {
        "triangles": sum(common.triangle_count(m) for m in meshes),
        "materials": len(materials),
        "skinned_meshes": len(skinned),
        "basic_meshes": len(basic),
        "bones": len(armature.data.bones),
        "texture_mb": sum(_image_mb(img) for img in images),
    }

    categories = []
    for key, value in raw_values.items():
        category_thresholds = thresholds[key]
        rank, score = limits.category_score(value, category_thresholds)
        categories.append(CategoryStat(
            key=key,
            label=limits.CATEGORY_LABELS[key],
            value=value,
            rank=rank,
            score=score,
            thresholds=category_thresholds,
        ))

    overall_rank = limits.worst_rank([c.rank for c in categories])
    overall_score = sum(c.score for c in categories) / len(categories)

    heavy_meshes = sorted(
        ((m.name, common.triangle_count(m)) for m in meshes),
        key=lambda item: item[1],
        reverse=True,
    )[:5]

    texture_hotspots = sorted(
        ((img.name, f"{img.size[0]}x{img.size[1]}", _image_mb(img)) for img in images),
        key=lambda item: item[2],
        reverse=True,
    )[:5]

    bad = [c for c in categories if c.rank in ("POOR", "VERY_POOR")]
    bad.sort(key=lambda c: limits.RANK_ORDER.index(c.rank), reverse=True)
    fix_first = [limits.FIX_SUGGESTIONS[c.key] for c in bad[:3]]

    return AnalysisResult(
        avatar_name=armature.name,
        platform=platform,
        overall_rank=overall_rank,
        score=overall_score,
        categories=categories,
        blendshape_count=_blendshape_count(meshes),
        heavy_meshes=heavy_meshes,
        texture_hotspots=texture_hotspots,
        fix_first=fix_first,
    )


class AAT_OT_analyze_avatar(Operator):
    bl_idname = "aat.analyze_avatar"
    bl_label = "Analyze Avatar"
    bl_description = "Score the selected avatar against VRChat's performance rank thresholds"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return _resolve_armature(context) is not None

    def execute(self, context: Context):
        armature = _resolve_armature(context)
        if armature is None:
            self.report({'ERROR'}, "No armature found to analyze")
            return {'CANCELLED'}

        settings = context.scene.aat
        result = analyze(context, armature, settings.analyzer_platform)
        _set_last_result(result)
        self.report(
            {'INFO'},
            f"{armature.name}: {result.overall_rank.title()} ({round(result.score)}/100)",
        )
        return {'FINISHED'}


class AAT_OT_export_analysis_report(Operator):
    bl_idname = "aat.export_analysis_report"
    bl_label = "Export Report JSON"
    bl_description = "Analyze the selected avatar and save the results as a JSON report"
    bl_options = {'REGISTER'}

    filepath: StringProperty(subtype='FILE_PATH')
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})
    check_existing: bpy.props.BoolProperty(default=True, options={'HIDDEN'})

    @classmethod
    def poll(cls, context: Context) -> bool:
        return _resolve_armature(context) is not None

    def invoke(self, context: Context, event):
        if not self.filepath:
            armature = _resolve_armature(context)
            base = armature.name if armature else "avatar"
            blend = bpy.data.filepath
            directory = os.path.dirname(blend) if blend else ""
            self.filepath = os.path.join(directory, f"{base}_report.json")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context: Context):
        armature = _resolve_armature(context)
        if armature is None:
            self.report({'ERROR'}, "No armature found to analyze")
            return {'CANCELLED'}
        if not self.filepath:
            self.report({'ERROR'}, "No file path given")
            return {'CANCELLED'}

        settings = context.scene.aat
        result = analyze(context, armature, settings.analyzer_platform)
        _set_last_result(result)

        data = {
            "avatar": result.avatar_name,
            "platform": result.platform,
            "overall_rank": result.overall_rank,
            "score": round(result.score, 1),
            "categories": {
                c.key: {
                    "value": c.value,
                    "rank": c.rank,
                    "score": round(c.score, 1),
                    "thresholds": list(c.thresholds),
                }
                for c in result.categories
            },
            "blendshape_count": result.blendshape_count,
            "heavy_meshes": [
                {"name": name, "triangles": tris} for name, tris in result.heavy_meshes
            ],
            "texture_hotspots": [
                {"name": name, "size": size, "mb": round(mb, 2)}
                for name, size, mb in result.texture_hotspots
            ],
            "fix_first": result.fix_first,
        }

        with open(self.filepath, "w", encoding="utf-8") as report_file:
            json.dump(data, report_file, indent=2)

        self.report({'INFO'}, f"Saved report to {os.path.basename(self.filepath)}")
        return {'FINISHED'}


class AAT_OT_batch_report_scene(Operator):
    bl_idname = "aat.batch_report_scene"
    bl_label = "Batch Report (Scene)"
    bl_description = "Analyze every armature in the scene against VRChat's performance ranks"
    bl_options = {'REGISTER'}

    def execute(self, context: Context):
        settings = context.scene.aat
        armatures = [obj for obj in context.scene.objects if obj.type == 'ARMATURE']
        if not armatures:
            self.report({'ERROR'}, "No armatures in the scene")
            return {'CANCELLED'}

        results = [analyze(context, armature, settings.analyzer_platform) for armature in armatures]
        _set_last_batch(results)
        self.report({'INFO'}, f"Analyzed {len(results)} avatars")
        return {'FINISHED'}


def _pot_floor(value: int) -> int:
    if value <= 0:
        return value
    return 1 << (value.bit_length() - 1)


def _backup_image(image: Image) -> None:
    backup_name = _BACKUP_PREFIX + image.name
    if backup_name in bpy.data.images:
        return
    backup = image.copy()
    backup.name = backup_name
    backup.use_fake_user = True


def _optimize_images(images, max_dim: int, force_pot: bool) -> int:
    resized = 0
    for image in images:
        width, height = image.size
        if width <= 0 or height <= 0:
            continue
        target_w = min(width, max_dim)
        target_h = min(height, max_dim)
        if force_pot:
            target_w = _pot_floor(target_w)
            target_h = _pot_floor(target_h)
        if (target_w, target_h) == (width, height) or target_w <= 0 or target_h <= 0:
            continue
        _backup_image(image)
        image.scale(target_w, target_h)
        resized += 1
    return resized


class AAT_OT_optimize_textures(Operator):
    bl_idname = "aat.optimize_textures"
    bl_label = "Texture Optimizer"
    bl_description = (
        "Resize the avatar's textures down to the Max Texture setting, backing up "
        "the originals so they can be restored"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return _resolve_armature(context) is not None

    def execute(self, context: Context):
        armature = _resolve_armature(context)
        settings = context.scene.aat
        meshes = common.get_armature_meshes(context, armature)
        images = _used_images(_used_materials(meshes))
        if not images:
            self.report({'WARNING'}, "No textures found on this avatar")
            return {'CANCELLED'}

        resized = _optimize_images(images, int(settings.analyzer_max_texture), settings.analyzer_force_pot)
        if resized == 0:
            self.report({'INFO'}, "All textures are already within the target size")
            return {'FINISHED'}
        self.report({'INFO'}, f"Resized {resized} textures")
        return {'FINISHED'}


def _add_auto_decimate(context: Context, meshes, platform: str) -> int:
    target = limits.LIMITS_BY_PLATFORM[platform]["triangles"][1]
    candidates = [
        m for m in meshes
        if not common.has_shapekeys(m) and m.modifiers.get(DECIMATE_NAME) is None
    ]
    total = sum(common.triangle_count(m) for m in meshes)
    if total <= target or not candidates:
        return 0

    decimatable = sum(common.triangle_count(m) for m in candidates)
    protected = total - decimatable
    budget = target - protected
    if budget <= 0 or decimatable <= 0:
        return 0

    ratio = max(min(budget / decimatable, 1.0), 0.005)
    added = 0
    for mesh in candidates:
        if common.triangle_count(mesh) == 0:
            continue
        modifier = mesh.modifiers.new(name=DECIMATE_NAME, type='DECIMATE')
        modifier.ratio = ratio
        modifier.use_collapse_triangulate = True
        with context.temp_override(object=mesh, active_object=mesh, selected_objects=[mesh]):
            bpy.ops.object.modifier_move_to_index(modifier=modifier.name, index=0)
        added += 1
    return added


class AAT_OT_auto_fix_avatar(Operator):
    bl_idname = "aat.auto_fix_avatar"
    bl_label = "Auto Fix Avatar"
    bl_description = (
        "One-click optimization pass: resizes textures to the Max Texture setting "
        "and, if enabled, adds non-destructive Decimate modifiers to heavy meshes"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return _resolve_armature(context) is not None

    def execute(self, context: Context):
        armature = _resolve_armature(context)
        settings = context.scene.aat
        common.ensure_object_mode(context)
        meshes = common.get_armature_meshes(context, armature)

        changes = []
        images = _used_images(_used_materials(meshes))
        resized = _optimize_images(images, int(settings.analyzer_max_texture), settings.analyzer_force_pot)
        if resized:
            changes.append(f"resized {resized} textures")

        if settings.analyzer_auto_decimate:
            added = _add_auto_decimate(context, meshes, settings.analyzer_platform)
            if added:
                changes.append(f"added decimate modifiers to {added} meshes")

        if not changes:
            self.report({'INFO'}, "Nothing to fix, the avatar is already within target")
            return {'FINISHED'}

        self.report({'INFO'}, "Auto Fix: " + ", ".join(changes))
        return {'FINISHED'}


class AAT_OT_undo_auto_fix_session(Operator):
    bl_idname = "aat.undo_auto_fix_session"
    bl_label = "Undo Auto Fix Session"
    bl_description = "Undo the last action. Use this right after Auto Fix Avatar"
    bl_options = {'REGISTER'}

    def execute(self, context: Context):
        bpy.ops.ed.undo()
        self.report({'INFO'}, "Undone")
        return {'FINISHED'}


def _restore_image(original: Image, backup: Image) -> None:
    count = len(backup.pixels)
    buffer = np.empty(count, dtype=np.float32)
    backup.pixels.foreach_get(buffer)
    original.scale(backup.size[0], backup.size[1])
    original.pixels.foreach_set(buffer)
    original.update()


class AAT_OT_restore_texture_backup(Operator):
    bl_idname = "aat.restore_texture_backup"
    bl_label = "Restore Texture Size Backup"
    bl_description = (
        "Restore textures resized by Texture Optimizer or Auto Fix Avatar back to "
        "their original size"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return any(image.name.startswith(_BACKUP_PREFIX) for image in bpy.data.images)

    def execute(self, context: Context):
        restored = 0
        for backup in list(bpy.data.images):
            if not backup.name.startswith(_BACKUP_PREFIX):
                continue
            original_name = backup.name[len(_BACKUP_PREFIX):]
            original = bpy.data.images.get(original_name)
            if original is not None:
                _restore_image(original, backup)
                restored += 1
            bpy.data.images.remove(backup)

        if restored == 0:
            self.report({'WARNING'}, "No texture backups found")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Restored {restored} textures to their original size")
        return {'FINISHED'}


def _write_heatmap_group(obj: Object) -> None:
    mesh = obj.data
    poly_count = len(mesh.polygons)
    vert_count = len(mesh.vertices)
    if poly_count == 0 or vert_count == 0:
        return

    areas = np.empty(poly_count, dtype=np.float64)
    mesh.polygons.foreach_get("area", areas)
    density = 1.0 / np.maximum(areas, 1e-8)

    loop_total = np.empty(poly_count, dtype=np.int64)
    mesh.polygons.foreach_get("loop_total", loop_total)
    loop_vert = np.empty(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("vertex_index", loop_vert)
    poly_of_loop = np.repeat(np.arange(poly_count), loop_total)

    vert_sum = np.zeros(vert_count, dtype=np.float64)
    vert_hits = np.zeros(vert_count, dtype=np.float64)
    np.add.at(vert_sum, loop_vert, density[poly_of_loop])
    np.add.at(vert_hits, loop_vert, 1.0)
    vert_hits[vert_hits == 0.0] = 1.0
    heat = vert_sum / vert_hits

    low, high = heat.min(), heat.max()
    if high > low:
        heat = (heat - low) / (high - low)
    else:
        heat = np.zeros_like(heat)

    group = obj.vertex_groups.get(HEATMAP_GROUP)
    if group is None:
        group = obj.vertex_groups.new(name=HEATMAP_GROUP)
    for index, weight in enumerate(heat):
        group.add([index], float(weight), 'REPLACE')


class AAT_OT_toggle_mesh_heatmap(Operator):
    bl_idname = "aat.toggle_mesh_heatmap"
    bl_label = "Mesh Heatmap"
    bl_description = (
        "Paint a red/blue overlay on the active mesh showing where geometry is "
        "densest, as a guide for decimation. Click again to finish"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context: Context):
        obj = context.active_object
        active_group = obj.vertex_groups.active
        if (
            context.mode == 'PAINT_WEIGHT'
            and active_group is not None
            and active_group.name == HEATMAP_GROUP
        ):
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'FINISHED'}

        common.ensure_object_mode(context)
        _write_heatmap_group(obj)
        group = obj.vertex_groups.get(HEATMAP_GROUP)
        obj.vertex_groups.active_index = group.index
        common.switch_mode(context, obj, 'WEIGHT_PAINT')
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_analyze_avatar,
    AAT_OT_export_analysis_report,
    AAT_OT_batch_report_scene,
    AAT_OT_optimize_textures,
    AAT_OT_auto_fix_avatar,
    AAT_OT_undo_auto_fix_session,
    AAT_OT_restore_texture_backup,
    AAT_OT_toggle_mesh_heatmap,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
