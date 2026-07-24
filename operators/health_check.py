from dataclasses import dataclass

import bmesh
import bpy
from bpy.types import Context, Object, Operator
from mathutils.kdtree import KDTree

from ..core import bone_names, common

_HUMANOID_REQUIRED = (
    "Hips", "Spine", "Head",
    "Left arm", "Left elbow", "Left wrist",
    "Right arm", "Right elbow", "Right wrist",
    "Left leg", "Left knee", "Left ankle",
    "Right leg", "Right knee", "Right ankle",
)

UNITY_MAX_INFLUENCES = 4


@dataclass
class Issue:
    level: str
    label: str
    detail: str
    fix: str = ""


@dataclass
class HealthReport:
    avatar_name: str
    issues: list
    passed: list


_last_report = None


def get_last_report():
    return _last_report


def _set_last_report(report) -> None:
    global _last_report
    _last_report = report


def bone_group_indices(mesh: Object, armature: Object) -> set:
    if armature is None:
        return {vg.index for vg in mesh.vertex_groups}
    bones = armature.data.bones
    return {vg.index for vg in mesh.vertex_groups if vg.name in bones}


def weight_stats(mesh: Object, armature: Object, threshold: float):
    bone_indices = bone_group_indices(mesh, armature)
    unweighted = 0
    over_limit = 0
    unnormalized = 0
    peak = 0
    for vertex in mesh.data.vertices:
        total = 0.0
        count = 0
        for entry in vertex.groups:
            if entry.group in bone_indices and entry.weight > threshold:
                total += entry.weight
                count += 1
        if count == 0:
            unweighted += 1
            continue
        if count > UNITY_MAX_INFLUENCES:
            over_limit += 1
        if count > peak:
            peak = count
        if abs(total - 1.0) > 0.01:
            unnormalized += 1
    return unweighted, over_limit, unnormalized, peak


def geometry_stats(mesh: Object):
    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    loose = sum(1 for v in bm.verts if not v.link_faces)
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
    degenerate = sum(1 for f in bm.faces if f.calc_area() < 1e-9)
    bm.free()
    return loose, non_manifold, ngons, degenerate


def _transform_is_clean(obj: Object) -> bool:
    scale_ok = all(abs(v - 1.0) < 1e-4 for v in obj.scale)
    rotation_ok = all(abs(v) < 1e-4 for v in obj.rotation_euler)
    return scale_ok and rotation_ok


