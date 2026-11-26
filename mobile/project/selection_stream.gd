extends Node2D

const SMOKE = preload("res://selection_assets/beam_smoke_01.png")
const PLASMA = preload("res://selection_assets/beam_plasma_04.png")
const FLARE = preload("res://cast_fx/particle_flare_010.png")
const PULSE = preload("res://selection_assets/drag_card_type_seq6.png")
const SPELL = preload("res://selection_assets/drag_card_type_seq3.png")
const ITEM = preload("res://selection_assets/cardtype_weapon_psd.png")
var beams: Array[Line2D] = []
var origin := Vector2.ZERO
var tip := Vector2.ZERO
var age := 0.0
var item := false
var strength := 0.0

func _ready() -> void:
	for texture in [SMOKE, PLASMA]:
		var line := Line2D.new()
		var mat := ShaderMaterial.new()
		mat.shader = preload("res://selection_stream.gdshader")
		mat.set_shader_parameter("beam", texture)
		line.material = mat
		line.texture = texture
		line.texture_mode = Line2D.LINE_TEXTURE_STRETCH
		line.width = 49 if beams.is_empty() else 25
		add_child(line)
		beams.append(line)

func curve(t: float) -> Vector2:
	var bend := Vector2(-36.0, -45.0) * sin(t * PI)
	return origin.lerp(tip,t) + bend

func aim(start: Vector2, end: Vector2, seconds: float, is_item: bool, opacity: float) -> void:
	visible = opacity > 0 and start.distance_to(end) > 26
	if not visible: return
	origin = start
	tip = end
	item = is_item
	age = seconds
	strength = opacity
	for line in beams:
		var path := PackedVector2Array()
		for j in 29:
			path.append(curve(j / 28.0))
		line.points = path
		line.modulate.a = opacity * 0.88
		line.material.set_shader_parameter("scroll",seconds*4.0)
	queue_redraw()

func _draw() -> void:
	var cyan := Color(0.4,1,0.97,strength*0.9)
	for i in 40:
		var t := fposmod(age*1.25 + i/40.0,1.0)
		var wave := Vector2(sin(i*17.2+age*2),cos(i*9.4))*13*sin(t*PI)
		var at := curve(t) + wave
		var size_px := 10.0 + 11.0*sin(i*2.8)*sin(i*2.8)
		draw_texture_rect(FLARE,Rect2(at-Vector2.ONE*size_px/2,Vector2.ONE*size_px),false,Color(cyan,cyan.a*sin(PI*t)))
	var extent := Vector2.ONE * (77 + 8*sin(age*TAU))
	draw_texture_rect(PULSE,Rect2(tip-extent/2,extent),false,Color(cyan,strength*0.28))
	draw_texture_rect(ITEM if item else SPELL,Rect2(tip-Vector2(32,32),Vector2(64,64)),false,cyan)
