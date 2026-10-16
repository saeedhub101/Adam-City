"""Convert Saeed's GLB to an FBX suitable for UEFN import, using Blender's own import/export pipeline."""
import os
import sys
import bpy

def args_after_separator():
    if "--" not in sys.argv:
        raise RuntimeError("Expected arguments after Blender's -- separator: input.glb output.fbx")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 2:
        raise RuntimeError("Expected exactly two arguments: input.glb output.fbx")
    return os.path.abspath(args[0]), os.path.abspath(args[1])

def validate_scene(stage):
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    if not meshes:
        raise RuntimeError(f"{stage}: no mesh was found")
    if not armatures:
        raise RuntimeError(f"{stage}: no armature/skeleton was found; refusing to package a static-only conversion")
    skinned = [mesh for mesh in meshes if any(mod.type == "ARMATURE" for mod in mesh.modifiers)]
    if not skinned:
        raise RuntimeError(f"{stage}: mesh exists but no mesh has an Armature modifier")
    shape_key_count = sum(len(mesh.data.shape_keys.key_blocks) - 1 for mesh in meshes if mesh.data.shape_keys)
    action_count = len(bpy.data.actions)
    print(f"{stage}: meshes={len(meshes)}, armatures={len(armatures)}, skinned_meshes={len(skinned)}, shape_keys={shape_key_count}, actions={action_count}")
    return meshes, armatures

def main():
    source, destination = args_after_separator()
    if not os.path.isfile(source):
        raise RuntimeError(f"Input GLB does not exist: {source}")
    os.makedirs(os.path.dirname(destination), exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.import_scene.gltf(filepath=source)
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender GLB import did not finish: {result}")
    meshes, armatures = validate_scene("GLB import")

    # Export only model-related objects, preserving skinning, shape keys, and animation tracks where supported.
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type in {"MESH", "ARMATURE", "EMPTY"}:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = armatures[0]
    result = bpy.ops.export_scene.fbx(
        filepath=destination,
        use_selection=True,
        object_types={"MESH", "ARMATURE", "EMPTY"},
        add_leaf_bones=False,
        bake_anim=True,
        bake_anim_use_all_actions=True,
        use_mesh_modifiers=True,
        use_armature_deform_only=False,
        mesh_smooth_type="FACE",
        path_mode="COPY",
        embed_textures=True,
        axis_forward="-Z",
        axis_up="Y",
    )
    if "FINISHED" not in result or not os.path.isfile(destination):
        raise RuntimeError(f"FBX export failed: {result}")
    if os.path.getsize(destination) < 1024:
        raise RuntimeError("Exported FBX is unexpectedly small")

    # Re-import the FBX into a clean scene to catch broken/empty exports before packaging.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.import_scene.fbx(filepath=destination, use_anim=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"FBX re-import did not finish: {result}")
    validate_scene("FBX round-trip validation")
    print(f"SUCCESS: {destination} ({os.path.getsize(destination)} bytes)")

if __name__ == "__main__":
    main()