def run_health_check(context: Context, armature: Object) -> HealthReport:
    settings = context.scene.aat
    threshold = settings.merge_weights_threshold
    meshes = common.get_armature_meshes(context, armature)
    issues: list = []
    passed: list = []

    if not meshes:
        issues.append(Issue(
            'ERROR', "No meshes bound",
            "The armature has no meshes attached to it",
        ))
        return HealthReport(armature.name, issues, passed)

    resolved: dict[str, str] = {}
    renameable = 0
    for bone in armature.data.bones:
        resolved.setdefault(bone.name, bone.name)
        standard = bone_names.standard_bone_name(bone.name)
        if standard:
            resolved.setdefault(standard, bone.name)
            if standard != bone.name:
                renameable += 1

    missing = [name for name in _HUMANOID_REQUIRED if name not in resolved]
    if missing:
        issues.append(Issue(
            'ERROR', f"{len(missing)} humanoid bones missing",
            "Unity needs these for a humanoid rig: " + ", ".join(missing[:6])
            + ("..." if len(missing) > 6 else ""),
            "aat.fix_model",
        ))
    else:
        passed.append("Humanoid bone set is complete")

    if renameable:
        issues.append(Issue(
            'INFO', f"{renameable} bones use non-standard names",
            "Everything Unity needs is here, but names like 'Arm_L' are not "
            "the standard scheme yet. Fix Model renames them for you",
            "aat.fix_model",
        ))

    total_unweighted = 0
    total_over = 0
    total_unnormalized = 0
    peak_influences = 0
    for mesh in meshes:
        unweighted, over, unnormalized, peak = weight_stats(mesh, armature, threshold)
        total_unweighted += unweighted
        total_over += over
        total_unnormalized += unnormalized
        peak_influences = max(peak_influences, peak)

    if total_unweighted:
        issues.append(Issue(
            'ERROR', f"{total_unweighted:,} unweighted vertices",
            "Unity refuses to import these and VRChat will reject the avatar",
            "aat.fix_unweighted_vertices",
        ))
    else:
        passed.append("Every vertex carries a bone weight")

    if total_over:
        issues.append(Issue(
            'WARNING', f"{total_over:,} vertices over {UNITY_MAX_INFLUENCES} bones",
            f"Peak is {peak_influences} bones on one vertex. Unity keeps only the "
            f"strongest {UNITY_MAX_INFLUENCES}, so deformation will differ from Blender",
            "aat.limit_bone_influences",
        ))
    else:
        passed.append(f"No vertex exceeds {UNITY_MAX_INFLUENCES} bone influences")

    if total_unnormalized:
        issues.append(Issue(
            'WARNING', f"{total_unnormalized:,} vertices with unnormalized weights",
            "Weights that do not add up to 1.0 make limbs shrink or drift when posed",
            "aat.normalize_weights",
        ))
    else:
        passed.append("Bone weights are normalized")

    dirty = [obj.name for obj in [armature, *meshes] if not _transform_is_clean(obj)]
    if dirty:
        issues.append(Issue(
            'ERROR', f"{len(dirty)} objects have unapplied transforms",
            "Rotation or scale is not applied, which Unity imports at the wrong "
            "size or orientation: " + ", ".join(dirty[:3]),
            "aat.fix_model",
        ))
    else:
        passed.append("Transforms are applied")

    no_uvs = [m.name for m in meshes if not m.data.uv_layers]
    if no_uvs:
        issues.append(Issue(
            'WARNING', f"{len(no_uvs)} meshes have no UV map",
            "These cannot be textured or painted: " + ", ".join(no_uvs[:3]),
        ))
    else:
        passed.append("Every mesh has UVs")

    loose_total = 0
    manifold_total = 0
    ngon_total = 0
    degenerate_total = 0
    for mesh in meshes:
        loose, non_manifold, ngons, degenerate = geometry_stats(mesh)
        loose_total += loose
        manifold_total += non_manifold
        ngon_total += ngons
        degenerate_total += degenerate

    if loose_total:
        issues.append(Issue(
            'WARNING', f"{loose_total:,} loose vertices",
            "Vertices not attached to any face. They export as junk and often "
            "cause the unweighted vertex error",
            "aat.remove_loose_geometry",
        ))
    else:
        passed.append("No loose vertices")

    if degenerate_total:
        issues.append(Issue(
            'WARNING', f"{degenerate_total:,} zero-area faces",
            "Degenerate faces break normal maps and confuse remeshers",
            "aat.remove_loose_geometry",
        ))

    if manifold_total:
        issues.append(Issue(
            'INFO', f"{manifold_total:,} non-manifold edges",
            "Fine for rendering, but Quad Remesh and some bakes need clean geometry",
        ))
    else:
        passed.append("Geometry is manifold")

    if ngon_total:
        issues.append(Issue(
            'INFO', f"{ngon_total:,} ngons",
            "Faces with more than 4 sides. Unity triangulates them anyway, but "
            "they can shade oddly",
        ))

    empty_slots = sum(
        1 for m in meshes for slot in m.material_slots if slot.material is None
    )
    if empty_slots:
        issues.append(Issue(
            'WARNING', f"{empty_slots} empty material slots",
            "Empty slots become missing materials in Unity",
            "aat.remove_unused_material_slots",
        ))
    else:
        passed.append("No empty material slots")

    tris = sum(common.triangle_count(m) for m in meshes)
    if tris > 70000:
        issues.append(Issue(
            'WARNING', f"{tris:,} triangles",
            "Above VRChat's 70,000 triangle guidance for a Good rank",
            "aat.decimate",
        ))
    else:
        passed.append(f"{tris:,} triangles is within budget")

    if len(armature.data.bones) > 256:
        issues.append(Issue(
            'INFO', f"{len(armature.data.bones)} bones",
            "A high bone count costs performance rank in VRChat",
            "aat.remove_zero_weight_bones",
        ))

    return HealthReport(armature.name, issues, passed)


class AAT_OT_health_check(Operator):
    bl_idname = "aat.health_check"
    bl_label = "Check Avatar Health"
    bl_description = (
        "Give your avatar a full check-up before it goes to Unity. Looks for "
        "unweighted vertices, vertices riding too many bones, unnormalized "
        "weights, unapplied transforms, missing humanoid bones, loose and "
        "degenerate geometry, missing UVs and more, with a one-click fix beside "
        "everything it can mend"
    )
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def execute(self, context: Context):
        armature = common.get_armature(context)
        common.ensure_object_mode(context)
        report = run_health_check(context, armature)
        _set_last_report(report)

        errors = sum(1 for i in report.issues if i.level == 'ERROR')
        warnings = sum(1 for i in report.issues if i.level == 'WARNING')
        problem_word = "problem" if errors == 1 else "problems"
        look_word = "thing" if warnings == 1 else "things"
        if errors:
            self.report(
                {'WARNING'},
                f"{errors} {problem_word} to fix and {warnings} {look_word} worth a look",
            )
        elif warnings:
            self.report({'INFO'}, f"No blockers, but {warnings} {look_word} worth a look")
        else:
            self.report({'INFO'}, "Your avatar looks lovely, everything passed")
        return {'FINISHED'}


