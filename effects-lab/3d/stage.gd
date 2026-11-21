extends Node3D

const TILE := 1.10
const RIVER_GAP := 0.24
const EFFECT_LENGTHS := [0.80, 1.05, 1.20]
const NEAR := Color("#9ee0bd")
const FAR := Color("#ea9871")
const GOLD := Color("#f9c77b")
const CARD_FOOTPRINT := Vector2(0.86, 1.02)

var camera: Camera3D
var attacker: Node3D
var defender: Node3D
var projectile: MeshInstance3D
var slash: MeshInstance3D
var impact: MeshInstance3D
var cannon_origin: Vector3
var cannon_flash: Sprite3D
var cannon_ring: Sprite3D
var cannon_smoke: Array[Sprite3D] = []
var cannon_trail: Array[Sprite3D] = []
var sparks: Array[MeshInstance3D] = []
var marked_cells: Array[MeshInstance3D] = []
var cards: Array[Node3D] = []
var fx_material: StandardMaterial3D
var area_material: StandardMaterial3D
var effect := 0
var clock := 0.0
var playing := false
var playback_rate := 1.0
var web: JavaScriptObject
var web_command: JavaScriptObject

func _ready() -> void:
	_build_board()
	_build_effects()
	get_viewport().size_changed.connect(_frame_camera)
	_frame_camera()
	_render()
	if OS.has_feature("web"):
		web = JavaScriptBridge.get_interface("window")
		web_command = JavaScriptBridge.create_callback(_on_web_command)
		web.stageCommand = web_command
		web.stageReady()

func _process(delta: float) -> void:
	if not playing:
		return
	var duration: float = EFFECT_LENGTHS[effect]
	clock = minf(duration, clock + delta * playback_rate)
	if clock >= duration:
		playing = false
	_render()
	if web:
		web.stageProgress(clock / duration, playing)

func _unhandled_key_input(event: InputEvent) -> void:
	if OS.has_feature("web") or not event.is_pressed() or event.is_echo():
		return
	match event.physical_keycode:
		KEY_1: _select_effect(0)
		KEY_2: _select_effect(1)
		KEY_3: _select_effect(2)
		KEY_SPACE: _replay()
		KEY_V: _frame_camera(74.0 if camera.rotation_degrees.x > -68.0 else 55.0)

func _on_web_command(args: Array) -> void:
	if args.is_empty():
		return
	match str(args[0]):
		"select": _select_effect(clampi(int(args[1]), 0, EFFECT_LENGTHS.size() - 1))
		"replay": _replay()
		"pause": playing = false
		"resume":
			if clock >= EFFECT_LENGTHS[effect]:
				clock = 0.0
			playing = true
		"seek":
			playing = false
			clock = clampf(float(args[1]), 0.0, 1.0) * EFFECT_LENGTHS[effect]
			_render()
		"rate": playback_rate = clampf(float(args[1]), 0.25, 2.0)
		"camera": _frame_camera(clampf(float(args[1]), 48.0, 82.0))
		"inspect": _inspect_card(Vector2(float(args[1]), float(args[2])))

func _inspect_card(normalized: Vector2) -> void:
	var screen := normalized * get_viewport().get_visible_rect().size
	var origin := camera.project_ray_origin(screen)
	var direction := camera.project_ray_normal(screen)
	for card in cards:
		var center := card.global_position
		var plane := Plane(Vector3.UP, center.y + 0.114)
		var hit = plane.intersects_ray(origin, direction)
		if hit == null:
			continue
		var offset := Vector2(hit.x - center.x, hit.z - center.z)
		if Rect2(-CARD_FOOTPRINT * 0.5, CARD_FOOTPRINT).has_point(offset):
			web.stageInspect(int(card.get_meta("card_id")))
			return

func _select_effect(index: int) -> void:
	effect = index
	clock = 0.0
	playing = false
	_render()

func _replay() -> void:
	clock = 0.0
	playing = true
	_render()

