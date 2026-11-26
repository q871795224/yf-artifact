extends Node2D

const Source = preload("res://cast_fx/cast_data.gd")
const DATA = Source.DATA
var layers: Array[Dictionary] = []

func _ready() -> void:
	var additive := CanvasItemMaterial.new()
	additive.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	material = additive
	var rng := RandomNumberGenerator.new()
	rng.seed = 10300
	for kind in ["mist", "card", "embers", "flash"]:
		var spec: Dictionary = DATA[kind]
		var c: Array = spec.color
		for i in int(spec.count):
			var sprite := Sprite2D.new()
			sprite.use_parent_material = true
			add_child(sprite)
			var pt: Array = DATA.points[rng.randi_range(0, DATA.points.size()-1)]
			var offset := Vector2(pt[0]*47.5, pt[1]*42.2)
			var life := float(spec.life)
			var span := Vector2(415, 512)
			var vel := Vector2.ZERO
			var frames: Array = []
			var trail: Sprite2D
			match kind:
				"mist":
					frames = spec.seq[rng.randi_range(0,1)]
					life = rng.randf_range(1,1.5)
					span = Vector2.ONE * rng.randf_range(162, 240)
					vel = offset.normalized() * rng.randf_range(80,125)
				"embers":
					life = rng.randf_range(0.4,1.0)
					span = Vector2.ONE * rng.randf_range(36,72)
					vel = offset.normalized() * rng.randf_range(-42,42)
					trail = Sprite2D.new()
					trail.texture = Source.TEXTURES[spec.trail]
					trail.use_parent_material = true
					add_child(trail)
				"flash":
					offset = Vector2.ZERO
					span = Vector2.ONE * 920
				"card":
					offset = Vector2.ZERO
			sprite.texture = Source.TEXTURES[frames[0] if kind == "mist" else spec.tex]
			layers.append({"sprite":sprite,"kind":kind,"frames":frames,"trail":trail,"span":span,"offset":offset,"velocity":vel,"life":life,"color":Color8(c[0],c[1],c[2],c[3])})
	seek(-1)

func seek(age: float) -> void:
	visible = age >= 0 and age < 1.5
	if not visible: return
	for p in layers:
		var sprite: Sprite2D = p.sprite
		var t := clampf(age/p.life,0,1)
		sprite.visible = t < 1.0
		var opacity := 1.0 - t
		var size_factor := 1.0
		if p.kind == "mist":
			var index := mini(int(age * 0.3 * p.frames.size()), p.frames.size()-1)
			sprite.texture = Source.TEXTURES[p.frames[index]]
			opacity = smoothstep(0,0.1,t)*(1.0-smoothstep(0.3,1,t))*0.60
			size_factor = 1+t
		elif p.kind == "embers":
			size_factor = 1.0-t
			opacity = 1.0-smoothstep(0.5,1,t)
		elif p.kind == "flash":
			size_factor = lerpf(0.5,1,t)
		sprite.position = p.offset + p.velocity * age
		sprite.scale = p.span * size_factor / sprite.texture.get_size()
		sprite.modulate = Color(p.color, opacity)
		if p.trail:
			var tail: Sprite2D = p.trail
			tail.visible = sprite.visible
			tail.position = sprite.position - p.velocity * 0.08
			tail.rotation = p.velocity.angle()
			tail.scale = Vector2(p.velocity.length()*0.4,5.0)*size_factor/tail.texture.get_size()
			tail.modulate = sprite.modulate
