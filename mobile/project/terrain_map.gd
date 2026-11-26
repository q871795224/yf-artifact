extends "res://layout.gd"

const TREE := preload("res://terrain/crown.glb")
const ROCK := preload("res://terrain/models/props_rock/badside_rocks002.glb")
const BONES := preload("res://terrain/models/props_bones/badside_bones002.glb")
var rng := RandomNumberGenerator.new()

func _ready() -> void:
	OS.low_processor_usage_mode = false
	arena_preview = true
	cell_ratio = 1.2
	wood_extension = 1.69
	camera_elevation = 58
	piece_pitch = 22
	compensate_pitch = true
	equipment_preview = 2
	pitch_study = "--full" in OS.get_cmdline_user_args()
	fill_all_cells = true
	capture_tower_bounds()
	rng.seed = 570
	$DirectionalLight3D.shadow_opacity = 0.66
	build_terrain()
	rebuild_geometry()
	pass


func rebuild_geometry() -> void:
	pass
	if tower_bounds.is_empty(): return
	rebuild_samples()
	$Camera3D.fov = 9.0
	$Camera3D.look_at_from_position(arena_camera_position(),ARENA_TARGET)

func ground_plane(extent: Vector2, shader: Shader, height: float, subdivisions: int) -> ShaderMaterial:
	var node := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = extent
	plane.subdivide_width = subdivisions
	plane.subdivide_depth = subdivisions*2
	node.mesh = plane
	var material := ShaderMaterial.new()
	material.shader = shader
	node.material_override = material
	add_child(node)
	node.position.y = height
	return material

func build_terrain() -> void:
	var land := ground_plane(Vector2(3.4,6.5),preload("res://terrain/land.gdshader"),0.,48)
	land.set_shader_parameter("grass",preload("res://terrain/textures/grass_goodside_00_color_tga_97397e2e.png"))
	land.set_shader_parameter("dirt",preload("res://terrain/textures/dirt_path002_color_psd_8fe1218a.png"))
	land.set_shader_parameter("ash",preload("res://terrain/textures/dirt_cracked_patchy_01_color_psd_a922a51a.png"))
	land.set_shader_parameter("rock",preload("res://terrain/textures/rocky01_color_psd_90a6357b.png"))
	land.set_shader_parameter("shore",preload("res://terrain/textures/river_rock001_color_psd_46760b98.png"))
	land.set_shader_parameter("profile",preload("res://terrain/profile.png"))
	var surface := preload("res://terrain/river.glb").instantiate()
	add_child(surface)
	var water := ShaderMaterial.new()
	water.shader = preload("res://terrain/stream.gdshader")
	for mesh in surface.find_children("*","MeshInstance3D",true,false):
		mesh.material_override = water
	water.set_shader_parameter("base_map",preload("res://assets/lane2/water_basetexture_psd_dd72473f.png"))
	water.set_shader_parameter("foam",preload("res://assets/lane2/water_ripple_color_psd_125d74ca.png"))
	water.set_shader_parameter("relief",preload("res://assets/lane2/water_river_normal_sharp_psd_c6855255.png"))

	for side in [-1,1]:
		for i in 10:
			var z := .19+.26*i+rng.randf_range(-.06,.06)
			var edge := .92+.055*sin(z*5.+side)+rng.randf_range(-.035,.04)
			if i%4 != 2:
				prop(TREE,Vector3(side*edge,-.009,z),rng.randf_range(.30,.42))
			prop(ROCK,Vector3(side*(edge+.008),-.023,-z),rng.randf_range(.18,.32))
		for i in 4:
			prop(ROCK,Vector3(side*(.70+i*.10),-.028,.08*side+rng.randf_range(-.04,.04)),rng.randf_range(.06,.10))
	prop(BONES,Vector3(-.79,.001,-1.05),.16)
	prop(BONES,Vector3(.78,.001,-.43),.11)
	pennant(Vector3(.84,0,.80),Color("#477a65"),-1)
	pennant(Vector3(-.85,0,-1.22),Color("#8a3934"),1)

func prop(scene: PackedScene, at: Vector3, width: float) -> void:
	var model := scene.instantiate() as Node3D
	add_child(model)
	model.rotation.y = rng.randf_range(-PI,PI)
	var bounds := AABB()
	for mesh: MeshInstance3D in model.find_children("*","MeshInstance3D",true,false):
		var box := mesh.global_transform*mesh.get_aabb()
		bounds = bounds.merge(box) if bounds.has_volume() else box
	var factor := width/maxf(bounds.size.x,bounds.size.z)
	model.scale *= factor
	model.position = at-Vector3(bounds.get_center().x,bounds.position.y,bounds.get_center().z)*factor

func pennant(at: Vector3, tint: Color, direction: float) -> void:
	var pole := MeshInstance3D.new()
	var rod := CylinderMesh.new()
	rod.height=.23
	rod.top_radius=.004
	rod.bottom_radius=.006
	pole.mesh=rod
	var bronze := StandardMaterial3D.new()
	bronze.albedo_color=Color("#78624c")
	pole.material_override=bronze
	add_child(pole)
	pole.position=at+Vector3.UP*.115
	var flag := MeshInstance3D.new()
	var cloth := PlaneMesh.new()
	cloth.orientation=PlaneMesh.FACE_Z
	cloth.size=Vector2(.105,.068)
	cloth.subdivide_width=14
	flag.mesh=cloth
	var mat := ShaderMaterial.new()
	mat.shader=preload("res://terrain/pennant.gdshader")
	mat.set_shader_parameter("tint",tint)
	flag.material_override=mat
	add_child(flag)
	flag.rotation.y=PI if direction<0 else 0.
	flag.position=at+Vector3(.0525*direction,.19,0)
