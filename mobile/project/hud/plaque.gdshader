shader_type canvas_item;
void fragment() {
	vec2 p=UV;
	float cut=abs(fract(p.x*1.6+p.y*0.48)-0.5);
	float etch=(1.0-smoothstep(0.002,0.009,cut))*0.035;
	vec3 tone=mix(vec3(0.085,0.105,0.115),vec3(0.27,0.24,0.19),pow(1.0-p.y,2.8));
	COLOR=vec4(tone+etch,0.95);
}
