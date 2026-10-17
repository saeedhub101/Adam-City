extends Node3D

const CityBuilder = preload("res://scripts/osm_city.gd")
const PlayerScene = preload("res://scenes/player.tscn")

var city_builder: Node3D

func _ready() -> void:
	_build_environment()
	_build_ground()
	var city_result := _build_city()
	var player = PlayerScene.instantiate()
	player.position = Vector3(0, 0.25, 12)
	add_child(player)
	_build_hud(int(city_result.get("buildings", 0)), int(city_result.get("roads", 0)), bool(city_result.get("ok", false)))

	if OS.get_cmdline_user_args().has("--qa-capture"):
		call_deferred("_run_visual_qa_capture")

func _run_visual_qa_capture() -> void:
	# Capture the rendered game viewport, not a generated mockup or a headless placeholder.
	var output_dir := ProjectSettings.globalize_path("res://qa_screenshots")
	DirAccess.make_dir_recursive_absolute(output_dir)
	var camera := Camera3D.new()
	camera.name = "VisualQACamera"
	camera.current = true
	camera.fov = 72.0
	add_child(camera)
	var player := get_node_or_null("Player")
	var captures := [
		{"name": "01-aerial-full-map.png", "position": Vector3(0, 1350, 30), "target": Vector3(0, 0, 0)},
		{"name": "02-street-west.png", "position": Vector3(-95, 28, 35), "target": Vector3(-30, 2, 20)},
		{"name": "03-street-east.png", "position": Vector3(115, 24, -70), "target": Vector3(40, 2, -15)},
		{"name": "04-street-north.png", "position": Vector3(-45, 32, -125), "target": Vector3(-10, 2, -45)},
		{"name": "05-street-south.png", "position": Vector3(70, 22, 135), "target": Vector3(20, 2, 65)}
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
		print("QA_SCREENSHOT=" + output_path + " SIZE=" + str(image.get_size()))
	# A dedicated close third-person view confirms the imported player mesh is present in the rendered scene.
	if player != null:
		camera.global_position = Vector3(0, 4.2, 0)
		camera.look_at(Vector3(0, 1.0, 12), Vector3.UP)
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
	print("VISUAL_QA_CAPTURE_COUNT=6")
	get_tree().quit(0)

func _build_city() -> Dictionary:
	# The workflow stages a textured, real-geography Manila GLB here before import.
	var map_path := "res://assets/manila_city.glb"
	if FileAccess.file_exists(map_path):
		var packed_map := load(map_path) as PackedScene
		if packed_map != null:
			var city := packed_map.instantiate()
			city.name = "ManilaRealWorldDistrict"
			add_child(city)
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
	env.ambient_light_energy = 0.7
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	world.environment = env
	add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48, -28, 0)
	sun.light_energy = 1.35
	sun.shadow_enabled = true
	add_child(sun)

func _build_ground() -> void:
	var ground := StaticBody3D.new()
	ground.name = "WalkableGround"
	ground.position.y = -0.12
	var collision := CollisionShape3D.new()
	collision.shape = WorldBoundaryShape3D.new()
	ground.add_child(collision)
	add_child(ground)
	var plane := MeshInstance3D.new()
	var plane_mesh := PlaneMesh.new()
	plane_mesh.size = Vector2(5000, 5000)
	plane.mesh = plane_mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.28, 0.31, 0.28)
	mat.roughness = 1.0
	plane.material_override = mat
	plane.position.y = -0.13
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
