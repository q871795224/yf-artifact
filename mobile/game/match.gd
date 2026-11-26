extends Node

const FONT = preload("res://selection_assets/kaiti.ttf")
const FACE = preload("res://game/card_face.gd")
const STEEL := Color("#263238ee")
const BRASS := Color("#a58a5e")
const MINT := Color("#9ae2d3")
const NAMES := {"card":"打出","item":"使用","reforge":"重铸抽牌","move":"移动","chen":"劝化","purify":"洗礼","swap":"换位","redirect":"引导箭头","rally_swap":"调位","blink":"闪烁"}
var engine := preload("res://game/match_engine.gd").new()
var board := preload("res://game/board.gd").new()
var hud := Control.new()
var dialog: Control
var state := {}
var catalog := {}
var textures := {}
var lobby := {}
var opts: Array = []
var marks := {}
var page := 0
var busy := false
var enemy := "pressure"
var expanded := false
var status: Label
var beam: Node2D
var target_text := ""
var anchor_card := 0

func _ready() -> void:
	add_child(engine)
	add_child(board)
	board.setup($Screen,artwork)
	$HUD.add_child(hud)
	hud.size = Vector2(1260,2800)
	hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	text_at(hud,"正在打开河岸战场…",Rect2(160,1280,940,130),58)
	load_lobby()

func load_lobby() -> void:
	busy = true
	lobby = await engine.request({"op":"lobby"})
	busy = false
	clear_hud()
	if lobby.has("error"):
		show_error(lobby.error)
		return
	for card in lobby.cards: catalog[int(card.card_id)] = card
	show_menu()

func card_data(id: int) -> Dictionary:
	return catalog.get(id,{"card_name":{"schinese":"近战小兵"},"card_type":"Creep"})

func title(id: int) -> String:
	return card_data(id).card_name.schinese

func artwork(id: int, team := "ally") -> Texture2D:
	var key := str(id)+team
	if textures.has(key): return textures[key]
	var aid := int(card_data(id).get("art_id",id))
	var paths := ["res://game/art/cards/%d.webp"%id,"res://game/art/classic/%d.webp"%aid,"res://game/art/icons/%d.webp"%aid]
	if id==64004 or (id==1006 and team=="enemy"):
		paths.push_front("res://game/art/units/"+(("dire-ranged" if team=="enemy" else "radiant-ranged") if id==64004 else "dire-melee")+".webp")
	paths.append("res://game/art/units/"+("dire-melee" if team=="ally" else "radiant-ranged")+".webp")
	for path in paths:
		if ResourceLoader.exists(path):
			textures[key] = load(path)
			if path.contains("/classic/"):
				var source: Texture2D = textures[key]
				var extent := source.get_size()
				if extent.y > extent.x:
					var crop := AtlasTexture.new()
					crop.atlas = source
					crop.region = Rect2(0,extent.y*0.12,extent.x,extent.y*(0.70 if card_data(id).get("card_type")=="Hero" else 0.46))
					textures[key] = crop
			return textures[key]
	return preload("res://models/card/ursa.png")

func clear_children(n: Node) -> void:
	for c in n.get_children():
		n.remove_child(c)
		c.queue_free()

func clear_hud() -> void:
	clear_children(hud)
	dialog = null
	status = null

func style(fill: Color, edge := BRASS, radius := 13) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = fill
	s.border_color = edge
	s.set_border_width_all(2)
	s.set_corner_radius_all(radius)
	return s

func panel(parent: Control, rect: Rect2, color: Color) -> Panel:
	var p := Panel.new()
	parent.add_child(p)
	p.position = rect.position
	p.size = rect.size
	p.add_theme_stylebox_override("panel",style(color))
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return p

func text_at(parent: Control, value: String, rect: Rect2, px: int, tint := Color("#f2e9d4")) -> Label:
	var l := Label.new()
	parent.add_child(l)
	l.position = rect.position
	l.size = rect.size
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.autowrap_mode = TextServer.AUTOWRAP_ARBITRARY
	l.add_theme_font_override("font",FONT)
	l.add_theme_font_size_override("font_size",px)
	l.add_theme_color_override("font_color",tint)
	l.add_theme_constant_override("outline_size",4)
	l.text = value
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l

