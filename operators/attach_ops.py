import bpy
from bpy.types import Context, Operator
from mathutils import Vector

from ..core import common, bone_names


def _match_map(base, incoming) -> dict[str, str]:
    base_by_lower: dict[str, str] = {}
    base_by_std: dict[str, str] = {}
    for bone in base.data.bones:
        base_by_lower.setdefault(bone.name.lower(), bone.name)
        std = bone_names.standard_bone_name(bone.name)
        if std:
            base_by_std.setdefault(std, bone.name)

    mapping: dict[str, str] = {}
    for bone in incoming.data.bones:
        lowered = bone.name.lower()
        if lowered in base_by_lower:
            mapping[bone.name] = base_by_lower[lowered]
            continue
        std = bone_names.standard_bone_name(bone.name)
        if std and std in base_by_std:
            mapping[bone.name] = base_by_std[std]
    return mapping


def _capture_new_bones(incoming, mapping):
    captured = []
    for bone in incoming.data.bones:
        if bone.name in mapping:
            continue
        captured.append({
            "name": bone.name,
            "parent": bone.parent.name if bone.parent else None,
            "matrix": bone.matrix_local.copy(),
            "head": bone.head_local.copy(),
            "tail": bone.tail_local.copy(),
        })
    return captured


def _add_new_bones(context, base, conv, new_bones, mapping) -> int:
    if not new_bones:
        return 0
    common.switch_mode(context, base, 'EDIT')
    edit_bones = base.data.edit_bones
    created: dict[str, object] = {}
    for data in new_bones:
        edit_bone = edit_bones.new(data["name"])
        head = conv @ data["head"]
        tail = conv @ data["tail"]
        if (tail - head).length < 1e-5:
            tail = head + Vector((0.0, 0.01, 0.0))
        edit_bone.head = head
        edit_bone.tail = tail
        edit_bone.matrix = conv @ data["matrix"]
        created[data["name"]] = edit_bone

    for data in new_bones:
        edit_bone = created[data["name"]]
        parent = data["parent"]
        if parent is None:
            continue
        if parent in mapping:
            edit_bone.parent = edit_bones.get(mapping[parent])
        elif parent in created:
            edit_bone.parent = created[parent]

    bpy.ops.object.mode_set(mode='OBJECT')
    return len(new_bones)


def _remap_vertex_groups(meshes, mapping) -> None:
    for mesh in meshes:
        for source, target in mapping.items():
            if source == target:
                continue
            group = mesh.vertex_groups.get(source)
            if group is None:
                continue
            if mesh.vertex_groups.get(target):
                common.merge_vertex_group(mesh, source, target)
            else:
                group.name = target


def _reparent_meshes(meshes, base, incoming) -> None:
    for mesh in meshes:
        world = mesh.matrix_world.copy()
        if mesh.parent is incoming:
            mesh.parent = base
            mesh.parent_type = 'OBJECT'
        mesh.matrix_world = world
        has_base_modifier = False
        for modifier in mesh.modifiers:
            if modifier.type == 'ARMATURE':
                if modifier.object is incoming:
                    modifier.object = base
                if modifier.object is base:
                    has_base_modifier = True
        if not has_base_modifier:
            modifier = mesh.modifiers.new(name="Armature", type='ARMATURE')
            modifier.object = base


class AAT_OT_merge_armatures(Operator):
    bl_idname = "aat.merge_armatures"
    bl_label = "Merge Armatures"
    bl_description = (
        "Merge an attachment that came with its own armature (a separate head, "
        "or clothing shipped with a matching rig) onto the base. Matching bones "
        "are fused by name, any extra bones the attachment adds are lovingly "
        "kept, meshes move onto the base armature, and the leftover armature is "
        "tidied away"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        settings = getattr(context.scene, "aat", None)
        base = common.get_armature(context)
        if base is None or settings is None:
            return False
        incoming = bpy.data.objects.get(settings.attach_incoming_armature)
        return incoming is not None and incoming is not base

    def execute(self, context: Context):
        settings = context.scene.aat
        base = common.get_armature(context)
        incoming = bpy.data.objects.get(settings.attach_incoming_armature)
        if base is None:
            self.report({'ERROR'}, "No base armature set")
            return {'CANCELLED'}
        if incoming is None or incoming.type != 'ARMATURE':
            self.report({'ERROR'}, "Pick the attachment's armature to merge")
            return {'CANCELLED'}
        if incoming is base:
            self.report({'ERROR'}, "The attachment armature is the base armature")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        meshes = common.get_armature_meshes(context, incoming)
        mapping = _match_map(base, incoming)
        if not mapping:
            self.report(
                {'ERROR'},
                "No matching bones found. Run Fix Model on both so their bone "
                "names line up first",
            )
            return {'CANCELLED'}

        new_bones = _capture_new_bones(incoming, mapping) if settings.attach_keep_new_bones else []
        conv = base.matrix_world.inverted() @ incoming.matrix_world

        added = _add_new_bones(context, base, conv, new_bones, mapping)
        _remap_vertex_groups(meshes, mapping)
        _reparent_meshes(meshes, base, incoming)

        incoming_data = incoming.data
        bpy.data.objects.remove(incoming, do_unlink=True)
        if incoming_data.users == 0:
            bpy.data.armatures.remove(incoming_data)

        settings.armature = base
        common.set_active(context, base)
        self.report(
            {'INFO'},
            f"Merged {len(meshes)} meshes onto the base "
            f"({len(mapping)} bones matched, {added} new bones kept)",
        )
        return {'FINISHED'}


class AAT_OT_attach_mesh_only(Operator):
    bl_idname = "aat.attach_mesh_only"
    bl_label = "Attach Mesh-Only"
    bl_description = (
        "For an attachment that is just a mesh with no armature (most clothing). "
        "Parents the selected meshes to the base armature and transfers body "
        "weights onto them, with an optional elastic fit pass first so nothing "
        "clips through"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        settings = getattr(context.scene, "aat", None)
        if settings is None or common.get_armature(context) is None:
            return False
        if settings.cloth_body_mesh == "NONE":
            return False
        return any(obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context: Context):
        settings = context.scene.aat
        body = bpy.data.objects.get(settings.cloth_body_mesh)
        targets = [
            obj for obj in context.selected_objects
            if obj.type == 'MESH' and obj is not body
        ]
        if not targets:
            self.report({'ERROR'}, "Select the mesh-only attachment to attach")
            return {'CANCELLED'}

        if settings.attach_meshonly_fit:
            result = bpy.ops.aat.fit_clothing()
            if 'CANCELLED' in result:
                return {'CANCELLED'}
        result = bpy.ops.aat.transfer_weights()
        if 'CANCELLED' in result:
            return {'CANCELLED'}

        self.report({'INFO'}, f"Attached {len(targets)} mesh-only attachments to the base")
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_merge_armatures,
    AAT_OT_attach_mesh_only,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
