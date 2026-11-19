extends Control

signal cell_clicked(pos: Vector2i, secondary: bool)

const INK := Color("#172326")
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

func _grid() -> Rect2:
	var columns := int(state.get("columns", 5))
	var tile := floorf(minf((size.x - 44) / columns, (size.y - 44) / 8.0))
	tile = maxf(tile, 12.0)
	var extent := Vector2(columns * tile, 8 * tile)
	return Rect2((size - extent) * 0.5, extent)

func _cell(pos: Vector2i) -> Rect2:
	var board := _grid()
	var side := board.size.y / 8.0
	return Rect2(board.position + Vector2(pos) * side + Vector2.ONE * TILE_GAP / 2,
		Vector2.ONE * (side - TILE_GAP))

func _coordinates(record: Dictionary) -> Vector2i:
	return Vector2i(int(record.col), int(record.row))

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT]:
		var field := _grid()
		if field.has_point(event.position):
			var pos := Vector2i((event.position - field.position) / (field.size.y / 8.0))
			cell_clicked.emit(pos, event.button_index == MOUSE_BUTTON_RIGHT)
			accept_event()

func _get_tooltip(at_position: Vector2) -> String:
	var field := _grid()
	if not field.has_point(at_position):
		return ""
	var pos := Vector2i((at_position - field.position) / (field.size.y / 8.0))
	for fort: Dictionary in state.get("forts", []):
		if _coordinates(fort) == pos:
			return "每次交战攻击范围内一名敌军 · 射程 %d" % int(fort.get("reach", 2))
	for unit: Dictionary in state.get("units", []):
		if _coordinates(unit) == pos:
			var name_data: Dictionary = catalog.get(int(unit.id), {}).get("card_name", {})
			return name_data.get("schinese", "小兵")
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
	draw_style_box(_board_border(), grid.grow(14))
	var font := details_font if details_font else ThemeDB.fallback_font
	for row in range(8):
		for col in range(int(state.get("columns", 5))):
			var pos := Vector2i(col, row)
			var rect := _cell(pos)
			var tile := Color("#243233") if (row + col) % 2 == 0 else Color("#202e30")
			if row == 0 or row == 7:
				tile = tile.lerp(RED if row == 0 else GREEN, 0.15)
			draw_rect(rect, tile)
			if pos in markers:
				draw_rect(rect, Color("#7ec0b044"))
				draw_rect(rect.grow(-1), Color("#99d8c8"), false, 2.0)
		var center := _cell(Vector2i(0, row)).get_center()
		draw_string(font, Vector2(grid.position.x - 17, center.y + 5), str(row + 1),
			HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color("#97aaa6"))

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

func _board_border() -> StyleBoxFlat:
	var border := StyleBoxFlat.new()
	border.bg_color = Color("#172123")
	border.border_color = Color("#40524f")
	border.set_border_width_all(1)
	border.set_corner_radius_all(7)
	return border

func _draw_fort(fort: Dictionary, font: Font) -> void:
	var rect := _cell(_coordinates(fort))
	var tint := GREEN if int(fort.team) == 0 else RED
	draw_rect(rect, Color("#182426"))
	draw_rect(rect, tint.darkened(0.4), false, 1.5)
	var center := rect.get_center()
	var radius := rect.size.x * 0.24
	var shape := PackedVector2Array([center + Vector2(-radius, radius / 3),
		center + Vector2(-radius, -radius), center + Vector2(-radius / 3, -radius),
		center + Vector2(-radius / 3, -radius / 2), center + Vector2(radius / 3, -radius / 2),
		center + Vector2(radius / 3, -radius), center + Vector2(radius, -radius), center + Vector2(radius, radius / 3)])
	draw_colored_polygon(shape, tint.darkened(0.25))
	var hp := "%d / %d" % [int(fort.hp), int(fort.maxHp)]
	_center_text(font, hp, Vector2(center.x, rect.end.y - 6), 13, PAPER)

func _draw_unit(unit: Dictionary, points: Dictionary, font: Font) -> void:
	var rect := _cell(_coordinates(unit))
	var target: Variant = unit.get("target")
	var reveal := _stage == "combat" and _progress >= 0.50
	var opacity := 1.0
	if _stage == "move" and _from.has(unit.key):
		var old := _cell(_coordinates(_from[unit.key])).position
		rect.position = old.lerp(rect.position, smoothstep(0.0, 1.0, _progress))
	if _stage == "combat" and target != null and points.has(target) and unit.get("canAttack") and float(unit.range) <= 1:
		var direction: Vector2 = (points[target] - rect.get_center()).normalized()
		var lunge := sin(PI * clampf(_progress / 0.82, 0.0, 1.0))
		rect.position += direction * rect.size.x * 0.27 * lunge
	if reveal and not _after.has(unit.key):
		opacity = 1.0 - smoothstep(0.56, 0.97, _progress)
	var tint := (GREEN if unit.team == "ally" else RED)
	var frame_alpha := Color(tint, opacity)
	draw_rect(rect, Color(INK, opacity))
	var picture := texture_for(int(unit.id), unit.team)
	if picture:
		var portrait := rect.grow(-2)
		portrait.size.y -= 17
		var image_size := picture.get_size()
		var visible_height := image_size.x * (portrait.size.y / maxf(1.0, portrait.size.x))
		var visible_width := image_size.y * (portrait.size.x / maxf(1.0, portrait.size.y))
		var crop := image_size.min(Vector2(visible_width, visible_height))
		var source := Rect2((image_size - crop) * Vector2(0.5, 0.35), crop)
		var fade := Color(1.0, 1.0, 1.0, opacity)
		if unit.get("stunned", false):
			fade = Color(0.62, 0.68, 0.80, opacity)
		draw_texture_rect_region(picture, portrait, source, fade)
	var outline := GOLD if selected == unit.key else frame_alpha
	draw_rect(rect, outline, false, 2.4 if unit.hero or selected == unit.key else 1.2)
	var hp := int(unit.hp)
	if reveal:
		hp = int(_after.get(unit.key, {"hp": 0}).hp)
	var prediction: Variant = state.get("forecast")
	var forecast: Dictionary = prediction.get("units", {}).get(unit.key, {}) if prediction is Dictionary else {}
	var predicted := ""
	if _stage == "" and not forecast.is_empty() and int(forecast.hp) != hp:
		predicted = " →%d" % int(forecast.hp)
	var caption := "%d  /  %d%s" % [int(unit.attack), hp, predicted]
	_center_text(font, caption, Vector2(rect.get_center().x, rect.end.y - 4), 12, Color(PAPER, opacity))
	if unit.hero:
		draw_rect(Rect2(rect.position + Vector2(2, 2), Vector2(25, 16)), Color("#172326db"))
		draw_string(font, rect.position + Vector2(4, 14), "Lv%d" % int(unit.get("level", 1)),
			HORIZONTAL_ALIGNMENT_LEFT, -1, 11, frame_alpha)

func _center_text(font: Font, text: String, point: Vector2, font_size: int, color: Color) -> void:
	var width := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	draw_string(font, point - Vector2(width / 2, 0), text,
		HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, color)

func _draw_arrow(origin: Vector2, aim: Vector2, tint: Color, in_range: bool) -> void:
	var direction := (aim - origin).normalized()
	var side := direction.orthogonal()
	var start := origin + direction * 12.0 + side * 4.0
	var end := aim - direction * 16.0 + side * 4.0
	var color := Color(tint, 0.72 if in_range else 0.38)
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
