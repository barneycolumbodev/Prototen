shader_type spatial;
// The far shore: dark towers with a grid of windows, some lit (warm or
// fluorescent), red aviation lamps on the tallest. Unshaded; fog softens it.
render_mode unshaded, cull_back, fog_disabled;

varying vec3 wpos;
varying vec3 wnrm;

float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = (MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz;
}

void fragment() {
	vec3 c = vec3(0.012, 0.012, 0.016);
	if (abs(wnrm.y) < 0.5) {
		vec2 g = vec2((wpos.x + wpos.z) / 3.2, wpos.y / 3.4);
		vec2 cell = floor(g);
		vec2 f = fract(g);
		float win = step(0.22, f.x) * step(f.x, 0.78) * step(0.3, f.y) * step(f.y, 0.75);
		float lit = step(0.62, hash(cell + floor(wpos.z)));
		vec3 wc = mix(vec3(1.0, 0.72, 0.42), vec3(0.75, 0.9, 1.0), step(0.6, hash(cell * 1.7)));
		c += wc * win * lit * (0.5 + hash(cell * 3.1));
		// ambient city glow from below
		c += vec3(0.06, 0.035, 0.02) * smoothstep(30.0, -2.0, wpos.y);
	} else {
		float beacon = step(0.985, hash(floor(wpos.xz / 6.0))) * (0.6 + 0.4 * sin(TIME * 2.0 + wpos.x));
		c += vec3(1.0, 0.05, 0.02) * beacon * 4.0;
	}
	// distance haze toward the horizon glow
	float d = length(wpos.xz);
	c = mix(c, vec3(0.13, 0.08, 0.06), clamp((d - 250.0) / 600.0, 0.0, 0.6));
	ALBEDO = c;
}
