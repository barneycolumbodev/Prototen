shader_type spatial;
// Harbour water at night: near-black, glossy, choppy. The brightest lights on
// the quay (passed in from layout.json) draw long shimmering streaks toward
// the camera, the way lights reflect on real water.
render_mode blend_mix, depth_draw_opaque, cull_back, specular_schlick_ggx, shadows_disabled;

uniform vec3 deep : source_color = vec3(0.008, 0.014, 0.018);
uniform float reflect = 1.0;
uniform vec4 light_pos[24];
uniform vec4 light_col[24];
uniform int light_count = 0;

varying vec3 wpos;

float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
float noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}
float waves(vec2 p, float t) {
	return noise(p * 0.9 + vec2(t * 0.35, t * 0.2)) * 0.5 + noise(p * 2.3 - vec2(t * 0.5, -t * 0.3)) * 0.3 + noise(p * 6.1 + t * 0.8) * 0.2;
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = wpos.xz;
	float e = 0.08;
	float h = waves(p, TIME);
	float hx = waves(p + vec2(e, 0.0), TIME);
	float hz = waves(p + vec2(0.0, e), TIME);
	vec3 n = normalize(vec3((h - hx) / e * 0.18, 1.0, (h - hz) / e * 0.18));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	ALBEDO = deep;
	ROUGHNESS = 0.06;
	METALLIC = 0.0;
	SPECULAR = 0.7;
	// light streaks: mirror each light in the water plane, find how far this
	// point is (sideways) from the line between the camera and that mirror image
	vec3 cam = (INV_VIEW_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	vec3 glow = vec3(0.0);
	float dist_cam = length(wpos.xz - cam.xz);
	for (int i = 0; i < 24; i++) {
		if (i >= light_count) break;
		vec3 L = light_pos[i].xyz;
		vec3 M = vec3(L.x, 2.0 * wpos.y - L.y, L.z);
		vec2 a = cam.xz;
		vec2 b = M.xz;
		vec2 ab = b - a;
		float t = clamp(dot(p - a, ab) / max(dot(ab, ab), 0.001), 0.0, 1.2);
		vec2 q = a + ab * t;
		float side = length(p - q);
		// how far along the reflected path (the streak is longest near the light)
		float along = length(p - b);
		float width = 0.25 + along * 0.06;
		float shimmer = smoothstep(0.35, 0.75, waves(p * vec2(3.0, 0.6) + float(i), TIME * 1.6));
		float s = exp(-side * side / (width * width)) * exp(-along * 0.09) * shimmer * step(0.0, t);
		glow += light_col[i].rgb * light_col[i].a * s;
	}
	EMISSION = glow * reflect * 2.2;
}
