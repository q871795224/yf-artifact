extends "res://mobile_layout.gd"

var held_cards: Array[Control] = []
var gold_label: Label
var deck_top: Sprite2D
const FACE = preload("res://hand_face.gd")

func card_image(parent: Control, tex: Texture2D, at: Vector2, extent: Vector2) -> void:
	var art := TextureRect.new()
	art.texture = tex
	art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	art.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	art.position = at
	art.size = extent
	parent.add_child(art)

func deck_pile(at: Vector2, angle: float) -> Sprite2D:
	var pile := Node2D.new()
	pile.position = at
	pile.rotation_degrees = angle
	add_child(pile)
	var back := AtlasTexture.new()
	back.atlas = preload("res://models/artifact_movie/card/card_back_color_psd_7981b7ea.png")
	back.region = Rect2(189, 0, 645, 1024)
	for layer in 4:
		var card := Sprite2D.new()
		card.texture = back
		card.scale = Vector2(0.224, 0.205)
		card.position = Vector2(layer * 1.4, -layer * 5.0)
		card.modulate = Color.WHITE.darkened((3 - layer) * 0.14)
		pile.add_child(card)

	return pile.get_child(-1)

func _ready() -> void:
	font.font_names = PackedStringArray(["Noto Serif CJK SC","Microsoft YaHei"])
	var bronze := Color("#8b7661")
	deck_top = deck_pile(Vector2(1138, 2780), 9.0)
	deck_pile(Vector2(1224, 33), 171.0)
	for i in 5:
		var back := panel(Rect2(153+i*124,-245,194,311),Color("#241e1c"),bronze)
		back.clip_contents = true
		card_image(back,preload("res://models/artifact_movie/card/card_back_color_psd_7981b7ea.png"),Vector2(5,4),Vector2(184,302))
		back.rotation_degrees = (i-2)*1.2
	var test_frame := panel(Rect2(18,35,163,65),Color("#151c1ddd"),bronze,8)
	var test := Button.new()
	test.position = Vector2(18,35)
	test.size = Vector2(163,68)
	test.add_theme_font_override("font",font)
	test.add_theme_font_size_override("font_size",30)
	test.text = "切换满员"
	test.pressed.connect(func():
		var map = get_parent().get_node("Screen/World/Map")
		map.pitch_study = not map.pitch_study
		map.rebuild_samples()
		test.text = "切换常规" if map.pitch_study else "切换满员")
	add_child(test)
	var fps := Button.new()
	fps.position = Vector2(18,107)
	fps.custom_minimum_size = Vector2(190,64)
	fps.add_theme_font_override("font",font)
	fps.add_theme_font_size_override("font_size",26)
	var refresh := func():
		fps.text = "%d / %d FPS" % [Engine.get_frames_per_second(),Engine.max_fps]
	fps.pressed.connect(func():
		var limits := [30,60,120]
		Engine.max_fps = limits[(limits.find(Engine.max_fps)+1)%limits.size()]
		refresh.call())
	add_child(fps)
	refresh.call()
	var timer := Timer.new()
	timer.wait_time = 1.0
	timer.timeout.connect(refresh)
	add_child(timer)
	timer.start()
	if get_parent().scene_file_path in ["res://move_preview.tscn", "res://respawn_preview.tscn", "res://damage_preview.tscn", "res://shop_preview.tscn"] or "--still" in OS.get_cmdline_user_args() or "--draw" in OS.get_cmdline_user_args():
		test_frame.hide()
		test.hide()
		fps.hide()

	for kind in ["unit", "spell", "item", "spell"]:
		var held := FACE.new()
		add_child(held)
		held.build(kind)
		held.pivot_offset = FACE.DIM * 0.5
		held_cards.append(held)
		position_hand(held, held_cards.size() - 1, 4)
	resource_panel(8)
	resource_panel(2592)
	if "--draw" in OS.get_cmdline_user_args():
		play_draw()

func position_hand(card: Control, index: int, count: float) -> void:
	var offset := index - (count - 1.0) * 0.5
	var step := 715.0 / (count - 1.0)
	card.position = Vector2(20 + index * step, 2632 + absf(offset) * 13)
	card.rotation_degrees = offset * 2.8

func play_draw() -> void:
	var moving := Node2D.new()
	add_child(moving)
	var start := deck_top.global_position
	var start_angle := deck_top.global_rotation_degrees
	moving.position = start
	var reverse := Sprite2D.new()
	reverse.texture = deck_top.texture
	reverse.scale = Vector2(FACE.DIM.x / 645.0, FACE.DIM.y / 1024.0)
	moving.add_child(reverse)
	var drawn := FACE.new()
	moving.add_child(drawn)
	drawn.build("unit")
	drawn.position = -FACE.DIM * 0.5
	drawn.hide()
	moving.hide()
	var sound := AudioStreamPlayer.new()
	sound.stream = preload("res://hud/draw_01.wav")
	add_child(sound)
	var tween := create_tween()
	tween.tween_interval(0.7)
	tween.tween_callback(func():
		moving.show()
		deck_top.hide()
		sound.play())
	var reveal := Vector2(818, 2288)
	tween.tween_method(func(t: float):
		var arc := sin(PI * t)
		moving.position = start.lerp(reveal, t) + Vector2(18, -62) * arc
		moving.rotation_degrees = lerpf(start_angle, -2, t)
		var flip := smoothstep(0.22, 0.9, t)
		moving.scale = Vector2(lerpf(0.44, 1.0, t) * maxf(0.008, absf(cos(PI * flip))), lerpf(0.382, 1.0, t))
		reverse.visible = flip < 0.5
		drawn.visible = not reverse.visible, 0.0, 1.0, 0.64).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tween.tween_interval(0.55)
	var target := FACE.DIM * 0.5 + Vector2(735, 2658)
	tween.tween_method(func(t: float):
		for i in held_cards.size():
			position_hand(held_cards[i], i, 4.0 + t)
		moving.position = reveal.lerp(target, t)
		moving.rotation_degrees = lerpf(-2, 5.6, t), 0.0, 1.0, 0.46).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tween.tween_callback(func():
		drawn.reparent(self, false)
		drawn.pivot_offset = FACE.DIM * 0.5
		position_hand(drawn, 4, 5)
		held_cards.append(drawn)
		moving.queue_free())

func resource_panel(y: int) -> void:
	var x := 862 if y < 100 else 981
	var shell := panel(Rect2(x,y,265,74),Color("#332e29"),Color("#aa9670"),6)
	var surface := ColorRect.new()
	surface.position = Vector2(3,3)
	surface.size = Vector2(259,68)
	var finish := ShaderMaterial.new()
	finish.shader = preload("res://hud/plaque.gdshader")
	surface.material = finish
	shell.add_child(surface)
	resource_icon(shell,preload("res://hud/gold.png"),Vector2(15,14),Vector2(61,47))
	var amount := caption(Vector2(x+77,y+2),"8" if y > 100 and get_parent().scene_file_path == "res://shop_preview.tscn" else "0",43,Color("#f3c054"))
	if y > 100:
		gold_label = amount
	resource_icon(shell,preload("res://hud/mana.svg"),Vector2(129,6),Vector2(46,62))
	caption(Vector2(x+178,y+2),"3/3",41,Color("#a4e3e9"))

func resource_icon(container: Control, texture: Texture2D, at: Vector2, extent: Vector2) -> void:
	var icon := Sprite2D.new()
	icon.texture = texture
	icon.position = at + extent * 0.5
	icon.scale = Vector2.ONE * minf(extent.x / texture.get_width(),extent.y / texture.get_height())
	container.add_child(icon)
