extends Node3D

const SPLAT_NODE_SCRIPT := preload("res://addons/gdgs/runtime/nodes/gaussian_splat_node.gd")
const CITY_SCAN_PATH := "res://assets/real_city/helsinki_city_scan.ply"

const ARENA_SIZE := 220.0
const BOT_COUNT := 14
const STARTING_AMMO := 30
const MAX_HEALTH := 100.0

var player: CharacterBody3D
var camera_pivot: Node3D
var camera: Camera3D
var enemies: Array[CharacterBody3D] = []
var pickups: Array[Node3D] = []
var hud_label: Label
var status_label: Label
var center_label: Label
var restart_button: Button
var storm_ring: MeshInstance3D
var storm_radius := 92.0
var storm_timer := 0.0
var elapsed := 0.0
var player_health := MAX_HEALTH
var ammo := STARTING_AMMO
var reserve_ammo := 120
var fire_cooldown := 0.0
var reload_timer := 0.0
var enemy_count := BOT_COUNT
var game_over := false
var victory := false
var mouse_captured := true
var player_speed := 7.0
var rng := RandomNumberGenerator.new()

func _ready() -> void:
	rng.randomize()
	_setup_input()
	_build_world()
	_spawn_player()
	_spawn_bots()
	_build_hud()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	_update_hud()

func _setup_input() -> void:
	var actions := {
		"move_forward": [KEY_W, KEY_UP],
		"move_back": [KEY_S, KEY_DOWN],
		"move_left": [KEY_A, KEY_LEFT],
		"move_right": [KEY_D, KEY_RIGHT],
		"jump": [KEY_SPACE],
		"sprint": [KEY_SHIFT],
		"reload": [KEY_R],
		"restart": [KEY_ENTER]
	}
	for action in actions:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for keycode in actions[action]:
			var event := InputEventKey.new()
			event.keycode = keycode
			InputMap.action_add_event(action, event)
	if not InputMap.has_action("fire"):
		InputMap.add_action("fire")
	var fire_event := InputEventMouseButton.new()
	fire_event.button_index = MOUSE_BUTTON_LEFT
	InputMap.action_add_event("fire", fire_event)

func _build_world() -> void:
	var environment := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = Sky.new()
	env.sky.sky_material = ProceduralSkyMaterial.new()
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.62, 0.72, 0.86)
	env.ambient_light_energy = 0.8
	environment.environment = env
	add_child(environment)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48, -28, 0)
	sun.light_energy = 1.25
	sun.shadow_enabled = true
	add_child(sun)

	_add_box(self, "Arena", Vector3(0, -0.6, 0), Vector3(ARENA_SIZE, 1.0, ARENA_SIZE),
		Color(0.22, 0.38, 0.20), true)

	for i in range(4):
		var wall_size := Vector3(ARENA_SIZE, 3.0, 1.0) if i < 2 else Vector3(1.0, 3.0, ARENA_SIZE)
		var wall_pos: Vector3 = [Vector3(0, 1, -ARENA_SIZE / 2), Vector3(0, 1, ARENA_SIZE / 2),
			Vector3(-ARENA_SIZE / 2, 1, 0), Vector3(ARENA_SIZE / 2, 1, 0)][i]
		_add_box(self, "BoundaryWall_%02d" % i, wall_pos, wall_size, Color(0.12, 0.2, 0.14), true)

	_add_real_city_scan()


	storm_ring = MeshInstance3D.new()
	var ring := TorusMesh.new()
	ring.inner_radius = 0.94
	ring.outer_radius = 1.0
	ring.rings = 12
	ring.ring_segments = 64
	storm_ring.mesh = ring
	storm_ring.position.y = 0.16
	storm_ring.scale = Vector3(storm_radius, 1, storm_radius)
	storm_ring.material_override = _material(Color(0.2, 0.85, 1.0, 0.7), true)
	add_child(storm_ring)


