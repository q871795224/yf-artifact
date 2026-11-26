extends "res://hand_face.gd"

func compose(card: Dictionary, texture: Texture2D, cost: String) -> void:
	var type: String = card.get("card_type","Creep")
	var item := type=="Item"
	var stats := type in ["Hero","Creep"]
	var palette := {"red":"#883347","green":"#49684b","blue":"#245b7c","black":"#34363e"}
	var colors: Array = card.get("colors",[])
	var team := Color("#87682f") if item else Color(palette.get(colors[0] if colors else "black","#394047"))
	size = DIM
	art(texture,Vector2.ZERO,DIM)
	panel(Vector2.ZERO,Vector2(328,47),Color(team,0.87),team,6)
	if item: art(preload("res://selection_assets/cardstat_goldcost_psd.png"), Vector2(4,10),Vector2(25,25))
	words(cost,Vector2(27 if item else 5,1),Vector2(37,44),29)
	words(card.get("card_name",{}).get("schinese","士兵"),Vector2(66 if item else 47,0),Vector2(260,46),27,Color.WHITE,false)
	var icon := str({"Hero":"hero","Creep":"unit","Spell":"spell"}.get(type,"item"))
	if item:
		icon = str({"Armor":"chainmail","Consumable":"salve"}.get(card.get("sub_type",""),"item"))
	panel(Vector2(10,56),Vector2(43,43),Color("#222326cc"),Color("#9d8a66"),22)
	art(ICONS[icon],Vector2(13,59),Vector2(37,37))
	var foot := 504 if stats else 539
	var desc: String = card.get("card_text",{}).get("schinese","")
	if desc != "":
		panel(Vector2(0,foot-114),Vector2(328,114),Color("#11191cc9"),Color("#827b6444"),1)
		words(desc,Vector2(10,foot-113),Vector2(308,112),22)
		var text := get_child(-1) as Label
		text.autowrap_mode = TextServer.AUTOWRAP_ARBITRARY
		text.clip_text = true
	panel(Vector2(0,foot),Vector2(328,550-foot),Color(team,0.84),team,4)
	if stats:
		for i in 2:
			art(preload("res://selection_assets/cardstat_attack_psd.png") if i==0 else preload("res://selection_assets/cardstat_health_psd.png"),Vector2(43+i*157,514),Vector2(28,28))
			words(str(int(card.get("attack" if i==0 else "hit_points",0))),Vector2(74+i*157,505),Vector2(58,44),30)
