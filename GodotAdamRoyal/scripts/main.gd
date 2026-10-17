extends Node3D

const CityBuilder = preload("res://scripts/osm_city.gd")
const PlayerScene = preload("res://scenes/player.tscn")

var city_builder: Node3D
var status_label: Label

func _ready() -> void:
	_build_environment()
	city_builder = CityBuilder.new()
	city_builder.name = "ManilaRealCity"
	add_child(city_builder)
	var result: Dictionary = city_builder.load_city()
	var player = PlayerScene.instantiate()
	player.position = Vector3(0, 0.25, 12)
	add_child(player)
	_build_hud(int(result.get("buildings", 0)), int(result.get("roads", 0)), bool(result.get("ok", false)))

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

func _build_hud(buildings: int, roads: int, loaded: bool) -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var panel := PanelContainer.new()
	panel.position = Vector2(20, 20)
	panel.custom_minimum_size = Vector2(410, 100)
	layer.add_child(panel)
	var column := VBoxContainer.new()
	panel.add_child(column)
	var heading := Label.new()
	heading.text = "ADAM ROYAL  /  MANILA, PHILIPPINES"
	heading.add_theme_font_size_override("font_size", 20)
	column.add_child(heading)
	status_label = Label.new()
	if loaded:
		status_label.text = "REAL OPENSTREETMAP GEOMETRY  •  %d buildings  •  %d road segments" % [buildings, roads]
	else:
		status_label.text = "CITY DATA MISSING — run Tools/build_manila_city.py before launching"
	column.add_child(status_label)
	var help := Label.new()
	help.text = "WASD move  •  Mouse look  •  Space jump  •  Esc releases mouse"
	column.add_child(help)
	var attribution := Label.new()
	attribution.text = "Map data © OpenStreetMap contributors"
	attribution.add_theme_font_size_override("font_size", 12)
	column.add_child(attribution)
