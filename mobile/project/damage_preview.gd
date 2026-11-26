extends Node

const Tracks = preload("res://clash_tracks.gd")
const SWING := 1.65
const HIT := SWING + 0.60
var actors: Array[Node3D] = []
var poses: Array[Transform3D] = []
var hp: Array[int] = []
var damage: Array[int] = []
var tags: Array[Panel] = []
var elapsed := 0.0
@onready var camera: Camera3D = $Screen/World/Map/Camera3D

func _ready() -> void:
	var pieces := {}
	for node in $Screen/World/Map/LayoutSamples.get_children():
		if node.has_meta("piece_cell"):
			pieces[node.get_meta("piece_cell")] = node
	actors.assign([pieces[Vector2i(2,3)], pieces[Vector2i(2,4)]])
	# A strengthened creep lets both units survive the one exchange.
	actors[0].get_node("card_attack_value").text = "5"
	actors[0].get_node("card_health_value").text = "12"
	for i in 2:
		var piece := actors[i]
		poses.append(piece.transform)
		hp.append(int(piece.get_node("card_health_value").text))
		var armor := piece.get_node_or_null("card_armor_value") as Label3D
		var attack := int(actors[1-i].get_node("card_attack_value").text)
		damage.append(maxi(0, attack - (int(armor.text) if armor else 0)))
		var tag: Panel = $HUD.panel(Rect2(0,0,53,42), Color("#912e22"), Color("#52231c"), 3)
		var number := Label.new()
		number.text = "-%d" % damage[i]
		number.size = tag.size
		number.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		number.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		number.add_theme_font_size_override("font_size",34)
		number.add_theme_color_override("font_color",Color("#fff1d6"))
		tag.add_child(number)
		tags.append(tag)
	assert(hp[0] > damage[0] and hp[1] > damage[1])
	update_frame(0.0)

func sample_track(rows: Array, time: float) -> Vector3:
	var last: Array = rows[0]
	for row: Array in rows:
		if row[0] > time:
			var mix_amount := inverse_lerp(float(last[0]),float(row[0]),time)
			return Vector3(last[1],last[2],last[3]).lerp(Vector3(row[1],row[2],row[3]),mix_amount)
		last = row
	return Vector3(last[1],last[2],last[3])

func update_frame(time: float) -> void:
	var after := time - HIT
	var t := maxf(after if after >= 0 else time-SWING, 0)
	for i in 2:
		var moves: Array = Tracks.LOCAL_CLASH_TRANSLATION if i == 0 else Tracks.OPPONENT_CLASH_TRANSLATION
		var turns: Array = Tracks.LOCAL_CLASH_ROTATION if i == 0 else Tracks.OPPONENT_CLASH_ROTATION
		if after >= 0:
			moves = Tracks.LOCAL_RETURN_TRANSLATION if i == 0 else Tracks.OPPONENT_RETURN_TRANSLATION
			turns = Tracks.LOCAL_RETURN_ROTATION if i == 0 else Tracks.OPPONENT_RETURN_ROTATION
		var p := sample_track(moves,t)
		var q := sample_track(turns,t)
		var offset_z := p.z * (2.66 if (p.z > 0) == (i == 0) else (0.24 if i == 0 else 1.5))
		actors[i].transform = Transform3D(poses[i].basis.rotated(Vector3.RIGHT,-2.0*asin(q.y)),poses[i].origin+Vector3(0,p.x*0.43,offset_z))
		var life: Label3D = actors[i].get_node("card_health_value")
		life.text = str(hp[i] - (damage[i] if after >= 0 else 0))
		var pulse := sin(PI*clampf(after/0.24,0,1))
		var badge_scale := Vector3.ONE * (1.0 + 0.22*pulse)
		life.scale = badge_scale
		var badge: Node3D = actors[i].get_node("card_health")
		badge.scale = badge_scale
		var anchor: Vector2 = $Screen.get_global_transform() * camera.unproject_position(badge.to_global(Vector3(0,-0.029,0.009)))
		tags[i].position = anchor - Vector2(tags[i].size.x * 0.5, 0)
		tags[i].modulate.a = smoothstep(0.32,0.50,time)*(1.0-smoothstep(0.18,0.55,after))

func _process(delta: float) -> void:
	elapsed += delta
	update_frame(elapsed)
