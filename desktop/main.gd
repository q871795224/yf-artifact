extends Control

const Battlefield = preload("res://battlefield.gd")
const LocalAPI = preload("res://local_api.gd")
const HandCard = preload("res://hand_card.gd")
const CONFIG := "user://desktop.cfg"
const ALL_TARGETS := ["all", "self", "draw", "fort", "ticket", "improvement"]
const MANA := Color("#9ed1ea")
const PAPER := Color("#ede3cd")
const MUTED := Color("#a5b5b1")
const GOLD := Color("#d1b079")
const GREEN := Color("#9dd1ac")
const RED := Color("#e5a38d")

var api: LocalAPI
var board: Battlefield
var font: SystemFont
var config := ConfigFile.new()
var state: Dictionary = {}
var catalog: Dictionary = {}
var cards: Dictionary = {}
var game_id := ""
var busy := false
var playback_speed := 1.0
var item_tab := false
var inspected: Dictionary = {}
var selected := ""
var mode := ""
var choices: Array = []
var deck_edit: Dictionary = {}
var deck_rows: Dictionary = {}
var archive_dir := ""

var round_label: Label
var resource_label: Label
var opponent_label: Label
var phase_label: Label
var reserve_label: Label
var notice: Label
var details: VBoxContainer
var log_text: RichTextLabel
var history_layer: PanelContainer
var detail_layer: PanelContainer
var hand: HBoxContainer
var hand_tabs: HBoxContainer
var pass_button: Button
var tactic_button: Button
var cancel_button: Button
var deck_button: Button
var concede_button: Button
var new_button: Button
var export_button: Button
var deck_window: Window
var deck_summary: Label
var deck_save: Button
var export_dialog: FileDialog
var pending_export: Dictionary = {}
var confirmation: ConfirmationDialog
var preview_window: Window
var sample_board: Battlefield
var sample_play: Button
var sample_speed: OptionButton

func _ready() -> void:
	get_window().min_size = Vector2i(1040, 710)
	config.load(CONFIG)
	font = SystemFont.new()
	font.font_names = ["Microsoft YaHei UI", "PingFang SC", "Noto Sans CJK SC", "WenQuanYi Micro Hei", "sans-serif"]
	font.allow_system_fallback = true
	theme = _make_theme()
	api = LocalAPI.new()
	var server := OS.get_environment("ARTIFACT_SERVER").strip_edges()
	if not server.is_empty():
		api.address = server.trim_suffix("/")
	add_child(api)
	var assets := OS.get_environment("ARTIFACT_ROOT")
	if assets.is_empty():
		assets = ProjectSettings.globalize_path("res://../").simplify_path()
	archive_dir = OS.get_environment("ARTIFACT_ARCHIVE")
	if archive_dir.is_empty():
		archive_dir = assets.path_join("output/playtests")
	_build(assets)
	await _connect_game()

func _make_theme() -> Theme:
	var skin := Theme.new()
	skin.default_font = font
	skin.default_font_size = 15
	skin.set_color("font_color", "Label", PAPER)
	skin.set_color("default_color", "RichTextLabel", MUTED)
	skin.set_color("font_color", "Button", PAPER)
	skin.set_color("font_disabled_color", "Button", Color("#7d8986"))
	skin.set_stylebox("normal", "Button", _surface("#201d18f2", "#6d5c43", 6, 8))
	skin.set_stylebox("hover", "Button", _surface("#3b3022", "#b8986a", 6, 8))
	skin.set_stylebox("pressed", "Button", _surface("#4d3a24", "#ccaa77", 6, 8))
	skin.set_stylebox("disabled", "Button", _surface("#222d2f", "#36413f", 5, 8))
	skin.set_stylebox("focus", "Button", _surface("#00000000", "#a4c6ac", 5, 8))
	return skin

func _surface(bg: String, border: String, corner: int, padding: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(bg)
	style.border_color = Color(border)
	style.set_corner_radius_all(corner)
	style.set_border_width_all(1)
	for side: int in [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]:
		style.set_content_margin(side, padding)
	return style

func _label(text: String, points := 15, tint := PAPER) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", points)
	label.add_theme_color_override("font_color", tint)
	return label

func _button(parent: Node, title: String, callback: Callable) -> Button:
	var button := Button.new()
	button.text = title
	button.pressed.connect(callback)
	parent.add_child(button)
	return button

func _panel(parent: Node, expand := true) -> VBoxContainer:
	var panel := PanelContainer.new()
	if expand:
		panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.add_theme_stylebox_override("panel", _surface("#1e2a2c", "#3a4a47", 7, 12))
	parent.add_child(panel)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 8)
	panel.add_child(column)
	return column

func _spacer(parent: Node) -> void:
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	parent.add_child(spacer)

