shader_type spatial;
// The attack dog's coat (docs/design.md §8.8b): Tripo's colour, ORM and
// normal maps, plus the readability the triad men get (triad.gdshader): a
// fill light from the viewer so a dark dog on a dark quay is never a black
// shape, and a cool rim that grows with distance. Both fade when it dies.
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2D base_tex : source_color, filter_linear_mipmap;
uniform sampler2D orm_tex : hint_default_white, filter_linear_mipmap;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap;
uniform vec3 rim_color : source_color = vec3(0.62, 0.72, 0.85);
uniform float rim_strength = 0.8;
uniform float rim_alive : hint_range(0.0, 1.0) = 1.0;
uniform float fill_light = 0.45;
// Blood on the coat from hits (0..1), darkening and wetting it.
uniform float bloodied : hint_range(0.0, 1.0) = 0.0;

void fragment() {
	vec3 col = texture(base_tex, UV).rgb;
	vec3 orm = texture(orm_tex, UV).rgb;
	col = mix(col, col * vec3(0.55, 0.12, 0.1), bloodied * 0.6);
	ALBEDO = col;
	NORMAL_MAP = texture(normal_tex, UV).rgb;
	ROUGHNESS = mix(orm.g, 0.25, bloodied * 0.5);
	METALLIC = orm.b;
	AO = orm.r;
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float fres = 1.0 - facing;
	float dist = length(VERTEX);
	float rim = fres * fres * fres * rim_strength * rim_alive * (0.25 + 0.75 * smoothstep(4.0, 24.0, dist));
	float fill = fill_light * (0.35 + 0.65 * facing) * (0.5 + 0.5 * smoothstep(3.0, 20.0, dist)) * (0.35 + 0.65 * rim_alive);
	EMISSION = rim_color * rim + col * fill;
}
