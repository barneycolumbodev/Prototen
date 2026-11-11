shader_type spatial;
// Blood on surfaces (src/gore/gore.gd): one quad per MultiMesh instance.
// The atlas holds shapes, not colours: R = how thick the blood is, A =
// coverage (raw_assets/gore/build_blood_textures.py). Colour and gloss come
// from thickness and age: a thin film is red and lets the surface show
// through, standing blood is dark and wet; over half a minute it dries from
// the thin edges inward to a dull brown-red.
// INSTANCE_CUSTOM: r = atlas cell, g = alpha (fades the oldest out),
// b = the clock when it landed, a = seconds it takes to run down (runs on
// walls are uncovered from the top; 0 = all there at once).
render_mode blend_mix, depth_draw_never, cull_disabled, shadows_disabled;

uniform sampler2D atlas : filter_linear_mipmap, repeat_disable;
uniform float cells = 4.0;
uniform float now = 0.0;
uniform vec3 fresh_thin : source_color = vec3(0.40, 0.022, 0.018);
uniform vec3 fresh_thick : source_color = vec3(0.13, 0.002, 0.006);
uniform vec3 dry_thin : source_color = vec3(0.17, 0.035, 0.02);
uniform vec3 dry_thick : source_color = vec3(0.075, 0.006, 0.006);
// Seconds until a thin film is dry; thick blood takes three times as long.
uniform float dry_time = 30.0;

varying vec2 v_cell;
varying float v_alpha;
varying float v_age;
varying float v_run;

void vertex() {
	float c = INSTANCE_CUSTOM.r;
	v_cell = vec2(mod(c, cells), floor(c / cells));
	v_alpha = INSTANCE_CUSTOM.g;
	v_age = max(now - INSTANCE_CUSTOM.b, 0.0);
	v_run = INSTANCE_CUSTOM.a > 0.0 ? clamp(v_age / INSTANCE_CUSTOM.a, 0.0, 1.0) : 2.0;
	// Pulled 0.4 % of the way to the camera: the same place on screen, but
	// in front of the surface it lies on even at a grazing angle far off
	// (a fixed offset z-fights there on a 16-bit-ish mobile depth buffer).
	vec4 view = MODELVIEW_MATRIX * vec4(VERTEX, 1.0);
	view.xyz *= 0.996;
	POSITION = PROJECTION_MATRIX * view;
}

void fragment() {
	vec4 t = texture(atlas, (UV + v_cell) / cells);
	float thick = t.r;
	float cover = t.a;
	// A run: only the part it has reached so far (it slows as it goes).
	float reach = v_run >= 2.0 ? 2.0 : 0.16 + 0.84 * (1.0 - (1.0 - v_run) * (1.0 - v_run));
	cover *= 1.0 - smoothstep(reach - 0.05, reach, UV.y);
	float dry = clamp(v_age / (dry_time * (1.0 + 2.0 * thick)), 0.0, 1.0);
	ALBEDO = mix(mix(fresh_thin, fresh_thick, thick), mix(dry_thin, dry_thick, thick), dry);
	ALPHA = cover * mix(0.78, 1.0, thick) * v_alpha;
	// Wet, but not a mirror: under 0.25 the sky shows in it in bands.
	ROUGHNESS = mix(mix(0.5, 0.27, thick), 0.8, dry);
	// Seen edge-on, the highlight breaks into bands on mobile GPUs: fade it.
	SPECULAR = mix(0.4, 0.2, dry) * smoothstep(0.06, 0.4, abs(dot(NORMAL, VIEW)));
}
