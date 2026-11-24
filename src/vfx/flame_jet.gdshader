shader_type spatial;
// Volumetric aerosol flame stream (Triad Flamer): smooth billowing orange/red/gold
// tongues of fire along +Z with scrolling 3D noise + upward thermal lift.
// Uses smooth alpha blending (no screen-door stipple) with rich saturated fire colors.
render_mode cull_disabled, depth_draw_never, unshaded, shadows_disabled;

uniform float now = 0.0;
uniform float length_m = 6.5;
uniform float intensity = 1.0;
uniform float seed = 0.0;

varying float v_u;
varying vec3 v_pos;
varying float v_noise;

float hash13(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.zyx + 31.32);
	return fract((p.x + p.y) * p.z);
}

float vnoise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = mix(hash13(i), hash13(i + vec3(1.0, 0.0, 0.0)), f.x);
	float b = mix(hash13(i + vec3(0.0, 1.0, 0.0)), hash13(i + vec3(1.0, 1.0, 0.0)), f.x);
	float c = mix(hash13(i + vec3(0.0, 0.0, 1.0)), hash13(i + vec3(1.0, 0.0, 1.0)), f.x);
	float d = mix(hash13(i + vec3(0.0, 1.0, 1.0)), hash13(i + vec3(1.0, 1.0, 1.0)), f.x);
	return mix(mix(a, b, f.y), mix(c, d, f.y), f.z);
}

float fbm(vec3 p) {
	return 0.56 * vnoise(p) + 0.29 * vnoise(p * 2.13 + vec3(5.2, 1.9, 3.7)) + 0.15 * vnoise(p * 4.21 + vec3(1.4, 7.1, 2.3));
}

// Rich saturated flame ramp (keeps vivid orange-red instead of blowing out to flat white).
vec3 flame_color(float h) {
	vec3 dark_red = vec3(0.55, 0.03, 0.004);
	vec3 fiery_orange = vec3(1.0, 0.20, 0.01);
	vec3 bright_amber = vec3(1.0, 0.44, 0.04);
	vec3 hot_gold = vec3(1.0, 0.74, 0.24);
	vec3 c = mix(dark_red, fiery_orange, smoothstep(0.08, 0.38, h));
	c = mix(c, bright_amber, smoothstep(0.36, 0.72, h));
	c = mix(c, hot_gold, smoothstep(0.72, 1.05, h));
	return c;
}

void vertex() {
	// Source mesh: unit tube along +Z from z=0 to z=1, unit radial ring in XY.
	float u = clamp(VERTEX.z, 0.0, 1.0);
	v_u = u;
	float z = u * length_m * clamp(intensity, 0.0, 1.0);
	// Tight aerosol ignition jet expanding into a billowing 0.44 m fiery plume.
	float base_r = mix(0.030, 0.44, pow(u, 0.76)) * (0.45 + 0.55 * clamp(intensity, 0.0, 1.0));
	base_r *= 1.0 - 0.30 * smoothstep(0.75, 1.0, u);
	vec2 radial = VERTEX.xy;
	float flow = now * 11.5;
	vec3 sample_p = vec3(radial * 2.0, u * 5.6 - flow) + vec3(seed * 7.0, seed * 3.0, 0.0);
	float n = fbm(sample_p);
	v_noise = n;
	float disp = 1.0 + (n - 0.45) * mix(0.28, 1.20, u);
	vec3 p = vec3(radial * base_r * disp, z);
	// Hot flames curl upward as the spray loses forward momentum.
	p.y += u * u * 0.48 * min(length_m / 6.5, 1.0);
	p.x += sin(u * 9.5 - flow * 1.2 + seed * 11.0) * 0.10 * u;
	v_pos = vec3(radial * 2.4, u * 7.2 - flow * 1.35) + vec3(seed * 13.0, 0.0, 0.0);
	VERTEX = p;
}

void fragment() {
	if (intensity <= 0.01) {
		discard;
	}
	float fine = fbm(v_pos * 1.4 + vec3(0.0, -now * 4.0, 0.0));
	float turb = mix(v_noise, fine, 0.62);
	float ndv = abs(dot(normalize(NORMAL), VIEW));
	// Soft turbulent flame edges & licking fiery tip (zero stipple).
	float edge_soft = pow(clamp(ndv, 0.0, 1.0), 1.15);
	float tip_fade = 1.0 - smoothstep(0.55, 1.0, v_u + (0.45 - turb) * 0.48);
	float nozzle_fade = smoothstep(0.0, 0.04, v_u);
	float alpha = smoothstep(0.18, 0.72, turb * 1.15 * tip_fade) * edge_soft * nozzle_fade * clamp(intensity, 0.0, 1.0);
	alpha = clamp(alpha * 0.92, 0.0, 0.92);
	if (alpha < 0.02) {
		discard;
	}
	// Core is hot gold, outer rolling licks are vivid crimson-orange.
	float heat = (0.98 - v_u * 0.65) * (0.45 + 0.75 * turb) + edge_soft * 0.28;
	heat = clamp(heat, 0.05, 1.12);
	vec3 col = flame_color(heat) * mix(1.05, 1.65, heat);
	// Crisp blue-hot ignition kiss right at the lighter wick.
	float ign = smoothstep(0.12, 0.0, v_u) * smoothstep(0.3, 0.85, ndv);
	col = mix(col, vec3(0.35, 0.65, 1.55), ign * 0.65);
	ALBEDO = col;
	ALPHA = alpha;
}
