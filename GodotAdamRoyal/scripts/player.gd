extends CharacterBody3D

@export var walk_speed := 7.0
@export var jump_velocity := 5.0
@export var mouse_sensitivity := 0.002
var gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var camera_pitch := 0.0
var character_loaded := false
@onready var pivot: Node3D = $CameraPivot

func _ready() -> void:
	_setup_character()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _setup_character() -> void:
	var model_path := "res://assets/adam_royal_character.glb"
	if not FileAccess.file_exists(model_path):
		push_error("Adam Royal character model is missing: " + model_path)
		print("CHARACTER_MODEL_LOADED=false")
		return
	var packed_character := load(model_path) as PackedScene
	if packed_character == null:
		push_error("Godot could not import the Adam Royal character GLB: " + model_path)
		print("CHARACTER_MODEL_LOADED=false")
		return
	var character := packed_character.instantiate()
	character.name = "AdamRoyalCharacter"
	character.position = Vector3.ZERO
	character.scale = Vector3.ONE
	add_child(character)
	var placeholder := get_node_or_null("Body") as MeshInstance3D
	if placeholder != null:
		placeholder.visible = false
	character_loaded = true
	_play_idle_if_available(character)
	print("CHARACTER_MODEL_LOADED=true")

func _play_idle_if_available(character: Node) -> void:
	var players := character.find_children("*", "AnimationPlayer", true, false)
	for item in players:
		var animation_player := item as AnimationPlayer
		if animation_player == null:
			continue
		for animation_name in animation_player.get_animation_list():
			if "idle" in animation_name.to_lower():
				animation_player.play(animation_name)
				return

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * mouse_sensitivity)
		camera_pitch = clamp(camera_pitch - event.relative.y * mouse_sensitivity, -1.0, 0.8)
		pivot.rotation.x = camera_pitch
	if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	if event is InputEventMouseButton and event.pressed and Input.mouse_mode == Input.MOUSE_MODE_VISIBLE:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravity * delta
	if Input.is_action_just_pressed("jump") and is_on_floor():
		velocity.y = jump_velocity
	var input_dir := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var direction := (transform.basis * Vector3(input_dir.x, 0, input_dir.y)).normalized()
	if direction:
		velocity.x = direction.x * walk_speed
		velocity.z = direction.z * walk_speed
	else:
		velocity.x = move_toward(velocity.x, 0.0, walk_speed * 5.0 * delta)
		velocity.z = move_toward(velocity.z, 0.0, walk_speed * 5.0 * delta)
	move_and_slide()
