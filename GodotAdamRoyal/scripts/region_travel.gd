extends Node
## Region travel for Adam Royal. Keeps the existing Manila scene intact.
## Travel order: 1 Manila, 2 Amman, 3 San Francisco, 4 Chicago.
const REGION_PATHS := {
	"Amman": "res://assets/cities/tabarbour/Tabarbour.obj",
	"San Francisco": "res://assets/cities/san_francisco/SanFrancisco_City.obj",
	"Chicago": "res://assets/cities/chicago/Chicago.obj"
}
var active_region := "Manila"
var active_root: Node3D
var player: CharacterBody3D
var hud_label: Label

func _ready() -> void:
	await get_tree().process_frame
	player = get_tree().current_scene.get_node_or_null("Player") as CharacterBody3D
	# Every fresh game session starts in Manila; other regions are opt-in travel destinations.
	active_region = "Manila"
	_set_manila_visible(true)
	_build_travel_hud()
	for region_name in REGION_PATHS.keys():
		_validate_region_asset(region_name)
	print("REGION_TRAVEL_READY regions=Manila,Amman,San Francisco,Chicago")

func _validate_region_asset(region: String) -> void:
	var path: String = REGION_PATHS[region]
	if not ResourceLoader.exists(path):
		push_error("TRAVEL_ASSET_IMPORT_FAIL region=" + region + " path=" + path)
		print("TRAVEL_ASSET_IMPORT_FAIL region=" + region)
		return
	var resource = load(path)
	var mesh: Mesh = resource as Mesh
	if mesh == null and resource is PackedScene:
		var packed_root := (resource as PackedScene).instantiate()
		mesh = _combine_meshes(packed_root)
		packed_root.free()
	if mesh == null or mesh.get_surface_count() == 0:
		push_error("TRAVEL_ASSET_IMPORT_FAIL region=" + region + " no mesh surfaces")
		print("TRAVEL_ASSET_IMPORT_FAIL region=" + region)
		return
	print("TRAVEL_ASSET_IMPORT_PASS region=" + region + " surfaces=" + str(mesh.get_surface_count()) + " vertices=" + str(_mesh_vertex_count(mesh)))

func _unhandled_key_input(event: InputEvent) -> void:
	if not event.pressed or event.echo:
		return
	match event.keycode:
		KEY_1: travel_to("Manila")
		KEY_2: travel_to("Amman")
		KEY_3: travel_to("San Francisco")
		KEY_4: travel_to("Chicago")

func travel_to(region: String) -> void:
	if region == active_region:
		return
	if region == "Manila":
		if is_instance_valid(active_root):
			active_root.queue_free()
			active_root = null
		_set_manila_visible(true)
		active_region = "Manila"
		_place_player(Vector3.ZERO)
		_update_hud()
		print("REGION_TRAVEL_SUCCESS region=Manila")
		return
	var path: String = REGION_PATHS.get(region, "")
	if path.is_empty() or not ResourceLoader.exists(path):
		push_error("Travel region asset is missing: " + path)
		print("REGION_TRAVEL_FAILED region=" + region + " missing=" + path)
		return
	var resource = load(path)
	var imported_mesh: Mesh
	if resource is Mesh:
		imported_mesh = resource as Mesh
	elif resource is PackedScene:
		var packed_root := (resource as PackedScene).instantiate()
		imported_mesh = _combine_meshes(packed_root)
		packed_root.free()
	if imported_mesh == null or imported_mesh.get_surface_count() == 0:
		push_error("Could not load a renderable OBJ mesh for region: " + region)
		print("REGION_TRAVEL_FAILED region=" + region + " invalid_mesh=true")
		return
	var root := Node3D.new()
	root.name = region.replace(" ", "") + "TravelRegion"
	var city_mesh := MeshInstance3D.new()
	city_mesh.name = "ImportedCityGeometry"
	city_mesh.mesh = imported_mesh
	root.add_child(city_mesh)
	var bounds := city_mesh.get_aabb()
	if bounds.size.length() <= 0.001:
		root.queue_free()
		push_error("Imported region has empty bounds: " + region)
		return
	# Center the source geometry and normalize huge OBJ coordinates to a walkable scene scale.
	var center := bounds.get_center()
	city_mesh.position = Vector3(-center.x, -bounds.position.y, -center.z)
	var horizontal_span := maxf(bounds.size.x, bounds.size.z)
	var scale_factor := 1.0
	if horizontal_span > 1200.0:
		scale_factor = 1200.0 / horizontal_span
	elif horizontal_span < 80.0:
		scale_factor = 80.0 / maxf(horizontal_span, 0.01)
	root.scale = Vector3.ONE * scale_factor
	var static_body := StaticBody3D.new()
	static_body.name = "ImportedCityCollision"
	static_body.position = city_mesh.position
	var collision := CollisionShape3D.new()
	collision.shape = imported_mesh.create_trimesh_shape()
	static_body.add_child(collision)
	root.add_child(static_body)
	get_tree().current_scene.add_child(root)
	if is_instance_valid(active_root):
		active_root.queue_free()
	active_root = root
	_set_manila_visible(false)
	active_region = region
	_place_player(Vector3(0.0, maxf(2.0, bounds.size.y * scale_factor * 0.04), 0.0))
	_update_hud()
	print("REGION_TRAVEL_SUCCESS region=" + region + " surfaces=" + str(imported_mesh.get_surface_count()) + " vertices=" + str(_mesh_vertex_count(imported_mesh)) + " bounds=" + str(bounds) + " scale=" + str(scale_factor))

