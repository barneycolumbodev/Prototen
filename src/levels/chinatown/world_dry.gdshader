shader_type spatial;
// Static indoor world geometry (Hotel): same texture-array and baked lightmap
// pipeline as world.gdshader, without rain wetness, puddle noise, ripples or
// world-space derivatives/varyings.
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_lambert, specular_schlick_ggx;

uniform sampler2DArray albedo_arr : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2DArray normal_arr : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2DArray orm_arr : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform sampler2D lightmap : hint_default_black, filter_linear, repeat_disable;
uniform float lm_max = 8.0;
uniform float lm_gain = 1.0;
uniform float emission_gain = 1.0;
// 0 = normal, 1 = albedo only, 2 = lightmap only, 3 = UV (debug captures)
uniform int debug_view = 0;

varying flat float v_layer;
varying float v_emit;

void vertex() {
	v_layer = floor(COLOR.a * 255.0 + 0.5);
	v_emit = CUSTOM0.x;
}

void fragment() {
	vec3 uvw = vec3(UV, v_layer);
	vec4 a = texture(albedo_arr, uvw);
	vec3 orm = texture(orm_arr, uvw).rgb;
	vec3 nm = texture(normal_arr, uvw).rgb;
	vec3 alb = a.rgb * COLOR.rgb * 2.0;

	vec3 lm = texture(lightmap, UV2).rgb;
	lm = lm * lm * lm_max * lm_gain;
	float micro_ao = mix(1.0, orm.r, 0.85);

	ALBEDO = alb;
	ROUGHNESS = orm.g;
	METALLIC = orm.b;
	NORMAL_MAP = nm;
	SPECULAR = 0.5;
	EMISSION = alb * lm * micro_ao + alb * a.a * v_emit * emission_gain;
	if (debug_view == 1) {
		EMISSION = alb;
	} else if (debug_view == 3) {
		EMISSION = vec3(fract(UV), 0.0);
		ALBEDO = vec3(0.0);
	} else if (debug_view == 2) {
		EMISSION = lm * 0.5;
		ALBEDO = vec3(0.0);
	}
}
