extends "res://preview.gd"

const FONT = preload("res://selection_assets/kaiti.ttf")
const FACE = preload("res://hand_face.gd")
const OFFERS = [["神秘商店","chainmail"], ["物品牌堆","item"], ["消耗品","salve"]]

var player: AnimationPlayer
var shade := ColorRect.new()
var view := TextureRect.new()
var goods := Control.new()
var cards: Array[Control] = []
var homes: Array[Vector2] = []
var focus_tween: Tween
var selected := -1
var browsing := false
var gold := 8

func _ready() -> void:
	var viewport := SubViewport.new()
	viewport.world_3d = World3D.new()
	viewport.transparent_bg = true
	viewport.size = Vector2i(1080, 1080)
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
	shade.color = Color(0.028,0.021,0.018,0.49)
	shade.size = Vector2(1260,2800)
	add_child(shade)
	view.texture = viewport.get_texture()
	view.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	view.size = Vector2(1260,1260)
	view.position = Vector2(0,770)
	$HUD.add_child(view)
	$HUD.add_child(goods)
	for i in OFFERS.size():
		show_offer(i)
	var done := plate(Rect2(445,1840,370,102), "#262b2cf8", "#91836a", 6)
	write(done, "结束采购", Vector2.ZERO, done.size, 48)
	tap_area(done, finish)
	if "--still" in OS.get_cmdline_user_args():
		await super()
		return
	open_shop()

func plate(rect: Rect2, fill: String, edge: String, radius: int) -> Panel:
	var panel: Panel = $HUD.panel(rect,Color(fill),Color(edge),radius)
	panel.reparent(goods,false)
	return panel

func write(parent: Control, words: String, at: Vector2, extent: Vector2, px: int, tint := Color("#fff2db")) -> void:
	var label := Label.new()
	label.text = words
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.position = at
	label.size = extent
	label.add_theme_font_override("font",FONT)
	label.add_theme_font_size_override("font_size",px)
	label.add_theme_color_override("font_color",tint)
	label.add_theme_constant_override("outline_size",3)
	label.add_theme_color_override("font_outline_color",Color("#2d211c"))
	parent.add_child(label)

func show_offer(index: int) -> void:
	var data: Array = OFFERS[index]
	var x := 178 + index * 306
	var card := FACE.new()
	goods.add_child(card)
	card.build(data[1])
	card.scale = Vector2.ONE * 0.83
	card.position = Vector2(x + (290.0 - FACE.DIM.x * card.scale.x) / 2, 1055)
	cards.append(card)
	homes.append(card.position)
	tap_area(card, inspect.bind(index))
	var button := plate(Rect2(x+24,1525,242,78),"#51402c","#b79a63",8)
	write(button,"购买",Vector2(10,0),Vector2(119,78),37)
	$HUD.resource_icon(button,preload("res://hud/gold.png"),Vector2(139,27),Vector2(34,24))
	write(button,FACE.BOOK[data[1]][1],Vector2(173,0),Vector2(48,78),35,Color("#ffcf65"))
	tap_area(button, buy.bind(index))
	var slot := Control.new()
	slot.position = Vector2(x,1607)
	slot.size = Vector2(290,66)
	goods.add_child(slot)
	write(slot,data[0],Vector2.ZERO,slot.size,30,Color("#c2ae8e"))

func tap_area(parent: Control, action: Callable) -> void:
	var button := Button.new()
	parent.add_child(button)
	button.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	button.flat = true
	button.focus_mode = Control.FOCUS_NONE
	for state in ["normal","pressed","hover","disabled"]:
		button.add_theme_stylebox_override(state,StyleBoxEmpty.new())
	button.pressed.connect(action)

func sound(clip: AudioStream) -> void:
	var voice := AudioStreamPlayer.new()
	voice.stream = clip
	add_child(voice)
	voice.finished.connect(voice.queue_free)
	voice.play()

func open_shop() -> void:
	goods.modulate.a = 0
	goods.hide()
	shade.modulate.a = 0
	view.hide()
	await get_tree().create_timer(0.45).timeout
	view.show()
	sound(preload("res://shop/open.wav"))
	player.play("in_game_shop_appear_maximized",0,1.25)
	create_tween().tween_property(shade,"modulate:a",1.0,0.55)
	await player.animation_finished
	player.play("in_game_shop_maximized_idle_1")
	goods.show()
	await create_tween().tween_property(goods,"modulate:a",1.0,0.22).finished
	browsing = true
	if "--demo" in OS.get_cmdline_user_args():
		await get_tree().create_timer(0.6).timeout
		if "--skip" in OS.get_cmdline_user_args():
			finish()
			return
		inspect(1)
		await get_tree().create_timer(1.25).timeout
		buy(1)

func inspect(index: int) -> void:
	if not browsing: return
	if focus_tween: focus_tween.kill()
	selected = -1 if selected == index else index
	focus_tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_SINE)
	for i in cards.size():
		var focus := i == selected
		var size_factor := 1.28 if focus else 0.83
		var offset := Vector2(-FACE.DIM.x*(size_factor-0.83)/2,-FACE.DIM.y*(size_factor-0.83)-15) if focus else Vector2.ZERO
		cards[i].z_index = 1 if focus else 0
		focus_tween.tween_property(cards[i],"position",homes[i]+offset,0.22)
		focus_tween.tween_property(cards[i],"scale",Vector2.ONE*size_factor,0.22)

func buy(index: int) -> void:
	var price := int(FACE.BOOK[OFFERS[index][1]][1])
	if not browsing or gold < price: return
	browsing = false
	if focus_tween: focus_tween.kill()
	var card := cards[index]
	var origin := card.global_position
	card.reparent($HUD,false)
	card.position = origin
	gold -= price
	$HUD.gold_label.text = str(gold)
	sound(preload("res://shop/buy.wav"))
	purchase_fx(card)
	var start_scale := card.scale
	var count: int = $HUD.held_cards.size()
	var target := Vector2(735,2632+count*6.5)
	var tween := create_tween()
	tween.tween_interval(0.16)
	tween.tween_method(func(t: float):
		for i in count:
			$HUD.position_hand($HUD.held_cards[i],i,count+t)
		card.scale = start_scale.lerp(Vector2.ONE,t)
		card.position = origin.lerp(target,t)+Vector2(72,-85)*sin(PI*t)
		card.rotation_degrees = lerpf(0, count*1.4,t)
		# Shift the spinning origin to match the hand's final pivot.
		card.pivot_offset = FACE.DIM*0.5*t,0.0,1.0,0.72).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	await tween.finished
	$HUD.held_cards.append(card)
	$HUD.position_hand(card,count,count+1)
	close_shop()

func finish() -> void:
	if not browsing: return
	browsing = false
	close_shop()

func close_shop() -> void:
	await create_tween().tween_property(goods,"modulate:a",0.0,0.16).finished
	goods.hide()
	sound(preload("res://shop/close.wav"))
	player.play("in_game_shop_finish_shopping_from_maximized",0,1.25)
	var brighten := create_tween()
	brighten.tween_interval(0.60)
	brighten.tween_property(shade,"modulate:a",0.0,0.58)
	await player.animation_finished
	view.hide()
	player.stop()
	shade.hide()

func purchase_fx(card: Control) -> void:
	var at := card.global_position + card.size*card.scale*Vector2(0.5,0.64)
	var burst := preload("res://shop/purchase_fx.gd").new()
	$HUD.add_child(burst)
	burst.start(at)