func _add_real_city_scan() -> void:
	# Use a real photogrammetry/Gaussian-splat capture of Helsinki. No generated
	# box buildings are used as a substitute for the scan.
	var gaussian: Resource = load(CITY_SCAN_PATH)
	if gaussian == null:
		push_error("Real Helsinki city scan failed to import: " + CITY_SCAN_PATH)
		return
	var bounds: AABB = gaussian.get("aabb")
	var scan: Node3D = SPLAT_NODE_SCRIPT.new()
	scan.name = "HelsinkiPhotogrammetryCity"
	scan.set("gaussian", gaussian)
	add_child(scan)
	# The PLY capture is Y-up. Keep the renderer's default horizontal
	# orientation correction, and align the scan's lowest point with the arena.
	scan.scale = Vector3.ONE * 0.3
	scan.position.y = bounds.size.y * 0.15

func _add_box(parent: Node3D, node_name: String, pos: Vector3, size: Vector3, color: Color, solid: bool) -> Node3D:
	var root: Node3D = StaticBody3D.new() if solid else Node3D.new()
	root.name = node_name
	root.position = pos
	if solid:
		var collision := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = size
		collision.shape = shape
		root.add_child(collision)
	var mesh_instance := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	mesh_instance.mesh = mesh
	mesh_instance.material_override = _material(color)
	root.add_child(mesh_instance)
	parent.add_child(root)
	return root

func _material(color: Color, transparent := false) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.88
	if transparent:
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return mat

func _spawn_player() -> void:
	player = CharacterBody3D.new()
	player.name = "Player"
	var collision := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.42
	capsule.height = 1.9
	collision.shape = capsule
	collision.position.y = 0.95
	player.add_child(collision)

	var body := MeshInstance3D.new()
	var body_mesh := CapsuleMesh.new()
	body_mesh.radius = 0.42
	body_mesh.height = 1.9
	body.mesh = body_mesh
	body.position.y = 0.95
	body.material_override = _material(Color(0.08, 0.48, 0.92))
	player.add_child(body)

	var head := MeshInstance3D.new()
	var head_mesh := SphereMesh.new()
	head_mesh.radius = 0.22
	head.mesh = head_mesh
	head.position = Vector3(0, 1.78, 0)
	head.material_override = _material(Color(0.88, 0.68, 0.51))
	player.add_child(head)

	var gun := MeshInstance3D.new()
	var gun_mesh := BoxMesh.new()
	gun_mesh.size = Vector3(0.16, 0.14, 0.72)
	gun.mesh = gun_mesh
	gun.position = Vector3(0.34, 1.28, -0.28)
	gun.material_override = _material(Color(0.1, 0.12, 0.14))
	player.add_child(gun)

	camera_pivot = Node3D.new()
	camera_pivot.position = Vector3(0, 1.55, 0)
	player.add_child(camera_pivot)
	camera = Camera3D.new()
	camera.position = Vector3(0.7, 0.45, 5.2)
	camera.current = true
	camera.fov = 75
	camera_pivot.add_child(camera)
	player.position = Vector3(0, 0.1, 0)
	add_child(player)

func _spawn_bots() -> void:
	for i in range(BOT_COUNT):
		var bot := CharacterBody3D.new()
		bot.name = "Rival_%02d" % (i + 1)
		bot.set_meta("enemy", true)
		bot.set_meta("health", 100.0)
		bot.set_meta("attack_wait", rng.randf_range(0.5, 2.0))
		bot.set_meta("wander", Vector3(rng.randf_range(-1, 1), 0, rng.randf_range(-1, 1)))
		var angle := TAU * float(i) / BOT_COUNT + rng.randf_range(-0.2, 0.2)
		var radius := rng.randf_range(25, 68)
		bot.position = Vector3(cos(angle) * radius, 0.1, sin(angle) * radius)
		var collision := CollisionShape3D.new()
		var shape := CapsuleShape3D.new()
		shape.radius = 0.42
		shape.height = 1.8
		collision.shape = shape
		collision.position.y = 0.9
		bot.add_child(collision)
		var body := MeshInstance3D.new()
		var mesh := CapsuleMesh.new()
		mesh.radius = 0.42
		mesh.height = 1.8
		body.mesh = mesh
		body.position.y = 0.9
		body.material_override = _material([Color(0.8, 0.22, 0.18), Color(0.8, 0.56, 0.12), Color(0.55, 0.22, 0.72)][i % 3])
		bot.add_child(body)
		var head := MeshInstance3D.new()
		var head_mesh := SphereMesh.new()
		head_mesh.radius = 0.2
		head.mesh = head_mesh
		head.position.y = 1.7
		head.material_override = _material(Color(0.86, 0.65, 0.48))
		bot.add_child(head)
		add_child(bot)
		enemies.append(bot)