func _frame_camera(angle := 0.0) -> void:
	if angle == 0.0:
		angle = absf(camera.rotation_degrees.x)
		if angle < 1.0:
			angle = 55.0
	var radians := deg_to_rad(angle)
	var viewport_size := get_viewport().get_visible_rect().size
	var aspect := viewport_size.x / maxf(1.0, viewport_size.y)
	var span := maxf(9.65 * sin(radians) + 0.9, 8.6 / maxf(aspect, 0.1))
	var distance := span / (2.0 * tan(deg_to_rad(camera.fov * 0.5))) + cos(radians) * 3.75
	var center := Vector3(0, 0, cos(radians) * 1.08)
	camera.position = center + Vector3(0.0, sin(radians) * distance, cos(radians) * distance)
	camera.look_at(center)

func _cell(column: int, row: int) -> Vector3:
	var side := -1.0 if row < 4 else 1.0
	return Vector3((column - 2.0) * TILE, 0.12, (row - 3.5) * TILE + side * RIVER_GAP / 2.0)

func _paint(color: Color, metallic := 0.0, roughness := 0.8) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.metallic = metallic
	material.roughness = roughness
	return material

func _light_paint(color: Color) -> StandardMaterial3D:
	var material := _paint(color)
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return material

func _mesh(shape: Mesh, at: Vector3, material: Material, parent: Node3D = self) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.mesh = shape
	instance.material_override = material
	parent.add_child(instance)
	instance.position = at
	return instance

func _box(size: Vector3, at: Vector3, material: Material, parent: Node3D = self) -> MeshInstance3D:
	var shape := BoxMesh.new()
	shape.size = size
	return _mesh(shape, at, material, parent)

func _cylinder(radius: float, height: float, sides: int, at: Vector3, material: Material, parent: Node3D = self) -> MeshInstance3D:
	var shape := CylinderMesh.new()
	shape.top_radius = radius
	shape.bottom_radius = radius * 1.12
	shape.height = height
	shape.radial_segments = sides
	return _mesh(shape, at, material, parent)

func _build_board() -> void:
	var surroundings := WorldEnvironment.new()
	var lighting := Environment.new()
	lighting.background_mode = Environment.BG_COLOR
	lighting.background_color = Color("#10191c")
	lighting.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	lighting.ambient_light_color = Color("#d5ded1")
	lighting.ambient_light_energy = 0.51
	surroundings.environment = lighting
	add_child(surroundings)
	_add_light(Vector3(-51, -26, 0), Color("#fff0dd"), 0.92, true)
	_add_light(Vector3(-36, 146, 0), Color("#91c6d9"), 0.28, false)

	var slate := _paint(Color("#233238"))
	var plinth := _paint(Color("#354246"), 0.12, 0.70)
	var brass := _paint(Color("#947859"), 0.40, 0.57)
	var water := _paint(Color("#2e5359"), 0.28, 0.32)
	_box(Vector3(7.95, 0.48, 9.48), Vector3(0, -0.41, 0), slate)
	_box(Vector3(7.80, 0.22, 9.32), Vector3(0, -0.16, 0), plinth)
	_box(Vector3(7.60, 0.012, 0.25), Vector3(0, -0.033, 0), water)
	for side: float in [-1.0, 1.0]:
		_box(Vector3(7.70, 0.026, 0.028), Vector3(0, -0.017, side * 0.14), brass)
		_box(Vector3(7.68, 0.03, 0.037), Vector3(0, -0.030, side * 4.58), brass)
		_box(Vector3(0.035, 0.03, 9.19), Vector3(side * 3.84, -0.030, 0), brass)
		for z: float in [-4.36, 4.36]:
			_cylinder(0.083, 0.028, 8, Vector3(side * 3.61, -0.005, z), brass)

	var upper := [_stone(Color("#453833")), _stone(Color("#4d4039"))]
	var lower := [_stone(Color("#2c4643")), _stone(Color("#344e49"))]
	for row in range(8):
		var palette := upper if row < 4 else lower
		for column in range(5):
			var at := _cell(column, row)
			_box(Vector3(1.043, 0.13, 1.043), Vector3(at.x, -0.012, at.z), palette[(row + column) % 2])

	cannon_origin = _tower(_cell(2, 6), NEAR)
	_tower(_cell(2, 1), FAR)
	_deck(Vector3(-3.17, 0.015, 3.15), NEAR, -0.12)
	_deck(Vector3(3.17, 0.015, -3.15), FAR, 0.12)
	attacker = _piece(10032, preload("res://art/10032.webp"), _cell(2, 4), NEAR)
	defender = _piece(10022, preload("res://art/10022.webp"), _cell(2, 3), FAR)
	_piece(61007, preload("res://art/61007.webp"), _cell(0, 5), NEAR)
	_piece(61006, preload("res://art/61006.webp"), _cell(3, 2), FAR)
	_piece(61006, preload("res://art/61006.webp"), _cell(1, 2), FAR)
	camera = Camera3D.new()
	camera.fov = 35.0
	add_child(camera)
	camera.current = true

