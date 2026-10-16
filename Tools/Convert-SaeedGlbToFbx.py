"""Convert Saeed's GLB to FBX for UEFN using Blender, validating rigging and blendshape preservation."""
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
    shape_key_count = sum(
        max(0, len(mesh.data.shape_keys.key_blocks) - 1)
        for mesh in meshes if mesh.data.shape_keys
    )
    action_count = len(bpy.data.actions)
    print(
        f"{stage}: meshes={len(meshes)}, armatures={len(armatures)}, "
        f"skinned_meshes={len(skinned)}, shape_keys={shape_key_count}, actions={action_count}"
    )
    return {
        "meshes": meshes,
        "armatures": armatures,
        "shape_keys": shape_key_count,
        "actions": action_count,
    }


def main():
    source, destination = args_after_separator()
    if not os.path.isfile(source):
        raise RuntimeError(f"Input GLB does not exist: {source}")
    os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.import_scene.gltf(filepath=source)
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender GLB import did not finish: {result}")
    original = validate_scene("GLB import")

    # Keep mesh modifiers unapplied: applying modifiers can discard or invalidate shape keys.
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type in {"MESH", "ARMATURE", "EMPTY"}:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = original["armatures"][0]
    result = bpy.ops.export_scene.fbx(
        filepath=destination,
        use_selection=True,
        object_types={"MESH", "ARMATURE", "EMPTY"},
        add_leaf_bones=False,
        bake_anim=True,
        bake_anim_use_all_actions=True,
        use_mesh_modifiers=False,
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

    # Re-import into a clean scene and fail the package if rigging or existing blendshapes were lost.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.import_scene.fbx(filepath=destination, use_anim=True)
    if "FINISHED" not in result:
        raise RuntimeError(f"FBX re-import did not finish: {result}")
    converted = validate_scene("FBX round-trip validation")
    if original["shape_keys"] > 0 and converted["shape_keys"] < original["shape_keys"]:
        raise RuntimeError(
            f"FBX round-trip lost shape keys: source={original['shape_keys']}, "
            f"FBX={converted['shape_keys']}"
        )
    if original["actions"] > 0 and converted["actions"] == 0:
        raise RuntimeError("FBX round-trip lost all animation actions")
    print(
        f"SUCCESS: {destination} ({os.path.getsize(destination)} bytes); "
        f"shape_keys={converted['shape_keys']}, actions={converted['actions']}"
    )


if __name__ == "__main__":
    main()