func button(parent: Control, name_: String, rect: Rect2, call_: Callable, active := true) -> Button:
	var b := Button.new()
	parent.add_child(b)
	b.position = rect.position
	b.size = rect.size
	b.text = name_
	b.add_theme_font_override("font",FONT)
	b.add_theme_font_size_override("font_size",38)
	for kind in ["normal","hover","pressed","disabled"]:
		b.add_theme_stylebox_override(kind,style(Color("#365955f5") if kind in ["pressed","hover"] else STEEL,Color("#746855") if kind=="disabled" else BRASS))
	b.disabled = not active
	b.pressed.connect(call_)
	return b

func icon(parent: Control, tex: Texture2D, rect: Rect2) -> void:
	var t := TextureRect.new()
	parent.add_child(t)
	t.position = rect.position
	t.size = rect.size
	t.texture = tex
	t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	t.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	t.mouse_filter = Control.MOUSE_FILTER_IGNORE

func modal() -> Control:
	close_dialog()
	var shade := ColorRect.new()
	hud.add_child(shade)
	shade.size = hud.size
	shade.color = Color(0.035,0.045,0.05,0.67)
	dialog = shade
	return shade

func close_dialog() -> void:
	if is_instance_valid(dialog):
		hud.remove_child(dialog)
		dialog.queue_free()
	dialog = null

func show_error(msg: String) -> void:
	var layer := modal()
	text_at(layer,msg,Rect2(80,990,1100,520),45)
	button(layer,"重新打开",Rect2(350,1610,560,104),load_lobby)

func show_menu() -> void:
	var layer := modal()
	panel(layer,Rect2(110,820,1040,1040),Color("#182326ef"))
	text_at(layer,"河岸交战",Rect2(140,886,980,160),94)
	text_at(layer,"摧毁敌塔取胜。双方连续让过后，棋子自动交战。",Rect2(170,1035,920,130),37,MINT)
	button(layer,"牌组  ·  "+("红绿扩充" if expanded else "经典绿组"),Rect2(230,1190,800,108),func(): expanded=not expanded;show_menu())
	button(layer,"对手  ·  "+("前线压迫" if enemy=="pressure" else "装备成长"),Rect2(230,1320,800,108),func(): enemy="equipment" if enemy=="pressure" else "pressure";show_menu())
	button(layer,"开始新对局",Rect2(230,1495,800,115),start_game)
	button(layer,"继续上次对局",Rect2(230,1632,800,100),run_request.bind({"op":"resume"}),lobby.get("saved",false))

func start_game() -> void:
	page = 0
	run_request({"op":"new","preset":"expansion" if expanded else "classic","enemy":enemy,"seed":randi_range(1,2147483600)})

func act(id: String) -> void:
	if not busy: run_request({"op":"act","version":state.version,"action":id})

