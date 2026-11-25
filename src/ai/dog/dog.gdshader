shader_type spatial;
// The attack dog's coat (docs/design.md §8.8b): Tripo's colour, ORM and
// normal maps, plus the readability the triad men get (triad.gdshader): a
// fill light from the viewer so a dark dog on a dark quay is never a black
// shape, and a cool rim that grows with distance. Both fade when it dies.
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_lambert, specular_schlick_ggx;

uniform sampler2D base_tex : source_color, filter_linear_mipmap;
uniform sampler2D orm_tex : hint_default_white, filter_linear_mipmap;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap;
uniform vec3 rim_color : source_color = vec3(0.62, 0.72, 0.85);
uniform float rim_strength = 0.8;
uniform float rim_alive : hint_range(0.0, 1.0) = 1.0;
uniform float fill_light = 0.45;
// Blood on the coat from hits (0..1), darkening and wetting it.
uniform float bloodied : hint_range(0.0, 1.0) = 0.0;

// Rest position (CUSTOM0, AttackDog.set_flay gives the mesh one) for the flaying.
varying vec3 rest_pos;
varying vec3 rest_nrm;

float hash3(vec3 p) {
	p = fract(p * 0.3183099 + vec3(0.1, 0.2, 0.3));
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float vnoise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(hash3(i), hash3(i + vec3(1, 0, 0)), f.x),
			mix(hash3(i + vec3(0, 1, 0)), hash3(i + vec3(1, 1, 0)), f.x), f.y),
			mix(mix(hash3(i + vec3(0, 0, 1)), hash3(i + vec3(1, 0, 1)), f.x),
			mix(hash3(i + vec3(0, 1, 1)), hash3(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}

#define FLAY_QUADRUPED
#include "res://src/gore/flay.gdshaderinc"

void vertex() {
	rest_pos = CUSTOM0.xyz;
	rest_nrm = CUSTOM1.xyz;
	VERTEX -= NORMAL * FL_SHRINK * 0.6 * flay_amount;
}

void fragment() {
	vec3 col = texture(base_tex, UV).rgb;
	vec3 orm = texture(orm_tex, UV).rgb;
	col = mix(col, col * vec3(0.55, 0.12, 0.1), bloodied * 0.6);
	float rough = mix(orm.g, 0.25, bloodied * 0.5);
	float metal = orm.b;
	float wet = 0.0;
	float flay_h = 0.0;
	float flay_m = 0.0;
	if (flay_amount > 0.0) {
		flay_m = flay_apply(flay_amount, rest_pos, rest_nrm, col, rough, metal, wet, flay_h);
		NORMAL = normalize(mix(NORMAL, flay_bump(NORMAL, VERTEX, flay_h, 0.0022), flay_m));
		rough = mix(rough, 0.18, wet);
	}
	ALBEDO = col;
	NORMAL_MAP = mix(texture(normal_tex, UV).rgb, vec3(0.5, 0.5, 1.0), flay_m);
	ROUGHNESS = rough;
	METALLIC = metal;
	AO = mix(orm.r, 1.0, flay_m);
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float fres = 1.0 - facing;
	float dist = length(VERTEX);
	float rim = fres * fres * fres * rim_strength * rim_alive * (0.25 + 0.75 * smoothstep(4.0, 24.0, dist));
	float fill = fill_light * (0.35 + 0.65 * facing) * (0.5 + 0.5 * smoothstep(3.0, 20.0, dist)) * (0.35 + 0.65 * rim_alive);
	EMISSION = rim_color * rim + col * fill;
}