func _stone(color: Color) -> ShaderMaterial:
	var shader := Shader.new()
	shader.code = """
shader_type spatial;
uniform vec4 stone : source_color;
varying vec3 surface;
void vertex() {
  surface = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}
void fragment() {
  vec2 p = surface.xz;
  float veins = sin(p.x * 12.0 + p.y * 15.0 + 2.5 * sin(p.y * 4.3 - p.x * 1.9));
  float grain = fract(sin(dot(floor(p * 125.0), vec2(127.1, 311.7))) * 43758.5453);
  ALBEDO = stone.rgb * (0.93 + veins * 0.055 + grain * 0.12);
  ROUGHNESS = 0.84;
}
"""
	var material := ShaderMaterial.new()
	material.shader = shader
	material.set_shader_parameter("stone", color)
	return material

func _add_light(angles: Vector3, color: Color, energy: float, shadows: bool) -> void:
	var lamp := DirectionalLight3D.new()
	lamp.rotation_degrees = angles
	lamp.light_color = color
	lamp.light_energy = energy
	lamp.shadow_enabled = shadows
	lamp.directional_shadow_max_distance = 19.0
	add_child(lamp)

func _deck(at: Vector3, color: Color, angle: float) -> void:
	var stack := Node3D.new()
	add_child(stack)
	stack.position = at
	stack.rotation.y = angle
	var cloth := _paint(color.darkened(0.62))
	for layer in range(4):
		_box(Vector3(0.68, 0.035, 0.93), Vector3(0, layer * 0.035, 0), cloth if layer % 2 == 0 else _paint(color.darkened(0.42)), stack)
	var inset := _box(Vector3(0.23, 0.012, 0.23), Vector3(0, 0.129, 0), _paint(color.darkened(0.23)), stack)
	inset.rotation.y = PI / 4.0

func _tower(at: Vector3, color: Color) -> Vector3:
	var base := at - Vector3(0, 0.046, 0)
	var model: Node3D = preload("res://art/kenney/tower-square.glb").instantiate()
	add_child(model)
	model.position = base
	model.scale = Vector3(0.88, 0.72, 0.88)
	for node in model.find_children("*", "MeshInstance3D", true, false):
		var mesh := node as MeshInstance3D
		var material := mesh.get_active_material(0).duplicate() as StandardMaterial3D
		material.albedo_color *= Color("#717e82") if color == NEAR else Color("#806e64")
		material.roughness = 0.86
		mesh.set_surface_override_material(0, material)
	_box(Vector3(0.93, 0.04, 0.93), base, _paint(color.darkened(0.36), 0.28, 0.54))
	var beacon := base + Vector3(0, 0.96, 0)
	var jewel := _box(Vector3(0.16, 0.13, 0.16), beacon, _light_paint(color))
	jewel.rotation_degrees = Vector3(0, 45, 0)
	return beacon + Vector3(0, 0.12, 0)

func _piece(card_id: int, portrait: Texture2D, at: Vector3, color: Color) -> Node3D:
	var card := Node3D.new()
	card.set_meta("card_id", card_id)
	cards.append(card)
	add_child(card)
	card.position = at
	_box(Vector3(CARD_FOOTPRINT.x, 0.14, CARD_FOOTPRINT.y), Vector3(0, 0.006, 0), _paint(Color("#182322")), card)
	_box(Vector3(0.832, 0.034, 0.992), Vector3(0, 0.084, 0), _paint(color.darkened(0.37), 0.23), card)
	var image := PlaneMesh.new()
	image.size = Vector2(0.79, 0.93)
	var picture := _light_paint(Color.WHITE)
	picture.albedo_texture = portrait
	picture.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	# Crop the tall portrait to the tile without distorting its proportions.
	var crop := image.size.aspect() / Vector2(portrait.get_size()).aspect()
	var visible_height := 1.0 / crop
	picture.uv1_scale = Vector3(1.0, visible_height, 1.0)
	picture.uv1_offset = Vector3(0.0, (1.0 - visible_height) * 0.32, 0.0)
	_mesh(image, Vector3(0, 0.103, 0), picture, card)
	_box(Vector3(0.36, 0.012, 0.042), Vector3(0, 0.114, 0.480), _light_paint(color), card)
	return card

