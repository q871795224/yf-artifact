extends Control

signal cell_clicked(pos: Vector2i, secondary: bool)

const PAPER := Color("#e5ddc9")
const GOLD := Color("#d1b079")
const GREEN := Color("#8fc8a2")
const RED := Color("#e29280")
const TILE_GAP := 4.0

var assets_root := ""
var catalog: Dictionary = {}
var state: Dictionary = {}
var markers: Array[Vector2i] = []
var selected := ""
var show_arrows := true
var sound_enabled := true
var details_font: Font
var _textures: Dictionary = {}
var _illustrations: Dictionary = {}
var _from: Dictionary = {}
var _after: Dictionary = {}
var _shots: Array = []
var _progress := 0.0
var _stage := ""
var _impact_audio: AudioStreamPlayer

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	focus_mode = Control.FOCUS_ALL
	custom_minimum_size = Vector2(345, 476)
	mouse_exited.connect(queue_redraw)
	_impact_audio = AudioStreamPlayer.new()
	_impact_audio.stream = _impact_sample()
	add_child(_impact_audio)

func present(battle: Dictionary) -> void:
	state = battle
	queue_redraw()

func highlight(cells: Array[Vector2i], unit_key: String) -> void:
	markers = cells
	selected = unit_key
	queue_redraw()

func texture_for(id: int, team := "", large := false) -> Texture2D:
	var key := "%d:%s:%s" % [id, team, large]
	if _textures.has(key):
		return _textures[key]
	var card: Dictionary = catalog.get(id, {})
	var art_id := int(card.get("art_id", id))
	var file := assets_root.path_join("references/artifact-classic/assets/mobile/%s/%d.webp" % [
		"large_image" if large else "mini_image", art_id])
	if id == 64004 or (id == 1006 and team == "enemy"):
		var unit := "dire-melee"
		if id == 64004:
			unit = "dire-ranged" if team == "enemy" else "radiant-ranged"
		file = assets_root.path_join("prototype/assets/units/%s.webp" % unit)
	if not FileAccess.file_exists(file):
		file = assets_root.path_join("references/artifact-classic/assets/mobile/mini_image/%d.webp" % art_id)
	if not FileAccess.file_exists(file):
		_textures[key] = null
		return null
	var picture := Image.load_from_file(file)
	var texture: Texture2D = ImageTexture.create_from_image(picture) if not picture.is_empty() else null
	_textures[key] = texture
	return texture

func artwork_for(id: int, team := "") -> Texture2D:
	var key := "%d:%s" % [id, team]
	if _illustrations.has(key):
		return _illustrations[key]
	var source := texture_for(id, team, true)
	if source == null:
		return null
	var extent := source.get_size()
	var portrait := source
	if extent.y > extent.x and id != 64004 and (id != 1006 or team != "enemy"):
		var hero: bool = catalog.get(id, {}).get("card_type") == "Hero"
		var crop := AtlasTexture.new()
		crop.atlas = source
		crop.region = Rect2(0, extent.y * 0.12, extent.x, extent.y * (0.70 if hero else 0.46))
		portrait = crop
	_illustrations[key] = portrait
	return portrait

func unit_name(unit: Dictionary, short := false) -> String:
	if int(unit.id) in [1006, 64004]:
		var role := "近战兵" if int(unit.id) == 1006 else "远程兵"
		return role if short else ("天辉" if unit.team == "ally" else "夜魇") + role
	return catalog.get(int(unit.id), {}).get("card_name", {}).get("schinese", "单位")

func _grid() -> Rect2:
	var columns := int(state.get("columns", 5))
	var tile := floorf(minf((size.x - 44) / (columns * 1.42), (size.y - 12) / 8.0))
	tile = maxf(tile, 12.0)
	var extent := Vector2(columns * tile * 1.42, 8 * tile)
	return Rect2((size - extent) * 0.5, extent)

func _pitch(board: Rect2) -> Vector2:
	return board.size / Vector2(int(state.get("columns", 5)), 8)

