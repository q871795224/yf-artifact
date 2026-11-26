extends Panel

const DIM := Vector2(328, 550)
const BOOK = {
	"hero": ["熊战士", "", "英雄", "", "7", "10", preload("res://models/card/ursa.png"), Color("#87384a")],
	"spell": ["战斗训练", "2", "法术", "一名英雄永久获得\n+2 攻击。", "", "", preload("res://sample-art/training.webp"), Color("#87384a")],
	"unit": ["萌芽守卫", "1", "单位", "死亡时，左右相邻友军\n永久获得 +1 攻击、+1 生命。", "0", "2", preload("res://sample-art/sprout.webp"), Color("#47654b")],
	"item": ["短剑", "3", "武器", "装备此武器的英雄\n获得 +2 攻击。", "", "", preload("res://sample-art/short-sword.webp"), Color("#82602b")],
	"chainmail": ["锁子甲", "7", "护甲", "装备此护甲的英雄\n获得 +2 护甲。", "", "", preload("res://shop/10214.webp"), Color("#82602b")],
	"salve": ["治疗药膏", "3", "消耗品", "一名友军恢复 6 生命。", "", "", preload("res://shop/3003.webp"), Color("#82602b")]
}
const CHINESE_FONT = preload("res://selection_assets/kaiti.ttf")
const ICONS = {
	"hero": preload("res://selection_assets/cardtype_hero_psd.png"),
	"unit": preload("res://selection_assets/cardtype_creep_psd.png"),
	"spell": preload("res://selection_assets/cardtype_spell_psd.png"),
	"item": preload("res://selection_assets/cardtype_weapon_psd.png"),
	"chainmail": preload("res://selection_assets/cardtype_armor_psd.png"),
	"salve": preload("res://selection_assets/cardtype_consumable_psd.png")
}

func panel(at: Vector2, extent: Vector2, fill: Color, edge: Color, radius: int) -> Panel:
	var box := Panel.new()
	var paint := StyleBoxFlat.new()
	paint.bg_color = fill
	paint.border_color = edge
	paint.set_border_width_all(1)
	paint.set_corner_radius_all(radius)
	box.add_theme_stylebox_override("panel", paint)
	box.position = at
	box.size = extent
	add_child(box)
	return box

func words(value: String, at: Vector2, extent: Vector2, px: int, color := Color("#f4eadd"), center := true) -> void:
	var caption := Label.new()
	caption.text = value
	caption.position = at
	caption.size = extent
	caption.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	if center: caption.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	caption.add_theme_font_override("font", CHINESE_FONT)
	caption.add_theme_font_size_override("font_size", px)
	caption.add_theme_color_override("font_color", color)
	caption.add_theme_color_override("font_shadow_color", Color("#121416"))
	caption.add_theme_constant_override("shadow_offset_y", 2)
	add_child(caption)

func art(texture: Texture2D, at: Vector2, extent: Vector2) -> void:
	var window := Control.new()
	window.position = at
	window.size = extent
	window.clip_contents = true
	add_child(window)
	var image := TextureRect.new()
	image.texture = texture
	image.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	image.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	image.size = extent
	window.add_child(image)

func build(kind: String) -> void:
	var data: Array = BOOK[kind]
	var team: Color = data[7]
	var stats := kind in ["hero", "unit"]
	size = DIM
	var frame := StyleBoxFlat.new()
	frame.bg_color = Color("#202527")
	frame.border_color = team.lightened(0.18)
	frame.set_border_width_all(2)
	frame.set_corner_radius_all(9)
	frame.shadow_color = Color(0,0,0,0.55)
	frame.shadow_size = 7
	add_theme_stylebox_override("panel", frame)
	art(data[6], Vector2(3,3), Vector2(322,544))
	panel(Vector2(2,2), Vector2(324,40), Color(team,0.78), Color(team,0.5), 5)
	var title_x := 12
	if kind in ["item", "chainmail", "salve"]:
		art(preload("res://selection_assets/cardstat_goldcost_psd.png"), Vector2(7,7), Vector2(28,28))
		words(data[1],Vector2(35,2),Vector2(20,38),26)
		title_x = 64
	elif data[1] != "":
		words(data[1], Vector2(6,2), Vector2(33,38), 30)
		title_x = 45
	words(data[0],Vector2(title_x,2),Vector2(240,38),28,Color("#fff6e5"),false)
	panel(Vector2(10,50),Vector2(44,44),Color("#171a1bd9"),Color("#a39070"),22)
	art(ICONS[kind],Vector2(13,53),Vector2(38,38))
	if kind == "hero":
		panel(Vector2(12,438),Vector2(59,59),Color("#18191e"),Color("#ab9364"),3)
		art(preload("res://models/card/fury.png"),Vector2(15,441),Vector2(53,53))
	else:
		var bottom := 506 if stats else 538
		panel(Vector2(3,bottom-88),Vector2(322,88),Color("#111618bf"),Color("#514e424f"),1)
		words(data[3], Vector2(10,bottom-86), Vector2(308,84), 23)
	var footer := 506 if stats else 538
	panel(Vector2(2,footer),Vector2(324,548-footer),Color(team,0.73),Color(team,0.42),4)
	if stats:
		art(preload("res://selection_assets/cardstat_attack_psd.png"),Vector2(38,512),Vector2(31,31))
		words(data[4],Vector2(72,508),Vector2(47,38),30,Color.WHITE,false)
		art(preload("res://selection_assets/cardstat_health_psd.png"),Vector2(212,512),Vector2(31,31))
		words(data[5],Vector2(248,508),Vector2(58,38),30,Color.WHITE,false)