func _build(assets: String) -> void:
	var backdrop := ColorRect.new()
	backdrop.color = Color("#181d20")
	backdrop.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(backdrop)
	backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

	var margins := MarginContainer.new()
	add_child(margins)
	margins.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side: String in ["left", "right", "top", "bottom"]:
		margins.add_theme_constant_override("margin_" + side, 16)
	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 5)
	margins.add_child(root)
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 7)
	root.add_child(header)
	header.add_child(_label("单路战场", 24, GOLD))
	round_label = _label("连接战场", 15, MUTED)
	header.add_child(round_label)
	_spacer(header)
	var roster := _button(header, "阵容", _show_roster)
	roster.tooltip_text = "查英雄成长和返场回合"
	var report := CheckButton.new()
	report.text = "战报"
	report.toggled.connect(func(value: bool) -> void: history_layer.visible = value)
	header.add_child(report)
	deck_button = _button(header, "构筑", _open_deck)
	_button(header, "特效", _open_preview)
	export_button = _button(header, "导出", _open_export)
	_button(header, "记录文件", _open_archive)
	concede_button = _button(header, "认输", _ask_concede)
	new_button = _button(header, "新一局", _ask_new)

	var enemy_bar := HBoxContainer.new()
	enemy_bar.alignment = BoxContainer.ALIGNMENT_CENTER
	root.add_child(enemy_bar)
	opponent_label = _label("", 15, RED)
	enemy_bar.add_child(opponent_label)

	var board_area := Control.new()
	board_area.size_flags_vertical = Control.SIZE_EXPAND_FILL
	board_area.custom_minimum_size.y = 424
	root.add_child(board_area)
	board = Battlefield.new()
	board.assets_root = assets
	board.details_font = font
	board.cell_clicked.connect(_cell_clicked)
	board_area.add_child(board)
	board.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

	var history := _panel(board_area)
	history_layer = history.get_parent()
	_side_layer(history_layer, false)
	history_layer.hide()
	history.add_child(_label("交战记录", 18, GOLD))
	log_text = RichTextLabel.new()
	log_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	log_text.scroll_following = true
	log_text.selection_enabled = true
	history.add_child(log_text)

	var side := _panel(board_area)
	detail_layer = side.get_parent()
	_side_layer(detail_layer, true)
	side.add_child(_label("详情", 16, GOLD))
	var detail_scroll := ScrollContainer.new()
	detail_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	detail_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	detail_scroll.custom_minimum_size.y = 140
	side.add_child(detail_scroll)
	details = VBoxContainer.new()
	details.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	details.add_theme_constant_override("separation", 6)
	detail_scroll.add_child(details)
	reserve_label = _label("", 13, MUTED)
	reserve_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	side.add_child(reserve_label)

	var turn_bar := HBoxContainer.new()
	turn_bar.add_theme_constant_override("separation", 10)
	root.add_child(turn_bar)
	resource_label = _label("等待对局", 16, MANA)
	turn_bar.add_child(resource_label)
	phase_label = _label("", 14, PAPER)
	phase_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	phase_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	phase_label.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	turn_bar.add_child(phase_label)
	cancel_button = _button(turn_bar, "取消", _cancel_target)
	tactic_button = _button(turn_bar, "调位", _start_tactic)
	pass_button = _button(turn_bar, "让过", _advance)
	pass_button.custom_minimum_size.x = 98
	pass_button.add_theme_stylebox_override("normal", _surface("#513a24", "#cba363", 7, 9))
	pass_button.add_theme_stylebox_override("hover", _surface("#755433", "#f0ce90", 7, 9))

	hand_tabs = HBoxContainer.new()
	root.add_child(hand_tabs)
	_button(hand_tabs, "普通牌", func() -> void: _hand_tab(false))
	_button(hand_tabs, "物品", func() -> void: _hand_tab(true))
	var arrows := CheckButton.new()
	arrows.text = "攻击箭头"
	arrows.button_pressed = true
	arrows.toggled.connect(func(value: bool) -> void:
		board.show_arrows = value
		board.queue_redraw())
	hand_tabs.add_child(arrows)
	var speed := OptionButton.new()
	for text: String in ["常速", "两倍速", "跳过动画"]:
		speed.add_item(text)
	speed.item_selected.connect(func(index: int) -> void:
		playback_speed = [1.0, 2.0, 0.0][index])
	hand_tabs.add_child(speed)
	_spacer(hand_tabs)
	notice = _label("", 13, MUTED)
	notice.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	hand_tabs.add_child(notice)
	var hand_scroll := ScrollContainer.new()
	hand_scroll.custom_minimum_size.y = 135
	hand_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	root.add_child(hand_scroll)
	hand = HBoxContainer.new()
	hand.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hand.alignment = BoxContainer.ALIGNMENT_CENTER
	hand.add_theme_constant_override("separation", 5)
	hand_scroll.add_child(hand)

	confirmation = ConfirmationDialog.new()
	add_child(confirmation)
	export_dialog = FileDialog.new()
	export_dialog.title = "导出对局"
	export_dialog.access = FileDialog.ACCESS_FILESYSTEM
	export_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE
	export_dialog.add_filter("*.json", "对局记录")
	export_dialog.file_selected.connect(_write_export)
	add_child(export_dialog)
	_render()

