shader_type spatial;
render_mode unshaded;
uniform sampler2D portrait : source_color, filter_linear_mipmap_anisotropic;
uniform bool round_mask;
uniform vec2 crop;
uniform vec2 offset;
void fragment() {
	if (round_mask && distance(UV, vec2(0.5)) > 0.50) { discard; }
	ALBEDO = texture(portrait, UV * crop + offset).rgb;
}
