"""Run inside Unreal Editor (Python Editor Script Plugin enabled).

Creates /Game/Maps/ManilaCentral as a native Unreal level, imports the cached
Manila GLB through the editor import pipeline, adds lighting, a ground plane,
and a PlayerStart. This script intentionally fails if Unreal cannot import the
GLB; it never creates a fake .umap or reports success from source-file checks.
"""
import os
import unreal

ROOT = os.path.abspath(os.path.join(unreal.Paths.project_dir(), ".."))
GLB = os.path.join(ROOT, "StandaloneBattleRoyale", "Content", "Maps", "Manila-Central-District.glb")
LEVEL_PACKAGE = "/Game/Maps/ManilaCentral"
IMPORT_PATH = "/Game/Maps/ManilaDistrictSource"

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def main():
    require(os.path.isfile(GLB), "Cached Manila GLB is missing: " + GLB)
    require(os.path.getsize(GLB) > 100000, "Cached Manila GLB is unexpectedly small.")

    tools = unreal.AssetToolsHelpers.get_asset_tools()
    task = unreal.AssetImportTask()
    task.filename = GLB
    task.destination_path = IMPORT_PATH
    task.automated = True
    task.replace_existing = True
    task.save = True
    tools.import_asset_tasks([task])
    imported = list(task.imported_object_paths or [])
    if not imported:
        # Some Interchange versions populate the destination without returning
        # imported_object_paths; discover assets from the destination instead.
        registry = unreal.AssetRegistryHelpers.get_asset_registry()
        imported = [a.object_path_string for a in registry.get_assets_by_path(
            unreal.Name(IMPORT_PATH), recursive=True
        )]
    require(imported, "Unreal import produced no assets. Enable the GLTF/Interchange importer plugin and rerun.")

    level_lib = unreal.EditorLevelLibrary
    require(level_lib.new_level(LEVEL_PACKAGE), "Could not create native level " + LEVEL_PACKAGE)
    world = unreal.EditorLevelLibrary.get_editor_world()
    require(world is not None, "New Unreal level has no editor world.")

    # Importers can emit a scene hierarchy or one/more static meshes. Place any
    # imported static meshes into the level; do not silently leave an empty map.
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    assets = registry.get_assets_by_path(unreal.Name(IMPORT_PATH), recursive=True)
    placed = 0
    for data in assets:
        asset = data.get_asset()
        if isinstance(asset, unreal.StaticMesh):
            actor = level_lib.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0))
            require(actor is not None, "Failed spawning imported static mesh actor.")
            actor.static_mesh_component.set_static_mesh(asset)
            placed += 1

    # GLB scene import may create a generated level or scene asset rather than
    # standalone meshes; still require that an import actually exists and leave
    # it discoverable for a manual placement pass instead of inventing geometry.
    require(placed > 0, "GLB imported but no StaticMesh assets were found to place in the level. Inspect Interchange scene-import output; level was not accepted as playable.")

    level_lib.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 12000))
    sky = level_lib.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000))
    if sky:
        sky.set_actor_label("Manila Sky Light")
    floor = level_lib.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -100))
    if floor:
        floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane"))
        floor.set_actor_scale3d(unreal.Vector(500, 500, 1))
        floor.set_actor_label("Temporary Ground Plane")
    start = level_lib.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0, 0, 300))
    require(start is not None, "Could not create PlayerStart.")
    start.set_actor_label("Manila Player Start")

    require(unreal.EditorLevelLibrary.save_current_level(), "Failed saving native .umap.")
    unreal.log("CREATED_NATIVE_LEVEL=" + LEVEL_PACKAGE + " | placed_static_meshes=" + str(placed))
    unreal.log_warning("Review map scale/origin and assign a visible skeletal character before claiming gameplay-ready.")
    return placed

main()
