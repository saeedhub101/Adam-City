extends Node3D

const CityBuilder = preload("res://scripts/osm_city.gd")
const PlayerScene = preload("res://scenes/player.tscn")

var city_builder: Node3D
var city_bounds := AABB(Vector3(-500, 0, -500), Vector3(1000, 100, 1000))

func _ready() -> void:
	_build_environment()
	_build_ground()
	var city_result := _build_city()
	_build_real_elevation_terrain()
	city_bounds = _measure_city_bounds()
	var player = PlayerScene.instantiate()
	var city_center := city_bounds.get_center()
	var spawn_point := _find_nearest_road_point(Vector3(city_center.x, 0.0, city_center.z))
	player.position = Vector3(spawn_point.x, 0.25, spawn_point.z)
	add_child(player)
	_build_hud(int(city_result.get("buildings", 0)), int(city_result.get("roads", 0)), bool(city_result.get("ok", false)))

	if OS.get_cmdline_user_args().has("--qa-capture"):
		call_deferred("_run_city_asset_qa_capture")


func _run_city_asset_qa_capture() -> void:
	# QA explicitly renders the imported real-city assets, rather than the generated Manila blockout.
	var travel := get_node_or_null("RegionTravel")
	if travel == null:
		push_error("CITY_ASSET_QA_FAIL: RegionTravel node is missing")
		get_tree().quit(2)
		return
	travel.call("travel_to", "San Francisco")
	for i in range(8):
		await get_tree().process_frame
	var city_root := get_node_or_null("SanFranciscoTravelRegion")
	if city_root == null:
		push_error("CITY_ASSET_QA_FAIL: San Francisco asset could not be loaded")
		get_tree().quit(2)
		return
	var city_mesh: MeshInstance3D = city_root.get_node_or_null("ImportedCityGeometry") as MeshInstance3D
	if city_mesh == null or city_mesh.mesh == null:
		push_error("CITY_ASSET_QA_FAIL: imported San Francisco mesh is missing")
		get_tree().quit(2)
		return
	var bounds := city_mesh.get_aabb()
	var center := city_mesh.global_transform * bounds.get_center()
	var span := maxf(maxf(bounds.size.x, bounds.size.z) * city_root.scale.x, 80.0)
	var output_dir := ProjectSettings.globalize_path("res://qa_screenshots")
		DirAccess.make_dir_recursive_absolute(output_dir)
	var camera := Camera3D.new()
	camera.name = "CityAssetQACamera"
	camera.current = true
	camera.fov = 68.0
	add_child(camera)
	var player_node := get_node_or_null("Player")
	var captures := [
		{"name": "01-san-francisco-aerial.png", "position": center + Vector3(0.0, span * 0.85, 0.0), "target": center},
		{"name": "02-san-francisco-street-west.png", "position": center + Vector3(-span * 0.20, span * 0.035, 0.0), "target": center + Vector3(-span * 0.05, span * 0.02, 0.0)},
		{"name": "03-san-francisco-street-east.png", "position": center + Vector3(span * 0.20, span * 0.035, 0.0), "target": center + Vector3(span * 0.05, span * 0.02, 0.0)},
		{"name": "04-san-francisco-street-north.png", "position": center + Vector3(0.0, span * 0.035, -span * 0.20), "target": center + Vector3(0.0, span * 0.02, -span * 0.05)},
		{"name": "05-san-francisco-street-south.png", "position": center + Vector3(0.0, span * 0.035, span * 0.20), "target": center + Vector3(0.0, span * 0.02, span * 0.05)}
	]
	for shot in captures:
		camera.global_position = shot.position
		camera.look_at(shot.target, Vector3.UP)
		await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var image := get_viewport().get_texture().get_image()
		var path := output_dir.path_join(shot.name)
		if image.save_png(path) != OK:
			push_error("CITY_ASSET_QA_FAIL: screenshot save failed " + path)
			get_tree().quit(2)
			return
		print("CITY_ASSET_QA_IMAGE=" + path + " BYTES=" + str(FileAccess.get_file_as_bytes(path).size()))
	if player_node != null:
		camera.global_position = player_node.global_position + Vector3(1.7, 1.2, 2.8)
		camera.look_at(player_node.global_position + Vector3.UP, Vector3.UP)
		await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var player_image := get_viewport().get_texture().get_image()
		var player_path := output_dir.path_join("06-san-francisco-player.png")
		if player_image.save_png(player_path) != OK:
			push_error("CITY_ASSET_QA_FAIL: player screenshot save failed")
			get_tree().quit(2)
			return
		print("CITY_ASSET_QA_IMAGE=" + player_path + " BYTES=" + str(FileAccess.get_file_as_bytes(player_path).size()))
	else:
		push_error("CITY_ASSET_QA_FAIL: Player node is missing")
		get_tree().quit(2)
		return
	print("CITY_ASSET_QA_PASS city=SanFrancisco captures=6 source=imported_OBJ")
	print("VISUAL_QA_CAPTURE_COUNT=6")
	get_tree().quit(0)

