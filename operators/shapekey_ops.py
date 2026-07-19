import bpy
from bpy.types import Context, Operator

from ..core import common


class AAT_OT_shapekey_to_basis(Operator):
    bl_idname = "aat.shapekey_to_basis"
    bl_label = "Apply Shape Key to Basis"
    bl_description = (
        "Bake the active shape key (at its current value) into the basis so it "
        "becomes the mesh's default shape. The key itself is kept, inverted"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        obj = context.active_object
        return (
            obj is not None
            and obj.type == 'MESH'
            and obj.active_shape_key is not None
            and obj.active_shape_key_index > 0
        )

    def execute(self, context: Context):
        obj = context.active_object
        key = obj.active_shape_key
        basis = obj.data.shape_keys.key_blocks[0]
        value = key.value if key.value != 0.0 else 1.0

        deltas = [
            (key.data[i].co - basis.data[i].co) * value
            for i in range(len(basis.data))
        ]
        for other in obj.data.shape_keys.key_blocks:
            if other == key:
                continue
            for i, delta in enumerate(deltas):
                other.data[i].co += delta
        for i, delta in enumerate(deltas):
            obj.data.vertices[i].co += delta

        for i, delta in enumerate(deltas):
            key.data[i].co += delta
            key.data[i].co -= delta * 2.0
        key.name = key.name + " - Reverted" if not key.name.endswith(" - Reverted") else key.name
        key.value = 0.0

        obj.data.update()
        self.report({'INFO'}, f"Applied '{key.name}' to basis")
        return {'FINISHED'}


class AAT_OT_remove_empty_shapekeys(Operator):
    bl_idname = "aat.remove_empty_shapekeys"
    bl_label = "Remove Empty Shape Keys"
    bl_description = "Delete shape keys that do not actually move any vertices"
    bl_options = {'REGISTER', 'UNDO'}

    tolerance: bpy.props.FloatProperty(
        name="Tolerance",
        description="Maximum vertex offset that still counts as 'no movement'",
        default=0.00001,
        min=0.0,
        precision=6,
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None or (
            context.active_object is not None and context.active_object.type == 'MESH'
        )

    def execute(self, context: Context):
        armature = common.get_armature(context)
        if armature:
            meshes = common.get_armature_meshes(context, armature)
        else:
            meshes = [context.active_object]

        removed = 0
        for mesh in meshes:
            if not common.has_shapekeys(mesh):
                continue
            key_blocks = mesh.data.shape_keys.key_blocks
            basis = key_blocks[0]
            for kb in list(key_blocks[1:]):
                if kb.name.startswith("vrc."):
                    continue
                moved = any(
                    (kb.data[i].co - basis.data[i].co).length > self.tolerance
                    for i in range(len(basis.data))
                )
                if not moved:
                    mesh.shape_key_remove(kb)
                    removed += 1
        self.report({'INFO'}, f"Removed {removed} empty shape keys")
        return {'FINISHED'}


class AAT_OT_sort_shapekeys(Operator):
    bl_idname = "aat.sort_shapekeys"
    bl_label = "Sort Shape Keys"
    bl_description = "Move vrc.* shape keys (visemes) to the top, right after the basis"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        obj = context.active_object
        return obj is not None and common.has_shapekeys(obj)

    def execute(self, context: Context):
        obj = context.active_object
        common.set_active(context, obj)
        key_blocks = obj.data.shape_keys.key_blocks
        vrc_names = [kb.name for kb in key_blocks if kb.name.startswith("vrc.")]

        for name in reversed(vrc_names):
            index = key_blocks.find(name)
            obj.active_shape_key_index = index
            bpy.ops.object.shape_key_move(type='TOP')
            if obj.active_shape_key_index == 0 and key_blocks[0].name == name:
                bpy.ops.object.shape_key_move(type='DOWN')

        obj.active_shape_key_index = 0
        self.report({'INFO'}, f"Sorted {len(vrc_names)} vrc.* shape keys to the top")
        return {'FINISHED'}


class AAT_OT_smooth_shapekeys(Operator):
    bl_idname = "aat.smooth_shapekeys"
    bl_label = "Smooth Shape Keys"
    bl_description = (
        "Smooth the deformation of the active shape key (or all keys) by "
        "relaxing its vertex deltas, removing jagged or crunchy areas"
    )
    bl_options = {'REGISTER', 'UNDO'}

    factor: bpy.props.FloatProperty(
        name="Factor",
        description="Strength of each smoothing pass",
        default=0.5,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
    )
    iterations: bpy.props.IntProperty(
        name="Iterations",
        description="Number of smoothing passes",
        default=10,
        min=1,
        max=200,
    )
    all_keys: bpy.props.BoolProperty(
        name="All Shape Keys",
        description="Smooth every shape key instead of only the active one",
        default=False,
    )
    mask_group: bpy.props.StringProperty(
        name="Vertex Mask",
        description="Optional vertex group that limits where smoothing applies",
        default="",
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        obj = context.active_object
        return obj is not None and common.has_shapekeys(obj)

    def invoke(self, context: Context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context: Context):
        import numpy as np

        obj = context.active_object
        mesh = obj.data
        key_blocks = mesh.shape_keys.key_blocks
        if self.all_keys:
            keys = list(key_blocks[1:])
        else:
            key = obj.active_shape_key
            if key is None or obj.active_shape_key_index == 0:
                self.report({'ERROR'}, "Select a shape key other than the basis")
                return {'CANCELLED'}
            keys = [key]

        n = len(mesh.vertices)
        edges = common.edge_index_array(mesh)
        basis = np.empty(n * 3, dtype=np.float64)
        key_blocks[0].data.foreach_get("co", basis)
        basis = basis.reshape(-1, 3)

        mask = np.ones(n, dtype=np.float64)
        if self.mask_group:
            group = obj.vertex_groups.get(self.mask_group)
            if group is None:
                self.report({'ERROR'}, f"Vertex group '{self.mask_group}' not found")
                return {'CANCELLED'}
            mask = np.zeros(n, dtype=np.float64)
            for vertex in mesh.vertices:
                for entry in vertex.groups:
                    if entry.group == group.index:
                        mask[vertex.index] = entry.weight
                        break

        strength = (self.factor * mask)[:, None]
        for kb in keys:
            data = np.empty(n * 3, dtype=np.float64)
            kb.data.foreach_get("co", data)
            deltas = data.reshape(-1, 3) - basis
            for _ in range(self.iterations):
                averaged = common.neighbor_average(deltas, edges, n)
                deltas = deltas * (1.0 - strength) + averaged * strength
            kb.data.foreach_set("co", (basis + deltas).ravel())

        mesh.update()
        self.report({'INFO'}, f"Smoothed {len(keys)} shape keys")
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_shapekey_to_basis,
    AAT_OT_remove_empty_shapekeys,
    AAT_OT_sort_shapekeys,
    AAT_OT_smooth_shapekeys,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
