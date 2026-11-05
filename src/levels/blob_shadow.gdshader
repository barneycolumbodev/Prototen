shader_type spatial;
// Soft contact shadow under a character on a baked map (the map's lighting
// is baked, so live characters cast nothing on it otherwise).
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform float strength = 0.55;

void fragment() {
	float r = length(UV - 0.5) * 2.0;
	ALBEDO = vec3(0.0);
	ALPHA = strength * smoothstep(1.0, 0.15, r) * smoothstep(1.0, 0.6, r);
}
