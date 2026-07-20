from __future__ import annotations

import bpy
from bpy.types import Context, Object, Operator

from ..core import common


class AAT_OT_decimate(Operator):
    bl_idname = "aat.decimate"
    bl_label = "Decimate Model"
    bl_description = (
        "Gently trims the model down to the target triangle count. Safe mode "
        "promises never to touch your precious meshes with shape keys"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def execute(self, context: Context):
        settings = context.scene.aat
        armature = common.get_armature(context)
        meshes = common.get_armature_meshes(context, armature)
        common.ensure_object_mode(context)

        mode = settings.decimate_mode
        if mode == 'SELECTED':
            candidates = [m for m in meshes if m.select_get()]
            if not candidates:
                self.report({'ERROR'}, "No meshes of this model are selected")
                return {'CANCELLED'}
        elif mode == 'SAFE':
            candidates = [m for m in meshes if not common.has_shapekeys(m)]
        else:
            candidates = list(meshes)

        total_tris = sum(common.triangle_count(m) for m in meshes)
        protected_tris = sum(
            common.triangle_count(m) for m in meshes if m not in candidates
        )
        target = settings.decimate_max_tris

        if total_tris <= target:
            self.report({'INFO'}, f"Model already has {total_tris:,} triangles (target {target:,})")
            return {'CANCELLED'}
        if not candidates:
            self.report(
                {'ERROR'},
                "Nothing to decimate: every mesh has shape keys. Use Full or Selected mode",
            )
            return {'CANCELLED'}

        decimatable_tris = total_tris - protected_tris
        budget = target - protected_tris
        if budget <= 0:
            self.report(
                {'ERROR'},
                f"Protected meshes alone have {protected_tris:,} triangles, above the "
                f"target of {target:,}. Use Full mode or raise the target",
            )
            return {'CANCELLED'}

        ratio = budget / decimatable_tris
        lost_shapekeys: list[str] = []

        for mesh in candidates:
            if common.triangle_count(mesh) == 0:
                continue
            if common.has_shapekeys(mesh):
                lost_shapekeys.append(mesh.name)
                common.set_active(context, mesh)
                bpy.ops.object.shape_key_remove(all=True, apply_mix=False)
            elif mesh.data.shape_keys is not None:
                common.set_active(context, mesh)
                bpy.ops.object.shape_key_remove(all=True, apply_mix=False)

            if settings.decimate_remove_doubles:
                common.switch_mode(context, mesh, 'EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.remove_doubles(threshold=0.0001)
                bpy.ops.object.mode_set(mode='OBJECT')

            self._decimate_mesh(context, mesh, ratio)

        final_tris = sum(common.triangle_count(m) for m in common.get_armature_meshes(context, armature))
        message = f"Decimated to {final_tris:,} triangles (target {target:,})"
        if lost_shapekeys:
            message += f". Shape keys removed from: {', '.join(lost_shapekeys)}"
            self.report({'WARNING'}, message)
        else:
            self.report({'INFO'}, message)
        return {'FINISHED'}

    def _decimate_mesh(self, context: Context, mesh: Object, ratio: float) -> None:
        modifier = mesh.modifiers.new(name="AAT Decimate", type='DECIMATE')
        modifier.ratio = max(min(ratio, 1.0), 0.005)
        modifier.use_collapse_triangulate = True
        with context.temp_override(object=mesh, active_object=mesh, selected_objects=[mesh]):
            bpy.ops.object.modifier_move_to_index(modifier=modifier.name, index=0)
        common.apply_modifier(context, mesh, modifier.name)


_CLASSES = (AAT_OT_decimate,)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
