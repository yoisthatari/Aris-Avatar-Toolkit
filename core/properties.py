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


def _incoming_armature_items(self, context):
    base = common.get_armature(context)
    items: list[tuple[str, str, str]] = [
        (obj.name, obj.name, "Attachment armature to merge into the base")
        for obj in context.scene.objects
        if obj.type == 'ARMATURE' and obj is not base
    ]
    if not items:
        items = [("NONE", "No other armature", "Import an attachment that has its own armature")]
    _enum_cache["attach_incoming"] = items
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

    cloth_max_distance: FloatProperty(
        name="Search Distance",
        description="How far the fit looks for the body surface. Keeps stray vertices from snapping across to the far side of a limb",
        default=0.25,
        min=0.001,
        max=10.0,
        precision=3,
        subtype='DISTANCE',
    )
    cloth_passes: IntProperty(
        name="Fit Passes",
        description="How many push-and-relax rounds to run. More passes settle stubborn clipping",
        default=2,
        min=1,
        max=10,
    )
    cloth_hide_threshold: FloatProperty(
        name="Hide Depth",
        description="How far under the clothing body geometry may sit and still count as hidden",
        default=0.01,
        min=0.0001,
        max=0.5,
        precision=4,
        subtype='DISTANCE',
    )

    health_max_influences: IntProperty(
        name="Max Bones",
        description="How many bones a single vertex may be weighted to. Unity keeps 4",
        default=4,
        min=1,
        max=8,
    )

    remesh_mode: EnumProperty(
        name="Target",
        description="How the new quad count is chosen",
        items=(
            ('FACES', "Face Count", "Aim for a specific number of quads"),
            ('RATIO', "Ratio", "Aim for a fraction of the current face count"),
        ),
        default='FACES',
    )
    remesh_target_faces: IntProperty(
        name="Quads",
        description="Roughly how many quads the remeshed model should end up with",
        default=5000,
        min=50,
        max=500000,
    )
    remesh_ratio: FloatProperty(
        name="Ratio",
        description="Fraction of the current face count to aim for",
        default=0.25,
        min=0.01,
        max=1.0,
        subtype='FACTOR',
    )
    remesh_symmetry: BoolProperty(
        name="Use Symmetry",
        description="Keep the new topology mirrored down the middle, which avatars almost always want",
        default=True,
    )
    remesh_preserve_sharp: BoolProperty(
        name="Preserve Sharp",
        description="Try to keep hard edges crisp instead of rounding them off",
        default=False,
    )
    remesh_preserve_boundary: BoolProperty(
        name="Preserve Boundary",
        description="Hold open edges in place, which keeps clothing hems and cuffs where they belong",
        default=True,
    )
    remesh_smooth_normals: BoolProperty(
        name="Smooth Normals",
        description="Shade the remeshed result smoothly",
        default=False,
    )
    remesh_transfer_weights: BoolProperty(
        name="Transfer Weights Back",
        description="Rebuild the bone weights on the new topology using the robust inpainting transfer, so the model still deforms",
        default=True,
    )
    remesh_force_shapekeys: BoolProperty(
        name="Remesh Shape Key Meshes",
        description="Remesh meshes that have shape keys too. A remesh cannot keep them, so they will be lost",
        default=False,
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
        name="Threshold",
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

    painter_triangulate: BoolProperty(
        name="Triangulate",
        description="Export triangles so Substance Painter bakes exactly what you see in Unity",
        default=True,
    )
    painter_include_armature: BoolProperty(
        name="Include Armature",
        description="Send the armature along too. Painter does not need it, so this is usually off",
        default=False,
    )
    painter_reset_pose: BoolProperty(
        name="Bind Pose First",
        description="Settle the armature back into its bind pose before prepping or exporting",
        default=True,
    )

    batch_shapekey_names: StringProperty(
        name="Names",
        description="Comma-separated shape key names to create on every selected mesh",
        default="",
    )
    batch_page: IntProperty(
        name="Page",
        description="Current page of the shape key list",
        default=0,
        min=0,
    )

    vertex_error_input: StringProperty(
        name="Vertex Indices",
        description="Paste Unity's unweighted-vertex error text here; the index numbers are picked out for you",
        default="",
    )

    attach_incoming_armature: EnumProperty(
        name="Attachment Armature",
        description="Armature that came with the attachment, to merge into the base",
        items=_incoming_armature_items,
    )
    attach_keep_new_bones: BoolProperty(
        name="Keep Extra Bones",
        description="Copy bones the attachment adds that the base does not have (jaw, ears, extra clothing bones)",
        default=True,
    )
    attach_meshonly_fit: BoolProperty(
        name="Elastic Fit First",
        description="Run an elastic fit pass before transferring weights so the attachment does not clip into the body",
        default=True,
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
