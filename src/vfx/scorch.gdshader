shader_type spatial;
// Blast scorches (ExplosionFx): flat quads laid on the surface a grenade burst
// on. Soot burnt into a ragged star (streaks thrown out by the blast), a few
// embers glowing in it for the first seconds. INSTANCE_CUSTOM = (birth, seed,
// strength, 0); `now` in game seconds. One MultiMesh for all of them.
render_mode blend_mix, depth_draw_never, cull_disabled, unshaded, shadows_disabled;

uniform float now = 0.0;
uniform float fade_after = 70.0;
uniform float fade_time = 30.0;

varying float v_birth;
varying float v_seed;
varying float v_strength;

float hash12(vec2 p) {
	vec3 q = fract(vec3(p.xyx) * 0.1031);
	q += dot(q, q.yzx + 33.33);
	return fract((q.x + q.y) * q.z);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = hash12(i);
	float b = hash12(i + vec2(1.0, 0.0));
	float c = hash12(i + vec2(0.0, 1.0));
	float d = hash12(i + vec2(1.0, 1.0));
	return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

void vertex() {
	v_birth = INSTANCE_CUSTOM.r;
	v_seed = INSTANCE_CUSTOM.g;
	v_strength = INSTANCE_CUSTOM.b;
}

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float r = length(p);
	float a = atan(p.y, p.x) / 6.2831853 + 0.5;
	// Streaks: angular noise wrapped round the circle.
	float streak = vnoise(vec2(a * 18.0 + v_seed * 37.0, r * 2.5)) * 0.6 + vnoise(p * 6.0 + v_seed * 11.0) * 0.4;
	float burn = smoothstep(1.0, 0.18, r + (streak - 0.5) * 0.65);
	float core = smoothstep(0.45, 0.0, r);
	float t = now - v_birth;
	float life = clamp(1.0 - (t - fade_after) / fade_time, 0.0, 1.0);
	float alpha = clamp(burn * 0.82 + core * 0.15, 0.0, 0.95) * v_strength * life;
	vec3 col = vec3(0.014, 0.012, 0.011);
	float ember = smoothstep(0.82, 0.95, vnoise(p * 11.0 + v_seed * 5.0)) * smoothstep(0.75, 0.15, r) * exp(-t / 2.2);
	col += vec3(1.0, 0.32, 0.06) * ember * 5.0;
	alpha = max(alpha, ember * life);
	ALBEDO = col;
	ALPHA = alpha;
}
