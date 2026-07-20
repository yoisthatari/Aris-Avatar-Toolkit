import os

import bpy
from bpy.props import CollectionProperty, FloatProperty, StringProperty
from bpy.types import Context, Operator, OperatorFileListElement

from ..core import common

MMD_TOOLS_URL = "https://extensions.blender.org/add-ons/mmd-tools/"


def op_exists(namespace: str, name: str) -> bool:
    try:
        getattr(getattr(bpy.ops, namespace), name).get_rna_type()
        return True
    except Exception:
        return False


def mmd_tools_available() -> bool:
    return op_exists("mmd_tools", "import_model")


def vrm_available() -> bool:
    return op_exists("import_scene", "vrm")


class AAT_OT_import_model(Operator):
    bl_idname = "aat.import_model"
    bl_label = "Import Model"
    bl_description = (
        "Bring your model home in any supported format. PMX/PMD imports through "
        "the official MMD Tools extension, VRM through the VRM add-on, and FBX, "
        "glTF, OBJ and more through Blender's cozy built-in importers"
    )
    bl_options = {'REGISTER', 'UNDO'}

    filepath: StringProperty(subtype='FILE_PATH')
    directory: StringProperty(subtype='DIR_PATH')
    files: CollectionProperty(type=OperatorFileListElement)
    filter_glob: StringProperty(
        default="*.pmx;*.pmd;*.fbx;*.vrm;*.glb;*.gltf;*.obj;*.dae;*.stl",
        options={'HIDDEN'},
    )
    mmd_scale: FloatProperty(
        name="MMD Scale",
        description="Import scale for PMX/PMD models (0.08 matches meters)",
        default=0.08,
        min=0.001,
        max=10.0,
    )

    def invoke(self, context: Context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context: Context):
        if self.files and self.directory:
            paths = [os.path.join(self.directory, f.name) for f in self.files if f.name]
        elif self.filepath:
            paths = [self.filepath]
        else:
            self.report({'ERROR'}, "No file selected")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        before = set(bpy.data.objects)
        imported = 0
        for path in paths:
            if self._import_one(context, path):
                imported += 1

        if imported == 0:
            return {'CANCELLED'}

        new_armatures = [
            obj for obj in bpy.data.objects
            if obj not in before and obj.type == 'ARMATURE'
        ]
        if new_armatures:
            context.scene.aat.armature = new_armatures[0]

        self.report({'INFO'}, f"Imported {imported} of {len(paths)} files")
        return {'FINISHED'}

    def _import_one(self, context: Context, path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in (".pmx", ".pmd"):
                if not mmd_tools_available():
                    self.report(
                        {'ERROR'},
                        "PMX/PMD needs the MMD Tools extension. Use the Install "
                        "MMD Tools button in the panel",
                    )
                    return False
                bpy.ops.mmd_tools.import_model(
                    filepath=path, scale=self.mmd_scale, clean_model=True)
            elif ext == ".vrm":
                if not vrm_available():
                    self.report(
                        {'ERROR'},
                        "VRM needs the VRM add-on (VRM format extension)",
                    )
                    return False
                bpy.ops.import_scene.vrm(filepath=path)
            elif ext == ".fbx":
                bpy.ops.import_scene.fbx(filepath=path)
            elif ext in (".glb", ".gltf"):
                bpy.ops.import_scene.gltf(filepath=path)
            elif ext == ".obj":
                bpy.ops.wm.obj_import(filepath=path)
            elif ext == ".stl":
                bpy.ops.wm.stl_import(filepath=path)
            elif ext == ".dae":
                if not op_exists("wm", "collada_import"):
                    self.report({'ERROR'}, "Collada import is not available in this Blender build")
                    return False
                bpy.ops.wm.collada_import(filepath=path)
            else:
                self.report({'ERROR'}, f"Unsupported format: {ext}")
                return False
        except RuntimeError as exc:
            self.report({'ERROR'}, f"Import failed for {os.path.basename(path)}: {exc}")
            return False
        return True


class AAT_OT_export_model(Operator):
    bl_idname = "aat.export_model"
    bl_label = "Export Model"
    bl_description = (
        "Export your gorgeous model as FBX with avatar-safe settings: shape "
        "keys preserved, no leaf bones, textures embedded, Unity-friendly scale"
    )
    bl_options = {'REGISTER'}

    filepath: StringProperty(subtype='FILE_PATH')
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})
    check_existing: bpy.props.BoolProperty(default=True, options={'HIDDEN'})

    @classmethod
    def poll(cls, context: Context) -> bool:
        return common.get_armature(context) is not None

    def invoke(self, context: Context, event):
        if not self.filepath:
            blend = bpy.data.filepath
            base = os.path.splitext(os.path.basename(blend))[0] if blend else "model"
            self.filepath = os.path.join(os.path.dirname(blend), base + ".fbx")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context: Context):
        armature = common.get_armature(context)
        meshes = common.get_armature_meshes(context, armature)
        if not meshes:
            self.report({'ERROR'}, "The armature has no meshes to export")
            return {'CANCELLED'}
        if not self.filepath:
            self.report({'ERROR'}, "No file path given")
            return {'CANCELLED'}

        common.ensure_object_mode(context)
        for obj in context.view_layer.objects:
            obj.select_set(False)
        armature.hide_set(False)
        armature.select_set(True)
        for mesh in meshes:
            mesh.hide_set(False)
            mesh.select_set(True)
        context.view_layer.objects.active = armature

        tris = sum(common.triangle_count(m) for m in meshes)
        materials = set()
        for mesh in meshes:
            for slot in mesh.material_slots:
                if slot.material:
                    materials.add(slot.material.name)

        try:
            bpy.ops.export_scene.fbx(
                filepath=self.filepath,
                use_selection=True,
                object_types={'ARMATURE', 'MESH', 'EMPTY'},
                use_mesh_modifiers=False,
                mesh_smooth_type='FACE',
                add_leaf_bones=False,
                bake_anim=False,
                apply_scale_options='FBX_SCALE_ALL',
                path_mode='COPY',
                embed_textures=True,
                primary_bone_axis='Y',
                secondary_bone_axis='X',
            )
        except RuntimeError as exc:
            self.report({'ERROR'}, f"Export failed: {exc}")
            return {'CANCELLED'}

        message = (
            f"Exported {len(meshes)} meshes, {tris:,} triangles, "
            f"{len(materials)} materials to {os.path.basename(self.filepath)}"
        )
        if tris > 70000:
            self.report({'WARNING'}, message + ". Triangle count is above 70k")
        else:
            self.report({'INFO'}, message)
        return {'FINISHED'}


