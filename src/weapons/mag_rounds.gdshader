shader_type spatial;
// The rounds in a clear magazine (the AUG's): one mesh, each round's UV.x is
// its slot from the top (0 = top) plus 0.25 on the brass case and 0.75 on the
// copper bullet (raw_assets/weapons/aug/build.py). Rounds in slots at or past
// `rounds` have been fired: their vertices collapse to nothing.
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_lambert, specular_schlick_ggx, shadows_disabled;

uniform float rounds = 30.0;
uniform vec3 brass : source_color = vec3(0.86, 0.66, 0.36);
uniform vec3 copper : source_color = vec3(0.78, 0.45, 0.30);

varying float v_kind;

void vertex() {
	float slot = floor(UV.x);
	v_kind = fract(UV.x);
	if (slot >= rounds) {
		VERTEX = vec3(0.0);
	}
}

void fragment() {
	float bullet = step(0.5, v_kind);
	ALBEDO = mix(brass, copper, bullet);
	METALLIC = 1.0;
	ROUGHNESS = mix(0.28, 0.34, bullet);
}