func _cell(pos: Vector2i) -> Rect2:
	var board := _grid()
	var pitch := _pitch(board)
	return Rect2(board.position + Vector2(pos) * pitch + Vector2.ONE * TILE_GAP / 2,
		pitch - Vector2.ONE * TILE_GAP)

func _coordinates(record: Dictionary) -> Vector2i:
	return Vector2i(int(record.col), int(record.row))

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT]:
		var field := _grid()
		if field.has_point(event.position):
			var pos := Vector2i((event.position - field.position) / _pitch(field))
			cell_clicked.emit(pos, event.button_index == MOUSE_BUTTON_RIGHT)
			accept_event()

func _get_tooltip(at_position: Vector2) -> String:
	var field := _grid()
	if not field.has_point(at_position):
		return ""
	var pos := Vector2i((at_position - field.position) / _pitch(field))
	for fort: Dictionary in state.get("forts", []):
		if _coordinates(fort) == pos:
			return "每次交战攻击范围内一名敌军 · 射程 %d" % int(fort.get("reach", 2))
	for unit: Dictionary in state.get("units", []):
		if _coordinates(unit) == pos:
			return unit_name(unit)
	return ""

func animate(old: Dictionary, next: Dictionary, stage: String, duration: float) -> void:
	_from = _unit_map(old)
	_after = _unit_map(next)
	_stage = stage
	_shots = old.get("fortShots", [])
	_progress = 0.0
	present(old if stage == "combat" else next)
	var tween := create_tween()
	tween.tween_method(_seek, 0.0, 1.0, duration)
	await tween.finished
	_stage = ""
	present(next)

func _seek(progress: float) -> void:
	if sound_enabled and _stage == "combat" and _progress < 0.48 and progress >= 0.48:
		if not _shots.is_empty() or _from.values().any(
			func(unit: Dictionary) -> bool: return unit.get("canAttack", false)):
			_impact_audio.play()
	_progress = progress
	queue_redraw()

func _impact_sample() -> AudioStreamWAV:
	var sound := AudioStreamWAV.new()
	sound.format = AudioStreamWAV.FORMAT_16_BITS
	sound.mix_rate = 22050
	var data := PackedByteArray()
	var samples := int(sound.mix_rate * 0.15)
	data.resize(samples * 2)
	var random := RandomNumberGenerator.new()
	random.seed = 103
	for i in range(samples):
		var t := float(i) / sound.mix_rate
		var body := sin(TAU * (139.0 * t - 220.0 * t * t)) * exp(-33.0 * t)
		var contact := random.randf_range(-1, 1) * exp(-115.0 * t)
		var envelope := minf(1.0, t / 0.002)
		data.encode_s16(i * 2, int((body * 0.48 + contact * 0.24) * envelope * 32767.0))
	sound.data = data
	return sound

func _unit_map(frame: Dictionary) -> Dictionary:
	var result := {}
	for unit: Dictionary in frame.get("units", []):
		result[unit.key] = unit
	return result

func _target_points(units: Dictionary) -> Dictionary:
	var points := {}
	for key: String in units:
		points[key] = _cell(_coordinates(units[key])).get_center()
	for fort: Dictionary in state.get("forts", []):
		points["AF" if int(fort.team) == 0 else "BF"] = _cell(_coordinates(fort)).get_center()
	return points