func _combine_meshes(root: Node) -> Mesh:
	var combined := ArrayMesh.new()
	for item in root.find_children("*", "MeshInstance3D", true, false):
		var instance := item as MeshInstance3D
		if instance.mesh == null:
			continue
		for surface in range(instance.mesh.get_surface_count()):
			var arrays := instance.mesh.surface_get_arrays(surface)
			if arrays.is_empty():
				continue
			var tool := SurfaceTool.new()
			tool.begin(Mesh.PRIMITIVE_TRIANGLES)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			if indices.size() > 0:
				for index in indices:
					tool.set_uv(arrays[Mesh.ARRAY_TEX_UV][index] if arrays[Mesh.ARRAY_TEX_UV].size() > index else Vector2.ZERO)
					tool.add_vertex(instance.global_transform * vertices[index])
			else:
				for vertex in vertices:
					tool.add_vertex(instance.global_transform * vertex)
			tool.commit(combined)
	return combined if combined.get_surface_count() > 0 else null

func _mesh_vertex_count(mesh: Mesh) -> int:
	var total := 0
	for i in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(i)
		if not arrays.is_empty():
			total += (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()
	return total

func _set_manila_visible(visible: bool) -> void:
	var scene := get_tree().current_scene
	for node_name in ["ManilaRealWorldDistrict", "ManilaOSMFallback", "ManilaSRTMElevationTerrain"]:
		var node := scene.get_node_or_null(node_name)
		if node != null:
			node.visible = visible
	var ground := scene.get_node_or_null("WalkableGround")
	if ground != null:
		ground.visible = visible

func _place_player(position: Vector3) -> void:
	if not is_instance_valid(player):
		player = get_tree().current_scene.get_node_or_null("Player") as CharacterBody3D
	if is_instance_valid(player):
		player.global_position = position + Vector3.UP * 2.0
		player.velocity = Vector3.ZERO

func _build_travel_hud() -> void:
	var layer := CanvasLayer.new()
	layer.name = "RegionTravelHUD"
	add_child(layer)
	var panel := PanelContainer.new()
	panel.position = Vector2(20, 145)
	layer.add_child(panel)
	var column := VBoxContainer.new()
	panel.add_child(column)
	var title := Label.new()
	title.text = "TRAVEL REGIONS"
	title.add_theme_font_size_override("font_size", 16)
	column.add_child(title)
	hud_label = Label.new()
	column.add_child(hud_label)
	_update_hud()

func _update_hud() -> void:
	if is_instance_valid(hud_label):
		hud_label.text = "1  Manila\n2  Amman\n3  San Francisco\n4  Chicago\nCurrent: " + active_region
