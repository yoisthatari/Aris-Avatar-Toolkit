import bpy
from bpy.types import Context, Object, Operator

from ..core import common


def _sync_targets(context: Context) -> list[Object]:
    targets = []
    seen = set()

    def add(obj):
        if obj is not None and obj.type == 'MESH' and obj.name not in seen:
            seen.add(obj.name)
            targets.append(obj)

    add(context.active_object)
    settings = getattr(context.scene, "aat", None)
    if settings is not None:
        add(settings.sync_auxiliary)
    for obj in context.selected_objects:
        add(obj)
    return targets


class AAT_OT_sync_blendshape(Operator):
    bl_idname = "aat.sync_blendshape"
    bl_label = "Sync Blendshape"
    bl_description = (
        "Turn on the selected shape key, by name, on the active object, the "
        "Auxiliary object, and every selected mesh that has a matching key"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        settings = getattr(context.scene, "aat", None)
        return settings is not None and settings.sync_shapekey != "NONE"

    def execute(self, context: Context):
        settings = context.scene.aat
        name = settings.sync_shapekey
        synced = 0
        skipped = 0
        for obj in _sync_targets(context):
            if not common.has_shapekeys(obj):
                continue
            key = obj.data.shape_keys.key_blocks.get(name)
            if key is None:
                skipped += 1
                continue
            key.value = 1.0
            key.mute = False
            synced += 1

        if synced == 0:
            self.report({'ERROR'}, f"No selected object has a shape key named '{name}'")
            return {'CANCELLED'}

        message = f"Synced '{name}' on {synced} objects"
        if skipped:
            message += f", {skipped} did not have a matching key"
        self.report({'INFO'}, message)
        return {'FINISHED'}


class AAT_OT_sculpt_shapekey_mode(Operator):
    bl_idname = "aat.sculpt_shapekey_mode"
    bl_label = "Quick Sculpt Mode"
    bl_description = (
        "Highlight the selected shape key on the active object and enter Sculpt "
        "Mode with only that shape key visible, for safe localized editing"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        obj = context.active_object
        settings = getattr(context.scene, "aat", None)
        return (
            obj is not None and common.has_shapekeys(obj)
            and settings is not None and settings.sync_shapekey != "NONE"
        )

    def execute(self, context: Context):
        obj = context.active_object
        settings = context.scene.aat
        name = settings.sync_shapekey
        key_blocks = obj.data.shape_keys.key_blocks
        index = key_blocks.find(name)
        if index < 0:
            self.report({'ERROR'}, f"Active object has no shape key named '{name}'")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        obj.active_shape_key_index = index
        obj.show_only_shape_key = True
        common.switch_mode(context, obj, 'SCULPT')
        self.report({'INFO'}, f"Sculpting '{name}'")
        return {'FINISHED'}


class AAT_OT_reset_synced_shapekeys(Operator):
    bl_idname = "aat.reset_synced_shapekeys"
    bl_label = "Reset Synced Shapekeys"
    bl_description = (
        "Clear every shape key value back to 0 on the active object, the "
        "Auxiliary object, and every selected mesh"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.active_object is not None

    def execute(self, context: Context):
        reset = 0
        for obj in _sync_targets(context):
            if not common.has_shapekeys(obj):
                continue
            for key in obj.data.shape_keys.key_blocks[1:]:
                key.value = 0.0
            reset += 1

        self.report({'INFO'}, f"Reset shape keys on {reset} objects")
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_sync_blendshape,
    AAT_OT_sculpt_shapekey_mode,
    AAT_OT_reset_synced_shapekeys,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