func _run_visual_qa_capture() -> void:
	# Derive camera framing from the real imported map bounds instead of guessed coordinates.
	var output_dir := ProjectSettings.globalize_path("res://qa_screenshots")
	DirAccess.make_dir_recursive_absolute(output_dir)
	var camera := Camera3D.new()
	camera.name = "VisualQACamera"
	camera.current = true
	camera.fov = 68.0
	add_child(camera)
	var player := get_node_or_null("Player")
	var center := city_bounds.get_center()
	var map_center := Vector3(center.x, 0.12, center.z)
	var span := maxf(maxf(city_bounds.size.x, city_bounds.size.z), 100.0)
	var west_road := _find_nearest_road_point(map_center + Vector3(-span * 0.22, 0.0, 0.0))
	var east_road := _find_nearest_road_point(map_center + Vector3(span * 0.22, 0.0, 0.0))
	var north_road := _find_nearest_road_point(map_center + Vector3(0.0, 0.0, -span * 0.22))
	var south_road := _find_nearest_road_point(map_center + Vector3(0.0, 0.0, span * 0.22))
	var captures := [
		{"name": "01-aerial-full-map.png", "position": map_center + Vector3(0.0, span * 0.9, 0.0), "target": map_center},
		{"name": "02-street-west.png", "position": west_road + Vector3(-7.0, 4.2, 0.0), "target": west_road + Vector3(7.0, 1.8, 0.0)},
		{"name": "03-street-east.png", "position": east_road + Vector3(7.0, 4.2, 0.0), "target": east_road + Vector3(-7.0, 1.8, 0.0)},
		{"name": "04-street-north.png", "position": north_road + Vector3(0.0, 4.2, -7.0), "target": north_road + Vector3(0.0, 1.8, 7.0)},
		{"name": "05-street-south.png", "position": south_road + Vector3(0.0, 4.2, 7.0), "target": south_road + Vector3(0.0, 1.8, -7.0)}
	]
	for shot in captures:
		camera.global_position = shot.position
		camera.look_at(shot.target, Vector3.UP)
		await get_tree().process_frame
		await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var image := get_viewport().get_texture().get_image()
		var output_path := output_dir.path_join(shot.name)
		var error := image.save_png(output_path)
		if error != OK:
			push_error("QA screenshot save failed: " + output_path + " error=" + str(error))
			get_tree().quit(2)
			return
		print("QA_SCREENSHOT=" + output_path + " SIZE=" + str(image.get_size()) + " CITY_CENTER=" + str(center))
	if player != null:
		camera.global_position = player.global_position + Vector3(1.7, 1.2, 2.8)
		camera.look_at(player.global_position + Vector3.UP * 1.0, Vector3.UP)
		await get_tree().process_frame
		await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var player_image := get_viewport().get_texture().get_image()
		var player_path := output_dir.path_join("06-player-in-game.png")
		var player_error := player_image.save_png(player_path)
		if player_error != OK:
			push_error("Player screenshot save failed: " + player_path)
			get_tree().quit(2)
			return
		print("QA_SCREENSHOT=" + player_path + " CHARACTER_MODEL_LOADED=" + str(player.get("character_loaded")))
	else:
		push_error("Visual QA could not find Player node")
		get_tree().quit(2)
		return
	print("CITY_BOUNDS=" + str(city_bounds) + " CITY_CENTER=" + str(map_center))
	print("VISUAL_QA_CAPTURE_COUNT=6")
	get_tree().quit(0)