func run_request(q: Dictionary) -> void:
	if busy: return
	busy = true
	close_dialog()
	opts.clear()
	marks.clear()
	target_text = ""
	board.highlight([])
	if status: status.text = "正在结算…"
	var packet: Dictionary = await engine.request(q)
	if packet.has("error"):
		busy = false
		show_error(packet.error)
		return
	if not state.is_empty() and q.op=="act":
		for frame in packet.get("frames",[]):
			if status: status.text = frame.label
			var a: Variant = frame.get("action")
			if a is Dictionary and a.has("card_id"):
				var left := face(hud,int(a.card_id),Vector2(-250,630),0.91)
				var t := left.create_tween()
				t.tween_property(left,"position:x",18,0.18)
				t.tween_interval(0.63)
				t.tween_property(left,"modulate:a",0,0.18)
				t.tween_callback(left.queue_free)
				var cast := preload("res://cast_fx/hand_cast.gd").new()
				hud.add_child(cast)
				cast.position = Vector2(168,845)
				cast.scale = Vector2.ONE*0.74
				var flight := cast.create_tween()
				flight.tween_method(cast.seek,0.0,1.3,0.72)
				flight.tween_callback(cast.queue_free)
				await get_tree().create_timer(0.53).timeout
			board.sync(frame,true)
			if a is Dictionary and a.kind=="item":
				board.equip_effect(str(a.target),card_data(int(a.get("card_id",0))).get("sub_type",""))
			if a is Dictionary and a.has("card_id"):
				await get_tree().create_timer(0.38).timeout
			if "开始交战" in frame.label:
				board.clash(frame.units)
				await get_tree().create_timer(0.56).timeout
			else: await get_tree().create_timer(0.23).timeout
	if q.op=="act" and packet.state.phase=="finished" and packet.state.get("endReason") in ["tower-destroyed","simultaneous"]:
		board.sync(packet.state,true)
		await get_tree().create_timer(1.28).timeout
	var drew: bool = q.get("action")=="next_round"
	state = packet.state
	lobby.saved = true
	board.sync(state,false)
	board.forecast(state.get("forecast"))
	busy = false
	anchor_card = 0
	refresh()
	if drew:
		sound(preload("res://hud/draw_01.wav"))
		if state.hand.size()>0:
			var drawn := face(hud,int(state.hand[-1]),Vector2(1020,2370),0.4)
			var flight := drawn.create_tween()
			flight.tween_property(drawn,"position",Vector2(600,2210),0.23)
			flight.tween_property(drawn,"position",Vector2(475,2490),0.29)
			flight.tween_callback(drawn.queue_free)
	print("RIVER_MATCH ",int(state.round)," ",state.phase," v",int(state.version))

func costs(id: int) -> String:
	var c := card_data(id)
	return str(int(c.gold_cost)) if c.get("card_type")=="Item" else str(int(state.get("cardCosts",{}).get(str(id),c.get("mana_cost",0))))

func face(parent: Control, id: int, pos: Vector2, ratio: float) -> Control:
	var f := FACE.new()
	parent.add_child(f)
	f.compose(card_data(id),artwork(id),costs(id))
	f.position = pos
	f.scale = Vector2.ONE*ratio
	f.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for ch in f.find_children("*","Control",true,false): ch.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return f

func resources(y: int, mana: int, money: int) -> void:
	var plate := panel(hud,Rect2(860,y,365,88),Color("#1d2629eb"))
	icon(plate,preload("res://hud/mana.svg"),Rect2(18,19,53,48))
	text_at(plate,str(mana),Rect2(75,1,84,84),45)
	icon(plate,preload("res://hud/gold.png"),Rect2(172,18,61,50))
	text_at(plate,str(money),Rect2(238,1,100,84),45)