func _build_effects() -> void:
	fx_material = _light_paint(GOLD)
	area_material = _light_paint(NEAR)
	area_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	var orb := SphereMesh.new()
	orb.radius = 0.14
	orb.height = 0.28
	orb.radial_segments = 12
	orb.rings = 6
	projectile = _mesh(orb, Vector3.ZERO, fx_material)
	cannon_flash = _particle_sprite(preload("res://art/effekseer/burst-mask.png"))
	cannon_ring = _particle_sprite(preload("res://art/effekseer/particle-03.png"))
	cannon_ring.billboard = BaseMaterial3D.BILLBOARD_DISABLED
	cannon_ring.rotation_degrees.x = -90
	var soft := preload("res://art/effekseer/particle-soft.png")
	for i in range(3):
		cannon_smoke.append(_particle_sprite(soft))
	for i in range(7):
		cannon_trail.append(_particle_sprite(soft))
	impact = _cylinder(0.35, 0.025, 24, Vector3.ZERO, area_material)
	var blade := _light_paint(Color("#fff0bb"))
	blade.cull_mode = BaseMaterial3D.CULL_DISABLED
	slash = _mesh(_blade_arc(), Vector3.ZERO, blade)
	slash.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	for i in range(18):
		sparks.append(_box(Vector3(0.055, 0.055, 0.17), Vector3.ZERO, fx_material))
	for row in [2, 3]:
		for column in [1, 2, 3]:
			marked_cells.append(_box(Vector3(0.98, 0.012, 0.98), _cell(column, row) + Vector3(0, -0.055, 0), area_material))

func _particle_sprite(texture: Texture2D) -> Sprite3D:
	var sprite := Sprite3D.new()
	sprite.texture = texture
	sprite.pixel_size = 1.0 / texture.get_width()
	sprite.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	sprite.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(sprite)
	return sprite

func _show_particle(sprite: Sprite3D, position: Vector3, width: float, tint: Color, alpha: float) -> void:
	sprite.visible = alpha > 0.01
	if sprite.visible:
		sprite.position = position
		sprite.scale = Vector3.ONE * width
		sprite.modulate = Color(tint, alpha)

func _blade_arc() -> ArrayMesh:
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLE_STRIP)
	for step in range(25):
		var progress := step / 24.0
		var angle := lerpf(-1.43, 1.43, progress)
		var radial := Vector3(sin(angle), 0, -cos(angle))
		surface.add_vertex(radial * 0.64)
		surface.add_vertex(radial * (0.64 - 0.23 * sin(progress * PI)))
	return surface.commit()