func _find_nearest_road_point(reference: Vector3) -> Vector3:
	var city := get_node_or_null("ManilaRealWorldDistrict")
	if city == null:
		return Vector3(reference.x, 0.12, reference.z)
	var best_point := Vector3(reference.x, 0.12, reference.z)
	var best_distance: float = INF
	for node in city.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := node as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		if not mesh_instance.name.to_lower().contains("asphalt") or mesh_instance.mesh.get_surface_count() == 0:
			continue
		var arrays: Array = mesh_instance.mesh.surface_get_arrays(0)
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		if indices.size() >= 3:
			for i in range(0, indices.size(), 3):
				var local_point: Vector3 = (vertices[indices[i]] + vertices[indices[i + 1]] + vertices[indices[i + 2]]) / 3.0
				var world_point: Vector3 = mesh_instance.global_transform * local_point
				var distance: float = Vector2(world_point.x - reference.x, world_point.z - reference.z).length_squared()
				if distance < best_distance:
					best_distance = distance
					best_point = Vector3(world_point.x, 0.12, world_point.z)
		else:
			for local_point in vertices:
				var world_point: Vector3 = mesh_instance.global_transform * local_point
				var distance: float = Vector2(world_point.x - reference.x, world_point.z - reference.z).length_squared()
				if distance < best_distance:
					best_distance = distance
					best_point = Vector3(world_point.x, 0.12, world_point.z)
	return best_point

func _measure_city_bounds() -> AABB:
	var combined := AABB()
	var found := false
	var city := get_node_or_null("ManilaRealWorldDistrict")
	if city == null:
		city = get_node_or_null("ManilaOSMFallback")
	if city != null:
		for node in city.find_children("*", "MeshInstance3D", true, false):
			var mesh_instance := node as MeshInstance3D
			if mesh_instance == null or mesh_instance.mesh == null:
				continue
			var bounds := mesh_instance.global_transform * mesh_instance.get_aabb()
			combined = bounds if not found else combined.merge(bounds)
			found = true
	if not found:
		push_warning("Could not measure imported city geometry; using conservative fallback bounds.")
		return AABB(Vector3(-1200, 0, -1200), Vector3(2400, 120, 2400))
	print("CITY_BOUNDS_MEASURED=" + str(combined))
	return combined

func _build_city() -> Dictionary:
	# The workflow stages a textured, real-geography Manila GLB here before import.
	var map_path := "res://assets/manila_city.glb"
	if FileAccess.file_exists(map_path):
		var packed_map := load(map_path) as PackedScene
		if packed_map != null:
			var city := packed_map.instantiate()
			city.name = "ManilaRealWorldDistrict"
			# The Manila GLB uses Z-up coordinates; Godot's world is Y-up.
			city.rotation_degrees = Vector3(-90.0, 0.0, 0.0)
			add_child(city)
			var collision_mesh_count := _add_city_collisions(city)
			print("CITY_COLLISION_MESHES=" + str(collision_mesh_count))
			var stats := _read_city_stats()
			stats["ok"] = true
			print("CITY_RENDER_SOURCE=GLB")
			print("CITY_BUILDINGS=%d CITY_ROADS=%d" % [int(stats.get("buildings", 0)), int(stats.get("roads", 0))])
			return stats
		push_error("Manila GLB exists but Godot could not load it: " + map_path)

	# Diagnostic fallback keeps the scene inspectable if the GLB is unavailable.
	city_builder = CityBuilder.new()
	city_builder.name = "ManilaOSMFallback"
	add_child(city_builder)
	var fallback_result: Dictionary = city_builder.load_city()
	print("CITY_RENDER_SOURCE=OSM_JSON_FALLBACK")
	return fallback_result

