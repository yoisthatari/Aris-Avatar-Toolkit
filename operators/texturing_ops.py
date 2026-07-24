import os
import re

import bpy
from bpy.props import BoolProperty, CollectionProperty, StringProperty
from bpy.types import Context, Operator, OperatorFileListElement

from ..core import common, translations

_UNSAFE_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")
_IMAGE_EXTENSIONS = (".png", ".tga", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".bmp")

_SUFFIX_TYPES = {
    "basecolor": 'BASE',
    "base": 'BASE',
    "albedo": 'BASE',
    "diffuse": 'BASE',
    "color": 'BASE',
    "albedotransparency": 'BASE_ALPHA',
    "basecoloropacity": 'BASE_ALPHA',
    "diffuseopacity": 'BASE_ALPHA',
    "normal": 'NORMAL',
    "normalmap": 'NORMAL',
    "normalgl": 'NORMAL',
    "normalopengl": 'NORMAL',
    "normalbump": 'NORMAL',
    "normaldx": 'NORMAL_DX',
    "normaldirectx": 'NORMAL_DX',
    "metallic": 'METALLIC',
    "metalness": 'METALLIC',
    "roughness": 'ROUGHNESS',
    "smoothness": 'SMOOTHNESS',
    "glossiness": 'SMOOTHNESS',
    "metallicsmoothness": 'METALLIC_SMOOTHNESS',
    "metallicsmooth": 'METALLIC_SMOOTHNESS',
    "ao": 'AO',
    "occlusion": 'AO',
    "ambientocclusion": 'AO',
    "mixedao": 'AO',
    "emissive": 'EMISSION',
    "emission": 'EMISSION',
    "emissioncolor": 'EMISSION',
    "opacity": 'ALPHA',
    "alpha": 'ALPHA',
    "transparency": 'ALPHA',
    "height": 'HEIGHT',
    "displacement": 'HEIGHT',
}

_NON_COLOR_TYPES = {
    'NORMAL', 'NORMAL_DX', 'METALLIC', 'ROUGHNESS', 'SMOOTHNESS',
    'METALLIC_SMOOTHNESS', 'AO', 'ALPHA', 'HEIGHT',
}


def safe_material_name(name: str) -> str:
    translated = translations.translate(common.sanitize_name(name))
    cleaned = _UNSAFE_PATTERN.sub("_", translated)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "Material"


def target_meshes(context: Context) -> list:
    selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
    if selected:
        return selected
    armature = common.get_armature(context)
    if armature is not None:
        return common.get_armature_meshes(context, armature)
    return []


def collect_materials(meshes) -> list:
    materials = []
    for mesh in meshes:
        for slot in mesh.material_slots:
            if slot.material is not None and slot.material not in materials:
                materials.append(slot.material)
    return materials


