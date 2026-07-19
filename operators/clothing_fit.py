import bpy
import numpy as np
from bpy.types import Context, Operator
from mathutils.bvhtree import BVHTree

from ..core import common


def _apply_deltas(obj, deltas):
    mesh = obj.data
    flat = deltas.ravel()
    coords = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", coords)
    coords += flat
    mesh.vertices.foreach_set("co", coords)
    if mesh.shape_keys:
        for kb in mesh.shape_keys.key_blocks:
            data = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
            kb.data.foreach_get("co", data)
            data += flat
            kb.data.foreach_set("co", data)
    mesh.update()


def _vertex_group_weights(obj, name):
    weights = np.zeros(len(obj.data.vertices), dtype=np.float64)
    group = obj.vertex_groups.get(name) if name else None
    if group is not None:
        for vertex in obj.data.vertices:
            for entry in vertex.groups:
                if entry.group == group.index:
                    weights[vertex.index] = entry.weight
                    break
    return weights


def _compute_push(bvh, to_body, to_cloth, mesh, offsets, pinned):
    n = len(mesh.vertices)
    deltas = np.zeros((n, 3), dtype=np.float64)
    moved = np.zeros(n, dtype=bool)
    for vertex in mesh.vertices:
        if pinned[vertex.index]:
            continue
        offset = offsets[vertex.index]
        co = to_body @ vertex.co
        location, normal, _face, _dist = bvh.find_nearest(co)
        if location is None:
            continue
        depth = (co - location).dot(normal)
        if depth < offset:
            pushed = to_cloth @ (location + normal * offset)
            difference = pushed - vertex.co
            deltas[vertex.index] = (difference.x, difference.y, difference.z)
            moved[vertex.index] = True
    return deltas, moved


class AAT_OT_fit_clothing(Operator):
    bl_idname = "aat.fit_clothing"
    bl_label = "Fit Clothing"
    bl_description = (
        "Push selected clothing meshes out of the body mesh with an elastic "
        "falloff. UV and topology safe: only vertex positions move, and shape "
        "keys are carried along"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        settings = getattr(context.scene, "aat", None)
        return settings is not None and settings.cloth_body_mesh != "NONE"

    def execute(self, context: Context):
        settings = context.scene.aat
        body = bpy.data.objects.get(settings.cloth_body_mesh)
        if body is None or body.type != 'MESH':
            self.report({'ERROR'}, "Body mesh not found")
            return {'CANCELLED'}
        targets = [
            obj for obj in context.selected_objects
            if obj.type == 'MESH' and obj is not body
        ]
        if not targets:
            self.report({'ERROR'}, "Select the clothing meshes to fit")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        depsgraph = context.evaluated_depsgraph_get()
        bvh = BVHTree.FromObject(body, depsgraph)
        offset = settings.cloth_offset
        factor = settings.cloth_smooth_factor
        iterations = settings.cloth_smooth_iterations
        total_moved = 0

        for cloth in targets:
            mesh = cloth.data
            n = len(mesh.vertices)
            to_body = body.matrix_world.inverted() @ cloth.matrix_world
            to_cloth = to_body.inverted()
            edges = common.edge_index_array(mesh)
            offsets = offset + settings.cloth_extra_offset * _vertex_group_weights(
                cloth, settings.cloth_offset_group)
            pinned = _vertex_group_weights(cloth, settings.cloth_pin_group) > 0.5

            for _ in range(2):
                deltas, moved = _compute_push(bvh, to_body, to_cloth, mesh, offsets, pinned)
                if not moved.any():
                    break
                fixed = deltas[moved].copy()
                for _ in range(iterations):
                    averaged = common.neighbor_average(deltas, edges, n)
                    deltas = deltas * (1.0 - factor) + averaged * factor
                    deltas[moved] = fixed
                    deltas[pinned] = 0.0
                _apply_deltas(cloth, deltas)
                total_moved += int(moved.sum())

            deltas, moved = _compute_push(bvh, to_body, to_cloth, mesh, offsets, pinned)
            if moved.any():
                _apply_deltas(cloth, deltas)

        if total_moved == 0:
            self.report({'INFO'}, "Nothing was clipping into the body")
            return {'FINISHED'}
        self.report(
            {'INFO'},
            f"Fitted {len(targets)} meshes ({total_moved} clipping vertices resolved)",
        )
        return {'FINISHED'}


_CLASSES = (AAT_OT_fit_clothing,)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