func _add_city_collisions(city: Node3D) -> int:
	var collision_mesh_count := 0
	for node in city.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := node as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		var is_facade := mesh_instance.name.to_lower().contains("facade")
		if not is_facade:
			for surface_index in range(mesh_instance.mesh.get_surface_count()):
				var material := mesh_instance.mesh.surface_get_material(surface_index)
				if material != null and material.resource_name.to_lower().contains("facade"):
					is_facade = true
					break
		if not is_facade:
			continue
		var shape: Shape3D = mesh_instance.mesh.create_trimesh_shape()
		if shape == null:
			push_error("Could not build collision for city mesh: " + mesh_instance.name)
			continue
		var body := StaticBody3D.new()
		body.name = mesh_instance.name + "_Collision"
		body.transform = mesh_instance.transform
		var collision := CollisionShape3D.new()
		collision.shape = shape
		body.add_child(collision)
		mesh_instance.get_parent().add_child(body)
		collision_mesh_count += 1
	return collision_mesh_count

func _read_city_stats() -> Dictionary:
	var path := "res://assets/manila_city.json"
	if not FileAccess.file_exists(path):
		return {"buildings": 0, "roads": 0}
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {"buildings": 0, "roads": 0}
	var parsed = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		return {"buildings": 0, "roads": 0}
	return {
		"buildings": int(parsed.get("buildings", []).size()) if parsed.get("buildings", null) is Array else int(parsed.get("buildings", 0)),
		"roads": int(parsed.get("roads", []).size()) if parsed.get("roads", null) is Array else int(parsed.get("roads", 0))
	}

func _build_real_elevation_terrain() -> void:
	var path := "res://assets/manila_terrain.json"
	if not FileAccess.file_exists(path):
		push_error("Real Manila elevation grid is missing; terrain must not be fabricated.")
		return
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("Could not open Manila elevation grid.")
		return
	var data = JSON.parse_string(file.get_as_text())
	if typeof(data) != TYPE_DICTIONARY:
		push_error("Manila elevation grid JSON is invalid.")
		return
	var grid_size := int(data.get("grid_size", 0))
	var heights: Array = data.get("heights_scaled_m", [])
	if grid_size < 10 or heights.size() != grid_size:
		push_error("Manila elevation grid has invalid dimensions.")
		return
	var south := float(data.bounds.south)
	var west := float(data.bounds.west)
	var north := float(data.bounds.north)
	var east := float(data.bounds.east)
	var lat0 := (south + north) * 0.5
	var lon0 := (west + east) * 0.5
	var tool := SurfaceTool.new()
	tool.begin(Mesh.PRIMITIVE_TRIANGLES)
	for row in range(grid_size - 1):
		if heights[row].size() != grid_size or heights[row + 1].size() != grid_size:
			push_error("Manila elevation grid row is incomplete.")
			return
		for col in range(grid_size - 1):
			var vertices: Array[Vector3] = []
			for cell in [Vector2i(row, col), Vector2i(row + 1, col), Vector2i(row, col + 1), Vector2i(row + 1, col + 1)]:
				var lat := north - (north - south) * float(cell.x) / float(grid_size - 1)
				var lon := west + (east - west) * float(cell.y) / float(grid_size - 1)
				var x := (lon - lon0) * 111320.0 * cos(deg_to_rad(lat0))
				var z := (lat - lat0) * 110540.0
				var elevation := float(heights[cell.x][cell.y]) + 0.02
				# Terrain is generated directly in Godot Y-up world coordinates.
				vertices.append(Vector3(x, elevation, z))
			# Counter-clockwise winding when viewed from above, so generated normals face upward.
			tool.set_color(Color(0.30, 0.32, 0.27)); tool.add_vertex(vertices[0])
			tool.set_color(Color(0.30, 0.32, 0.27)); tool.add_vertex(vertices[2])
			tool.set_color(Color(0.30, 0.32, 0.27)); tool.add_vertex(vertices[1])
			tool.set_color(Color(0.30, 0.32, 0.27)); tool.add_vertex(vertices[2])
			tool.set_color(Color(0.30, 0.32, 0.27)); tool.add_vertex(vertices[3])
			tool.set_color(Color(0.30, 0.32, 0.27)); tool.add_vertex(vertices[1])
	tool.generate_normals()
	var mesh := tool.commit()
	var material := StandardMaterial3D.new()
	material.vertex_color_use_as_albedo = true
	material.roughness = 1.0
	var terrain := MeshInstance3D.new()
	terrain.name = "ManilaSRTMElevationTerrain"
	terrain.mesh = mesh
	terrain.material_override = material
	# Do not rotate generated terrain: its vertices already use Godot Y-up coordinates.
	add_child(terrain)
	print("REAL_TERRAIN_LOADED source=" + str(data.get("source")) + " grid=" + str(grid_size) + "x" + str(grid_size) + " elevation_range_m=" + str(data.get("minimum_elevation_m")) + ".." + str(data.get("maximum_elevation_m")))

