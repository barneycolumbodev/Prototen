shader_type spatial;
// Harbour water at night: near-black, glossy, choppy. The brightest lights on
// the quay (passed in from layout.json) draw long shimmering streaks toward
// the camera, the way lights reflect on real water.
//
// Phone budget (playtest 2026-11-05): waves come from two scrolling samples of
// one tiling normal map, and the streak shimmer from one sample of a noise
// texture shared by every light (it used to be ~80 procedural noise calls per
// pixel). At most 12 lights.
render_mode blend_mix, depth_draw_opaque, cull_back, specular_schlick_ggx, shadows_disabled;

uniform vec3 deep : source_color = vec3(0.008, 0.014, 0.018);
uniform float reflect = 1.0;
uniform sampler2D wave_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D shimmer_tex : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform vec4 light_pos[12];
uniform vec4 light_col[12];
uniform int light_count = 0;
// 0 = no light streaks (feature benchmark / low setting)
uniform float streaks = 1.0;

varying vec3 wpos;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = wpos.xz;
	vec2 n1 = texture(wave_normal, p * 0.11 + vec2(TIME * 0.021, TIME * 0.013)).xy * 2.0 - 1.0;
	vec2 n2 = texture(wave_normal, p * 0.29 - vec2(TIME * 0.017, -TIME * 0.026)).xy * 2.0 - 1.0;
	vec2 slope = (n1 * 0.6 + n2 * 0.4) * 0.35;
	vec3 n = normalize(vec3(slope.x, 1.0, slope.y));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	ALBEDO = deep;
	ROUGHNESS = 0.06;
	METALLIC = 0.0;
	SPECULAR = 0.7;
	vec3 glow = vec3(0.0);
	if (streaks > 0.5) {
		// Mirror each light in the water plane, find how far this point is
		// (sideways) from the line between the camera and that mirror image.
		vec3 cam = (INV_VIEW_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
		// One shimmer sample, stretched toward the camera like the streaks.
		float sh = texture(shimmer_tex, p * vec2(0.9, 0.18) + vec2(0.0, TIME * 0.35)).r;
		sh = smoothstep(0.3, 0.75, sh + slope.x * 0.8);
		for (int i = 0; i < 12; i++) {
			if (i >= light_count) break;
			vec2 a = cam.xz;
			vec2 b = light_pos[i].xz;
			vec2 ab = b - a;
			float t = clamp(dot(p - a, ab) / max(dot(ab, ab), 0.001), 0.0, 1.2);
			vec2 q = a + ab * t;
			float side = length(p - q);
			float along = length(p - b);
			float width = 0.25 + along * 0.06;
			float s = exp(-side * side / (width * width) - along * 0.09) * step(0.0, t);
			glow += light_col[i].rgb * (light_col[i].a * s);
		}
		glow *= sh;
	}
	EMISSION = glow * reflect * 2.2;
}
