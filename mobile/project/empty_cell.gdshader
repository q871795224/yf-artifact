shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never;

uniform vec4 tint : source_color;

void fragment() {
	vec2 edge = min(UV, 1.0 - UV);
	float stroke = 1.0 - smoothstep(0.010, 0.019, min(edge.x, edge.y));
	float corner = 1.0 - smoothstep(0.17, 0.20, max(edge.x, edge.y));
	ALBEDO = tint.rgb;
	ALPHA = tint.a * stroke * corner;
}