func _build_environment() -> void:
	var world := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.16, 0.36, 0.58)
	sky_mat.sky_horizon_color = Color(0.68, 0.78, 0.84)
	sky_mat.ground_bottom_color = Color(0.18, 0.2, 0.19)
	sky_mat.ground_horizon_color = Color(0.52, 0.56, 0.54)
	sky.sky_material = sky_mat
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.68, 0.72, 0.78)
	env.ambient_light_energy = 0.38
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	world.environment = env
	add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48, -28, 0)
	sun.light_energy = 0.85
	sun.shadow_enabled = true
	add_child(sun)

func _build_ground() -> void:
	var ground := StaticBody3D.new()
	ground.name = "WalkableGround"
	ground.position.y = 0.12
	var collision := CollisionShape3D.new()
	collision.shape = WorldBoundaryShape3D.new()
	ground.add_child(collision)
	add_child(ground)
	var plane := MeshInstance3D.new()
	var plane_mesh := PlaneMesh.new()
	plane_mesh.size = Vector2(5000, 5000)
	plane.mesh = plane_mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.22, 0.24, 0.21)
	mat.roughness = 1.0
	plane.material_override = mat
	plane.position.y = -0.35
	add_child(plane)

func _build_hud(buildings: int, roads: int, loaded: bool) -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var panel := PanelContainer.new()
	panel.position = Vector2(20, 20)
	panel.custom_minimum_size = Vector2(460, 110)
	layer.add_child(panel)
	var column := VBoxContainer.new()
	panel.add_child(column)
	var heading := Label.new()
	heading.text = "ADAM ROYAL  /  MANILA, PHILIPPINES"
	heading.add_theme_font_size_override("font_size", 20)
	column.add_child(heading)
	var status_label := Label.new()
	if loaded:
		status_label.text = "REAL CITY MODEL  •  %d mapped buildings  •  %d road ways" % [buildings, roads]
	else:
		status_label.text = "CITY DATA MISSING — map import failed"
	column.add_child(status_label)
	var help := Label.new()
	help.text = "WASD move  •  Mouse look  •  Space jump  •  Esc releases mouse"
	column.add_child(help)
	var attribution := Label.new()
	attribution.text = "Map data © OpenStreetMap contributors"
	attribution.add_theme_font_size_override("font_size", 12)
	column.add_child(attribution)
