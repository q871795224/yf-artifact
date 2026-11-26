extends CanvasLayer

var font := SystemFont.new()
const INK := Color("#e9e3d1")
const MUTED := Color("#b1ad9d")

func panel(rect: Rect2, fill: Color, edge: Color, radius := 12) -> Panel:
	var node := Panel.new()
	var skin := StyleBoxFlat.new()
	skin.bg_color = fill
	skin.border_color = edge
	skin.set_border_width_all(2)
	skin.set_corner_radius_all(radius)
	node.add_theme_stylebox_override("panel",skin)
	node.position = rect.position
	node.size = rect.size
	add_child(node)
	return node

func caption(at: Vector2, words: String, pixels: int, color: Color) -> Label:
	var label := Label.new()
	label.position = at
	label.text = words
	label.add_theme_font_override("font",font)
	label.add_theme_font_size_override("font_size",pixels)
	label.add_theme_color_override("font_color",color)
	add_child(label)
	return label