func _side_layer(panel: PanelContainer, right: bool) -> void:
	var edge := 1.0 if right else 0.0
	panel.anchor_left = edge
	panel.anchor_right = edge
	panel.anchor_top = 0.06
	panel.anchor_bottom = 0.94
	panel.offset_left = -288 if right else 0
	panel.offset_right = 0 if right else 246
	panel.add_theme_stylebox_override("panel", _surface("#171917f5", "#79664e", 10, 13))

func _connect_game() -> void:
	_set_busy(true)
	var package := await api.request("/api/catalog")
	if package.has("error"):
		_set_busy(false)
		_message(package.error)
		return
	catalog = package
	for card: Dictionary in catalog.cards:
		cards[int(card.card_id)] = card
	cards[1006] = {"card_name": {"schinese": "近战小兵"}, "card_text": {"schinese": "自动向前移动，正交一格攻击。"}}
	board.catalog = cards
	var last: String = config.get_value("match", api.address, "")
	if last.is_empty():
		await _new_game()
	else:
		var packet := await api.request("/api/games/" + last)
		_set_busy(false)
		if packet.has("error"):
			_message(packet.error)
			return
		_accept(packet)

func _new_game() -> void:
	_set_busy(true)
	var payload := {"source": "desktop"}
	if config.has_section_key("deck", "current"):
		payload["deck_config"] = _integer_deck(config.get_value("deck", "current"))
	var requested_seed := OS.get_environment("ARTIFACT_SEED").to_int()
	if requested_seed > 0:
		payload["seed"] = requested_seed
	var packet := await api.request("/api/games", payload)
	_set_busy(false)
	if packet.has("error"):
		_message(packet.error)
		return
	item_tab = false
	_reset_selection()
	_accept(packet)
	_message("对局已保存到电脑")

func _accept(packet: Dictionary) -> void:
	game_id = packet.game_id
	state = packet.state
	if config.get_value("match", api.address, "") != game_id:
		config.set_value("match", api.address, game_id)
		config.save(CONFIG)
	_render()

func _set_busy(value: bool) -> void:
	busy = value
	_render_controls()

func _render() -> void:
	board.present(state)
	_update_markers()
	_render_controls()
	_render_hand()
	_render_detail()
	if state.is_empty():
		return
	var summary: Array[String] = []
	for unit: Dictionary in state.heroes:
		if unit.row == null:
			summary.append("%s %s · R%d" % ["我方" if unit.team == "ally" else "敌方", _unit_name(unit), int(unit.due)])
	reserve_label.text = "返场  " + "   ".join(summary) if not summary.is_empty() else ""
	reserve_label.visible = not summary.is_empty()
	var lines: Array[String] = []
	for item: Dictionary in state.log:
		lines.append("%02d  %s" % [int(item.round), item.text])
	log_text.text = "\n".join(lines)
	if state.phase == "finished":
		_message("平局" if state.winner == null else "胜利" if int(state.winner) == 0 else "失利")

func _render_controls() -> void:
	var initialized := not state.is_empty()
	new_button.disabled = busy
	deck_button.disabled = busy or catalog.is_empty()
	concede_button.disabled = busy or not initialized or state.get("phase") == "finished"
	export_button.disabled = busy or not initialized
	var skill: Dictionary = state.get("globalSkill", {})
	tactic_button.text = "%s · %d 费" % [skill.get("name", "调位"), int(skill.get("cost", 2))]
	tactic_button.disabled = busy or _actions(skill.get("kind", "rally_swap")).is_empty()
	tactic_button.tooltip_text = "本回合已使用" if skill.get("used", false) else "移动一名友军到八邻空格，或与八邻友军交换"
	cancel_button.visible = not mode.is_empty()
	pass_button.disabled = busy or not initialized
	pass_button.text = "下一回合" if state.get("phase") == "round_end" else "查看结果" if state.get("phase") == "finished" else "让过"
	if not initialized:
		round_label.text = "正在连接" if busy else "等待开局"
		phase_label.text = ""
		return
	var opponent: Dictionary = state.get("opponent", {})
	round_label.text = "第 %d 回合" % int(state.round)
	resource_label.text = "%d / %d 法力    %d 金" % [int(state.mana), int(state.maxMana), int(state.gold)]
	opponent_label.text = "敌方    %d 法力    %d 金" % [int(opponent.get("mana", 0)), int(opponent.get("gold", 0))]
	if busy:
		phase_label.text = "正在结算"
	elif not mode.is_empty():
		phase_label.text = "选择高亮目标 · Esc 取消"
	else:
		phase_label.text = {"action": "你的行动", "round_end": "交战结束", "finished": "对局结束"}.get(state.phase, "")

