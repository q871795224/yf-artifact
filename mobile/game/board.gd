extends Node
const PIECE = preload("res://unit_piece.gd")
var tiles := {}
var figures := {}
var marks := {}
var badges := {}
var fort_state := {}
var fort_rest := {}
var map: Node3D
var region: SubViewportContainer
var texture_for: Callable

func setup(screen: SubViewportContainer, texture: Callable) -> void:
	region = screen
	map = screen.get_node("World/Map")
	texture_for = texture
	var camera: Camera3D = map.get_node("Camera3D")
	camera.fov = 10.7
	camera.position -= camera.global_basis.y*0.39
	for model in map.get_node("Towers").get_children(): fort_rest[model.get_index()] = model.transform
	for node in map.get_node("LayoutSamples").get_children():
		if node.has_meta("piece_cell"):
			node.hide()
			node.queue_free()
		elif node.has_meta("cell_marker"):
			var index: Vector2i = node.get_meta("cell_marker")
			tiles[Vector2i(4-index.x,7-index.y)] = node
		elif node.has_node("card_health_value"):
			badges[int(node.position.z > 0)] = node

func cell_of(unit: Dictionary) -> Vector2i:
	return Vector2i(int(unit.col),int(unit.row))

func screen_at(cell: Vector2i) -> Vector2:
	var tile: Node3D = tiles[cell]
	return region.get_transform() * map.get_node("Camera3D").unproject_position(tile.global_position + Vector3.UP*0.045)

func pick(point: Vector2) -> Vector2i:
	var nearest := Vector2i(-1,-1)
	var score := 1.0
	for cell: Vector2i in tiles:
		var center := screen_at(cell)
		var width := center.distance_to(screen_at(Vector2i(1 if cell.x == 0 else cell.x-1,cell.y)))
		var dy := absf(center.y-screen_at(Vector2i(cell.x,cell.y+1 if cell.y < 7 else 6)).y)
		var delta := (point-center).abs()
		var metric := maxf(delta.x/(width*0.51),delta.y/(dy*0.51))
		if metric < score:
			score = metric
			nearest = cell
	return nearest

func highlight(cells: Array) -> void:
	for node in marks.values(): node.queue_free()
	marks.clear()
	for cell in cells:
		if marks.has(cell) or not tiles.has(cell): continue
		var glow := MeshInstance3D.new()
		var plane := PlaneMesh.new()
		plane.size = Vector2(0.32,0.38)
		glow.mesh = plane
		var mat := ShaderMaterial.new()
		mat.shader = preload("res://move_tile.gdshader")
		glow.material_override = mat
		map.add_child(glow)
		glow.position = tiles[cell].position + Vector3.UP*0.003
		marks[cell] = glow

func sync(frame: Dictionary, animate: bool) -> void:
	var present := {}
	for unit in frame.units:
		var key: String = unit.key
		present[key] = true
		var cell := cell_of(unit)
		var home: Vector3 = tiles[cell].position + Vector3(0,0.065,-0.014)
		var signature := str(unit.equipment.map(func(e): return e.id)) + str(int(unit.armor)>0)
		var obj: Node3D = figures.get(key)
		if obj != null and obj.get_meta("signature") != signature:
			obj.queue_free()
			obj = null
		if obj == null:
			obj = PIECE.new()
			map.add_child(obj)
			figures[key] = obj
			obj.set_meta("signature",signature)
			obj.build_piece(unit.hero,[],1.2)
			obj.basis = Basis(Vector3.LEFT,Vector3.BACK,Vector3.UP)
			var ray: Vector3 = map.get_node("Camera3D").position-home
			obj.rotate_x(atan2(ray.y,-ray.z)-deg_to_rad(22+58))
			obj.scale = Vector3.ONE*1.08
			for child in obj.get_children():
				if child is MeshInstance3D and child.mesh is QuadMesh:
					var image: Texture2D = texture_for.call(int(unit.id),unit.team)
					var m: ShaderMaterial = child.material_override
					if image is AtlasTexture:
						var factor: Vector2 = image.region.size/image.atlas.get_size()
						m.set_shader_parameter("offset",image.region.position/image.atlas.get_size()+factor*Vector2(0.1,0.015))
						m.set_shader_parameter("crop",factor*Vector2(0.8,0.94))
						image = image.atlas
					m.set_shader_parameter("portrait",image)
				if child is Node3D and child.name.to_lower().contains("ability") and unit.get("skillKind")==null:
					child.hide()
			if int(unit.armor)>0: obj.add_stat("card_armor",int(unit.armor),Vector3(0,-0.13,0.016))
			var slot_num := {"Weapon":0,"Armor":1,"Accessory":2}
			for equip in unit.equipment:
				obj.add_equipment(slot_num.get(equip.slot,2),texture_for.call(int(equip.id),unit.team),0.028)
			obj.position = home + (Vector3.UP*0.13 if animate else Vector3.ZERO)
		if animate and not obj.position.is_equal_approx(home):
			obj.create_tween().tween_property(obj,"position",home,0.22).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		else: obj.position = home
		for stat in {"attack":unit.attack,"health":unit.hp,"armor":unit.armor}:
			var label := obj.get_node_or_null("card_"+stat+"_value") as Label3D
			if label:
				label.text = str(int(unit[{"attack":"attack","health":"hp","armor":"armor"}[stat]]))
				label.modulate = Color("#ffb7a5") if unit.team=="enemy" else Color("#c7f8e4")
	for key in figures.keys():
		if present.has(key): continue
		var obj: Node3D = figures[key]
		figures.erase(key)
		if animate:
			var tween := obj.create_tween()
			var rest := obj.position
			tween.tween_property(obj,"position",rest+Vector3(0.06,0.12,0),0.15)
			tween.parallel().tween_property(obj,"rotation:z",obj.rotation.z+0.45,0.22)
			tween.tween_property(obj,"position",rest+Vector3(0.09,-0.04,0),0.17)
			tween.tween_interval(0.14)
			tween.tween_property(obj,"position:y",rest.y+0.18,0.24)
			tween.parallel().tween_property(obj,"scale",Vector3.ONE*0.01,0.24)
			tween.tween_callback(obj.queue_free)
		else: obj.queue_free()
	for f in frame.forts:
		var team := int(f.team)
		var model: Node3D = map.get_node("Towers").get_child(team)
		var last: Dictionary = fort_state.get(team,{})
		if animate and not last.is_empty() and int(last.hp)>0 and int(f.hp)<=0:
			fracture(model,team)
		elif animate and not last.is_empty() and int(f.hp)<int(last.hp):
			var rock := model.create_tween()
			rock.tween_property(model,"rotation:x",model.rotation.x+0.08,0.07)
			rock.tween_property(model,"rotation:x",fort_rest[team].basis.get_euler().x,0.19)
		model.visible = int(f.hp)>0
		fort_state[team] = f
		var badge: Node3D = badges.get(team)
		if badge:
			badge.get_node("card_health_value").text = str(int(f.hp))
			badge.get_node("card_attack_value").text = str(int(f.attack))

