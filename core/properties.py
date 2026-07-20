import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from . import common

_enum_cache: dict[str, list[tuple[str, str, str]]] = {}


def _poll_armature(self, obj) -> bool:
    return obj.type == 'ARMATURE'


def _poll_mesh(self, obj) -> bool:
    return obj.type == 'MESH'


def _sync_bst_preview(self, context):
    from ..operators import blendshape_transfer

    blendshape_transfer.sync_preview_modifiers(self)


def _mesh_items(self, context):
    armature = common.get_armature(context)
    items: list[tuple[str, str, str]] = []
    if armature:
        for mesh in common.get_armature_meshes(context, armature):
            items.append((mesh.name, mesh.name, "Mesh object"))
    if not items:
        items = [("NONE", "No meshes found", "No meshes are bound to the armature")]
    _enum_cache["meshes"] = items
    return items


def _shapekey_items_for(mesh_prop: str, cache_key: str):
    def items_fn(self, context):
        settings = context.scene.aat
        mesh_name = getattr(settings, mesh_prop, "NONE")
        mesh = bpy.data.objects.get(mesh_name)
        items: list[tuple[str, str, str]] = [("NONE", "None", "No shape key selected")]
        if mesh and mesh.type == 'MESH' and mesh.data.shape_keys:
            for kb in mesh.data.shape_keys.key_blocks[1:]:
                items.append((kb.name, kb.name, "Shape key"))
        _enum_cache[cache_key] = items
        return items
    return items_fn


def _bone_items(context, cache_key: str):
    armature = common.get_armature(context)
    items: list[tuple[str, str, str]] = [("NONE", "None", "No bone selected")]
    if armature:
        preferred = []
        others = []
        for bone in armature.data.bones:
            lowered = bone.name.lower()
            if "eye" in lowered or "目" in bone.name:
                preferred.append((bone.name, bone.name, "Bone"))
            else:
                others.append((bone.name, bone.name, "Bone"))
        items.extend(preferred)
        items.extend(others)
    _enum_cache[cache_key] = items
    return items


def _left_eye_items(self, context):
    return _bone_items(context, "eye_left")


def _right_eye_items(self, context):
    return _bone_items(context, "eye_right")


def _active_shapekey_items(self, context):
    obj = context.active_object
    items: list[tuple[str, str, str]] = [("NONE", "None", "No shape key selected")]
    if obj is not None and common.has_shapekeys(obj):
        for kb in obj.data.shape_keys.key_blocks[1:]:
            items.append((kb.name, kb.name, "Shape key"))
    _enum_cache["sync_shapekey"] = items
    return items


def _armature_items(self, context):
    items: list[tuple[str, str, str]] = [
        (obj.name, obj.name, "Armature")
        for obj in context.scene.objects
        if obj.type == 'ARMATURE'
    ]
    if not items:
        items = [("NONE", "No armatures found", "No armature objects in the scene")]
    _enum_cache["analyzer_armature"] = items
    return items


