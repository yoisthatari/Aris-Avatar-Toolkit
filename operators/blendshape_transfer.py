import bpy
import numpy as np
from bpy.types import Context, Operator
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.interpolate import poly_3d_calc

from ..core import common

MASK_GROUP = "AAT Transfer Mask"
SUBSURF_NAME = "AAT BST Subsurf"
DISPLACE_NAME = "AAT BST Displace"


def sync_preview_modifiers(settings) -> None:
    source = settings.bst_source
    if source is None or source.type != 'MESH':
        return
    subsurf = source.modifiers.get(SUBSURF_NAME)
    if settings.bst_use_subsurf and settings.bst_preview_subsurf:
        if subsurf is None:
            subsurf = source.modifiers.new(name=SUBSURF_NAME, type='SUBSURF')
        subsurf.levels = settings.bst_subsurf_levels
        subsurf.render_levels = settings.bst_subsurf_levels
    elif subsurf is not None:
        source.modifiers.remove(subsurf)
    displace = source.modifiers.get(DISPLACE_NAME)
    if settings.bst_use_displace and settings.bst_preview_displace:
        if displace is None:
            displace = source.modifiers.new(name=DISPLACE_NAME, type='DISPLACE')
            displace.mid_level = 0.0
        displace.strength = settings.bst_displace_strength
    elif displace is not None:
        source.modifiers.remove(displace)


def _evaluated_coords(context, obj):
    depsgraph = context.evaluated_depsgraph_get()
    depsgraph.update()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    coords = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", coords)
    polygons = [tuple(p.vertices) for p in mesh.polygons]
    evaluated.to_mesh_clear()
    return coords.reshape(-1, 3), polygons


def _mask_weights(target):
    n = len(target.data.vertices)
    group = target.vertex_groups.get(MASK_GROUP)
    if group is None:
        return np.ones(n, dtype=np.float64)
    weights = np.zeros(n, dtype=np.float64)
    for vertex in target.data.vertices:
        for entry in vertex.groups:
            if entry.group == group.index:
                weights[vertex.index] = entry.weight
                break
    return weights


