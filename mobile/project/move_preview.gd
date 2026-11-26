extends Node

@onready var map := $Screen/World/Map
@onready var camera: Camera3D = map.get_node("Camera3D")
var tiles := {}
var occupied := {}
var allowed := {}
var hero: Node3D
var hero_cell := Vector2i(2, 2)
var selected := false
var moving := false
var moved := false
var highlight := ShaderMaterial.new()
var original_materials := {}
var rest: Vector3
var hero_pose: Basis

func _ready() -> void:
	highlight.shader = preload("res://move_tile.gdshader")
	var markers := []
	for node in map.get_node("LayoutSamples").get_children():
		if node.has_meta("cell_marker"):
			markers.append(node)
		if node.has_meta("piece_cell"):
			var cell: Vector2i = node.get_meta("piece_cell")
			if cell == Vector2i(2, 4):
				hero = node
			else:
				occupied[cell] = node
	for marker: MeshInstance3D in markers:
		var cell: Vector2i = marker.get_meta("cell_marker")
		tiles[cell] = marker
		original_materials[cell] = marker.material_override
	for tower in map.get_node("Towers").get_children():
		occupied[tower.get_meta("board_cell")] = tower
	var blocker: Node3D = occupied[Vector2i(2, 3)]
	blocker.position += tiles[Vector2i(3, 2)].position - tiles[Vector2i(2, 3)].position
	occupied.erase(Vector2i(2, 3))
	occupied[Vector2i(3, 2)] = blocker
	hero_pose = hero.basis
	rest = hero.position - tiles[Vector2i(2, 4)].position
	hero.position = tiles[hero_cell].position + rest
	if "--demo" in OS.get_cmdline_user_args():
		demonstrate()

func _unhandled_input(event: InputEvent) -> void:
	var tap := event as InputEventMouseButton
	if not tap or not tap.pressed or tap.button_index != MOUSE_BUTTON_LEFT:
		return
	# Godot maps a primary touch to this mouse event, including on Android.
	var local: Vector2 = $Screen.get_global_transform().affine_inverse() * tap.position
	choose_at(local)

func choose_at(at: Vector2) -> void:
	if moving or moved:
		return
	var origin := camera.project_ray_origin(at)
	var ray := camera.project_ray_normal(at)
	var hit = Plane(Vector3.UP, 0.006).intersects_ray(origin, ray)
	if hit == null:
		return
	# Pick the raised portrait as well as its ground footprint.
	var center := camera.unproject_position(hero.position)
	if (at - center).abs().x < 49 and (at - center).abs().y < 49:
		select_hero(not selected)
		return
	for cell: Vector2i in tiles:
		var d: Vector3 = hit - tiles[cell].position
		if absf(d.x) <= 0.169 and absf(d.z) <= 0.203:
			if cell == hero_cell:
				select_hero(not selected)
			elif allowed.has(cell):
				move_to(cell)
			else:
				select_hero(false)
			return
	select_hero(false)

func select_hero(value: bool) -> void:
	for cell in allowed:
		tiles[cell].material_override = original_materials[cell]
	allowed.clear()
	selected = value
	hero.position = tiles[hero_cell].position + rest
	hero.basis = hero_pose
	if selected:
		hero.position.y += 0.032
		hero.scale *= 1.038
		for cell: Vector2i in tiles:
			var delta := (cell - hero_cell).abs()
			if maxi(delta.x, delta.y) == 1 and not occupied.has(cell):
				tiles[cell].material_override = highlight
				allowed[cell] = true

func move_to(cell: Vector2i) -> void:
	var start := hero.position
	select_hero(false)
	moving = true
	var end: Vector3 = tiles[cell].position + rest
	var tween := create_tween()
	tween.tween_method(func(t: float):
		hero.position = start.lerp(end, t) + Vector3.UP * 0.070 * sin(PI * t),
		0.0, 1.0, 0.34).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tween.tween_callback(func():
		hero_cell = cell
		moved = true
		moving = false)

func demo_tap(cell: Vector2i) -> void:
	var screen_pos: Vector2 = $Screen.get_global_transform() * camera.unproject_position(tiles[cell].position)
	for down in [true, false]:
		var event := InputEventMouseButton.new()
		event.button_index = MOUSE_BUTTON_LEFT
		event.pressed = down
		event.position = screen_pos
		get_viewport().push_input(event, true)

func demonstrate() -> void:
	await get_tree().create_timer(0.7).timeout
	demo_tap(hero_cell)
	assert(selected and allowed.size() == 6)
	await get_tree().create_timer(1.1).timeout
	demo_tap(Vector2i(3, 2))
	assert(not selected and not moving)
	await get_tree().create_timer(0.55).timeout
	demo_tap(hero_cell)
	await get_tree().create_timer(0.8).timeout
	demo_tap(Vector2i(1, 3))
	await get_tree().create_timer(0.5).timeout
	assert(moved and hero_cell == Vector2i(1, 3))