func _draw() -> void:
	var grid := _grid()
	var font := details_font if details_font else ThemeDB.fallback_font
	var felt := grid.grow(15)
	draw_rect(felt, Color("#303532"))
	draw_rect(felt.grow(-2), Color("#232a28"))
	draw_rect(felt, Color("#7d6d55"), false, 1.0)
	draw_rect(felt.grow(-5), Color("#7d6d5544"), false, 1.0)
	var middle := grid.get_center().y
	draw_line(Vector2(grid.position.x, middle), Vector2(grid.end.x, middle), Color("#c29c655f"), 1.0, true)
	for row in range(8):
		for col in range(int(state.get("columns", 5))):
			var pos := Vector2i(col, row)
			var rect := _cell(pos)
			var tile := Color("#333c39") if (row + col) % 2 == 0 else Color("#303936")
			if row == 0 or row == 7:
				tile = Color("#423833") if row == 0 else Color("#29433f")
			draw_rect(rect, tile)
			var outline := Color("#b5a17933") if row in [0,7] else Color("#b8b09928")
			draw_rect(rect, outline, false, 1.0)
			if pos in markers:
				draw_rect(rect, Color("#7ec0b044"))
				draw_rect(rect.grow(-1), Color("#99d8c8"), false, 2.0)
		var center := _cell(Vector2i(0, row)).get_center()
		draw_string(font, Vector2(grid.position.x - 17, center.y + 5), str(row + 1),
			HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#b6b7a589"))

	var units := _unit_map(state)
	var targets := _target_points(units)
	for fort: Dictionary in state.get("forts", []):
		_draw_fort(fort, font)
	for key: String in units:
		_draw_unit(units[key], targets, font)
	if show_arrows and _stage != "combat":
		for key: String in units:
			var unit: Dictionary = units[key]
			var target: Variant = unit.get("target")
			if target != null and targets.has(target) and not unit.get("stunned", false):
				_draw_arrow(targets[key], targets[target], GREEN if unit.team == "ally" else RED,
					bool(unit.get("canAttack", true)))
	if _stage == "combat":
		_draw_impacts(units, targets, font)

func _draw_fort(fort: Dictionary, font: Font) -> void:
	var rect := _cell(_coordinates(fort))
	var tint := GREEN if int(fort.team) == 0 else RED
	var center := rect.get_center()
	var radius := rect.size.y * 0.35
	var core := center - Vector2(0, rect.size.y * 0.10)
	draw_circle(core + Vector2(0, 4), radius + 2, Color("#000000a6"), true, -1, true)
	draw_circle(core, radius, Color("#252323"), true, -1, true)
	draw_arc(core, radius, 0.0, TAU, 36, GOLD.darkened(0.20), 1.6, true)
	draw_arc(core, radius * 0.77, 0.2, TAU - 0.2, 30, Color(tint, 0.72), 1.7, true)
	var shard := PackedVector2Array([core + Vector2(0, -radius * 0.66), core + Vector2(radius * 0.43, 0),
		core + Vector2(0, radius * 0.62), core - Vector2(radius * 0.43, 0)])
	draw_colored_polygon(shard, tint.darkened(0.26))
	draw_line(shard[0], shard[2], tint.lightened(0.18), 1.4, true)
	var hp := "%d / %d" % [int(fort.hp), int(fort.maxHp)]
	draw_rect(Rect2(Vector2(center.x - 25, rect.end.y - 19), Vector2(50, 18)), Color("#1a1614ed"))
	_center_text(font, hp, Vector2(center.x, rect.end.y - 5), 13, PAPER)

func _draw_unit(unit: Dictionary, points: Dictionary, font: Font) -> void:
	var rect := _cell(_coordinates(unit))
	rect = _piece_rect(rect)
	var target: Variant = unit.get("target")
	var reveal := _stage == "combat" and _progress >= 0.50
	var opacity := 1.0
	if _stage == "move" and _from.has(unit.key):
		var old := _piece_rect(_cell(_coordinates(_from[unit.key]))).position
		rect.position = old.lerp(rect.position, smoothstep(0.0, 1.0, _progress))
	if _stage == "combat" and target != null and points.has(target) and unit.get("canAttack") and float(unit.range) <= 1:
		var direction: Vector2 = (points[target] - rect.get_center()).normalized()
		var lunge := sin(PI * clampf(_progress / 0.82, 0.0, 1.0))
		rect.position += direction * rect.size.x * 0.27 * lunge
	if reveal and not _after.has(unit.key):
		opacity = 1.0 - smoothstep(0.56, 0.97, _progress)
	var tint := (GREEN if unit.team == "ally" else RED)
	var frame_alpha := Color(tint, opacity)
	var frame := StyleBoxFlat.new()
	frame.bg_color = Color("#1d211f", opacity)
	frame.border_color = Color(tint.darkened(0.22), opacity)
	frame.set_corner_radius_all(3)
	frame.set_border_width_all(1)
	frame.shadow_color = Color(0.0, 0.0, 0.0, 0.60 * opacity)
	frame.shadow_size = 3
	frame.shadow_offset = Vector2(2, 3)
	draw_style_box(frame, rect)
	var picture := artwork_for(int(unit.id), unit.team)
	if picture:
		var portrait := Rect2(rect.position + Vector2(2, 15), rect.size - Vector2(4, 34))
		var image_size := picture.get_size()
		var visible_height := image_size.x * (portrait.size.y / maxf(1.0, portrait.size.x))
		var visible_width := image_size.y * (portrait.size.x / maxf(1.0, portrait.size.y))
		var crop := image_size.min(Vector2(visible_width, visible_height))
		var source := Rect2((image_size - crop) * Vector2(0.5, 0.43), crop)
		var fade := Color(1.0, 1.0, 1.0, opacity)
		if unit.get("stunned", false):
			fade = Color(0.62, 0.68, 0.80, opacity)
		draw_texture_rect_region(picture, portrait, source, fade)
	draw_rect(Rect2(rect.position + Vector2(1, 1), Vector2(rect.size.x - 2, 13)), Color(tint.darkened(0.72), opacity))
	var title := unit_name(unit, true)
	var title_width := font.get_string_size(title, HORIZONTAL_ALIGNMENT_LEFT, -1, 11).x
	var title_size := int(clampf(11.0 * (rect.size.x - 4) / maxf(1.0, title_width), 8.0, 11.0))
	_center_text(font, title, Vector2(rect.get_center().x, rect.position.y + 11), title_size, Color(PAPER, opacity))
	var outline := GOLD if selected == unit.key else frame_alpha
	if unit.hero or selected == unit.key:
		draw_rect(rect.grow(-1), outline, false, 1.4)
	var hp := int(unit.hp)
	if reveal:
		hp = int(_after.get(unit.key, {"hp": 0}).hp)
	var prediction: Variant = state.get("forecast")
	var forecast: Dictionary = prediction.get("units", {}).get(unit.key, {}) if prediction is Dictionary else {}
	_draw_stats(rect, [int(unit.attack), int(unit.get("armor", 0)), hp], font, opacity)
	if _stage == "" and not forecast.is_empty() and int(forecast.hp) != hp:
		var loss := hp - int(forecast.hp)
		var badge := Rect2(rect.end - Vector2(24, 34), Vector2(23, 13))
		draw_rect(badge, Color("#46332ef5") if loss > 0 else Color("#294b3ff5"))
		var change := "−%d" % loss if loss > 0 else "+%d" % -loss
		_center_text(font, change, Vector2(badge.get_center().x, badge.end.y - 3), 10, PAPER)
	if unit.hero:
		draw_rect(Rect2(rect.position + Vector2(2, 15), Vector2(23, 13)), Color("#172326db"))
		draw_string(font, rect.position + Vector2(4, 25), "Lv%d" % int(unit.get("level", 1)),
			HORIZONTAL_ALIGNMENT_LEFT, -1, 9, frame_alpha)

func _draw_stats(rect: Rect2, values: Array, font: Font, opacity: float) -> void:
	var col_width := (rect.size.x - 2) / 3
	var labels := ["攻", "甲", "血"]
	var tints := [Color("#e0bb7e"), Color("#b3cbd1"), Color("#efa49b")]
	for i in range(3):
		var cell := Rect2(Vector2(rect.position.x + 1 + i * col_width, rect.end.y - 18), Vector2(col_width, 17))
		draw_rect(cell, Color("#292b26", opacity))
		draw_rect(cell, Color("#88755e", opacity * 0.47), false, 1)
		_center_text(font, "%s%d" % [labels[i], values[i]], Vector2(cell.get_center().x, cell.end.y - 4),
			10, Color(tints[i], opacity))

func _piece_rect(rect: Rect2) -> Rect2:
	var width := minf(rect.size.x - 4, rect.size.y * 0.92)
	return Rect2(Vector2(rect.get_center().x - width / 2, rect.position.y), Vector2(width, rect.size.y))

func _center_text(font: Font, text: String, point: Vector2, font_size: int, color: Color) -> void:
	var width := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	draw_string(font, point - Vector2(width / 2, 0), text,
		HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, color)

func _draw_arrow(origin: Vector2, aim: Vector2, tint: Color, in_range: bool) -> void:
	var direction := (aim - origin).normalized()
	var side := direction.orthogonal()
	var half := _piece_rect(_cell(Vector2i.ZERO)).size * 0.5
	var ray_box := maxf(absf(direction.x) / half.x, absf(direction.y) / half.y)
	var inset := 1.0 / maxf(0.001, ray_box)
	var start := origin + direction * inset + side * 5.0
	var end := aim - direction * inset + side * 5.0
	var color := Color(tint, 0.72 if in_range else 0.38)
	if (end - start).dot(direction) < 9.0:
		var point := origin.lerp(aim, 0.5) + side * 7.0
		draw_colored_polygon(PackedVector2Array([point + direction * 3,
			point - direction * 3 + side * 4, point - direction * 3 - side * 4]), color)
		return
	if in_range:
		draw_line(start, end, color, 2, true)
	else:
		draw_dashed_line(start, end, color, 2, 5.0, true, true)
	draw_colored_polygon(PackedVector2Array([end, end - direction * 7 + side * 4, end - direction * 7 - side * 4]), color)

func _draw_impacts(units: Dictionary, points: Dictionary, font: Font) -> void:
	for unit: Dictionary in units.values():
		var target: Variant = unit.get("target")
		if target == null or not points.has(target) or not unit.get("canAttack", true):
			continue
		var start: Vector2 = points[unit.key]
		var end: Vector2 = points[target]
		var tint := GREEN if unit.team == "ally" else RED
		if int(unit.range) > 1 and _progress < 0.5:
			var flight := clampf(_progress * 2, 0.0, 1.0)
			draw_line(start.lerp(end, maxf(0.0, flight - 0.20)), start.lerp(end, flight), tint, 3, true)
			draw_circle(start.lerp(end, flight), 4, PAPER)
		if _progress >= 0.45 and _progress <= 0.72:
			var hit := (_progress - 0.45) / 0.27
			var at := end if int(unit.range) > 1 else start.lerp(end, 0.5)
			_shock(at, hit, tint, 18)
	for shot: Dictionary in _shots:
		if not points.has(shot.target):
			continue
		var start: Vector2 = points["AF" if int(shot.team) == 0 else "BF"]
		var end: Vector2 = points[shot.target]
		if _progress < 0.18:
			draw_circle(start, 8.0 + _progress * 32, Color(GOLD, 0.8))
		elif _progress < 0.50:
			var flight := (_progress - 0.18) / 0.32
			var point := start.lerp(end, flight) - Vector2(0, sin(PI * flight) * 39)
			draw_line(start, point, Color(GOLD, 0.48), 3, true)
			draw_circle(point, 6, PAPER)
		else:
			var hit := (_progress - 0.50) * 2.0
			_shock(end, hit, GOLD, 26)
			var text := "免疫" if shot.get("immune", false) else "格挡" if int(shot.damage) == 0 else "−%d" % int(shot.damage)
			_center_text(font, text, end - Vector2(0, 19 + 21 * hit), 17, Color(PAPER, 1.0 - hit * 0.75))

func _shock(at: Vector2, time: float, tint: Color, radius: float) -> void:
	var fade := Color(tint, 1.0 - time)
	draw_arc(at, 5.0 + time * radius, 0, TAU, 24, fade, 2, true)
	for n in range(6):
		var ray := Vector2.from_angle(TAU * n / 6.0 + 0.3)
		draw_line(at + ray * (5 + time * radius), at + ray * (9 + time * radius), fade, 2, true)
