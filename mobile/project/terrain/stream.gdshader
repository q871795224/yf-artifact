shader_type spatial;
render_mode unshaded;
uniform sampler2D base_map : source_color, repeat_enable;
uniform sampler2D foam : repeat_enable;
uniform sampler2D relief : repeat_enable;
varying vec2 pos;
void vertex(){pos=(MODEL_MATRIX*vec4(VERTEX,1.0)).xz;}
void fragment(){
	vec2 uv=pos*vec2(1.5,3.0);
	vec2 n=texture(relief,uv+vec2(TIME*.075,0)).rg-.5;
	vec3 base=texture(base_map,uv+n*.06+vec2(TIME*.043,0)).rgb;
	float rim=clamp(abs(pos.y)*9.,0.,1.);
	float froth=texture(foam,uv*1.7+vec2(TIME*.125,0)+n*.09).a;
	ALBEDO=mix(vec3(.025,.128,.145),vec3(.17,.32,.28),clamp(dot(base,vec3(.333))*.55+rim*.32+n.y*.35,0.,1.))+vec3(.31,.42,.39)*froth*(.13+.59*smoothstep(.5,1.,rim));
}