func refresh() -> void:
	clear_hud()
	var back := panel(hud,Rect2(26,28,475,91),STEEL)
	text_at(back,"第 %d 回合   ·   %s"%[int(state.round),{"action":"行动","round_end":"采购","finished":"终局"}.get(state.phase,"交战")],Rect2(0,0,475,91),43)
	resources(28,int(state.opponent.mana),int(state.opponent.gold))
	text_at(hud,"敌方手牌  %d"%int(state.opponent.cards),Rect2(500,27,343,85),36)
	var strip := panel(hud,Rect2(31,2170,1198,92),Color("#172124e8"))
	status = text_at(strip,target_text if target_text else ("点手牌出牌，或点英雄移动" if int(state.version)==0 else str(state.label)),Rect2(12,0,1174,89),39,MINT)
	resources(2280,int(state.mana),int(state.gold))
	button(hud,"对局",Rect2(32,2280,197,91),show_info)
	if not opts.is_empty():
		button(hud,"取消选择",Rect2(250,2280,355,91),cancel_selection)
	else:
		var tactic: Dictionary = state.globalSkill
		button(hud,tactic.name,Rect2(245,2280,222,91),choose.bind(actions(str(tactic.kind)),str(tactic.name)),not actions(str(tactic.kind)).is_empty())
		button(hud,"让过",Rect2(483,2280,285,91),act.bind("pass"),state.phase=="action")
	var all_cards: Array = []
	for i in state.hand.size(): all_cards.append([int(state.hand[i]),"card",i])
	for i in state.items.size(): all_cards.append([int(state.items[i].id),"item",i])
	page = clampi(page,0,maxi(0,ceili(all_cards.size()/5.0)-1))
	for i in mini(5,all_cards.size()-page*5):
		var entry: Array = all_cards[page*5+i]
		var at := Vector2(20+i*230,2470)
		face(hud,entry[0],at,0.69)
		var hit := Button.new()
		hud.add_child(hit)
		hit.flat = true
		hit.position = at
		hit.size = Vector2(225,330)
		hit.pressed.connect(inspect_card.bind(entry[0],entry[1],entry[2]))
	button(hud,"‹",Rect2(38,2384,105,75),change_page.bind(-1),page>0)
	text_at(hud,"手牌  %d / %d"%[page+1,maxi(1,ceili(all_cards.size()/5.0))],Rect2(154,2380,325,80),36)
	button(hud,"›",Rect2(480,2384,105,75),change_page.bind(1),(page+1)*5<all_cards.size())
	draw_pile(Vector2(1145,2425),9)
	text_at(hud,"牌堆 %d"%int(state.deck),Rect2(750,2383,290,78),38)
	show_reserves()
	if anchor_card and not opts.is_empty():
		face(hud,anchor_card,Vector2(12,157),0.58)
		beam = preload("res://selection_stream.gd").new()
		hud.add_child(beam)
	if state.phase=="round_end": show_shop()
	elif state.phase=="finished": show_result()

func _process(_delta: float) -> void:
	if is_instance_valid(beam) and not opts.is_empty() and not marks.is_empty() and not busy:
		var tip := hud.get_local_mouse_position()
		if not marks.has(board.pick(tip)): tip = board.screen_at(marks.keys()[0])
		beam.aim(Vector2(195,450),tip,Time.get_ticks_msec()/1000.0,card_data(anchor_card).get("card_type")=="Item",0.8)

func draw_pile(at: Vector2, angle: float) -> void:
	var back := AtlasTexture.new()
	back.atlas = preload("res://models/artifact_movie/card/card_back_color_psd_7981b7ea.png")
	back.region = Rect2(189,0,645,1024)
	for i in 3:
		var card := Sprite2D.new()
		hud.add_child(card)
		card.texture = back
		card.position = at+Vector2(i*2,-i*4)
		card.scale = Vector2(0.12,0.092)
		card.rotation_degrees = angle
		card.modulate = Color.WHITE.darkened((2-i)*0.15)

func change_page(d: int) -> void:
	if busy: return
	page += d
	refresh()

func actions(kind: String, actor := "") -> Array:
	return state.get("actions",[]).filter(func(a): return a.kind==kind and (actor.is_empty() or str(a.actor)==actor))

func inspect_card(id: int, kind: String, index: int) -> void:
	if busy: return
	var layer := modal()
	face(layer,id,Vector2(292,670),2.06)
	var use := actions(kind,str(index))
	var reforge := actions("reforge",str(index)) if kind=="card" else []
	button(layer,"打出" if kind=="card" else "使用物品",Rect2(140,1852,465,115),func(): anchor_card=id;choose(use,title(id)),not use.is_empty())
	button(layer,"重铸抽牌",Rect2(655,1852,465,115),func(): act(reforge[0].id),not reforge.is_empty())
	button(layer,"收起",Rect2(380,2005,500,100),close_dialog)

func sound(clip: AudioStream) -> void:
	var player := AudioStreamPlayer.new()
	add_child(player)
	player.stream = clip
	player.finished.connect(player.queue_free)
	player.play()

