extends Control

const PITCH_X := 0.93
const PITCH_Z := 0.78
const RIVER_GAP := 0.33

var _viewport: SubViewport
var _world: Node3D
var _camera: Camera3D
var _buildings: Array[Node3D] = []
var _columns := 5

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_viewport = SubViewport.new()
	_viewport.own_world_3d = true
	_viewport.transparent_bg = true
	_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(_viewport)
	var screen := TextureRect.new()
	screen.texture = _viewport.get_texture()
	screen.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	screen.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(screen)
	screen.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_world = Node3D.new()
	_viewport.add_child(_world)
	_build()
	resized.connect(_resize_world)
	_resize_world()

func _build() -> void:
	var lighting := WorldEnvironment.new()
	var ambient := Environment.new()
	ambient.background_mode = Environment.BG_COLOR
	ambient.background_color = Color("#191510")
	ambient.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	ambient.ambient_light_color = Color("#ecd5ba")
	ambient.ambient_light_energy = 0.64
	lighting.environment = ambient
	_world.add_child(lighting)

	var key_light := DirectionalLight3D.new()
	key_light.rotation_degrees = Vector3(-56, -32, 0)
	key_light.light_color = Color("#ffe0b5")
	key_light.light_energy = 0.80
	key_light.shadow_enabled = true
	_world.add_child(key_light)
	var fill := DirectionalLight3D.new()
	fill.rotation_degrees = Vector3(-44, 144, 0)
	fill.light_color = Color("#a6ddd9")
	fill.light_energy = 0.34
	_world.add_child(fill)

	var base := _material("#39291f", 0.05, 0.83)
	var rim := _material("#684f3b", 0.35, 0.46)
	var metal := _material("#987650", 0.55, 0.36)
	var wood := _wood()
	var span := 4 * PITCH_Z
	_box(Vector3(8.40, 0.31, 7.24), Vector3(0, -0.34, 0.02), base)
	_box(Vector3(8.25, 0.15, 7.08), Vector3(0, -0.14, 0), rim)
	for corner: Vector2 in [Vector2(-3.77,-3.22),Vector2(3.77,-3.22),Vector2(-3.77,3.22),Vector2(3.77,3.22)]:
		_box(Vector3(0.50, 0.30, 0.53), Vector3(corner.x, -0.56, corner.y), base)
	_box(Vector3(8.0, 0.06, RIVER_GAP + 0.1), Vector3(0, -0.06, 0), _water())
	for side: float in [-1.0, 1.0]:
		var z := side * (span + RIVER_GAP) / 2
		for lane in range(7):
			var x := (lane - 3) * 1.14
			_box(Vector3(1.132, 0.18, span), Vector3(x, -0.08, z), wood)
		_box(Vector3(8.02, 0.10, 0.11), Vector3(0, 0.01, side * (span + RIVER_GAP / 2)), rim)
		_box(Vector3(8.02, 0.04, 0.072), Vector3(0, 0.034, side * RIVER_GAP / 2), metal)
		for x: float in [-3.90, 3.90]:
			_box(Vector3(0.10, 0.12, span), Vector3(x, 0.008, z), rim)
			for pin: float in [0.31, 2.86]:
				_cylinder(0.055, 0.035, Vector3(x, 0.076, side * pin), metal, _world)

	# The two decks sit on opposite outer corners of the table.
	for team in range(2):
		var at := deck_world(team)
		var board_tint := _material("#254744" if team == 0 else "#613530", 0.16, 0.56)
		for layer in range(5):
			var mesh := _box(Vector3(0.70, 0.030, 0.94),
				at + Vector3(0.007 * layer, 0.015 + layer * 0.032, 0), board_tint if layer in [0,4] else metal)
			mesh.rotate_y(0.10 if team == 0 else -0.10)
		var inlay := _box(Vector3(0.22, 0.010, 0.22), at + Vector3(0.025, 0.164, 0), metal)
		inlay.rotate_y(PI / 4)
		_buildings.append(_make_tower(team, metal))

	_camera = Camera3D.new()
	_camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	_camera.position = Vector3(0, 11, 5.3)
	_world.add_child(_camera)
	_camera.look_at(Vector3.ZERO)
	_camera.current = true

func _make_tower(team: int, metal: Material) -> Node3D:
	var tower := Node3D.new()
	_world.add_child(tower)
	var stone := _material("#574a40", 0.25, 0.59)
	var enamel := _material("#5bafa5" if team == 0 else "#c17d56", 0.25, 0.40)
	_cylinder(0.25, 0.10, Vector3(0, 0.06, 0), stone, tower)
	_cylinder(0.20, 0.09, Vector3(0, 0.14, 0), metal, tower)
	_box(Vector3(0.24, 0.30, 0.24), Vector3(0, 0.28, 0), stone, tower)
	var crest := _box(Vector3(0.18, 0.18, 0.18), Vector3(0, 0.49, 0), enamel, tower)
	crest.rotate_y(PI / 4)
	crest.rotate_z(PI / 5)
	return tower