func _render() -> void:
	var phase := clock / float(EFFECT_LENGTHS[effect])
	var hit := [0.39, 0.56, 0.51][effect] as float
	var aftermath := clampf((phase - hit) / 0.44, 0.0, 1.0)
	var source := _cell(2, 4)
	var target := _cell(2, 3)
	fx_material.albedo_color = NEAR if effect == 2 else GOLD
	var shade := Color("#71d8b9") if effect == 2 else Color("#ffb278")
	shade.a = (sin(PI * clampf(phase / 0.94, 0.0, 1.0)) * 0.46) if effect == 2 else (1.0 - aftermath) * 0.66
	area_material.albedo_color = shade

	var lunge := clampf((phase - 0.12) / 0.27, 0, 1) * (1.0 - smoothstep(hit, 0.76, phase))
	attacker.position = source.lerp(target, 0.55 * lunge) if effect == 0 else source
	defender.position = target + Vector3(0, 0.06 * sin(PI * aftermath), -0.13 * sin(PI * aftermath))
	slash.visible = effect == 0 and phase >= 0.29 and phase < 0.60
	slash.position = attacker.position.lerp(target, 0.32) + Vector3(0, 0.25, 0)
	slash.rotation_degrees = Vector3(21.0, lerpf(-48.0, 48.0, smoothstep(0.29, 0.60, phase)), -16.0)
	slash.scale = Vector3.ONE * (0.82 + phase)
	_render_cannon(phase, hit, target)
	impact.visible = effect != 1 and phase >= hit and aftermath < 1.0
	impact.position = target + Vector3(0, 0.09, 0)
	impact.scale = Vector3(0.35 + aftermath * 1.36, 1.0, 0.35 + aftermath * 1.36)
	for mark in marked_cells:
		mark.visible = effect == 2 and phase > 0.06 and phase < 0.94
	for i in range(sparks.size()):
		_place_spark(i, phase, hit, aftermath, target)

func _render_cannon(phase: float, hit: float, target: Vector3) -> void:
	var active := effect == 1
	var flight := clampf((phase - 0.18) / (hit - 0.18), 0.0, 1.0)
	var destination := target + Vector3(0, 0.22, 0)
	projectile.visible = active and phase >= 0.18 and phase < hit
	projectile.position = _trajectory(cannon_origin, destination, flight)
	projectile.scale = Vector3.ONE * (0.65 + 0.35 * flight)
	var at_muzzle := phase < hit
	var flash_start := 0.14 if at_muzzle else hit
	var flash_time := clampf((phase - flash_start) / 0.18, 0.0, 1.0)
	var flash_alpha := sin(PI * pow(flash_time, 0.55)) if active else 0.0
	var flash_position := cannon_origin if at_muzzle else destination
	_show_particle(cannon_flash, flash_position, 0.42 + flash_time * 0.67, Color("#ffbd75"), flash_alpha)
	var ring_time := clampf((phase - hit) / 0.26, 0.0, 1.0)
	var ring_alpha := sin(PI * pow(ring_time, 0.50)) * 0.8 if active else 0.0
	_show_particle(cannon_ring, target + Vector3(0, -0.052, 0), 0.70 + ring_time * 1.72, GOLD, ring_alpha)
	for i in range(cannon_trail.size()):
		var behind := flight - (i + 1) * 0.055
		var alpha := (1.0 - i * 0.095) * 0.64 if active and at_muzzle and behind > 0.0 else 0.0
		var trail_at := _trajectory(cannon_origin, destination, clampf(behind, 0.0, 1.0))
		_show_particle(cannon_trail[i], trail_at, 0.25 - i * 0.023, Color("#ff914f"), alpha)
	for i in range(cannon_smoke.size()):
		var smoke_start := hit + i * 0.035
		var drift := clampf((phase - smoke_start) / (1.0 - smoke_start), 0.0, 1.0)
		var alpha := sin(PI * drift) * 0.27 if active else 0.0
		var smoke_at := destination + Vector3((i - 1) * 0.28, drift * 0.31, -drift * 0.21)
		_show_particle(cannon_smoke[i], smoke_at, 0.23 + drift * 0.68, Color("#9a7265"), alpha)

func _trajectory(from: Vector3, to: Vector3, progress: float) -> Vector3:
	return from.lerp(to, progress) + Vector3.UP * (1.17 * sin(PI * progress))

func _place_spark(index: int, phase: float, hit: float, aftermath: float, target: Vector3) -> void:
	var spark := sparks[index]
	var angle := index * 2.39996
	var direction := Vector3(cos(angle), 0, sin(angle))
	spark.visible = effect != 1 and phase >= hit and aftermath < 0.97
	var origin := target
	if effect == 2:
		origin = marked_cells[index % marked_cells.size()].position
	spark.position = origin + direction * (0.10 + aftermath * (0.41 + (index % 4) * 0.09))
	spark.position.y += 0.05 + sin(PI * aftermath) * (0.27 + (index % 5) * 0.10)
	spark.rotation = Vector3(aftermath * 3.0, angle, aftermath * 2.0)
	spark.scale = Vector3.ONE * (1.15 - aftermath)