def _principled(material):
    if material.node_tree is None:
        material.use_nodes = True
    tree = material.node_tree
    bsdf = next((n for n in tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        bsdf = tree.nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.location = (0.0, 0.0)
        output = next((n for n in tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if output is None:
            output = tree.nodes.new('ShaderNodeOutputMaterial')
            output.location = (300.0, 0.0)
        tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    return tree, bsdf


def _clear_previous(tree) -> None:
    for node in list(tree.nodes):
        if node.get("aat_painter"):
            tree.nodes.remove(node)


def _new_node(tree, kind, x, y):
    node = tree.nodes.new(kind)
    node.location = (x, y)
    node["aat_painter"] = True
    return node


def _image_node(tree, image, map_type, x, y):
    node = _new_node(tree, 'ShaderNodeTexImage', x, y)
    node.image = image
    node.label = map_type.replace("_", " ").title()
    image.colorspace_settings.name = (
        'Non-Color' if map_type in _NON_COLOR_TYPES else 'sRGB'
    )
    if map_type in _NON_COLOR_TYPES:
        image.alpha_mode = 'CHANNEL_PACKED'
    return node


class AAT_OT_prep_for_painter(Operator):
    bl_idname = "aat.prep_for_painter"
    bl_label = "Prep for Painter"
    bl_description = (
        "Get your model ready for Substance Painter in one click: gives every "
        "material a clean ASCII name so its texture set exports nicely, drops "
        "unused material slots, checks every mesh has UVs, and settles the "
        "armature back into its bind pose"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return bool(target_meshes(context))

    def execute(self, context: Context):
        settings = context.scene.aat
        meshes = target_meshes(context)
        if not meshes:
            self.report({'ERROR'}, "Select the meshes, or set the armature first")
            return {'CANCELLED'}

        common.ensure_object_mode(context)

        if settings.painter_reset_pose:
            armature = common.get_armature(context)
            if armature is not None:
                for pose_bone in armature.pose.bones:
                    pose_bone.matrix_basis.identity()

        removed_slots = 0
        for mesh in meshes:
            used = {poly.material_index for poly in mesh.data.polygons}
            for index in reversed(range(len(mesh.material_slots))):
                if index in used and mesh.material_slots[index].material is not None:
                    continue
                mesh.active_material_index = index
                with context.temp_override(
                    object=mesh, active_object=mesh, selected_objects=[mesh]
                ):
                    bpy.ops.object.material_slot_remove()
                removed_slots += 1

        materials = collect_materials(meshes)
        taken = {m.name for m in bpy.data.materials}
        renamed = 0
        for material in materials:
            wanted = safe_material_name(material.name)
            if wanted == material.name:
                continue
            candidate = wanted
            counter = 1
            while candidate in taken and candidate != material.name:
                candidate = f"{wanted}_{counter}"
                counter += 1
            taken.discard(material.name)
            material.name = candidate
            taken.add(candidate)
            renamed += 1

        missing_uvs = [m.name for m in meshes if not m.data.uv_layers]
        if missing_uvs:
            self.report(
                {'WARNING'},
                f"{len(missing_uvs)} meshes have no UV map and cannot be painted: "
                + ", ".join(missing_uvs[:3]) + ("..." if len(missing_uvs) > 3 else ""),
            )
        else:
            self.report(
                {'INFO'},
                f"Ready for Painter: {len(materials)} texture sets, {renamed} materials "
                f"renamed, {removed_slots} unused slots removed",
            )
        return {'FINISHED'}


class AAT_OT_export_for_painter(Operator):
    bl_idname = "aat.export_for_painter"
    bl_label = "Export for Painter"
    bl_description = (
        "Export an FBX tuned for Substance Painter: triangulated for predictable "
        "baking, tangents included so normal maps come out right, meter scale "
        "and Y-up so it lands the same way Unity expects"
    )
    bl_options = {'REGISTER'}

    filepath: StringProperty(subtype='FILE_PATH')
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})
    check_existing: BoolProperty(default=True, options={'HIDDEN'})

    @classmethod
    def poll(cls, context: Context) -> bool:
        return bool(target_meshes(context))

    def invoke(self, context: Context, event):
        if not self.filepath:
            blend = bpy.data.filepath
            base = os.path.splitext(os.path.basename(blend))[0] if blend else "model"
            self.filepath = os.path.join(
                os.path.dirname(blend), base + "_painter.fbx")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context: Context):
        settings = context.scene.aat
        meshes = target_meshes(context)
        if not meshes:
            self.report({'ERROR'}, "Nothing to export")
            return {'CANCELLED'}
        if not self.filepath:
            self.report({'ERROR'}, "No file path given")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        armature = common.get_armature(context)
        if settings.painter_reset_pose and armature is not None:
            for pose_bone in armature.pose.bones:
                pose_bone.matrix_basis.identity()

        for obj in context.view_layer.objects:
            obj.select_set(False)
        for mesh in meshes:
            mesh.hide_set(False)
            mesh.select_set(True)
        object_types = {'MESH'}
        if settings.painter_include_armature and armature is not None:
            armature.hide_set(False)
            armature.select_set(True)
            object_types.add('ARMATURE')
        context.view_layer.objects.active = meshes[0]

        no_uvs = [m.name for m in meshes if not m.data.uv_layers]
        try:
            bpy.ops.export_scene.fbx(
                filepath=self.filepath,
                use_selection=True,
                object_types=object_types,
                use_mesh_modifiers=False,
                use_triangles=settings.painter_triangulate,
                use_tspace=True,
                mesh_smooth_type='FACE',
                add_leaf_bones=False,
                bake_anim=False,
                apply_scale_options='FBX_SCALE_ALL',
                global_scale=1.0,
                axis_forward='-Z',
                axis_up='Y',
                path_mode='COPY',
                embed_textures=False,
                primary_bone_axis='Y',
                secondary_bone_axis='X',
            )
        except RuntimeError as exc:
            self.report({'ERROR'}, f"Export failed: {exc}")
            return {'CANCELLED'}

        materials = collect_materials(meshes)
        message = (
            f"Exported {len(meshes)} meshes / {len(materials)} texture sets to "
            f"{os.path.basename(self.filepath)}"
        )
        if no_uvs:
            self.report({'WARNING'}, message + f". {len(no_uvs)} meshes have no UVs")
        else:
            self.report({'INFO'}, message)
        return {'FINISHED'}


class AAT_OT_import_painted_textures(Operator):
    bl_idname = "aat.import_painted_textures"
    bl_label = "Import Painted Textures"
    bl_description = (
        "Point this at the folder Substance Painter exported to and it wires "
        "every texture into the matching material for you: base colour, normal, "
        "metallic, roughness and emission, each with the right colour space. "
        "Unity's packed Metallic Smoothness and Albedo Transparency maps are "
        "unpacked automatically"
    )
    bl_options = {'REGISTER', 'UNDO'}

    directory: StringProperty(subtype='DIR_PATH')
    files: CollectionProperty(type=OperatorFileListElement)
    filter_glob: StringProperty(
        default="*.png;*.tga;*.jpg;*.jpeg;*.tif;*.tiff;*.exr;*.bmp",
        options={'HIDDEN'},
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        return bool(collect_materials(target_meshes(context)))

    def invoke(self, context: Context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context: Context):
        if not self.directory or not os.path.isdir(self.directory):
            self.report({'ERROR'}, "Pick the folder Substance Painter exported to")
            return {'CANCELLED'}

        materials = collect_materials(target_meshes(context))
        if not materials:
            self.report({'ERROR'}, "No materials found on the selected meshes")
            return {'CANCELLED'}

        entries = [
            name for name in os.listdir(self.directory)
            if name.lower().endswith(_IMAGE_EXTENSIONS)
        ]
        if not entries:
            self.report({'ERROR'}, "No image files in that folder")
            return {'CANCELLED'}

        by_material: dict[str, dict[str, str]] = {}
        directx = False
        for entry in entries:
            stem = os.path.splitext(entry)[0]
            match = None
            for material in materials:
                for candidate in {material.name, safe_material_name(material.name)}:
                    prefix = candidate.lower() + "_"
                    if stem.lower().startswith(prefix) and (
                        match is None or len(candidate) > len(match[1])
                    ):
                        match = (material, candidate)
            if match is None:
                continue
            material, candidate = match
            suffix = stem[len(candidate) + 1:]
            key = re.sub(r"[^a-z0-9]", "", suffix.lower())
            map_type = _SUFFIX_TYPES.get(key)
            if map_type is None:
                continue
            if map_type == 'NORMAL_DX':
                directx = True
                map_type = 'NORMAL'
            by_material.setdefault(material.name, {})[map_type] = os.path.join(
                self.directory, entry)

        if not by_material:
            self.report(
                {'ERROR'},
                "No textures matched a material name. Substance Painter names "
                "files after the texture set, so run Prep for Painter first",
            )
            return {'CANCELLED'}

        wired = 0
        for material in materials:
            found = by_material.get(material.name)
            if not found:
                continue
            self._build(material, found)
            wired += len(found)

        message = f"Wired {wired} textures into {len(by_material)} materials"
        if directx:
            self.report(
                {'WARNING'},
                message + ". DirectX normals detected; re-export from Painter as "
                "OpenGL or the lighting will look inverted",
            )
        else:
            self.report({'INFO'}, message)
        return {'FINISHED'}

    def _build(self, material, found) -> None:
        tree, bsdf = _principled(material)
        _clear_previous(tree)
        base_x = bsdf.location.x - 900.0
        row = 400.0

        def place(map_type):
            nonlocal row
            image = bpy.data.images.load(found[map_type], check_existing=True)
            node = _image_node(tree, image, map_type, base_x, row)
            row -= 320.0
            return node

        links = tree.links
        if 'BASE_ALPHA' in found:
            node = place('BASE_ALPHA')
            links.new(node.outputs['Color'], bsdf.inputs['Base Color'])
            links.new(node.outputs['Alpha'], bsdf.inputs['Alpha'])
        elif 'BASE' in found:
            node = place('BASE')
            links.new(node.outputs['Color'], bsdf.inputs['Base Color'])

        if 'ALPHA' in found:
            node = place('ALPHA')
            links.new(node.outputs['Color'], bsdf.inputs['Alpha'])

        if 'METALLIC_SMOOTHNESS' in found:
            node = place('METALLIC_SMOOTHNESS')
            separate = _new_node(
                tree, 'ShaderNodeSeparateColor', base_x + 300.0, node.location.y)
            links.new(node.outputs['Color'], separate.inputs['Color'])
            links.new(separate.outputs['Red'], bsdf.inputs['Metallic'])
            invert = _new_node(
                tree, 'ShaderNodeInvert', base_x + 300.0, node.location.y - 160.0)
            links.new(node.outputs['Alpha'], invert.inputs['Color'])
            links.new(invert.outputs['Color'], bsdf.inputs['Roughness'])
        else:
            if 'METALLIC' in found:
                node = place('METALLIC')
                links.new(node.outputs['Color'], bsdf.inputs['Metallic'])
            if 'ROUGHNESS' in found:
                node = place('ROUGHNESS')
                links.new(node.outputs['Color'], bsdf.inputs['Roughness'])
            elif 'SMOOTHNESS' in found:
                node = place('SMOOTHNESS')
                invert = _new_node(
                    tree, 'ShaderNodeInvert', base_x + 300.0, node.location.y)
                links.new(node.outputs['Color'], invert.inputs['Color'])
                links.new(invert.outputs['Color'], bsdf.inputs['Roughness'])

        if 'NORMAL' in found:
            node = place('NORMAL')
            normal_map = _new_node(
                tree, 'ShaderNodeNormalMap', base_x + 300.0, node.location.y)
            links.new(node.outputs['Color'], normal_map.inputs['Color'])
            links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])

        if 'EMISSION' in found:
            node = place('EMISSION')
            links.new(node.outputs['Color'], bsdf.inputs['Emission Color'])
            bsdf.inputs['Emission Strength'].default_value = 1.0

        for extra in ('AO', 'HEIGHT'):
            if extra in found:
                place(extra)

        if ('BASE_ALPHA' in found or 'ALPHA' in found) and hasattr(
            material, "surface_render_method"
        ):
            material.surface_render_method = 'DITHERED'


class AAT_OT_fix_colorspaces(Operator):
    bl_idname = "aat.fix_colorspaces"
    bl_label = "Fix Colour Spaces"
    bl_description = (
        "The classic Blender-to-Unity gotcha: fixes every texture's colour "
        "space so colour maps stay sRGB and data maps (normal, metallic, "
        "roughness, AO) become Non-Colour, which stops washed-out or flat "
        "shading in Unity"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        return bool(collect_materials(target_meshes(context)))

    def execute(self, context: Context):
        data_sockets = {'Metallic', 'Roughness', 'Normal', 'Alpha', 'Specular IOR Level'}
        color_sockets = {'Base Color', 'Emission Color'}
        fixed = 0
        for material in collect_materials(target_meshes(context)):
            tree = material.node_tree
            if tree is None:
                continue
            for node in tree.nodes:
                if node.type != 'TEX_IMAGE' or node.image is None:
                    continue
                wants_data = None
                for link in tree.links:
                    if link.from_node != node:
                        continue
                    target = link.to_node
                    socket = link.to_socket.name
                    if target.type in {'NORMAL_MAP', 'BUMP', 'SEPARATE_COLOR', 'INVERT'}:
                        wants_data = True
                    elif socket in data_sockets:
                        wants_data = True
                    elif socket in color_sockets:
                        wants_data = False
                if wants_data is None:
                    continue
                wanted = 'Non-Color' if wants_data else 'sRGB'
                if node.image.colorspace_settings.name != wanted:
                    node.image.colorspace_settings.name = wanted
                    fixed += 1
        self.report({'INFO'}, f"Corrected the colour space on {fixed} textures")
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_prep_for_painter,
    AAT_OT_export_for_painter,
    AAT_OT_import_painted_textures,
    AAT_OT_fix_colorspaces,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