class AAT_OT_transfer_blendshapes(Operator):
    bl_idname = "aat.transfer_blendshapes"
    bl_label = "Transfer Blendshapes"
    bl_description = (
        "Copies every shape key from the source mesh to the target mesh with "
        "a gentle kiss, even across totally different topology. Areas painted "
        "blue in the transfer mask are left untouched"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        settings = getattr(context.scene, "aat", None)
        return (
            settings is not None
            and settings.bst_source is not None
            and settings.bst_target is not None
            and settings.bst_source is not settings.bst_target
        )

    def execute(self, context: Context):
        settings = context.scene.aat
        source = settings.bst_source
        target = settings.bst_target
        if not common.has_shapekeys(source):
            self.report({'ERROR'}, "The source mesh has no shape keys to transfer")
            return {'CANCELLED'}

        common.ensure_object_mode(context)

        added_temp = []
        if settings.bst_use_subsurf and source.modifiers.get(SUBSURF_NAME) is None:
            subsurf = source.modifiers.new(name=SUBSURF_NAME, type='SUBSURF')
            subsurf.levels = settings.bst_subsurf_levels
            subsurf.render_levels = settings.bst_subsurf_levels
            added_temp.append(SUBSURF_NAME)
        if settings.bst_use_displace and source.modifiers.get(DISPLACE_NAME) is None:
            displace = source.modifiers.new(name=DISPLACE_NAME, type='DISPLACE')
            displace.mid_level = 0.0
            displace.strength = settings.bst_displace_strength
            added_temp.append(DISPLACE_NAME)

        key_blocks = source.data.shape_keys.key_blocks
        saved = [(kb.value, kb.mute) for kb in key_blocks]
        for kb in key_blocks:
            kb.value = 0.0
            kb.mute = False

        try:
            basis_coords, polygons = _evaluated_coords(context, source)
            bvh = BVHTree.FromPolygons(basis_coords.tolist(), polygons)

            to_source = source.matrix_world.inverted() @ target.matrix_world
            delta_rotation = np.array(
                target.matrix_world.to_3x3().inverted() @ source.matrix_world.to_3x3(),
                dtype=np.float64,
            )

            samples = []
            for vertex in target.data.vertices:
                co = to_source @ vertex.co
                location, _normal, face_index, _dist = bvh.find_nearest(co)
                if location is None:
                    samples.append(None)
                    continue
                poly = polygons[face_index]
                corner_weights = poly_3d_calc(
                    [Vector(basis_coords[i]) for i in poly], location)
                samples.append((poly, corner_weights))

            mask = _mask_weights(target)
            if target.data.shape_keys is None:
                target.shape_key_add(name="Basis", from_mix=False)
            target_keys = target.data.shape_keys.key_blocks

            n_target = len(target.data.vertices)
            created = 0
            for kb in key_blocks[1:]:
                for other in key_blocks:
                    other.value = 0.0
                kb.value = 1.0
                key_coords, _ = _evaluated_coords(context, source)
                kb.value = 0.0
                if key_coords.shape != basis_coords.shape:
                    self.report(
                        {'WARNING'},
                        f"Skipped '{kb.name}': evaluated topology changed mid-transfer",
                    )
                    continue
                deltas = key_coords - basis_coords

                existing = target_keys.get(kb.name)
                if existing is not None:
                    target.shape_key_remove(existing)
                new_key = target.shape_key_add(name=kb.name, from_mix=False)
                data = np.empty(n_target * 3, dtype=np.float64)
                new_key.data.foreach_get("co", data)
                data = data.reshape(-1, 3)
                for i, sample in enumerate(samples):
                    if sample is None or mask[i] <= 0.0:
                        continue
                    poly, corner_weights = sample
                    delta = np.zeros(3, dtype=np.float64)
                    for corner, weight in zip(poly, corner_weights):
                        delta += deltas[corner] * weight
                    data[i] += (delta_rotation @ delta) * mask[i]
                new_key.data.foreach_set("co", data.ravel())
                new_key.slider_min = kb.slider_min
                new_key.slider_max = kb.slider_max
                new_key.value = 0.0
                created += 1
        finally:
            for (value, mute), kb in zip(saved, key_blocks):
                kb.value = value
                kb.mute = mute
            for name in added_temp:
                modifier = source.modifiers.get(name)
                if modifier is not None:
                    source.modifiers.remove(modifier)
            sync_preview_modifiers(settings)

        target.data.update()
        self.report(
            {'INFO'},
            f"Transferred {created} blendshapes from '{source.name}' to '{target.name}'",
        )
        return {'FINISHED'}


class AAT_OT_draw_transfer_mask(Operator):
    bl_idname = "aat.draw_transfer_mask"
    bl_label = "Draw Transfer Mask"
    bl_description = (
        "Paint where blendshapes transfer: red areas transfer fully, blue "
        "areas not at all. Click again to finish your masterpiece"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        settings = getattr(context.scene, "aat", None)
        return settings is not None and settings.bst_target is not None

    def execute(self, context: Context):
        settings = context.scene.aat
        target = settings.bst_target
        if context.mode == 'PAINT_WEIGHT' and context.active_object is target:
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'FINISHED'}

        common.ensure_object_mode(context)
        group = target.vertex_groups.get(MASK_GROUP)
        if group is None:
            group = target.vertex_groups.new(name=MASK_GROUP)
            group.add(list(range(len(target.data.vertices))), 1.0, 'REPLACE')
        target.vertex_groups.active_index = group.index
        common.switch_mode(context, target, 'WEIGHT_PAINT')
        return {'FINISHED'}


class AAT_OT_reset_transfer_mask(Operator):
    bl_idname = "aat.reset_transfer_mask"
    bl_label = "Reset Mask"
    bl_description = "Sets the whole transfer mask back to full transfer (red), fresh as new"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        settings = getattr(context.scene, "aat", None)
        return settings is not None and settings.bst_target is not None

    def execute(self, context: Context):
        target = context.scene.aat.bst_target
        group = target.vertex_groups.get(MASK_GROUP)
        if group is None:
            group = target.vertex_groups.new(name=MASK_GROUP)
        group.add(list(range(len(target.data.vertices))), 1.0, 'REPLACE')
        return {'FINISHED'}


class AAT_OT_invert_transfer_mask(Operator):
    bl_idname = "aat.invert_transfer_mask"
    bl_label = "Invert Mask"
    bl_description = "Swaps transfer and no-transfer areas of the mask, effortlessly"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        settings = getattr(context.scene, "aat", None)
        return (
            settings is not None
            and settings.bst_target is not None
            and settings.bst_target.vertex_groups.get(MASK_GROUP) is not None
        )

    def execute(self, context: Context):
        target = context.scene.aat.bst_target
        group = target.vertex_groups.get(MASK_GROUP)
        weights = _mask_weights(target)
        for vertex in target.data.vertices:
            group.add([vertex.index], 1.0 - weights[vertex.index], 'REPLACE')
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_transfer_blendshapes,
    AAT_OT_draw_transfer_mask,
    AAT_OT_reset_transfer_mask,
    AAT_OT_invert_transfer_mask,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
