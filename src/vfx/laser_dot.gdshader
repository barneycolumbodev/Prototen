shader_type spatial;
// Laser dot (WeaponLaser): a camera-facing disc with a saturated green core
// and a soft halo. Mixed over the surface rather than added, so it stays
// green on a white wall; the over-bright core blooms on the Mobile renderer.
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled;

uniform vec4 color : source_color = vec4(0.25, 1.0, 0.35, 1.0);
uniform float energy = 2.2;

void vertex() {
	// Billboard, keeping the node's scale (the dot's size in metres).
	float s = length(MODEL_MATRIX[0].xyz);
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(INV_VIEW_MATRIX[0] * s, INV_VIEW_MATRIX[1] * s, INV_VIEW_MATRIX[2] * s,
			MODEL_MATRIX[3]);
}

void fragment() {
	float r = length(UV - vec2(0.5)) * 2.0;
	float core = 1.0 - smoothstep(0.22, 0.42, r);
	float halo = (1.0 - smoothstep(0.35, 1.0, r)) * 0.55;
	vec3 hot = mix(color.rgb, vec3(0.85, 1.0, 0.85), 0.35);
	ALBEDO = mix(color.rgb, hot, core) * mix(1.0, energy, core);
	ALPHA = clamp(core + halo, 0.0, 1.0);
}