class AATSettings(PropertyGroup):
    armature: PointerProperty(
        name="Armature",
        description="Armature the toolkit operates on",
        type=bpy.types.Object,
        poll=_poll_armature,
    )

    fix_standardize_names: BoolProperty(
        name="Standardize Bone Names",
        description="Rename bones from MMD/Mixamo/Source/VRoid conventions to the standard scheme (Hips, Spine, Left arm, ...)",
        default=True,
    )
    fix_translate_names: BoolProperty(
        name="Translate Japanese Names",
        description="Translate Japanese bone, shape key, material and object names to English (fully offline)",
        default=True,
    )
    fix_reparent_bones: BoolProperty(
        name="Fix Bone Hierarchy",
        description="Rebuild the Hips-Spine-Chest-Neck-Head chain and fix the hips orientation",
        default=True,
    )
    fix_remove_zero_weight: BoolProperty(
        name="Remove Zero-Weight Bones",
        description="Delete bones without any vertex weights and merge their children's weights upward",
        default=True,
    )
    fix_keep_twist_bones: BoolProperty(
        name="Keep Twist Bones",
        description="Do not delete twist bones even when they carry no weights",
        default=False,
    )
    fix_connect_bones: BoolProperty(
        name="Connect Bones",
        description="Snap parent bone tails to their single child's head for a cleaner armature",
        default=True,
    )
    fix_join_meshes: BoolProperty(
        name="Join Meshes",
        description="Join all meshes bound to the armature into a single 'Body' mesh",
        default=True,
    )
    fix_remove_constraints: BoolProperty(
        name="Remove Constraints",
        description="Remove all bone constraints (IK setups from MMD models etc.)",
        default=True,
    )
    fix_remove_rigidbodies: BoolProperty(
        name="Remove Rigid Bodies & Joints",
        description="Delete MMD rigid body and joint helper objects",
        default=True,
    )

    viseme_mesh: EnumProperty(
        name="Mesh",
        description="Mesh that holds the mouth shape keys",
        items=_mesh_items,
    )
    viseme_ah: EnumProperty(
        name="Shape A",
        description="Shape key for the open 'aa' mouth (e.g. 'Ah')",
        items=_shapekey_items_for("viseme_mesh", "viseme_ah"),
    )
    viseme_oh: EnumProperty(
        name="Shape O",
        description="Shape key for the rounded 'oh' mouth (e.g. 'Oh')",
        items=_shapekey_items_for("viseme_mesh", "viseme_oh"),
    )
    viseme_ch: EnumProperty(
        name="Shape CH",
        description="Shape key for the wide 'ch' mouth (e.g. 'Ch' or 'I')",
        items=_shapekey_items_for("viseme_mesh", "viseme_ch"),
    )
    viseme_intensity: FloatProperty(
        name="Shape Intensity",
        description="Strength multiplier applied to the generated visemes",
        default=1.0,
        min=0.1,
        max=2.0,
        subtype='FACTOR',
    )

    eye_left_bone: EnumProperty(
        name="Left Eye",
        description="Bone that drives the left eye",
        items=_left_eye_items,
    )
    eye_right_bone: EnumProperty(
        name="Right Eye",
        description="Bone that drives the right eye",
        items=_right_eye_items,
    )
    eye_reparent_to_head: BoolProperty(
        name="Parent to Head",
        description="Reparent the eye bones directly to the Head bone",
        default=True,
    )
    eye_straighten: BoolProperty(
        name="Straighten Eye Bones",
        description="Point the eye bones straight up, which most game engines expect",
        default=True,
    )

    cloth_body_mesh: EnumProperty(
        name="Body Mesh",
        description="Body mesh used as the fitting and weight source",
        items=_mesh_items,
    )
    cloth_offset: FloatProperty(
        name="Offset",
        description="Distance the clothing is kept above the body surface",
        default=0.003,
        min=0.0,
        max=0.5,
        precision=4,
        subtype='DISTANCE',
    )
    cloth_smooth_factor: FloatProperty(
        name="Elasticity",
        description="How far the fit adjustment spreads into surrounding vertices",
        default=0.5,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
    )
    cloth_smooth_iterations: IntProperty(
        name="Smoothing Passes",
        description="Number of relaxation passes after pushing vertices out",
        default=10,
        min=0,
        max=200,
    )
    cloth_offset_group: StringProperty(
        name="Offset Group",
        description="Optional vertex group whose weights add extra offset in that region",
        default="",
    )
    cloth_extra_offset: FloatProperty(
        name="Extra Offset",
        description="Additional offset applied at full offset group weight",
        default=0.005,
        min=0.0,
        max=0.5,
        precision=4,
        subtype='DISTANCE',
    )
    cloth_pin_group: StringProperty(
        name="Pin Group",
        description="Optional vertex group whose vertices are never moved by the fit",
        default="",
    )

    wt_max_distance: FloatProperty(
        name="Max Distance",
        description="Surface matches beyond this distance count as uncertain and get inpainted",
        default=0.05,
        min=0.0001,
        max=10.0,
        precision=4,
        subtype='DISTANCE',
    )
    wt_max_angle: FloatProperty(
        name="Max Angle",
        description="Normal difference in degrees above which a match counts as uncertain",
        default=30.0,
        min=1.0,
        max=90.0,
    )
    wt_smooth_iterations: IntProperty(
        name="Inpaint Passes",
        description="Diffusion passes used to fill uncertain areas",
        default=50,
        min=0,
        max=500,
    )

    decimate_mode: EnumProperty(
        name="Mode",
        description="How meshes with shape keys are handled during decimation",
        items=(
            ('SAFE', "Safe", "Only decimate meshes without shape keys"),
            ('SELECTED', "Selected", "Only decimate the currently selected meshes (shape keys on them are lost)"),
            ('FULL', "Full", "Decimate everything; shape keys are removed from decimated meshes"),
        ),
        default='SAFE',
    )
    decimate_max_tris: IntProperty(
        name="Max Triangles",
        description="Target triangle count for the whole model",
        default=70000,
        min=1000,
        max=500000,
    )
    decimate_remove_doubles: BoolProperty(
        name="Remove Doubles First",
        description="Merge duplicate vertices before decimating (skips meshes with shape keys)",
        default=False,
    )

    bst_source: PointerProperty(
        name="Source",
        description="Mesh with the blendshapes you want to transfer",
        type=bpy.types.Object,
        poll=_poll_mesh,
    )
    bst_target: PointerProperty(
        name="Target",
        description="Mesh that will receive the blendshapes",
        type=bpy.types.Object,
        poll=_poll_mesh,
    )
    bst_use_subsurf: BoolProperty(
        name="Subdivision Surface",
        description="Smooth the source mesh so the transfer has more data to work with. Expensive on dense meshes; 1-2 levels is usually enough",
        default=False,
        update=_sync_bst_preview,
    )
    bst_subsurf_levels: IntProperty(
        name="Levels",
        description="Subdivision levels applied to the source during transfer",
        default=1,
        min=1,
        max=4,
        update=_sync_bst_preview,
    )
    bst_preview_subsurf: BoolProperty(
        name="Preview",
        description="Show the subdivision on the source mesh in the viewport",
        default=False,
        update=_sync_bst_preview,
    )
    bst_use_displace: BoolProperty(
        name="Displace",
        description="Displace the source geometry along its normals to bring it closer to the target",
        default=False,
        update=_sync_bst_preview,
    )
    bst_displace_strength: FloatProperty(
        name="Strength",
        description="Displacement distance; negative values pull the surface inward",
        default=0.01,
        min=-1.0,
        max=1.0,
        precision=4,
        subtype='DISTANCE',
        update=_sync_bst_preview,
    )
    bst_preview_displace: BoolProperty(
        name="Preview",
        description="Show the displacement on the source mesh in the viewport",
        default=False,
        update=_sync_bst_preview,
    )

    merge_weights_threshold: FloatProperty(
        name="Weight Threshold",
        description="Weights at or below this value count as zero",
        default=0.0001,
        min=0.0,
        max=0.1,
        precision=4,
    )

    analyzer_armature: EnumProperty(
        name="Scope",
        description="Armature to analyze",
        items=_armature_items,
    )
    analyzer_platform: EnumProperty(
        name="Target",
        description="Platform to compare the avatar against",
        items=(
            ('PC', "PC", "VRChat PC performance rank thresholds"),
            ('QUEST', "Quest", "VRChat Quest performance rank thresholds"),
        ),
        default='PC',
    )
    analyzer_max_texture: EnumProperty(
        name="Max Texture",
        description="Target texture size for Texture Optimizer and Auto Fix Avatar",
        items=(
            ('256', "256", "256x256"),
            ('512', "512", "512x512"),
            ('1024', "1024", "1024x1024"),
            ('2048', "2048", "2048x2048"),
            ('4096', "4096", "4096x4096"),
            ('8192', "8192", "8192x8192"),
        ),
        default='2048',
    )
    analyzer_force_pot: BoolProperty(
        name="Force Power-of-Two",
        description="Round resized textures down to the nearest power-of-two size",
        default=True,
    )
    analyzer_auto_decimate: BoolProperty(
        name="Auto Add Decimate",
        description="Auto Fix Avatar adds non-destructive Decimate modifiers to heavy meshes",
        default=False,
    )

    sync_auxiliary: PointerProperty(
        name="Auxiliary",
        description="Optional second object kept in sync with the active object (e.g. teeth or eyelashes)",
        type=bpy.types.Object,
        poll=_poll_mesh,
    )
    sync_shapekey: EnumProperty(
        name="Shape Key",
        description="Shape key to sync, sculpt, or reset, taken from the active object",
        items=_active_shapekey_items,
    )


_CLASSES = (AATSettings,)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.aat = PointerProperty(type=AATSettings)


def unregister() -> None:
    del bpy.types.Scene.aat
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
