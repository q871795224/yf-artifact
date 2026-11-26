shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never;
void fragment() {
	vec2 edge = min(UV, 1.0 - UV);
	float rim = 1.0 - smoothstep(0.018, 0.030, min(edge.x, edge.y));
	float corner = 1.0 - smoothstep(0.17, 0.21, max(edge.x, edge.y));
	float light = rim * mix(0.22, 1.0, corner);
	ALBEDO = mix(vec3(0.04, 0.55, 0.51), vec3(0.42, 1.0, 0.90), light);
	ALPHA = 0.14 + 0.78 * light;
}