func _message(value: String) -> void:
	notice.text = value
	notice.tooltip_text = value

func _clear(container: Node) -> void:
	for node in container.get_children():
		container.remove_child(node)
		node.queue_free()

func _card(id: int) -> Dictionary:
	return cards.get(id, {})

func _card_name(id: int) -> String:
	return _card(id).get("card_name", {}).get("schinese", "牌 %d" % id)

func _unit_name(unit: Dictionary) -> String:
	return board.unit_name(unit)

func _unit(key: String) -> Dictionary:
	for unit: Dictionary in state.get("units", []):
		if unit.key == key:
			return unit
	return {}

func _on_cell(pos: Vector2i) -> Dictionary:
	for unit: Dictionary in state.get("units", []):
		if int(unit.col) == pos.x and int(unit.row) == pos.y:
			return unit
	return {}

func _pos(record: Dictionary) -> Vector2i:
	return Vector2i(int(record.col), int(record.row))

func _actions(kind: String, actor := "") -> Array:
	if state.get("phase") != "action":
		return []
	return state.get("actions", []).filter(func(action: Dictionary) -> bool:
		return action.kind == kind and (actor.is_empty() or action.actor == actor))

func _render_hand() -> void:
	_clear(hand)
	var ordinary: Array = state.get("hand", [])
	var items: Array = state.get("items", [])
	for i in range(2):
		var button: Button = hand_tabs.get_child(i)
		button.text = "%s %d" % ["普通牌" if i == 0 else "物品", ordinary.size() if i == 0 else items.size()]
		button.disabled = item_tab == (i == 1)
	var pile := items if item_tab else ordinary
	for index in range(pile.size()):
		var id := int(pile[index].id if item_tab else pile[index])
		var cost := _cost(id, index, item_tab)
		var unit_card: Dictionary = _card(id)
		var tile := HandCard.new()
		tile.title_line = _card_name(id)
		tile.cost_line = "%d 金" % cost if item_tab else "%d 费" % cost
		tile.type_line = {"Spell": "法术", "Item": "物品", "Creep": "单位"}.get(unit_card.get("card_type"), "")
		if unit_card.get("card_type") == "Creep":
			tile.stat_line = "%d / %d" % [int(unit_card.attack), int(unit_card.hit_points)]
		tile.accent = GOLD if item_tab else GREEN
		tile.payable = not _actions("item" if item_tab else "card", str(index)).is_empty()
		tile.artwork = board.artwork_for(id)
		tile.text_font = font
		tile.active = inspected.get("type") == "card" and inspected.get("index") == index and inspected.get("item") == item_tab
		tile.tooltip_text = unit_card.get("card_text", {}).get("schinese", "")
		tile.pressed.connect(_inspect_card.bind(index, item_tab))
		hand.add_child(tile)
	if pile.is_empty():
		hand.add_child(_label("手牌为空", 14, MUTED))

func _cost(id: int, index: int, is_item: bool) -> int:
	if is_item:
		return 0 if state.items[index].paid else int(_card(id).get("gold_cost", 0))
	return int(state.get("cardCosts", {}).get(str(id), _card(id).get("mana_cost", 0)))

func _hand_tab(show_items: bool) -> void:
	item_tab = show_items
	_render_hand()

func _inspect_card(index: int, is_item: bool) -> void:
	if busy:
		return
	_reset_selection()
	inspected = {"type": "card", "item": is_item, "index": index}
	_update_markers()
	_render_controls()
	_render_detail()
	_render_hand()

func _detail_text(text: String, tint := MUTED) -> void:
	var line := _label(text, 14, tint)
	line.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	details.add_child(line)

func _detail_header(title: String, text: String, texture: Texture2D = null) -> void:
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 9)
	details.add_child(header)
	if texture:
		var portrait := TextureRect.new()
		portrait.texture = texture
		portrait.custom_minimum_size = Vector2(68, 68)
		portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		header.add_child(portrait)
	var left := VBoxContainer.new()
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(left)
	left.add_child(_label(title, 20, PAPER))
	var facts := _label(text, 14, MUTED)
	facts.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	left.add_child(facts)

