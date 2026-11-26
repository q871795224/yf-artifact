extends Node3D

func part(parent: Node3D, id: String, at: Vector3) -> Node3D:
	var obj = load("res://models/card/" + id + ".glb").instantiate()
	parent.add_child(obj)
	obj.position = at
	return obj

const EQUIPMENT := [
	{"slot":0,"texture":preload("res://models/card/equip-3002.png"),"stats":Vector3i(2,0,0)},
	{"slot":1,"texture":preload("res://models/card/equip-10214.png"),"stats":Vector3i(0,0,2)},
	{"slot":2,"texture":preload("res://models/card/equip-3000.png"),"stats":Vector3i(0,4,0)}
]

func build_piece(hero: bool, equipment: Array, height_ratio := 1.0) -> void:
	var piece := self
	var rim := part(piece, "square_rim" if hero else "round_rim", Vector3.ZERO)
	rim.scale.y = height_ratio
	var extra := 0.141 * (height_ratio - 1.0)
	var art := MeshInstance3D.new()
	art.mesh = QuadMesh.new()
	art.mesh.size = Vector2(1.0,height_ratio) * 0.273 if hero else Vector2.ONE * 0.271
	var paint := ShaderMaterial.new()
	paint.shader = preload("res://piece_portrait.gdshader")
	paint.set_shader_parameter("portrait",preload("res://models/card/ursa.png") if hero else preload("res://models/artifact_movie/card/dire_melee_creep_color_psd_f7a6e9f8.png"))
	paint.set_shader_parameter("round_mask",not hero)
	paint.set_shader_parameter("crop",Vector2(0.76,0.76 * height_ratio) if hero else Vector2(0.79,0.79))
	paint.set_shader_parameter("offset",Vector2(0.12,0.035) if hero else Vector2(0.105,0.02))
	art.material_override = paint
	piece.add_child(art)
	art.position.z = 0.002
	var stats := Vector3i(7,10,0) if hero else Vector3i(2,4,0)
	if hero:
		for id in equipment:
			var equipment_item: Dictionary = EQUIPMENT[id]
			add_equipment(equipment_item.slot,equipment_item.texture,extra)
			stats += Vector3i(equipment_item.stats)
	for i in (3 if stats.z != 0 else 2):
		var at := Vector3(([-0.099,0.099,0.0] if hero else [-0.077,0.077])[i],-0.106-extra if hero else -0.087,0.009)
		add_stat(["card_attack","card_health","card_armor"][i],stats[i],at)
	if hero:
		var ability := part(piece,"ability_model",Vector3(-0.107,-0.039-extra,0.011))
		ability.scale = Vector3.ONE * 0.85
		var icon := StandardMaterial3D.new()
		icon.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		icon.albedo_texture = preload("res://models/card/fury.png")
		for mesh in ability.find_children("*","MeshInstance3D",true,false):
			if mesh.mesh.resource_name.begins_with("ability_model") or mesh.mesh.get_surface_count() == 1:
				mesh.set_surface_override_material(0,icon)

func show_emblem(badge: Node3D) -> void:
	for mesh in badge.find_children("*","MeshInstance3D",true,false):
		for s in mesh.mesh.get_surface_count():
			var mat = mesh.mesh.surface_get_material(s)
			if mat and mat.resource_name != "card_emblems":
				var hidden := StandardMaterial3D.new()
				hidden.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
				hidden.albedo_color.a = 0
				mesh.set_surface_override_material(s,hidden)

func add_equipment(slot: int, texture: Texture2D, extra: float) -> void:
	var center := Vector3((slot - 1) * 0.088,0.109+extra,0.009)
	var bezel := part(self,"round_rim",center)
	bezel.scale = Vector3(0.24,0.24,0.58)
	var face := MeshInstance3D.new()
	face.mesh = QuadMesh.new()
	face.mesh.size = Vector2.ONE * 0.0645
	var paint := ShaderMaterial.new()
	paint.shader = preload("res://piece_portrait.gdshader")
	paint.set_shader_parameter("portrait",texture)
	paint.set_shader_parameter("round_mask",true)
	paint.set_shader_parameter("crop",Vector2.ONE)
	paint.set_shader_parameter("offset",Vector2.ZERO)
	face.material_override = paint
	add_child(face)
	face.position = center + Vector3(0,0,0.0025)

func add_stat(model_id: String, amount: int, at: Vector3) -> void:
	var badge := part(self,model_id,at)
	badge.name = model_id
	show_emblem(badge)
	var value := Label3D.new()
	value.name = model_id + "_value"
	value.text = str(amount)
	value.font_size = 96
	value.pixel_size = 0.00032
	value.outline_size = 4
	add_child(value)
	value.position = at + Vector3(0,0,0.015)