func _resize_world() -> void:
	if _camera == null:
		return
	_viewport.size = Vector2i(maxf(2, size.x), maxf(2, size.y))
	var aspect := size.x / maxf(1.0, size.y)
	_camera.size = maxf(7.22, 8.95 / maxf(0.1, aspect))

func sync(columns: int, forts: Array) -> void:
	_columns = columns
	for team in range(_buildings.size()):
		_buildings[team].visible = team < forts.size()
		if team < forts.size():
			_buildings[team].position = cell_world(Vector2i(int(forts[team].col), int(forts[team].row)))
			_buildings[team].scale = Vector3.ONE * (1.20 if forts[team].get("stage") == "base" else 1.0)

func cell_world(pos: Vector2i) -> Vector3:
	var z := (pos.y - 3.5) * PITCH_Z + (-RIVER_GAP / 2 if pos.y < 4 else RIVER_GAP / 2)
	return Vector3((pos.x - (_columns - 1) / 2.0) * PITCH_X, 0.025, z)

func cell_rect(pos: Vector2i) -> Rect2:
	var origin := cell_world(pos)
	var radius := Vector3(PITCH_X * 0.48, 0, PITCH_Z * 0.48)
	var a := _camera.unproject_position(origin - radius)
	var b := _camera.unproject_position(origin + radius)
	return Rect2(a, b - a).abs()

func deck_world(team: int) -> Vector3:
	return Vector3(-3.2, 0.028, 2.65) if team == 0 else Vector3(3.2, 0.028, -2.65)

func deck_label(team: int) -> Vector2:
	return _camera.unproject_position(deck_world(team) + Vector3(0, 0.20, 0.58))

func _material(paint: String, metallic: float, roughness: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(paint)
	material.metallic = metallic
	material.roughness = roughness
	return material

func _box(dimensions: Vector3, at: Vector3, material: Material, parent: Node3D = null) -> MeshInstance3D:
	var shape := BoxMesh.new()
	shape.size = dimensions
	var piece := MeshInstance3D.new()
	piece.mesh = shape
	piece.material_override = material
	var container := parent if parent else _world
	container.add_child(piece)
	piece.position = at
	return piece

func _cylinder(radius: float, height: float, at: Vector3, material: Material, parent: Node3D) -> void:
	var shape := CylinderMesh.new()
	shape.top_radius = radius
	shape.bottom_radius = radius * 1.12
	shape.height = height
	shape.radial_segments = 16
	var piece := MeshInstance3D.new()
	piece.mesh = shape
	piece.material_override = material
	parent.add_child(piece)
	piece.position = at

func _wood() -> ShaderMaterial:
	var shader := Shader.new()
	shader.code = """shader_type spatial;
varying vec3 surface;
void vertex() { surface = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }
void fragment() {
	vec2 p = surface.xz;
	float curve = sin(p.y * 1.15 + p.x * .64) * .32 + sin(p.y * 3.2 + p.x) * .08;
	float grain = sin(p.x * 78.0 + curve * 4.0 + sin(p.y * .83) * 3.0);
	float bands = sin(p.x * 13.0 + curve * 3.6) * .34 + grain * .18;
	float pores = sin(p.x * 233.0 + p.y * 5.0 + grain * 1.1) * .10;
	float variation = clamp(.5 + bands + pores, 0.0, 1.0);
	float tone = sin(floor((p.x + 3.99) / 1.14) * 98.0) * .035;
	ALBEDO = mix(vec3(.105,.067,.046), vec3(.192,.120,.072), variation) + vec3(tone);
	ROUGHNESS = .67 + variation * .15;
	METALLIC = .04;
}"""
	var material := ShaderMaterial.new()
	material.shader = shader
	return material

func _water() -> ShaderMaterial:
	var shader := Shader.new()
	shader.code = """shader_type spatial;
render_mode unshaded;
varying vec3 surface;
void vertex() { surface = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }
void fragment() {
	vec2 p = surface.xz;
	float ripples = sin(p.x * 9.0 - TIME * 1.6 + sin(p.x * 2.7 + p.y * 8.2) * 1.9) *
		sin(p.y * 53.0 + sin(p.x * 4.0 - TIME * .7) * 1.2);
	float glint = smoothstep(.61, 1.0, ripples) * (.60 + sin(p.x * 3.1 - TIME) * .40);
	float bank = smoothstep(.10, .21, abs(p.y));
	ALBEDO = mix(vec3(.028,.12,.125), vec3(.42,.72,.67), glint * .47 + bank * .24);
}"""
	var material := ShaderMaterial.new()
	material.shader = shader
	return material
