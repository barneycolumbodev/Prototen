shader_type spatial;
// Under-barrel laser beam (WeaponLaser): brightest at the emitter, fading
// along its length. Drawn over the scene (mix, with an over-bright colour that
// blooms on the Mobile renderer) so it reads on pale and dark surfaces alike.
// UV.x across the ribbon, UV.y from the emitter (0) to the dot (1).
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled;

uniform vec4 color : source_color = vec4(0.25, 1.0, 0.35, 1.0);
uniform float energy = 0.6;
// Beam length in metres, and 1 when it ends in open air (fade out completely).
uniform float length = 10.0;
uniform float open_ended = 0.0;

void fragment() {
	float across = 1.0 - abs(UV.x * 2.0 - 1.0);
	float core = smoothstep(0.0, 0.9, across);
	float metres = UV.y * length;
	// Bright for the first metre or so, then a long faint tail.
	float fall = 0.3 + 0.7 * exp(-metres * 1.2);
	fall *= mix(1.0, 1.0 - UV.y, open_ended);
	ALBEDO = color.rgb * (1.0 + 0.8 * core);
	ALPHA = clamp(energy * fall * core, 0.0, 1.0);
}