func clash(units: Array) -> void:
	for unit in units:
		if unit.get("target")==null or not unit.get("canAttack",true): continue
		var obj: Node3D = figures.get(unit.key)
		if not obj: continue
		var home := obj.position
		var target: Node3D = figures.get(unit.target)
		var direction := (target.position-home).normalized() if target else Vector3.BACK*(1 if unit.team=="ally" else -1)
		var tween := obj.create_tween()
		tween.tween_property(obj,"position",home-direction*0.035+Vector3.UP*0.08,0.18)
		tween.tween_interval(0.09)
		tween.tween_property(obj,"position",home+direction*0.13,0.09).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		tween.tween_property(obj,"position",home,0.14)


func equip_effect(key: String, slot: String) -> void:
	var host: Node3D = figures.get(key)
	if host==null: return
	var effect := preload("res://source2_fx/equip_generic.tscn").instantiate()
	host.add_child(effect)
	effect.position = Vector3((int({"Weapon":0,"Armor":1,"Accessory":2}.get(slot,1))-1)*0.088,0.137,0.025)
	effect.unit_scale = 0.031
	var t := effect.create_tween()
	t.tween_method(effect.seek,0.0,1.2,1.2)
	t.tween_callback(effect.queue_free)

func fracture(model: Node3D, team: int) -> void:
	var debris := preload("res://shatter/dcg_tower_radiant_destruction_final.glb").instantiate() as Node3D
	map.add_child(debris)
	debris.transform = fort_rest[team]
	var clip := debris.find_children("*","AnimationPlayer",true,false)[0] as AnimationPlayer
	model.hide()
	clip.play("dcg_tower_radiant_destruction_final",0,0.75)
	clip.pause()
	var cut := debris.create_tween()
	cut.tween_interval(0.15)
	cut.tween_callback(func(): clip.play("dcg_tower_radiant_destruction_final",0,0.75))
	cut.tween_interval(1.05)
	var camera: Camera3D = map.get_node("Camera3D")
	var initial := camera.transform
	var focus: Vector3 = tiles[Vector2i(2,6 if team==0 else 1)].position
	var offset := focus-camera.position
	var center := camera.position+camera.global_basis.y*offset.dot(camera.global_basis.y)*0.66
	var lens := camera.create_tween()
	lens.tween_property(camera,"position",center,0.26)
	lens.parallel().tween_property(camera,"fov",7.8,0.26)
	lens.tween_interval(0.55)
	lens.tween_property(camera,"transform",initial,0.38)
	lens.parallel().tween_property(camera,"fov",10.7,0.38)
	cut.tween_property(debris,"scale",Vector3.ONE*0.0001,0.23)
	cut.tween_callback(debris.queue_free)

func forecast(data: Variant) -> void:
	for key in figures:
		var unit: Node3D = figures[key]
		var label := unit.get_node_or_null("Forecast") as Label3D
		var record: Dictionary = data.units.get(key,{}) if data is Dictionary else {}
		var hp: Label3D = unit.get_node("card_health_value")
		var loss := int(hp.text)-int(record.get("hp",int(hp.text)))
		if loss<=0:
			if label: label.hide()
			continue
		if not label:
			label = Label3D.new()
			label.name = "Forecast"
			unit.add_child(label)
			label.font_size = 76
			label.pixel_size = 0.00029
			label.outline_size = 12
			label.modulate = Color("#ff9a83")
		label.position = hp.position+Vector3(0,-0.035,0.004)
		label.text = "−%d"%loss
		label.show()
