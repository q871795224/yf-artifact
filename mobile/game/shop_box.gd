extends TextureRect
var player: AnimationPlayer
func _ready() -> void:
	var viewport := SubViewport.new()
	viewport.world_3d = World3D.new()
	viewport.transparent_bg = true
	viewport.size = Vector2i(512, 512)
	add_child(viewport)
	var world := Node3D.new()
	viewport.add_child(world)
	var box := preload("res://shop/dcg_shop_box.glb").instantiate()
	world.add_child(box)
	player = box.find_children("*","AnimationPlayer",true,false)[0]
	player.play("in_game_shop_maximized_idle_1")
	player.seek(0.5,true)
	player.pause()
	var skeleton: Skeleton3D = box.find_children("*","Skeleton3D",true,false)[0]
	# Source 2 renders this outer shell as glass over the painted eyeball.
	var glass := StandardMaterial3D.new()
	glass.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	glass.albedo_color = Color(0.7,0.85,0.9,0.065)
	for mesh in box.find_children("*","MeshInstance3D",true,false):
		for i in mesh.mesh.get_surface_count():
			if mesh.mesh.surface_get_material(i).resource_name == "artifact_shop_eye_gloss":
				mesh.set_surface_override_material(i,glass)
	var camera := Camera3D.new()
	world.add_child(camera)
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 0.84
	var center: Vector3 = skeleton.global_transform * skeleton.get_bone_global_pose(skeleton.find_bone("perspective_panel")).origin
	camera.look_at_from_position(center + Vector3(0,0.2,2),center)
	var key := DirectionalLight3D.new()
	world.add_child(key)
	key.rotation_degrees = Vector3(-55,-30,0)
	key.light_energy = 1.4
	var env := Environment.new()
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color.WHITE
	env.ambient_light_energy = 0.86
	camera.environment = env
	texture = viewport.get_texture()
	expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	player.play("in_game_shop_appear_maximized",0,1.8)
	player.queue("in_game_shop_maximized_idle_1")
