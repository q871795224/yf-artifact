extends SceneTree

var failed := false

func _initialize() -> void:
	call_deferred("_run")

func _expect(condition: bool, message: String) -> void:
	if not condition:
		failed = true
		push_error(message)

func _idle(app: Node) -> void:
	for tick in range(260):
		if not app.busy:
			return
		await create_timer(0.02).timeout
	failed = true
	push_error("客户端的请求或动画没有结束。")

func _capture(name_text: String) -> void:
	var folder := OS.get_environment("ARTIFACT_SCREENSHOTS")
	if folder.is_empty():
		return
	await RenderingServer.frame_post_draw
	await RenderingServer.frame_post_draw
	var picture := root.get_texture().get_image()
	_expect(not picture.is_empty(), "无法读取桌面画面。")
	if not picture.is_empty():
		_expect(picture.save_png(folder.path_join(name_text)) == OK, "无法保存截图。")

func _click_cell(board: Control, cell: Vector2i) -> void:
	var click := InputEventMouseButton.new()
	click.button_index = MOUSE_BUTTON_LEFT
	click.pressed = true
	click.position = board._cell(cell).get_center()
	board._gui_input(click)

func _run() -> void:
	var app := preload("res://main.tscn").instantiate()
	root.add_child(app)
	await process_frame
	await _idle(app)
	_expect(not app.state.is_empty(), "Godot 没有载入真人对局。")
	if failed:
		quit(1)
		return
	_expect(int(app.state.mana) == 1 and int(app.state.forts[1].row) == 1, "开局与塔位没有同步。")
	_expect(app.board.texture_for(10020) != null, "桌面未找到共享美术。")
	_expect(app.tactic_button.disabled and app.hand.get_child_count() == 5, "开局技能或手牌异常。")
	await _capture("桌面战场.png")

	# Exercise the actual UI bindings for card inspection and reforge.
	app.hand.get_child(0).pressed.emit()
	_expect(app.inspected.type == "card", "点击手牌未打开卡牌详情。")
	await _capture("桌面卡牌详情.png")
	app._choose_hand("reforge", 0)
	await _idle(app)
	_expect(int(app.state.version) == 1 and int(app.state.mana) == 1, "重铸没有通过对局服务执行。")

	for turn in range(35):
		if int(app.state.round) > 1:
			break
		app.pass_button.pressed.emit()
		await _idle(app)
	_expect(int(app.state.round) == 2 and not app.tactic_button.disabled, "没有经过交战并解锁调位。")
	var action: Dictionary = {}
	for entry: Dictionary in app._actions("rally_swap"):
		if entry.has("row"):
			action = entry
			break
	_expect(not action.is_empty(), "第二轮没有可进行的空格调位。")
	if action.is_empty():
		quit(1)
		return
	var actor: Dictionary = app._unit(action.firstTarget)
	var destination := Vector2i(int(action.col), int(action.row))
	app.tactic_button.pressed.emit()
	_click_cell(app.board, Vector2i(int(actor.col), int(actor.row)))
	_expect(destination in app.board.markers, "第二步没有高亮合法空格。")
	_click_cell(app.board, destination)
	await _idle(app)
	var moved: Dictionary = app._unit(action.firstTarget)
	_expect(not moved.is_empty() and int(moved.row) == destination.y and int(moved.col) == destination.x, "调位没有移动选中的友军。")
	_expect(app.tactic_button.disabled and int(app.state.mana) == 0, "调位次数或费用未同步。")
	var record: Dictionary = await app.api.request("/api/games/%s/export" % app.game_id)
	_expect(record.get("source") == "desktop" and not record.get("commands", []).is_empty(), "电脑试玩没有生成可导出记录。")

	app._open_deck()
	await process_frame
	_expect(app.deck_rows.size() >= 30 and not app.deck_save.disabled, "构筑没有载入合法默认牌组。")
	app._edit_copies("ordinary", int(app.deck_edit.ordinary[0]), -1)
	_expect(app.deck_save.disabled, "不完整构筑可以保存。")
	app._reset_deck()
	app._save_deck()
	await app._new_game()
	_expect(app.state.round == 1 and int(app.state.version) == 0, "保存构筑后未能创建新对局。")

	app._open_preview()
	await create_timer(0.52).timeout
	await _capture("桌面对撞.png")
	await create_timer(0.65).timeout
	_expect(app.sample_play.disabled == false and app.sample_board.state.units.size() == 1, "对撞演出未播放到阵亡状态。")
	app.preview_window.hide()
	if not failed:
		print("Godot smoke passed: opening, reforge, combat, tactics, archives, deck and FX.")
	quit(1 if failed else 0)
