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


def _compute_push(bvh, to_body, to_cloth, mesh, offsets, pinned, max_distance):
    n = len(mesh.vertices)
    deltas = np.zeros((n, 3), dtype=np.float64)
    moved = np.zeros(n, dtype=bool)
    for vertex in mesh.vertices:
        if pinned[vertex.index]:
            continue
        offset = offsets[vertex.index]
        co = to_body @ vertex.co
        location, normal, _face, _dist = bvh.find_nearest(co, max_distance)
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
        "Gently pushes selected clothing meshes out of the body mesh with a "
        "soft, elastic falloff. UV and topology safe: only vertex positions "
        "move, and shape keys come along for the ride"
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
        max_distance = settings.cloth_max_distance
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

            for _ in range(settings.cloth_passes):
                deltas, moved = _compute_push(
                    bvh, to_body, to_cloth, mesh, offsets, pinned, max_distance)
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

            deltas, moved = _compute_push(
                bvh, to_body, to_cloth, mesh, offsets, pinned, max_distance)
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


_HIDE_GROUP = "AAT Under Clothing"
_HIDE_MODIFIER = "AAT Hide Under Clothing"


class AAT_OT_hide_body_under_clothing(Operator):
    bl_idname = "aat.hide_body_under_clothing"
    bl_label = "Hide Body Under Clothing"
    bl_description = (
        "Tucks away the body geometry hiding underneath the selected clothing, "
        "so nothing pokes through and you save polygons. It uses a Mask "
        "modifier, so it is completely reversible and your shape keys stay "
        "perfectly intact"
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
        garments = [
            obj for obj in context.selected_objects
            if obj.type == 'MESH' and obj is not body
        ]
        if not garments:
            self.report({'ERROR'}, "Select the clothing that should cover the body")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        depsgraph = context.evaluated_depsgraph_get()
        threshold = settings.cloth_hide_threshold
        covered = np.zeros(len(body.data.vertices), dtype=bool)

        for garment in garments:
            bvh = BVHTree.FromObject(garment, depsgraph)
            to_garment = garment.matrix_world.inverted() @ body.matrix_world
            for vertex in body.data.vertices:
                if covered[vertex.index]:
                    continue
                co = to_garment @ vertex.co
                location, normal, _face, distance = bvh.find_nearest(co, threshold)
                if location is None:
                    continue
                if (co - location).dot(normal) < 0.0:
                    covered[vertex.index] = True

        count = int(covered.sum())
        group = body.vertex_groups.get(_HIDE_GROUP)
        if group is not None:
            body.vertex_groups.remove(group)

        if count == 0:
            modifier = body.modifiers.get(_HIDE_MODIFIER)
            if modifier is not None:
                body.modifiers.remove(modifier)
            self.report(
                {'WARNING'},
                "No body geometry is sitting under that clothing. Try raising "
                "the Hide Depth if the clothing floats further off the skin",
            )
            return {'CANCELLED'}

        group = body.vertex_groups.new(name=_HIDE_GROUP)
        for index in np.nonzero(covered)[0]:
            group.add([int(index)], 1.0, 'REPLACE')

        modifier = body.modifiers.get(_HIDE_MODIFIER)
        if modifier is None or modifier.type != 'MASK':
            if modifier is not None:
                body.modifiers.remove(modifier)
            modifier = body.modifiers.new(name=_HIDE_MODIFIER, type='MASK')
        modifier.vertex_group = _HIDE_GROUP
        modifier.invert_vertex_group = True
        modifier.show_in_editmode = True

        with context.temp_override(object=body, active_object=body, selected_objects=[body]):
            bpy.ops.object.modifier_move_to_index(modifier=modifier.name, index=0)

        percent = count / max(len(body.data.vertices), 1) * 100.0
        self.report(
            {'INFO'},
            f"Hid {count:,} body vertices ({percent:.0f}%) under {len(garments)} garments",
        )
        return {'FINISHED'}


class AAT_OT_show_body_under_clothing(Operator):
    bl_idname = "aat.show_body_under_clothing"
    bl_label = "Show Body Again"
    bl_description = "Bring back every bit of body geometry that was tucked away under clothing"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        settings = getattr(context.scene, "aat", None)
        if settings is None or settings.cloth_body_mesh == "NONE":
            return False
        body = bpy.data.objects.get(settings.cloth_body_mesh)
        return body is not None and _HIDE_MODIFIER in body.modifiers

    def execute(self, context: Context):
        settings = context.scene.aat
        body = bpy.data.objects.get(settings.cloth_body_mesh)
        if body is None:
            self.report({'ERROR'}, "Body mesh not found")
            return {'CANCELLED'}
        modifier = body.modifiers.get(_HIDE_MODIFIER)
        if modifier is not None:
            body.modifiers.remove(modifier)
        group = body.vertex_groups.get(_HIDE_GROUP)
        if group is not None:
            body.vertex_groups.remove(group)
        self.report({'INFO'}, "The whole body is visible again")
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_fit_clothing,
    AAT_OT_hide_body_under_clothing,
    AAT_OT_show_body_under_clothing,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