func _detail_art(artwork: Texture2D) -> void:
	if artwork == null:
		return
	var picture := TextureRect.new()
	picture.texture = artwork
	picture.custom_minimum_size.y = 150
	picture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	picture.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	details.add_child(picture)

func _render_detail() -> void:
	_clear(details)
	detail_layer.visible = not inspected.is_empty()
	match inspected.get("type", ""):
		"unit":
			_detail_unit(_unit(selected))
		"card":
			_detail_card(int(inspected.index), bool(inspected.item))
		"fort":
			_detail_fort(int(inspected.team))
		"roster":
			for unit: Dictionary in state.heroes:
				var team := "我方" if unit.team == "ally" else "敌方"
				var location := "第 %d 轮登场" % int(unit.due) if unit.row == null else "第 %d 排第 %d 列" % [int(unit.row) + 1, int(unit.col) + 1]
				_detail_header(_unit_name(unit), "%s · Lv%d · %s" % [team, int(unit.level), location],
					board.artwork_for(int(unit.id), unit.team))
		_:
			pass

func _show_roster() -> void:
	if state.is_empty():
		return
	_reset_selection()
	inspected = {"type": "roster"}
	_update_markers()
	_render_controls()
	_render_detail()

func _detail_card(index: int, is_item: bool) -> void:
	var pile: Array = state.get("items" if is_item else "hand", [])
	if index >= pile.size():
		return
	var id := int(pile[index].id if is_item else pile[index])
	var card := _card(id)
	_detail_header(_card_name(id), "%d %s" % [_cost(id, index, is_item), "金币" if is_item else "法力"])
	_detail_art(board.artwork_for(id))
	_detail_text(card.get("card_text", {}).get("schinese", ""))
	var kind := "item" if is_item else "card"
	var row := HBoxContainer.new()
	details.add_child(row)
	var play := _button(row, "使用物品" if is_item else "出牌", _choose_hand.bind(kind, index))
	play.disabled = busy or _actions(kind, str(index)).is_empty()
	if not is_item:
		var reforge := _button(row, "重铸", _choose_hand.bind("reforge", index))
		reforge.disabled = busy or _actions("reforge", str(index)).is_empty()

func _detail_unit(unit: Dictionary) -> void:
	if unit.is_empty():
		return
	var team := "我方" if unit.team == "ally" else "敌方"
	_detail_header(_unit_name(unit), "%s · %d 攻  %d 甲  %d/%d 血\n射程 %d 格%s" % [
		team, int(unit.attack), int(unit.armor), int(unit.hp), int(unit.maxHp), int(unit.range),
		" · Lv%d · 经验 %d" % [int(unit.level), int(unit.xp)] if unit.hero else ""],
		board.artwork_for(int(unit.id), unit.team))
	var target: Variant = unit.get("target")
	if target != null:
		var enemy := _unit(str(target))
		var destination := _unit_name(enemy) if not enemy.is_empty() else "建筑"
		_detail_text("目标  %s%s" % [destination, "" if unit.get("canAttack", true) else " · 射程外"], GREEN)
	var unit_skills := {"chen": "劝化", "purify": "洗礼", "swap": "换位", "redirect": "引导箭头"}
	var key := str(unit.key)
	var kind: String = unit.get("skillKind") if unit.get("skillKind") != null else ""
	var actions_row := HBoxContainer.new()
	details.add_child(actions_row)
	if unit.team == "ally" and unit.hero:
		var move := _button(actions_row, "移动", _begin_choices.bind("move", _actions("move", key)))
		move.disabled = busy or _actions("move", key).is_empty()
	if unit.team == "ally" and unit_skills.has(kind):
		var skill_label: String = unit_skills[kind]
		if int(unit.cooldown) > 0:
			skill_label += " · %d" % int(unit.cooldown)
		var skill := _button(actions_row, skill_label, _choose_ability.bind(kind, key))
		skill.disabled = busy or _actions(kind, key).is_empty()
	for equipment: Dictionary in unit.equipment:
		var label := _card_name(int(equipment.id))
		if equipment.get("active") != null and unit.team == "ally":
			var ability := str(equipment.active)
			if int(equipment.get("cooldown", 0)) > 0:
				label += " · %d" % int(equipment.cooldown)
			var gear := _button(details, label, _choose_ability.bind(ability, key))
			gear.disabled = busy or _actions(ability, key).is_empty()
			gear.tooltip_text = _card(int(equipment.id)).get("card_text", {}).get("schinese", "")
		else:
			_detail_text(label)
	var card_text: String = _card(int(unit.id)).get("card_text", {}).get("schinese", "")
	if not card_text.is_empty():
		_detail_text(card_text)
	if unit.get("stunned", false):
		_detail_text("当前眩晕", RED)
	if unit.hero and unit.get("panels") is Array:
		var phases: Array[String] = []
		for panel in unit.panels:
			phases.append("%d/%d/%d" % [int(panel[0]), int(panel[1]), int(panel[2])])
		_detail_text("成长（攻/甲/血）  " + " → ".join(phases))