def _target_meshes(context: Context):
    armature = common.get_armature(context)
    selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
    if selected:
        return armature, selected
    if armature is None:
        return None, []
    return armature, common.get_armature_meshes(context, armature)


class AAT_OT_limit_bone_influences(Operator):
    bl_idname = "aat.limit_bone_influences"
    bl_label = "Limit Bone Influences"
    bl_description = (
        "Keep only the strongest few bones on each vertex and renormalize what "
        "is left, so Blender deforms exactly the way Unity will. Non-bone "
        "vertex groups are left completely alone"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def execute(self, context: Context):
        settings = context.scene.aat
        armature, meshes = _target_meshes(context)
        if not meshes:
            self.report({'ERROR'}, "No meshes to work on")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        limit = settings.health_max_influences
        changed = 0
        for mesh in meshes:
            bone_indices = bone_group_indices(mesh, armature)
            groups = {vg.index: vg for vg in mesh.vertex_groups}
            for vertex in mesh.data.vertices:
                entries = [
                    (e.group, e.weight) for e in vertex.groups
                    if e.group in bone_indices and e.weight > 0.0
                ]
                if len(entries) <= limit:
                    continue
                entries.sort(key=lambda item: item[1], reverse=True)
                for index, _weight in entries[limit:]:
                    groups[index].remove([vertex.index])
                kept = entries[:limit]
                total = sum(weight for _index, weight in kept)
                if total > 0.0:
                    for index, weight in kept:
                        groups[index].add([vertex.index], weight / total, 'REPLACE')
                changed += 1

        if changed == 0:
            self.report({'INFO'}, f"Every vertex was already within {limit} bones")
            return {'FINISHED'}
        self.report({'INFO'}, f"Trimmed {changed:,} vertices down to {limit} bones")
        return {'FINISHED'}


class AAT_OT_normalize_weights(Operator):
    bl_idname = "aat.normalize_weights"
    bl_label = "Normalize Weights"
    bl_description = (
        "Make each vertex's bone weights add up to exactly 1.0, so limbs stop "
        "shrinking or drifting when the avatar moves"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def execute(self, context: Context):
        armature, meshes = _target_meshes(context)
        if not meshes:
            self.report({'ERROR'}, "No meshes to work on")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        changed = 0
        for mesh in meshes:
            bone_indices = bone_group_indices(mesh, armature)
            groups = {vg.index: vg for vg in mesh.vertex_groups}
            for vertex in mesh.data.vertices:
                entries = [
                    (e.group, e.weight) for e in vertex.groups
                    if e.group in bone_indices and e.weight > 0.0
                ]
                total = sum(weight for _index, weight in entries)
                if total <= 0.0 or abs(total - 1.0) <= 1e-4:
                    continue
                for index, weight in entries:
                    groups[index].add([vertex.index], weight / total, 'REPLACE')
                changed += 1

        self.report({'INFO'}, f"Normalized {changed:,} vertices")
        return {'FINISHED'}


class AAT_OT_fix_unweighted_vertices(Operator):
    bl_idname = "aat.fix_unweighted_vertices"
    bl_label = "Fix Unweighted Vertices"
    bl_description = (
        "Find vertices with no bone weight at all and borrow the weights of "
        "their nearest weighted neighbour, which clears Unity's unweighted "
        "vertex error"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def execute(self, context: Context):
        settings = context.scene.aat
        armature, meshes = _target_meshes(context)
        if not meshes:
            self.report({'ERROR'}, "No meshes to work on")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        threshold = settings.merge_weights_threshold
        fixed = 0
        hopeless: list[str] = []

        for mesh in meshes:
            bone_indices = bone_group_indices(mesh, armature)
            groups = {vg.index: vg for vg in mesh.vertex_groups}
            weighted: dict[int, list] = {}
            unweighted: list[int] = []
            for vertex in mesh.data.vertices:
                entries = [
                    (e.group, e.weight) for e in vertex.groups
                    if e.group in bone_indices and e.weight > threshold
                ]
                if entries:
                    weighted[vertex.index] = entries
                else:
                    unweighted.append(vertex.index)

            if not unweighted:
                continue
            if not weighted:
                hopeless.append(mesh.name)
                continue

            tree = KDTree(len(weighted))
            for index in weighted:
                tree.insert(mesh.data.vertices[index].co, index)
            tree.balance()

            for index in unweighted:
                _co, nearest, _distance = tree.find(mesh.data.vertices[index].co)
                for group_index, weight in weighted[nearest]:
                    groups[group_index].add([index], weight, 'REPLACE')
                fixed += 1

        if hopeless:
            self.report(
                {'WARNING'},
                f"Fixed {fixed:,} vertices, but these meshes have no weights at "
                f"all to borrow from: {', '.join(hopeless[:3])}. Use Attach Mesh "
                "or Transfer Weights on them",
            )
            return {'FINISHED'}
        if fixed == 0:
            self.report({'INFO'}, "Every vertex already had a weight")
            return {'FINISHED'}
        self.report({'INFO'}, f"Gave {fixed:,} stranded vertices their weights back")
        return {'FINISHED'}


class AAT_OT_select_unweighted_vertices(Operator):
    bl_idname = "aat.select_unweighted_vertices"
    bl_label = "Select Unweighted"
    bl_description = (
        "Jump straight to the unweighted vertices in Edit Mode so you can see "
        "exactly where the problem is"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def execute(self, context: Context):
        settings = context.scene.aat
        armature, meshes = _target_meshes(context)
        if not meshes:
            self.report({'ERROR'}, "No meshes to work on")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        threshold = settings.merge_weights_threshold
        best = None
        best_indices: list[int] = []
        for mesh in meshes:
            bone_indices = bone_group_indices(mesh, armature)
            stranded = []
            for vertex in mesh.data.vertices:
                if not any(
                    e.group in bone_indices and e.weight > threshold
                    for e in vertex.groups
                ):
                    stranded.append(vertex.index)
            if len(stranded) > len(best_indices):
                best = mesh
                best_indices = stranded

        if best is None or not best_indices:
            self.report({'INFO'}, "No unweighted vertices, everything is bound")
            return {'CANCELLED'}

        data = best.data
        data.vertices.foreach_set("select", [False] * len(data.vertices))
        data.edges.foreach_set("select", [False] * len(data.edges))
        data.polygons.foreach_set("select", [False] * len(data.polygons))
        for index in best_indices:
            data.vertices[index].select = True
        data.update()

        common.switch_mode(context, best, 'EDIT')
        bpy.ops.mesh.select_mode(type='VERT')
        self.report(
            {'WARNING'},
            f"Selected {len(best_indices):,} unweighted vertices on '{best.name}'",
        )
        return {'FINISHED'}


class AAT_OT_remove_loose_geometry(Operator):
    bl_idname = "aat.remove_loose_geometry"
    bl_label = "Remove Loose Geometry"
    bl_description = (
        "Sweep away vertices and edges that belong to no face, plus faces with "
        "no area. These are the usual culprits behind stray unweighted vertices"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def execute(self, context: Context):
        _armature, meshes = _target_meshes(context)
        if not meshes:
            self.report({'ERROR'}, "No meshes to work on")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        removed = 0
        for mesh in meshes:
            bm = bmesh.new()
            bm.from_mesh(mesh.data)
            doomed_faces = [f for f in bm.faces if f.calc_area() < 1e-9]
            for face in doomed_faces:
                bm.faces.remove(face)
            bm.verts.ensure_lookup_table()
            doomed_verts = [v for v in bm.verts if not v.link_faces]
            for vertex in doomed_verts:
                bm.verts.remove(vertex)
            count = len(doomed_faces) + len(doomed_verts)
            if count:
                bm.to_mesh(mesh.data)
                mesh.data.update()
                removed += count
            bm.free()

        if removed == 0:
            self.report({'INFO'}, "Nothing loose to sweep up")
            return {'FINISHED'}
        self.report({'INFO'}, f"Swept away {removed:,} loose bits")
        return {'FINISHED'}


class AAT_OT_fix_all_weights(Operator):
    bl_idname = "aat.fix_all_weights"
    bl_label = "Fix Weights"
    bl_description = (
        "The whole weight spa in one click: give stranded vertices their weights "
        "back, trim vertices riding too many bones, then normalize everything so "
        "Blender and Unity agree"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def execute(self, context: Context):
        for operator in (
            bpy.ops.aat.fix_unweighted_vertices,
            bpy.ops.aat.limit_bone_influences,
            bpy.ops.aat.normalize_weights,
        ):
            result = operator()
            if 'CANCELLED' in result:
                return {'CANCELLED'}
        armature = common.get_armature(context)
        if armature is not None:
            _set_last_report(run_health_check(context, armature))
        self.report({'INFO'}, "Weights fixed, trimmed and normalized")
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_health_check,
    AAT_OT_limit_bone_influences,
    AAT_OT_normalize_weights,
    AAT_OT_fix_unweighted_vertices,
    AAT_OT_select_unweighted_vertices,
    AAT_OT_remove_loose_geometry,
    AAT_OT_fix_all_weights,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
