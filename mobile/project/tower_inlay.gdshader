shader_type spatial;
uniform vec4 rock : source_color;
uniform float radius;
varying vec3 pos;
void vertex() { pos = VERTEX; }
float hash(vec2 p) { return fract(sin(dot(p,vec2(127.1,311.7)))*4375.55); }
float grain(vec2 p) {
	vec2 i=floor(p), f=fract(p);
	f=f*f*(3.0-2.0*f);
	return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+1.0),f.x),f.y);
}
void fragment() {
	vec2 p=pos.xz/radius;
	float a=atan(p.y,p.x);
	float edge=length(p)*cos(mod(a,0.785398)-0.392699);
	float border=(1.0-smoothstep(0.0,0.012,abs(edge-0.85)));
	float g=0.65*grain(p*7.0)+0.35*grain(p*65.0);
	ALBEDO=rock.rgb*(0.62+0.62*g)*(1.0-0.42*border);
	ROUGHNESS=0.91;
}