func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	hud_label = Label.new()
	hud_label.position = Vector2(22, 18)
	hud_label.add_theme_font_size_override("font_size", 20)
	hud_label.add_theme_color_override("font_color", Color.WHITE)
	layer.add_child(hud_label)

	var title := Label.new()
	title.text = "SAEED ROYALE"
	title.position = Vector2(0, 16)
	title.anchor_left = 0.5
	title.anchor_right = 0.5
	title.offset_left = -180
	title.offset_right = 180
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 26)
	title.add_theme_color_override("font_color", Color(0.45, 0.9, 1.0))
	layer.add_child(title)

	var crosshair := Label.new()
	crosshair.text = "+"
	crosshair.position = Vector2(0, 0)
	crosshair.anchor_left = 0.5
	crosshair.anchor_top = 0.5
	crosshair.anchor_right = 0.5
	crosshair.anchor_bottom = 0.5
	crosshair.offset_left = -12
	crosshair.offset_top = -18
	crosshair.offset_right = 12
	crosshair.offset_bottom = 18
	crosshair.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	crosshair.add_theme_font_size_override("font_size", 32)
	crosshair.add_theme_color_override("font_color", Color(1, 1, 1, 0.9))
	layer.add_child(crosshair)

	status_label = Label.new()
	status_label.position = Vector2(22, 125)
	status_label.add_theme_font_size_override("font_size", 17)
	status_label.add_theme_color_override("font_color", Color(0.65, 0.92, 1.0))
	layer.add_child(status_label)

	center_label = Label.new()
	center_label.anchor_left = 0.5
	center_label.anchor_top = 0.38
	center_label.anchor_right = 0.5
	center_label.anchor_bottom = 0.38
	center_label.offset_left = -330
	center_label.offset_right = 330
	center_label.offset_top = -30
	center_label.offset_bottom = 80
	center_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	center_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	center_label.add_theme_font_size_override("font_size", 30)
	center_label.add_theme_color_override("font_color", Color(1.0, 0.85, 0.3))
	layer.add_child(center_label)

	restart_button = Button.new()
	restart_button.text = "PLAY AGAIN"
	restart_button.position = Vector2(0, 0)
	restart_button.anchor_left = 0.5
	restart_button.anchor_top = 0.57
	restart_button.anchor_right = 0.5
	restart_button.anchor_bottom = 0.57
	restart_button.offset_left = -95
	restart_button.offset_right = 95
	restart_button.offset_top = 0
	restart_button.offset_bottom = 48
	restart_button.visible = false
	restart_button.pressed.connect(_restart_game)
	layer.add_child(restart_button)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		mouse_captured = not mouse_captured
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED if mouse_captured else Input.MOUSE_MODE_VISIBLE
	elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT and not mouse_captured and not game_over:
		mouse_captured = true
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif event is InputEventMouseMotion and mouse_captured and not game_over:
		player.rotate_y(-event.relative.x * 0.0025)
		camera_pivot.rotate_x(-event.relative.y * 0.0021)
		camera_pivot.rotation.x = clamp(camera_pivot.rotation.x, deg_to_rad(-35), deg_to_rad(35))

func _process(delta: float) -> void:
	if game_over:
		if Input.is_action_just_pressed("restart"):
			_restart_game()
		return
	elapsed += delta
	fire_cooldown = maxf(0.0, fire_cooldown - delta)
	if reload_timer > 0:
		reload_timer -= delta
		if reload_timer <= 0:
			var needed := STARTING_AMMO - ammo
			var loaded: int = mini(needed, reserve_ammo)
			ammo += loaded
			reserve_ammo -= loaded
	if Input.is_action_just_pressed("reload"):
		_start_reload()
	if Input.is_action_pressed("fire") and mouse_captured:
		_shoot()
	_update_pickups(delta)
	_update_storm(delta)
	if player_health <= 0:
		_finish_game(false)
	elif enemies.is_empty():
		_finish_game(true)
	_update_hud()

