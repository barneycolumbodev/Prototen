shader_type spatial;
// Blood splats and pools (src/gore/gore.gd): one quad per MultiMesh instance.
// INSTANCE_CUSTOM.r = atlas cell, .g = alpha (fades the oldest out).
render_mode blend_mix, depth_draw_never, cull_disabled, shadows_disabled;

uniform sampler2D atlas : source_color, filter_linear_mipmap, repeat_disable;
uniform float cells = 2.0;

varying vec2 v_cell;
varying float v_alpha;

void vertex() {
	float c = INSTANCE_CUSTOM.r;
	v_cell = vec2(mod(c, cells), floor(c / cells));
	v_alpha = INSTANCE_CUSTOM.g * COLOR.a;
}

void fragment() {
	vec4 t = texture(atlas, (UV + v_cell) / cells);
	ALBEDO = t.rgb * 0.75;
	ALPHA = clamp(t.a * 1.25, 0.0, 1.0) * v_alpha;
	// Wet: some gloss where it's thick, but blood is dark, not pink.
	ROUGHNESS = mix(0.6, 0.28, t.a);
	SPECULAR = 0.35;
}