func show_reserves() -> void:
	var x := 25
	for u in state.heroes:
		if u.team!="ally" or u.row!=null: continue
		var p := panel(hud,Rect2(x,2056,105,108),STEEL)
		icon(p,artwork(int(u.id)),Rect2(4,4,94,78))
		text_at(p,"✓" if int(u.due)<=int(state.round)+1 else "−1",Rect2(0,70,105,38),32,MINT)
		x += 111

func pos_for(a: Dictionary) -> Vector2i:
	if a.has("march"):
		return Vector2i(int(a.march[0].col),int(a.march[0].row))
	var token: String = str(a.get("firstTarget",a.get("target","")))
	if not a.has("firstTarget") and a.has("row"):
		return Vector2i(int(a.col),int(a.row))
	for u in state.units:
		if u.key==token: return board.cell_of(u)
	if "," in token:
		var parts := token.split(",")
		if parts.size()==2: return Vector2i(int(parts[1]),int(parts[0]))
	return Vector2i(-1,-1)

func choose(available: Array, caption: String) -> void:
	if busy or available.is_empty(): return
	close_dialog()
	opts = available
	marks.clear()
	for a in opts:
		var cell := pos_for(a)
		if board.tiles.has(cell):
			if not marks.has(cell): marks[cell] = []
			marks[cell].append(a)
	if marks.is_empty():
		if opts.size()==1: act(opts[0].id)
		else: action_list(opts)
		return
	target_text = caption+"  ·  点选青色格"
	board.highlight(marks.keys())
	refresh()

func cancel_selection() -> void:
	if busy: return
	opts = []
	marks.clear()
	anchor_card = 0
	target_text = ""
	board.highlight([])
	refresh()

func _unhandled_input(event: InputEvent) -> void:
	if busy or state.is_empty() or is_instance_valid(dialog): return
	if event is InputEventMouseButton and event.button_index==MOUSE_BUTTON_LEFT and event.pressed:
		tap_cell(board.pick(event.position))

func tap_cell(cell: Vector2i) -> void:
	if not opts.is_empty():
		if not marks.has(cell): return
		var choices: Array = marks[cell]
		if choices[0].has("firstTarget"):
			var second := []
			for a in choices:
				var b: Dictionary = a.duplicate()
				b.erase("firstTarget")
				b.target = b.secondTarget
				if b.has("secondRow"):
					b.row = b.secondRow
					b.col = b.secondCol
				second.append(b)
			choose(second,"选择第二个目标")
		elif choices.size()==1: act(choices[0].id)
		else: action_list(choices)
		return
	for u in state.units:
		if board.cell_of(u)==cell:
			unit_dialog(u)
			return
	for f in state.forts:
		if board.cell_of(f)==cell:
			var layer := modal()
			show_panel_text(layer,"防御塔" if f.stage=="tower" else "基地","攻击 %d     生命 %d / %d"%[int(f.attack),int(f.hp),int(f.maxHp)])
			button(layer,"返回棋盘",Rect2(340,1480,580,104),close_dialog)
			return

func unit_dialog(u: Dictionary) -> void:
	var layer := modal()
	var values := "%s   ·   攻击 %d   护甲 %d   生命 %d / %d"%["我方" if u.team=="ally" else "敌方",int(u.attack),int(u.armor),int(u.hp),int(u.maxHp)]
	show_panel_text(layer,title(int(u.id)),values)
	var y := 1400
	var kinds := {}
	for a in state.actions:
		if str(a.actor)==str(u.key): kinds[a.kind]=true
	for kind in kinds:
		button(layer,NAMES.get(kind,kind),Rect2(330,y,600,96),choose.bind(actions(kind,u.key),NAMES.get(kind,kind)))
		y += 110
	button(layer,"返回棋盘",Rect2(330,y+25,600,96),close_dialog)

func show_panel_text(layer: Control, heading: String, detail: String) -> void:
	panel(layer,Rect2(92,995,1076,865),Color("#182426f2"))
	text_at(layer,heading,Rect2(135,1050,990,135),65)
	text_at(layer,detail,Rect2(148,1195,964,175),42,MINT)

