shader_type spatial;
render_mode cull_disabled;
uniform vec4 tint:source_color;
void vertex(){VERTEX.z+=UV.x*(.012*sin(TIME*2.6-UV.x*6.)+.005*sin(TIME*4.-UV.x*9.));VERTEX.y+=.004*UV.x*sin(TIME*2.6-UV.x*5.);}
void fragment(){
	if(UV.x>.76+.24*abs(UV.y*2.-1.)){discard;}
	float edge=step(min(UV.y,1.-UV.y),.045);
	float sigil=1.-smoothstep(.021,.052,abs(abs(UV.x-.38)+abs(UV.y-.5)*.53-.19));
	ALBEDO=mix(tint.rgb,vec3(.49,.39,.18),max(edge,sigil)*.86);
	ROUGHNESS=.93;
}