func _physics_process(delta: float) -> void:
	if game_over:
		return
	_update_player(delta)
	_update_bots(delta)

func _update_player(delta: float) -> void:
	if not is_instance_valid(player):
		return
	var input_dir := Vector2(
		float(Input.is_action_pressed("move_right")) - float(Input.is_action_pressed("move_left")),
		float(Input.is_action_pressed("move_back")) - float(Input.is_action_pressed("move_forward"))
	)
	var direction := (player.global_transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()
	var speed := 11.0 if Input.is_action_pressed("sprint") else player_speed
	player.velocity.x = direction.x * speed
	player.velocity.z = direction.z * speed
	if not player.is_on_floor():
		player.velocity.y -= 22.0 * delta
	elif Input.is_action_just_pressed("jump"):
		player.velocity.y = 8.0
	player.move_and_slide()

func _shoot() -> void:
	if fire_cooldown > 0 or reload_timer > 0:
		return
	if ammo <= 0:
		_start_reload()
		return
	ammo -= 1
	fire_cooldown = 0.12
	var origin := camera.global_position
	var direction := -camera.global_transform.basis.z
	var query := PhysicsRayQueryParameters3D.create(origin, origin + direction * 130.0)
	query.exclude = [player.get_rid()]
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty():
		return
	var target: Object = hit.collider
	if target is Node and target.has_meta("enemy") and bool(target.get_meta("enemy")):
		_damage_enemy(target as CharacterBody3D, rng.randf_range(24.0, 36.0))
	_spawn_muzzle_flash()

func _spawn_muzzle_flash() -> void:
	var flash := MeshInstance3D.new()
	var mesh := SphereMesh.new()
	mesh.radius = 0.12
	mesh.height = 0.24
	flash.mesh = mesh
	flash.material_override = _material(Color(1.0, 0.8, 0.2))
	flash.global_position = camera.global_position - camera.global_transform.basis.z * 1.8
	add_child(flash)
	get_tree().create_timer(0.045).timeout.connect(flash.queue_free)

func _start_reload() -> void:
	if reload_timer > 0 or ammo >= STARTING_AMMO or reserve_ammo <= 0:
		return
	reload_timer = 1.35

func _damage_enemy(enemy: CharacterBody3D, amount: float) -> void:
	if not is_instance_valid(enemy) or not enemies.has(enemy):
		return
	var health := float(enemy.get_meta("health", 100.0)) - amount
	enemy.set_meta("health", health)
	if health <= 0:
		enemies.erase(enemy)
		if rng.randf() < 0.68:
			_spawn_pickup(enemy.global_position + Vector3(0, 0.5, 0), "ammo")
		if rng.randf() < 0.45:
			_spawn_pickup(enemy.global_position + Vector3(0.7, 0.5, 0), "med")
		enemy.queue_free()

func _update_bots(delta: float) -> void:
	for bot in enemies.duplicate():
		if not is_instance_valid(bot):
			enemies.erase(bot)
			continue
		var to_player: Vector3 = player.global_position - bot.global_position
		var flat := Vector3(to_player.x, 0, to_player.z)
		var distance := flat.length()
		var velocity: Vector3 = bot.velocity
		if distance > 11.0:
			var direction := flat.normalized()
			velocity.x = direction.x * 3.0
			velocity.z = direction.z * 3.0
			bot.look_at(Vector3(player.global_position.x, bot.global_position.y, player.global_position.z), Vector3.UP)
		else:
			velocity.x = move_toward(velocity.x, 0.0, 8.0 * delta)
			velocity.z = move_toward(velocity.z, 0.0, 8.0 * delta)
			var wait := float(bot.get_meta("attack_wait", 1.0)) - delta
			if wait <= 0:
				wait = rng.randf_range(0.7, 1.6)
				if distance < 16 and _has_line_of_sight(bot, player):
					player_health = maxf(0.0, player_health - rng.randf_range(5.0, 10.0))
			bot.set_meta("attack_wait", wait)
		if not bot.is_on_floor():
			velocity.y -= 22.0 * delta
		bot.velocity = velocity
		bot.move_and_slide()
		var bot_radius := Vector2(bot.global_position.x, bot.global_position.z).length()
		if bot_radius > storm_radius:
			var h := float(bot.get_meta("health", 100.0)) - delta * 7.0
			bot.set_meta("health", h)
			if h <= 0:
				enemies.erase(bot)
				bot.queue_free()

func _has_line_of_sight(from: Node3D, to: Node3D) -> bool:
	var query := PhysicsRayQueryParameters3D.create(from.global_position + Vector3(0, 1.1, 0), to.global_position + Vector3(0, 1.0, 0))
	query.exclude = [from.get_rid()]
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	return hit.is_empty() or hit.collider == to

func _spawn_pickup(pos: Vector3, kind: String) -> void:
	var pickup := Node3D.new()
	pickup.name = "Pickup_" + kind
	pickup.set_meta("kind", kind)
	pickup.position = pos
	var orb := MeshInstance3D.new()
	var mesh := SphereMesh.new()
	mesh.radius = 0.42
	mesh.height = 0.84
	orb.mesh = mesh
	orb.material_override = _material(Color(0.2, 0.85, 1.0) if kind == "ammo" else Color(0.2, 1.0, 0.42), true)
	pickup.add_child(orb)
	add_child(pickup)
	pickups.append(pickup)

func _update_pickups(delta: float) -> void:
	for pickup in pickups.duplicate():
		if not is_instance_valid(pickup):
			pickups.erase(pickup)
			continue
		pickup.rotate_y(delta * 1.8)
		pickup.position.y = 0.6 + sin(elapsed * 2.4 + pickup.position.x) * 0.15
		if pickup.global_position.distance_to(player.global_position) < 2.1:
			if str(pickup.get_meta("kind")) == "ammo":
				reserve_ammo += 30
			else:
				player_health = minf(MAX_HEALTH, player_health + 35.0)
			pickups.erase(pickup)
			pickup.queue_free()

func _update_storm(delta: float) -> void:
	storm_timer += delta
	if storm_timer > 12.0 and storm_radius > 13.0:
		storm_timer = 0
		storm_radius = maxf(13.0, storm_radius - 5.0)
		storm_ring.scale = Vector3(storm_radius, 1, storm_radius)
	var distance := Vector2(player.global_position.x, player.global_position.z).length()
	if distance > storm_radius:
		player_health = maxf(0.0, player_health - delta * 9.0)

func _update_hud() -> void:
	if not is_instance_valid(hud_label):
		return
	var remaining := maxi(0, enemies.size())
	hud_label.text = "HP  %03d\nRIFLE  %02d / %03d\nRIVALS  %02d\n" % [roundi(player_health), ammo, reserve_ammo, remaining]
	status_label.text = "SAFE ZONE  %dm\nTIME  %02d:%02d\nWASD Move  |  SHIFT Sprint\nSPACE Jump  |  R Reload\nLMB Fire  |  ESC Mouse" % [
		roundi(storm_radius), int(elapsed) / 60, int(elapsed) % 60]
	if reload_timer > 0:
		center_label.text = "RELOADING..."
	elif storm_timer > 8.0:
		center_label.text = "SAFE ZONE SHRINKING"
	else:
		center_label.text = ""

func _finish_game(won: bool) -> void:
	if game_over:
		return
	game_over = true
	victory = won
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	mouse_captured = false
	center_label.text = "VICTORY!  YOU ARE THE LAST SURVIVOR" if won else "ELIMINATED"
	center_label.add_theme_color_override("font_color", Color(0.4, 1.0, 0.48) if won else Color(1.0, 0.25, 0.22))
	restart_button.visible = true
	status_label.text = "Survival time: %02d:%02d" % [int(elapsed) / 60, int(elapsed) % 60]

func _restart_game() -> void:
	get_tree().reload_current_scene()