func action_list(choices: Array, offset := 0) -> void:
	var layer := modal()
	var scroll := ScrollContainer.new()
	layer.add_child(scroll)
	scroll.position = Vector2(110,555)
	scroll.size = Vector2(1040,1530)
	var list := VBoxContainer.new()
	scroll.add_child(list)
	for a in choices.slice(offset,offset+10):
		var caption: String = "%s   %s → %s"%[NAMES.get(a.kind,a.kind),a.get("firstTarget",a.actor),a.get("secondTarget",a.target)]
		if a.has("march"):
			var names := PackedStringArray()
			for step in a.march:
				for u in state.units:
					if u.key==step.unit: names.append(title(int(u.id)))
			caption = "推进  ·  "+"、".join(names)
		var b := button(list,caption,Rect2(0,0,998,99),act.bind(a.id))
		b.custom_minimum_size = Vector2(998,99)
	button(layer,"上一页",Rect2(150,1960,390,92),action_list.bind(choices,offset-10),offset>0)
	button(layer,"下一页",Rect2(720,1960,390,92),action_list.bind(choices,offset+10),offset+10<choices.size())
	button(layer,"返回棋盘",Rect2(335,2120,590,98),close_dialog)

func show_info() -> void:
	if busy: return
	var layer := modal()
	panel(layer,Rect2(80,555,1100,1610),Color("#1a2527f7"))
	text_at(layer,"对局记录",Rect2(130,610,1000,112),64)
	var lines := PackedStringArray()
	for entry in state.log.slice(-8): lines.append(str(entry.text))
	text_at(layer,"\n".join(lines),Rect2(140,745,980,740),39)
	button(layer,"可用行动",Rect2(215,1510,830,102),action_list.bind(state.actions))
	button(layer,"保存并返回主界面",Rect2(215,1643,830,102),show_menu)
	button(layer,"认输",Rect2(215,1776,830,102),confirm_concede)
	button(layer,"返回棋盘",Rect2(215,1910,830,102),close_dialog)

func confirm_concede() -> void:
	var layer := modal()
	show_panel_text(layer,"结束本局？","认输后会记录本局结果。")
	button(layer,"认输",Rect2(220,1470,370,103),act.bind("concede"))
	button(layer,"继续对局",Rect2(655,1470,385,103),close_dialog)

func show_shop() -> void:
	var layer := modal()
	if state.shop.bought:
		var coins := preload("res://shop/purchase_fx.gd").new()
		layer.add_child(coins)
		coins.start(Vector2(630,1190))
		sound(preload("res://shop/buy.wav"))
	var box := preload("res://game/shop_box.gd").new()
	layer.add_child(box)
	box.position = Vector2(155,415)
	box.size = Vector2(950,950)
	text_at(layer,"回合采购",Rect2(115,1015,1030,135),75)
	text_at(layer,"金币  %d"%int(state.gold),Rect2(160,1155,940,95),44,MINT)
	for i in state.shop.offers.size():
		var offer: Dictionary = state.shop.offers[i]
		var x: int = 45+i*398
		face(layer,int(offer.id),Vector2(x,1275),1.15)
		text_at(layer,offer.source,Rect2(x,1915,377,60),31)
		button(layer,"购买  ·  %d"%int(offer.price),Rect2(x,1990,377,100),act.bind(str(offer.action_id)),offer.action_id!=null and not state.shop.bought)
	text_at(layer,"已购入物品" if state.shop.bought else "每轮可购入一件物品",Rect2(110,2130,1040,86),38)
	button(layer,"进入下一回合",Rect2(265,2250,730,126),act.bind("next_round"))

func show_result() -> void:
	var layer := modal()
	var heading := "平局" if state.winner==null else ("胜利" if int(state.winner)==0 else "战败")
	show_panel_text(layer,heading,"第 %d 回合   ·   %s"%[int(state.round),str(state.label)])
	button(layer,"再来一局",Rect2(265,1450,730,110),start_game)
	button(layer,"主界面",Rect2(265,1588,730,105),show_menu)
