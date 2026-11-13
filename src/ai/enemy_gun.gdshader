shader_type spatial;
// Enemy guns (assets/weapons/enemy): one surface and one draw per gun
// instead of one per material (optimization overhaul C-08). The gun's
// untextured materials become columns of a small palette (GunFlatten):
// row 0 = linear albedo and metallic, row 1 = roughness and specular; UV.x
// is a vertex's column. Same values and shading as the imported
// double-sided StandardMaterial3D, checked pixel for pixel in the cloud.
// (Values passed from vertex() in custom varyings rendered without the
// ambient light in the lit pass of the Mobile renderer, so the column comes
// in through the built-in UV, as in the stock material.)
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx;

uniform sampler2D palette : filter_nearest, repeat_disable;

void fragment() {
	int col = int(UV.x + 0.5);
	vec4 a = texelFetch(palette, ivec2(col, 0), 0);
	vec4 b = texelFetch(palette, ivec2(col, 1), 0);
	ALBEDO = a.rgb;
	METALLIC = a.a;
	ROUGHNESS = b.x;
	SPECULAR = b.y;
}