class AAT_OT_install_mmd_tools(Operator):
    bl_idname = "aat.install_mmd_tools"
    bl_label = "Install MMD Tools"
    bl_description = (
        "Beautifully installs the official MMD Tools extension from "
        "extensions.blender.org for PMX/PMD import. Falls back to opening the "
        "download page"
    )
    bl_options = {'REGISTER'}

    def execute(self, context: Context):
        if mmd_tools_available():
            self.report({'INFO'}, "MMD Tools is already installed")
            return {'FINISHED'}
        if not bpy.app.online_access:
            bpy.ops.wm.url_open(url=MMD_TOOLS_URL)
            self.report(
                {'WARNING'},
                "Online access is disabled in Blender's preferences; opened the "
                "MMD Tools page instead",
            )
            return {'FINISHED'}
        try:
            repos = context.preferences.extensions.repos
            repo_index = -1
            for index, repo in enumerate(repos):
                if repo.enabled and "extensions.blender.org" in (repo.remote_url or ""):
                    repo_index = index
                    break
            if repo_index < 0:
                raise RuntimeError("extensions.blender.org repository not configured")
            bpy.ops.extensions.repo_sync(repo_index=repo_index)
            bpy.ops.extensions.package_install(repo_index=repo_index, pkg_id="mmd_tools")
        except Exception:
            bpy.ops.wm.url_open(url=MMD_TOOLS_URL)
            self.report(
                {'WARNING'},
                "Automatic install failed; opened the MMD Tools page so you can "
                "install it manually",
            )
            return {'FINISHED'}
        if mmd_tools_available():
            self.report({'INFO'}, "MMD Tools installed")
        else:
            self.report(
                {'INFO'},
                "MMD Tools install started; PMX import will work once it finishes",
            )
        return {'FINISHED'}


_CLASSES = (
    AAT_OT_import_model,
    AAT_OT_export_model,
    AAT_OT_install_mmd_tools,
)


def register() -> None:
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
