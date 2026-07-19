import math

import bpy
import numpy as np
from bpy.types import Context, Operator
from mathutils.bvhtree import BVHTree
from mathutils.interpolate import poly_3d_calc

from ..core import common


def _source_weight_matrix(source, group_names):
    lookup = {}
    for gi, name in enumerate(group_names):
        group = source.vertex_groups.get(name)
        if group is not None:
            lookup[group.index] = gi
    matrix = np.zeros((len(source.data.vertices), len(group_names)), dtype=np.float64)
    for vertex in source.data.vertices:
        for entry in vertex.groups:
            gi = lookup.get(entry.group)
            if gi is not None:
                matrix[vertex.index, gi] = entry.weight
    return matrix


class AAT_OT_transfer_weights(Operator):
    bl_idname = "aat.transfer_weights"
    bl_label = "Transfer Weights"
    bl_description = (
        "Transfer bone weights from the body to the selected meshes using "
        "confident surface matches plus diffusion inpainting for uncertain "
        "areas (armpits, between legs, chest), so no manual smoothing is needed"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        settings = getattr(context.scene, "aat", None)
        return settings is not None and settings.cloth_body_mesh != "NONE"

    def execute(self, context: Context):
        settings = context.scene.aat
        source = bpy.data.objects.get(settings.cloth_body_mesh)
        if source is None or source.type != 'MESH':
            self.report({'ERROR'}, "Body mesh not found")
            return {'CANCELLED'}
        targets = [
            obj for obj in context.selected_objects
            if obj.type == 'MESH' and obj is not source
        ]
        if not targets:
            self.report({'ERROR'}, "Select the meshes to receive weights")
            return {'CANCELLED'}

        armature = common.get_armature(context)
        if armature:
            group_names = [
                vg.name for vg in source.vertex_groups
                if vg.name in armature.data.bones
            ]
        else:
            group_names = [vg.name for vg in source.vertex_groups]
        if not group_names:
            self.report({'ERROR'}, "The body mesh has no bone weights to transfer")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        source_weights = _source_weight_matrix(source, group_names)
        depsgraph = context.evaluated_depsgraph_get()
        bvh = BVHTree.FromObject(source, depsgraph)
        cos_limit = math.cos(math.radians(settings.wt_max_angle))
        max_distance = settings.wt_max_distance
        source_polys = source.data.polygons
        source_verts = source.data.vertices
        matched_total = 0
        vertex_total = 0

        for target in targets:
            mesh = target.data
            n = len(mesh.vertices)
            vertex_total += n
            to_source = source.matrix_world.inverted() @ target.matrix_world
            normal_matrix = to_source.to_3x3()
            weights = np.zeros((n, len(group_names)), dtype=np.float64)
            known = np.zeros(n, dtype=bool)

            for vertex in mesh.vertices:
                co = to_source @ vertex.co
                location, normal, face_index, distance = bvh.find_nearest(co)
                if location is None:
                    continue
                poly = source_polys[face_index]
                indices = list(poly.vertices)
                corner_weights = poly_3d_calc(
                    [source_verts[i].co for i in indices], location)
                row = np.zeros(len(group_names), dtype=np.float64)
                for i, cw in zip(indices, corner_weights):
                    row += source_weights[i] * cw
                weights[vertex.index] = row
                if distance <= max_distance:
                    vn = (normal_matrix @ vertex.normal).normalized()
                    if abs(vn.dot(normal)) >= cos_limit:
                        known[vertex.index] = True

            matched_total += int(known.sum())
            unknown = ~known
            if known.any() and unknown.any():
                edges = common.edge_index_array(mesh)
                fixed = weights[known].copy()
                for _ in range(settings.wt_smooth_iterations):
                    averaged = common.neighbor_average(weights, edges, n)
                    weights[unknown] = averaged[unknown]
                    weights[known] = fixed

            sums = weights.sum(axis=1)
            positive = sums > 1e-8
            weights[positive] /= sums[positive, None]

            for name in group_names:
                existing = target.vertex_groups.get(name)
                if existing is not None:
                    target.vertex_groups.remove(existing)
            for gi, name in enumerate(group_names):
                column = weights[:, gi]
                indices = np.nonzero(column > 0.0005)[0]
                if len(indices) == 0:
                    continue
                group = target.vertex_groups.new(name=name)
                for i in indices:
                    group.add([int(i)], float(column[i]), 'REPLACE')

            if armature and not any(
                m.type == 'ARMATURE' and m.object == armature
                for m in target.modifiers
            ):
                modifier = target.modifiers.new(name="Armature", type='ARMATURE')
                modifier.object = armature

        percent = (matched_total / vertex_total * 100.0) if vertex_total else 0.0
        self.report(
            {'INFO'},
            f"Weights transferred to {len(targets)} meshes "
            f"({percent:.0f}% confident matches, rest inpainted)",
        )
        return {'FINISHED'}


_CLASSES = (AAT_OT_transfer_weights,)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
