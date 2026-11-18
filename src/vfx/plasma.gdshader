shader_type spatial;
// A ball of plasma (the SL-9 Slagger's charge and bolt, src/vfx/plasma_charge.gd,
// src/weapons/plasma_bolts.gd): additive, self-lit, a white-yellow core going
// to angry red-orange at the limb, churning (two scrolling noise reads, no
// sin hashes: costly on Mali). `heat` 0..1 pushes it whiter; `flicker`
// is set per frame from the script.
render_mode unshaded, blend_add, depth_draw_never, cull_back, shadows_disabled, fog_disabled;

uniform vec4 core_color : source_color = vec4(1.0, 0.85, 0.5, 1.0);
uniform vec4 hot_color : source_color = vec4(1.0, 0.32, 0.05, 1.0);
uniform sampler2D noise_tex : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform float intensity = 3.0;
uniform float heat : hint_range(0.0, 1.0) = 0.5;
uniform float churn = 1.0;
uniform float flicker = 1.0;
uniform float seed = 0.0;

void fragment() {
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	vec2 uv = UV * vec2(2.0, 1.0);
	float t = TIME * churn;
	float a = texture(noise_tex, uv + vec2(t * 0.31 + seed, t * 0.17)).r;
	float b = texture(noise_tex, uv * 2.3 + vec2(-t * 0.47, t * 0.29 + seed)).r;
	float turb = a * 0.6 + b * 0.4;
	// Granulation: cells of hotter plasma rising through it, like a star's face.
	float cells = smoothstep(0.45, 0.85, turb);
	float core = pow(facing, 1.6 + 2.0 * (1.0 - heat));
	vec3 col = mix(hot_color.rgb, core_color.rgb, clamp(core * 1.3 + cells * 0.35 - 0.15, 0.0, 1.0));
	col = mix(col, vec3(1.0, 0.97, 0.9), core * core * heat * 0.8);
	// The limb glows on past the edge (soft, so the silhouette isn't a hard disc).
	float limb = smoothstep(0.0, 0.35, facing);
	ALBEDO = col * intensity * flicker * (0.45 + 0.85 * turb) * limb;
}
