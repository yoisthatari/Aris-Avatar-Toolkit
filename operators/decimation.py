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


class AAT_OT_quad_remesh(Operator):
    bl_idname = "aat.quad_remesh"
    bl_label = "Quad Remesh"
    bl_description = (
        "Retopologise the selected meshes into clean, flowing quads using "
        "Blender's built-in QuadriFlow field-aligned remesher. Bone weights are "
        "transferred back onto the new topology with the robust inpainting "
        "method, so your model still deforms beautifully. Shape keys cannot "
        "survive a remesh, so meshes that have them are skipped unless you say "
        "otherwise"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return any(obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context: Context):
        from . import weight_transfer

        settings = context.scene.aat
        targets = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not targets:
            self.report({'ERROR'}, "Select the meshes to remesh")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        armature = common.get_armature(context)

        skipped: list[str] = []
        failed: list[str] = []
        lost_shapekeys: list[str] = []
        before_tris = 0
        after_tris = 0
        done = 0

        for mesh in targets:
            if common.has_shapekeys(mesh) and not settings.remesh_force_shapekeys:
                skipped.append(mesh.name)
                continue

            before_tris += common.triangle_count(mesh)
            source = None
            if settings.remesh_transfer_weights and mesh.vertex_groups:
                source = mesh.copy()
                source.data = mesh.data.copy()
                context.collection.objects.link(source)
                source.matrix_world = mesh.matrix_world.copy()

            if common.has_shapekeys(mesh):
                lost_shapekeys.append(mesh.name)
            if mesh.data.shape_keys is not None:
                common.set_active(context, mesh)
                bpy.ops.object.shape_key_remove(all=True, apply_mix=False)

            common.set_active(context, mesh)
            try:
                if settings.remesh_mode == 'RATIO':
                    bpy.ops.object.quadriflow_remesh(
                        mode='RATIO',
                        target_ratio=settings.remesh_ratio,
                        use_mesh_symmetry=settings.remesh_symmetry,
                        use_preserve_sharp=settings.remesh_preserve_sharp,
                        use_preserve_boundary=settings.remesh_preserve_boundary,
                        preserve_attributes=True,
                        smooth_normals=settings.remesh_smooth_normals,
                    )
                else:
                    bpy.ops.object.quadriflow_remesh(
                        mode='FACES',
                        target_faces=settings.remesh_target_faces,
                        use_mesh_symmetry=settings.remesh_symmetry,
                        use_preserve_sharp=settings.remesh_preserve_sharp,
                        use_preserve_boundary=settings.remesh_preserve_boundary,
                        preserve_attributes=True,
                        smooth_normals=settings.remesh_smooth_normals,
                    )
            except RuntimeError as exc:
                failed.append(f"{mesh.name} ({exc})")
                if source is not None:
                    source_data = source.data
                    bpy.data.objects.remove(source, do_unlink=True)
                    bpy.data.meshes.remove(source_data)
                continue

            if source is not None:
                weight_transfer.transfer_weights(
                    context,
                    source,
                    [mesh],
                    max_distance=settings.wt_max_distance,
                    max_angle=settings.wt_max_angle,
                    smooth_iterations=settings.wt_smooth_iterations,
                    armature=armature,
                )
                source_data = source.data
                bpy.data.objects.remove(source, do_unlink=True)
                bpy.data.meshes.remove(source_data)

            if armature is not None and not any(
                m.type == 'ARMATURE' and m.object == armature for m in mesh.modifiers
            ):
                modifier = mesh.modifiers.new(name="Armature", type='ARMATURE')
                modifier.object = armature

            after_tris += common.triangle_count(mesh)
            done += 1

        if done == 0:
            if skipped:
                self.report(
                    {'ERROR'},
                    f"Every mesh has shape keys, so nothing was remeshed. Enable "
                    f"Remesh Shape Key Meshes to go ahead anyway: {', '.join(skipped[:3])}",
                )
            elif failed:
                self.report(
                    {'ERROR'},
                    "QuadriFlow could not remesh this. It needs clean, manifold "
                    f"geometry: {failed[0]}",
                )
            else:
                self.report({'ERROR'}, "Nothing was remeshed")
            return {'CANCELLED'}

        message = f"Remeshed {done} meshes to quads ({before_tris:,} to {after_tris:,} triangles)"
        warnings = []
        if lost_shapekeys:
            warnings.append(f"shape keys lost on {', '.join(lost_shapekeys[:3])}")
        if skipped:
            warnings.append(f"{len(skipped)} skipped for shape keys")
        if failed:
            warnings.append(f"{len(failed)} failed")
        if warnings:
            self.report({'WARNING'}, message + ". " + "; ".join(warnings))
        else:
            self.report({'INFO'}, message)
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_decimate,
    AAT_OT_quad_remesh,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
