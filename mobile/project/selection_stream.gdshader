shader_type canvas_item;
render_mode unshaded, blend_add;
uniform sampler2D beam : source_color, repeat_enable;
uniform float scroll;
void fragment() {
	vec4 sample_color = texture(beam, vec2(UV.y, UV.x * 1.5 - scroll));
	float energy = sqrt(max(sample_color.r,max(sample_color.g,sample_color.b)) * sample_color.a);
	COLOR = vec4(0.19,0.98,0.94,energy * 0.93);
}
