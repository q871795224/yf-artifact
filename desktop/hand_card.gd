extends Button

const LIGHT := Color("#efdfbd")
const BRASS := Color("#b28a54")

var artwork: Texture2D
var title_line := ""
var cost_line := ""
var stat_line := ""
var accent := Color("#85b997")
var type_line := ""
var active := false
var payable := false
var text_font: Font
var peek := false

func _ready() -> void:
	flat = true
	custom_minimum_size = Vector2(102, 44 if peek else 128)
	for style: String in ["normal", "hover", "pressed", "focus", "disabled", "hover_pressed"]:
		add_theme_stylebox_override(style, StyleBoxEmpty.new())
	mouse_entered.connect(queue_redraw)
	mouse_exited.connect(queue_redraw)
	focus_entered.connect(queue_redraw)
	focus_exited.connect(queue_redraw)

func _draw() -> void:
	var frame := Rect2(Vector2(4, 5), Vector2(size.x - 8, 117 if peek else size.y - 11))
	var highlighted := is_hovered() or active or has_focus()
	if highlighted:
		frame.position.y -= 4
	var line := BRASS.lightened(0.35) if highlighted else BRASS
	var shadow := StyleBoxFlat.new()
	shadow.bg_color = Color("#151412")
	shadow.border_color = line
	shadow.set_border_width_all(1)
	shadow.set_corner_radius_all(6)
	shadow.shadow_color = Color("#000000c8")
	shadow.shadow_size = 4
	shadow.shadow_offset = Vector2(0, 4)
	draw_style_box(shadow, frame)
	var image_rect := Rect2(frame.position + Vector2(4, 27), Vector2(frame.size.x - 8, frame.size.y - 55))
	if artwork != null:
		var extent := artwork.get_size()
		var ratio := image_rect.size.x / image_rect.size.y
		var crop := extent.min(Vector2(extent.y * ratio, extent.x / ratio))
		var source := Rect2((extent - crop) * Vector2(0.5, 0.34), crop)
		draw_texture_rect_region(artwork, image_rect, source)
	else:
		draw_rect(image_rect, accent.darkened(0.70))
	var bottom := frame.end.y
	draw_rect(Rect2(frame.position + Vector2(1, 4), Vector2(2, frame.size.y - 8)), accent)
	draw_rect(Rect2(frame.position + Vector2(3, 2), Vector2(frame.size.x - 6, 25)), Color("#242019"))
	draw_rect(Rect2(Vector2(frame.position.x + 4, bottom - 27), Vector2(frame.size.x - 8, 24)), Color("#26211a"))
	draw_line(Vector2(frame.position.x + 5, bottom - 27), Vector2(frame.end.x - 5, bottom - 27), Color(line, 0.55))
	_text(title_line, frame.position + Vector2(7, 20), frame.size.x - 14, 14, LIGHT)
	if peek:
		return
	var descriptor := type_line if stat_line.is_empty() else stat_line
	_text(descriptor, Vector2(frame.position.x + 8, bottom - 8), frame.size.x - 44, 12, Color("#d2c2a1"))
	_text(cost_line, Vector2(frame.end.x - 35, bottom - 8), 30, 13, Color("#e5bd77") if payable else Color("#bfa094"))
	if payable:
		draw_line(Vector2(frame.position.x + 12, bottom - 2), Vector2(frame.end.x - 12, bottom - 2), Color(accent, 0.70), 2)

func _text(text: String, at: Vector2, width: float, text_size: int, color: Color) -> void:
	var ui_font := text_font if text_font else ThemeDB.fallback_font
	draw_string(ui_font, at, text, HORIZONTAL_ALIGNMENT_LEFT, width, text_size, color)