func _detail_fort(team: int) -> void:
	var fort: Dictionary = state.forts[team]
	_detail_header(("我方" if team == 0 else "敌方") + ("防御塔" if fort.stage == "tower" else "基地"),
		"%d/%d 血 · %d 攻" % [int(fort.hp), int(fort.maxHp), int(fort.attack)])
	_detail_text("第 %d 排 · 每次交战攻击周围 %d 格内一名敌军，含斜角。" % [int(fort.row) + 1, int(fort.get("reach", 2))])
	if not fort.ready:
		_detail_text("下回合激活", GOLD)

func _choose_hand(kind: String, index: int) -> void:
	_begin_choices(kind, _actions(kind, str(index)))

func _choose_ability(kind: String, key: String) -> void:
	_begin_choices(kind, _actions(kind, key))

func _start_tactic() -> void:
	var kind: String = state.globalSkill.kind
	selected = ""
	inspected = {}
	_begin_choices(kind, _actions(kind))

func _begin_choices(kind: String, available: Array) -> void:
	if busy or available.is_empty():
		return
	if available.size() == 1 and available[0].target in ALL_TARGETS:
		_submit(available[0].id)
		return
	mode = kind
	choices = available
	_update_markers()
	_render_controls()
	_render_detail()

func _matches_cell(action: Dictionary, pos: Vector2i, unit: Dictionary) -> bool:
	if action.get("firstTarget") != null:
		return not unit.is_empty() and unit.key == action.firstTarget
	if action.has("row"):
		return _pos(action) == pos
	return not unit.is_empty() and unit.key == action.target

func _update_markers() -> void:
	var marks: Array[Vector2i] = []
	if not mode.is_empty() and not state.is_empty():
		for row in range(int(state.rows)):
			for column in range(int(state.columns)):
				var pos := Vector2i(column, row)
				var unit := _on_cell(pos)
				if choices.any(func(action: Dictionary) -> bool: return _matches_cell(action, pos, unit)):
					marks.append(pos)
	board.highlight(marks, selected)

func _cell_clicked(pos: Vector2i, secondary: bool) -> void:
	if busy or state.is_empty():
		return
	if secondary and not mode.is_empty():
		_cancel_target()
		return
	var unit := _on_cell(pos)
	if not mode.is_empty():
		var matches := choices.filter(func(action: Dictionary) -> bool: return _matches_cell(action, pos, unit))
		if not matches.is_empty():
			if matches[0].get("firstTarget") != null:
				if mode == "rally_swap":
					selected = unit.key
					inspected = {"type": "unit"}
				choices = matches.map(func(action: Dictionary) -> Dictionary:
					var next := action.duplicate()
					next.erase("firstTarget")
					next.target = next.secondTarget
					return next)
				_update_markers()
				_render_detail()
				return
			_submit(matches[0].id)
			return
		if mode != "move":
			_message("请选择高亮目标，或按 Esc 取消")
			return
	_reset_selection()
	if not unit.is_empty():
		selected = unit.key
		inspected = {"type": "unit"}
		if not secondary and unit.team == "ally" and unit.hero and not _actions("move", selected).is_empty():
			_begin_choices("move", _actions("move", selected))
	else:
		for fort: Dictionary in state.forts:
			if _pos(fort) == pos:
				inspected = {"type": "fort", "team": fort.team}
	_update_markers()
	_render_controls()
	_render_detail()

func _input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel") and not mode.is_empty():
		_cancel_target()
		get_viewport().set_input_as_handled()

func _reset_selection() -> void:
	mode = ""
	choices = []
	selected = ""
	inspected = {}

func _cancel_target() -> void:
	mode = ""
	choices = []
	_update_markers()
	_render_controls()
	_render_detail()

func _advance() -> void:
	match state.get("phase", ""):
		"round_end": _submit("next_round")
		"action": _submit("pass")
		"finished":
			var outcome := AcceptDialog.new()
			outcome.title = "对局结果"
			outcome.dialog_text = "第 %d 回合结束 · %s" % [int(state.round),
				"平局" if state.winner == null else "胜利" if int(state.winner) == 0 else "失利"]
			add_child(outcome)
			outcome.close_requested.connect(outcome.queue_free)
			outcome.confirmed.connect(outcome.queue_free)
			outcome.popup_centered()

