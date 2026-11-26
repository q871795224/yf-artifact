extends Node

const PORTRAIT = preload("res://hud/ursa_icon.png")
const HIT := 0.9
const FOURTH_ROUND := 4.75
@onready var hud := $HUD
var hero: Node3D
var hp: Label3D
var tile: MeshInstance3D
var original: Material
var origin: Transform3D
var landing: Vector3
var waiting: Label
var ready_mark: Line2D
var badge: Panel
var round_label: Label
var full_hp: String
var time := 0.0

func label_on(parent: Control, at: Vector2, words: String, px: int) -> Label:
	var label := Label.new()
	label.text = words
	label.position = at
	label.add_theme_font_override("font", preload("res://selection_assets/kaiti.ttf"))
	label.add_theme_font_size_override("font_size", px)
	parent.add_child(label)
	return label

func _ready() -> void:
	var markers := {}
	for node in $Screen/World/Map/LayoutSamples.get_children():
		if node.has_meta("cell_marker"):
			markers[node.get_meta("cell_marker")] = node
		if node.get_meta("piece_cell", Vector2i(-1,-1)) == Vector2i(2,4):
			hero = node
	hero.position += markers[Vector2i(1,3)].position - markers[Vector2i(2,4)].position
	origin = hero.transform
	tile = markers[Vector2i(1,0)]
	landing = tile.position + hero.position - markers[Vector2i(1,3)].position
	original = tile.material_override
	for child in hero.get_children():
		if child is Label3D and child.position.x > 0.0:
			hp = child
	full_hp = hp.text
	var round_panel: Panel = hud.panel(Rect2(10,12,154,64), Color("#1a2020ef"), Color("#82715d"), 6)
	round_label = label_on(round_panel, Vector2(9,8), "第2轮", 43)
	badge = hud.panel(Rect2(22,2520,87,99), Color("#772337"), Color("#241d20"), 5)
	var portrait := TextureRect.new()
	portrait.texture = PORTRAIT
	portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	portrait.size = Vector2(81,87)
	portrait.position = Vector2(3,6)
	badge.add_child(portrait)
	waiting = label_on(badge, Vector2(0,-51), "-1", 42)
	waiting.size.x = badge.size.x
	waiting.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	waiting.add_theme_color_override("font_color", Color("#c5c5c1"))
	waiting.add_theme_constant_override("outline_size", 5)
	waiting.add_theme_color_override("font_outline_color", Color("#282824"))
	ready_mark = Line2D.new()
	ready_mark.points = PackedVector2Array([Vector2(26,-22), Vector2(38,-10), Vector2(62,-36)])
	ready_mark.width = 8
	ready_mark.default_color = Color("#60e4a2")
	ready_mark.antialiased = true
	ready_mark.joint_mode = Line2D.LINE_JOINT_ROUND
	badge.add_child(ready_mark)
	badge.hide()

func _process(delta: float) -> void:
	time += delta
	var age := time - HIT
	var entry := time - FOURTH_ROUND
	round_label.text = "第4轮" if entry >= 0 else ("第3轮" if time >= 3.1 else "第2轮")
	waiting.visible = entry < 0
	ready_mark.visible = entry >= 0
	badge.visible = age >= 0 and entry < 1.73
	hero.visible = age < 1.4 or entry >= 0.26
	if age < 0:
		hp.text = "1"
	elif entry < 0:
		hp.text = "0"
		var fall := smoothstep(0.0, 0.48, age)
		var depart := smoothstep(0.86, 1.4, age)
		hero.position = origin.origin + Vector3(0.05*fall, 0.14*sin(PI*fall)+0.15*depart, -0.10*fall)
		hero.basis = origin.basis.rotated(Vector3.BACK, -0.65*fall).scaled(Vector3.ONE * maxf(0.002, 1.0-depart))
	else:
		hp.text = full_hp
		var glow := smoothstep(0.0, 0.22, entry) * (1.0-smoothstep(1.73, 2.12, entry))
		if tile.material_override == original:
			tile.material_override = original.duplicate()
		var base: Color = original.get_shader_parameter("tint")
		tile.material_override.set_shader_parameter("tint", base.lerp(Color("#8dffed"), glow))
		# Same approach, hover, drop and rebound timings as the deployment study.
		var approach := smoothstep(0.26, 0.98, entry)
		var drop := smoothstep(1.49, 1.73, entry)
		var rebound := 0.034 * sin(PI * clampf((entry-1.73)/0.19,0,1))
		hero.position = landing + Vector3(0.10*(1.0-approach), 0.126*(1.0-drop)+rebound, -0.43*(1.0-approach))
		hero.basis = origin.basis.rotated(Vector3.RIGHT, deg_to_rad(-18.0*(1.0-drop)))
