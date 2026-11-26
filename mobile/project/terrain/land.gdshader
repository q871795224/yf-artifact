shader_type spatial;
uniform sampler2D grass:source_color,repeat_enable,filter_linear_mipmap_anisotropic;
uniform sampler2D dirt:source_color,repeat_enable,filter_linear_mipmap_anisotropic;
uniform sampler2D ash:source_color,repeat_enable,filter_linear_mipmap_anisotropic;
uniform sampler2D rock:source_color,repeat_enable,filter_linear_mipmap_anisotropic;
uniform sampler2D shore:source_color,repeat_enable,filter_linear_mipmap_anisotropic;
varying vec2 p;
uniform sampler2D profile : repeat_disable,filter_linear;
vec2 banks(float x){return textureLod(profile,vec2(clamp((x+1.09)/2.18,0.,1.),.5),0.).rg*.5-.25;}
float stream(float x){vec2 b=banks(x);return (b.x+b.y)*.5;}
float bank(vec2 q){vec2 b=banks(q.x);return max(b.x-q.y,q.y-b.y);}
void vertex(){
	p=VERTEX.xz;
	VERTEX.y=-.052+.051*smoothstep(-.018,.041,bank(p));
}
void fragment(){
	float path=abs(p.x-.16*sin(p.y*3.3)-.08*cos(p.y*7.1));
	vec2 uv=p*1.55+.075*vec2(sin(p.y*4.1),sin(p.x*5.2));
	vec3 g=texture(grass,uv*1.12).rgb;
	vec3 d=texture(dirt,uv*.83).rgb;
	vec3 a=texture(ash,uv*1.24).rgb;
	vec3 r=texture(rock,uv*.92).rgb;
	float trail=smoothstep(.22,.69,path+(g.g-.15)*.4);
	vec3 light=mix(d*vec3(.80,.69,.49),g*vec3(.65,.81,.52),.24+.74*trail);
	vec3 dark=mix(a*vec3(.67,.48,.39),r*vec3(.56,.53,.56),.19+.56*trail);
	vec2 cell=p*8.+.12*vec2(sin(32.*p.y),cos(25.*p.x));
	float first=8.;float second=9.;
	for(int i=-1;i<=1;i++){for(int j=-1;j<=1;j++){
		vec2 tile=floor(cell)+vec2(float(i),float(j));
		vec2 seed=fract(sin(vec2(dot(tile,vec2(13.2,73.1)),dot(tile,vec2(37.3,57.9))))*4375.2);
		float dd=length(tile+.18+.64*seed-cell);
		if(dd<first){second=first;first=dd;}else{second=min(second,dd);}
	}}
	float vein=(second-first) / (.6+.4*sin(p.y*35.+sin(p.x*39.)));
	float fissure=(1.-smoothstep(.004,.051,vein))*smoothstep(.55,.86,abs(p.x)+.08*sin(4.1*p.y))*smoothstep(.23,.60,-p.y)*smoothstep(-.3,.62,sin(p.y*6.3+p.x*2.6));
	float pulse=.68+.32*sin(p.y*12.-TIME*1.6+sin(p.x*8.));
	vec3 ground=mix(dark,light,step(0.,p.y-stream(p.x)));
	ground=mix(texture(shore,uv*2.).rgb*vec3(.68,.73,.65),ground,smoothstep(.008,.13,bank(p)));
	ALBEDO=ground*(1.-.60*fissure);
	EMISSION=fissure*pulse*vec3(1.0,.134,.018);
	ROUGHNESS=.94;
}