func _submit(action_id: String) -> void:
	if busy or game_id.is_empty():
		return
	_reset_selection()
	_update_markers()
	_set_busy(true)
	_render_detail()
	var packet := await api.request("/api/games/%s/actions" % game_id, {
		"version": int(state.version), "action_id": action_id})
	if packet.has("error"):
		_message(packet.error)
		var current := await api.request("/api/games/" + game_id)
		_set_busy(false)
		if not current.has("error"):
			_accept(current)
		return
	await _animate_packet(packet, action_id)
	_set_busy(false)
	_accept(packet)

func _animate_packet(packet: Dictionary, action_id: String) -> void:
	if playback_speed <= 0:
		return
	var frames: Array = packet.get("frames", [])
	var prior := state
	if frames.is_empty() and action_id == "next_round":
		await board.animate(prior, packet.state, "move", 0.25 / playback_speed)
	for index in range(frames.size()):
		var frame: Dictionary = frames[index]
		if frame.phase == "combat":
			var after: Dictionary = frames[index + 1] if index + 1 < frames.size() else packet.state
			phase_label.text = "交战"
			await board.animate(frame, after, "combat", 0.85 / playback_speed)
		elif index == 0 or frames[index - 1].phase != "combat":
			await board.animate(prior, frame, "move", 0.18 / playback_speed)
		prior = frame

func _confirm(title: String, copy: String, action: Callable) -> void:
	confirmation.title = title
	confirmation.dialog_text = copy
	for link: Dictionary in confirmation.confirmed.get_connections():
		confirmation.confirmed.disconnect(link.callable)
	confirmation.confirmed.connect(action, CONNECT_ONE_SHOT)
	confirmation.popup_centered()

func _ask_new() -> void:
	if catalog.is_empty():
		_connect_game()
	elif state.is_empty() or state.phase == "finished":
		_new_game()
	else:
		_confirm("开始新一局", "这局仍会保存在电脑的对局目录。", _new_game)

func _ask_concede() -> void:
	_confirm("认输", "结束当前对局并保存结果。", _submit.bind("concede"))

func _open_archive() -> void:
	if DirAccess.dir_exists_absolute(archive_dir):
		OS.shell_open(archive_dir)
	else:
		_message("尚未找到对局目录。")

func _open_export() -> void:
	pending_export = await api.request("/api/games/%s/export" % game_id)
	if pending_export.has("error"):
		_message(pending_export.error)
		return
	export_dialog.current_file = "artifact-%d-round-%d.json" % [int(pending_export.seed), int(pending_export.round)]
	export_dialog.popup_centered_ratio(0.72)

func _write_export(path: String) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		_message("无法写入对局文件。")
		return
	file.store_string(JSON.stringify(pending_export, "  "))
	_message("已导出 " + path.get_file())

func _window_contents(window: Window) -> VBoxContainer:
	var margin := MarginContainer.new()
	margin.theme = theme
	window.add_child(margin)
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for side: String in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, 13)
	var root := VBoxContainer.new()
	root.add_theme_constant_override("separation", 9)
	margin.add_child(root)
	return root

func _open_deck() -> void:
	if not is_instance_valid(deck_window):
		deck_window = Window.new()
		deck_window.title = "牌组构筑"
		deck_window.hide()
		deck_window.min_size = Vector2i(680, 510)
		deck_window.close_requested.connect(deck_window.hide)
		add_child(deck_window)
	deck_edit = _integer_deck(config.get_value("deck", "current", catalog.defaultDeck))
	deck_rows.clear()
	_clear(deck_window)
	var root := _window_contents(deck_window)
	deck_summary = _label("", 15, GOLD)
	root.add_child(deck_summary)
	var lists := HBoxContainer.new()
	lists.size_flags_vertical = Control.SIZE_EXPAND_FILL
	lists.add_theme_constant_override("separation", 12)
	root.add_child(lists)
	_build_deck_list(lists, "普通牌", "ordinary")
	_build_deck_list(lists, "物品", "items")
	var footer := HBoxContainer.new()
	root.add_child(footer)
	_button(footer, "还原默认", _reset_deck)
	_spacer(footer)
	deck_save = _button(footer, "保存到下一局", _save_deck)
	_refresh_deck()
	deck_window.popup_centered(Vector2i(766, 570))

