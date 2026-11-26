extends Node2D
# Godot adaptation of shop_card_purchase_coins and shop_card_purchase_flare.
func start(at: Vector2) -> void:
	position = at
	var viewport := SubViewport.new()
	viewport.world_3d = World3D.new()
	viewport.size = Vector2i(320,320)
	viewport.transparent_bg = true
	add_child(viewport)
	var camera := Camera3D.new()
	viewport.add_child(camera)
	camera.position.z = 3
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 1.1
	var light := DirectionalLight3D.new()
	viewport.add_child(light)
	light.rotation_degrees = Vector3(-24,-25,0)
	light.light_energy = 2.6
	var sprite := Sprite2D.new()
	sprite.texture = viewport.get_texture()
	sprite.scale = Vector2.ONE*1.6
	add_child(sprite)
	for i in 5:
		var coin := preload("res://shop/coin.glb").instantiate() as Node3D
		viewport.add_child(coin)
		var velocity := Vector2((i-2)*0.16,0.5 + 0.14*sin(i*4.0))
		var run := create_tween()
		run.tween_method(func(t: float):
			coin.position = Vector3(velocity.x*t,velocity.y*t-0.55*t*t,0)
			coin.rotation = Vector3(0.7+t*4+i,t*(3+i),i)
			coin.scale = Vector3.ONE*(1.0-0.9*smoothstep(0.7,1.4,t)),0.0,1.4,1.4)
	for i in 2:
		var flare := Sprite2D.new()
		flare.texture = preload("res://shop/combined_flare.png")
		flare.material = CanvasItemMaterial.new()
		flare.material.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		flare.modulate = Color("#ffd875")
		flare.position.x = (i-0.5)*90
		flare.scale = Vector2.ONE*0.07
		add_child(flare)
		var flash := create_tween().set_parallel(true)
		flash.tween_property(flare,"scale",flare.scale*4,0.4)
		flash.tween_property(flare,"modulate:a",0.0,0.4)
	await get_tree().create_timer(1.42).timeout
	queue_free()
