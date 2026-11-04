shader_type spatial;
// Window and shop glass: dark, reflective (reflection probes), a little dirt.
// Same vertex layout as world.gdshader; drawn after the opaque world.
render_mode blend_mix, depth_draw_opaque, cull_back, specular_schlick_ggx;

uniform sampler2DArray albedo_arr : source_color, filter_linear_mipmap, repeat_enable;
uniform sampler2DArray orm_arr : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform float opacity = 0.35;

void fragment() {
	vec3 uvw = vec3(UV, floor(COLOR.a * 255.0 + 0.5));
	vec3 a = texture(albedo_arr, uvw).rgb * COLOR.rgb * 2.0;
	float dirt = texture(orm_arr, uvw).g;
	ALBEDO = a;
	ROUGHNESS = clamp(dirt, 0.03, 0.6);
	METALLIC = 0.0;
	SPECULAR = 0.8;
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 3.0);
	ALPHA = clamp(opacity + fres * 0.5 + dirt * 0.2, 0.0, 0.92);
}