func _build_deck_list(parent: Node, title: String, key: String) -> void:
	var section := _panel(parent)
	section.get_parent().size_flags_horizontal = Control.SIZE_EXPAND_FILL
	section.add_child(_label(title, 18, GOLD))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	section.add_child(scroll)
	var rows := VBoxContainer.new()
	rows.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(rows)
	for card: Dictionary in catalog.cards:
		var id := int(card.card_id)
		var is_item: bool = card.card_type == "Item"
		if key == "items" and not is_item:
			continue
		if key == "ordinary" and (is_item or id < 61001 or id >= 63000 or not card.colors.has("green")):
			continue
		var row := HBoxContainer.new()
		rows.add_child(row)
		var caption := _label("%s  ·  %d" % [_card_name(id), int(card.gold_cost if is_item else card.mana_cost)], 14)
		caption.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		caption.tooltip_text = card.card_text.get("schinese", "")
		row.add_child(caption)
		var subtract := _button(row, "−", _edit_copies.bind(key, id, -1))
		var count := _label("0", 14)
		count.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		count.custom_minimum_size.x = 18
		row.add_child(count)
		var add := _button(row, "+", _edit_copies.bind(key, id, 1))
		deck_rows[id] = {"key": key, "count": count, "subtract": subtract, "add": add}

func _refresh_deck() -> void:
	var ordinary: Array = deck_edit.ordinary
	var items: Array = deck_edit.items
	deck_summary.text = "普通牌 %d/21 + 9 张专属     物品 %d/10     同名最多 3 张" % [ordinary.size(), items.size()]
	deck_save.disabled = ordinary.size() != 21 or items.size() != 10
	for id: int in deck_rows:
		var row: Dictionary = deck_rows[id]
		var pile: Array = deck_edit[row.key]
		var count := pile.count(id)
		row.count.text = str(count)
		row.subtract.disabled = count == 0
		row.add.disabled = count >= 3 or pile.size() >= (10 if row.key == "items" else 21)

func _edit_copies(key: String, id: int, increment: int) -> void:
	var pile: Array = deck_edit[key]
	if increment > 0:
		pile.append(id)
	else:
		pile.erase(id)
	_refresh_deck()

func _reset_deck() -> void:
	deck_edit = _integer_deck(catalog.defaultDeck)
	_refresh_deck()

func _integer_deck(deck: Dictionary) -> Dictionary:
	return {
		"ordinary": deck.ordinary.map(func(id: Variant) -> int: return int(id)),
		"items": deck.items.map(func(id: Variant) -> int: return int(id)),
	}

func _save_deck() -> void:
	config.set_value("deck", "current", deck_edit.duplicate(true))
	if config.save(CONFIG) == OK:
		deck_window.hide()
		_message("构筑已保存，下局生效")
	else:
		deck_summary.text = "构筑未能保存，请检查本地目录。"

func _open_preview() -> void:
	if not is_instance_valid(preview_window):
		preview_window = Window.new()
		preview_window.title = "特效预览"
		preview_window.hide()
		preview_window.close_requested.connect(preview_window.hide)
		add_child(preview_window)
		var contents := _window_contents(preview_window)
		sample_board = Battlefield.new()
		sample_board.assets_root = board.assets_root
		sample_board.catalog = cards
		sample_board.details_font = font
		sample_board.show_arrows = false
		sample_board.size_flags_vertical = Control.SIZE_EXPAND_FILL
		contents.add_child(sample_board)
		var controls := HBoxContainer.new()
		contents.add_child(controls)
		sample_play = _button(controls, "播放对撞", _play_sample)
		sample_speed = OptionButton.new()
		for name_text: String in ["0.5×", "1×", "2×"]:
			sample_speed.add_item(name_text)
		sample_speed.select(1)
		controls.add_child(sample_speed)
		var sound := CheckButton.new()
		sound.text = "音效"
		sound.button_pressed = true
		sound.toggled.connect(func(enabled: bool) -> void: sample_board.sound_enabled = enabled)
		controls.add_child(sound)
		_spacer(controls)
		controls.add_child(_label("双方对撞 · 塔炮格挡 · 阵亡", 14, MUTED))
	preview_window.popup_centered(Vector2i(530, 644))
	_play_sample()

func _play_sample() -> void:
	if sample_play.disabled:
		return
	sample_play.disabled = true
	var a := {"id": 10020, "key": "A", "team": "ally", "row": 4, "col": 2,
		"attack": 4, "hp": 7, "range": 1, "hero": true, "level": 1, "target": "B", "canAttack": true}
	var b := {"id": 10069, "key": "B", "team": "enemy", "row": 3, "col": 2,
		"attack": 4, "hp": 4, "range": 1, "hero": true, "level": 1, "target": "A", "canAttack": true}
	var sample := {"columns": 5, "rows": 8, "units": [a,b],
		"forts": [{"team": 1, "row": 3, "col": 1, "hp": 40, "maxHp": 40}],
		"fortShots": [{"team": 1, "target": "A", "damage": 0, "immune": false}]}
	var after := sample.duplicate()
	var alive := a.duplicate()
	alive.hp = 3
	after.units = [alive]
	await sample_board.animate(sample, after, "combat", 0.9 / [0.5, 1.0, 2.0][sample_speed.selected])
	sample_play.disabled = false
