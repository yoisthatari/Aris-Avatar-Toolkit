from __future__ import annotations

from typing import Iterable

import bpy
from bpy.types import Context, Object

WEIGHT_THRESHOLD = 0.0001


def get_armature(context: Context) -> Object | None:
    settings = getattr(context.scene, "aat", None)
    if settings and settings.armature and settings.armature.type == 'ARMATURE':
        return settings.armature
    for obj in context.scene.objects:
        if obj.type == 'ARMATURE':
            return obj
    return None


def get_armature_meshes(context: Context, armature: Object) -> list[Object]:
    meshes: list[Object] = []
    for obj in context.scene.objects:
        if obj.type != 'MESH':
            continue
        if obj.parent == armature:
            meshes.append(obj)
            continue
        for mod in obj.modifiers:
            if mod.type == 'ARMATURE' and mod.object == armature:
                meshes.append(obj)
                break
    return meshes


def set_active(context: Context, obj: Object, *, deselect_others: bool = True) -> None:
    if deselect_others:
        for other in context.view_layer.objects:
            other.select_set(False)
    obj.hide_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj


def ensure_object_mode(context: Context) -> None:
    active = context.view_layer.objects.active
    if active and active.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')


def switch_mode(context: Context, obj: Object, mode: str) -> None:
    ensure_object_mode(context)
    set_active(context, obj)
    if obj.mode != mode:
        bpy.ops.object.mode_set(mode=mode)


def unhide_everything(context: Context) -> None:
    for obj in context.scene.objects:
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.hide_select = False
    for layer_collection in _walk_layer_collections(context.view_layer.layer_collection):
        layer_collection.exclude = False
        layer_collection.hide_viewport = False
        layer_collection.collection.hide_viewport = False
        layer_collection.collection.hide_select = False


def _walk_layer_collections(root):
    for child in root.children:
        yield child
        yield from _walk_layer_collections(child)


def apply_transforms(context: Context, objects: Iterable[Object]) -> None:
    ensure_object_mode(context)
    objects = [obj for obj in objects if obj]
    if not objects:
        return
    for obj in context.view_layer.objects:
        obj.select_set(False)
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    context.view_layer.objects.active = objects[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def apply_modifier(context: Context, obj: Object, modifier_name: str) -> None:
    with context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
        bpy.ops.object.modifier_apply(modifier=modifier_name)


def apply_modifier_with_shapekeys(context: Context, obj: Object, modifier_name: str) -> None:
    if not has_shapekeys(obj):
        apply_modifier(context, obj, modifier_name)
        return

    ensure_object_mode(context)
    key_blocks = obj.data.shape_keys.key_blocks
    key_data = [
        (kb.name, kb.value, kb.slider_min, kb.slider_max, kb.mute)
        for kb in key_blocks
    ]
    active_index = obj.active_shape_key_index

    duplicates: list[Object] = []
    for name, *_ in key_data[1:]:
        dup = obj.copy()
        dup.data = obj.data.copy()
        context.collection.objects.link(dup)
        for kb in dup.data.shape_keys.key_blocks:
            kb.mute = False
            kb.value = 1.0 if kb.name == name else 0.0
        set_active(context, dup)
        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
        apply_modifier(context, dup, modifier_name)
        duplicates.append(dup)

    set_active(context, obj)
    for kb in obj.data.shape_keys.key_blocks:
        kb.mute = False
        kb.value = 0.0
    bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
    apply_modifier(context, obj, modifier_name)

    obj.shape_key_add(name=key_data[0][0], from_mix=False)
    for dup, (name, value, slider_min, slider_max, mute) in zip(duplicates, key_data[1:]):
        set_active(context, obj)
        dup.select_set(True)
        bpy.ops.object.join_shapes()
        kb = obj.data.shape_keys.key_blocks[-1]
        kb.name = name
        kb.slider_min = slider_min
        kb.slider_max = slider_max
        kb.value = value
        kb.mute = mute

    for dup in duplicates:
        mesh = dup.data
        bpy.data.objects.remove(dup)
        bpy.data.meshes.remove(mesh)

    obj.active_shape_key_index = min(active_index, len(obj.data.shape_keys.key_blocks) - 1)
    set_active(context, obj)


def has_shapekeys(obj: Object) -> bool:
    return (
        obj.type == 'MESH'
        and obj.data.shape_keys is not None
        and len(obj.data.shape_keys.key_blocks) > 1
    )


def shapekey_names(obj: Object) -> list[str]:
    if obj.type != 'MESH' or not obj.data.shape_keys:
        return []
    return [kb.name for kb in obj.data.shape_keys.key_blocks]


def merge_vertex_group(obj: Object, source: str, target: str) -> None:
    source_group = obj.vertex_groups.get(source)
    if source_group is None:
        return
    target_group = obj.vertex_groups.get(target)
    if target_group is None:
        target_group = obj.vertex_groups.new(name=target)
    source_index = source_group.index
    for vertex in obj.data.vertices:
        for group_entry in vertex.groups:
            if group_entry.group == source_index and group_entry.weight > 0.0:
                target_group.add([vertex.index], group_entry.weight, 'ADD')
                break
    obj.vertex_groups.remove(source_group)


def collect_weighted_bone_names(meshes: Iterable[Object], threshold: float = WEIGHT_THRESHOLD) -> set[str]:
    used: set[str] = set()
    for mesh in meshes:
        index_to_name = {vg.index: vg.name for vg in mesh.vertex_groups}
        if not index_to_name:
            continue
        for vertex in mesh.data.vertices:
            for group_entry in vertex.groups:
                if group_entry.weight > threshold:
                    name = index_to_name.get(group_entry.group)
                    if name:
                        used.add(name)
    return used


def remove_empty_vertex_groups(meshes: Iterable[Object], armature: Object | None = None) -> int:
    removed = 0
    for mesh in meshes:
        used = collect_weighted_bone_names([mesh])
        for group in list(mesh.vertex_groups):
            if group.name in used:
                continue
            if group.lock_weight:
                continue
            if armature and group.name in armature.data.bones:
                continue
            mesh.vertex_groups.remove(group)
            removed += 1
    return removed


def triangle_count(obj: Object) -> int:
    if obj.type != 'MESH':
        return 0
    return sum(
        max(len(polygon.vertices) - 2, 0)
        for polygon in obj.data.polygons
    )


def sanitize_name(name: str) -> str:
    return name.strip().replace("　", " ")
