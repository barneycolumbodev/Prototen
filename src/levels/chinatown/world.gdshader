shader_type spatial;
// Static world geometry (assets/levels/<map>): one draw call per chunk for any
// mix of surfaces.
// - Surfaces come from three texture arrays (raw_assets/env/materials):
//   COLOR.a * 255 = layer, COLOR.rgb * 2 = tint, UV = world-scale tiling.
// - Lighting is baked in Cycles (raw_assets/levels/<map>/bake.py) into a
//   lightmap on UV2, stored as sqrt(light / lm_max). It arrives as EMISSION,
//   so the lamps, neon and windows light the street without real-time lights.
//   Real-time lights (muzzle flashes) still add on top through ALBEDO.
// - CUSTOM0.x = emission strength (neon, lanterns, lit windows; the albedo
//   alpha masks it), CUSTOM0.y = 1 outdoors: the rain makes those surfaces
//   darker and glossier and fills hollows on the ground with rippling puddles.
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_lambert, specular_schlick_ggx;

uniform sampler2DArray albedo_arr : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2DArray normal_arr : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2DArray orm_arr : hint_default_white, filter_linear_mipmap, repeat_enable;
// Tiling value noise (puddle shapes) and per-cell white noise (ripples).
uniform sampler2D noise_tex : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform sampler2D hash_tex : filter_nearest, repeat_enable;
// 0 = no rain ripples in puddles (feature benchmark / low setting)
uniform float ripple_amount = 1.0;
uniform sampler2D lightmap : hint_default_black, filter_linear, repeat_disable;
uniform float lm_max = 8.0;
uniform float lm_gain = 1.0;
uniform float emission_gain = 1.0;
// 0 = dry, 1 = soaked (outdoor surfaces only)
uniform float rain : hint_range(0.0, 1.0) = 0.85;
uniform float puddles : hint_range(0.0, 1.0) = 0.55;
// 0 = normal, 1 = albedo only, 2 = lightmap only (debug captures)
uniform int debug_view = 0;

varying flat float v_layer;
varying vec2 v_data;
varying vec3 v_wpos;
varying vec3 v_wnrm;

// Rings of falling drops in a cell grid: returns a normal offset. Cell
// randoms come from a small white-noise texture (no sin() hashes: costly on
// Mali; playtest 2026-11-05).
vec2 ripples(vec2 p, float t) {
	vec2 acc = vec2(0.0);
	for (int k = 0; k < 2; k++) {
		vec2 q = p * (k == 0 ? 2.3 : 3.1) + float(k) * 7.31;
		vec2 cell = floor(q);
		vec2 f = fract(q) - 0.5;
		vec4 h = texelFetch(hash_tex, ivec2(mod(cell, 64.0)), 0);
		vec2 c = h.gb - 0.5;
		float ph = fract(t * 0.9 + h.r);
		vec2 d = f - c * 0.6;
		float r = length(d);
		float ring = sin((r - ph * 0.45) * 60.0) * smoothstep(0.08, 0.0, abs(r - ph * 0.45)) * (1.0 - ph);
		acc += d / (r + 1e-4) * ring;
	}
	return acc * 0.18;
}

void vertex() {
	v_layer = floor(COLOR.a * 255.0 + 0.5);
	v_data = CUSTOM0.xy;
	v_wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	v_wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec3 uvw = vec3(UV, v_layer);
	vec4 a = texture(albedo_arr, uvw);
	vec3 orm = texture(orm_arr, uvw).rgb;
	vec3 nm = texture(normal_arr, uvw).rgb;
	vec3 alb = a.rgb * COLOR.rgb * 2.0;
	float rough = orm.g;
	float metal = orm.b;

	// Rain: porous surfaces darken, everything gets glossier; puddles collect
	// where the ground is flat and low (texture cavities fill first).
	float wet = v_data.y * rain;
	float up = smoothstep(0.75, 0.97, v_wnrm.y);
	// The puddle noise only matters on wet ground facing up (puddle is 0
	// everywhere else): walls, ceilings and indoor surfaces skip both reads
	// (optimization overhaul W-01). Gradients are taken outside the branch so
	// the mip choice is the same as an unconditional read.
	float puddle = 0.0;
	vec2 pp = v_wpos.xz;
	vec2 pdx = dFdx(pp);
	vec2 pdy = dFdy(pp);
	if (up * wet > 0.0) {
		float pn = textureGrad(noise_tex, pp * 0.021, pdx * 0.021, pdy * 0.021).r * 0.65
				+ textureGrad(noise_tex, pp * 0.1, pdx * 0.1, pdy * 0.1).r * 0.35;
		puddle = up * wet * smoothstep(0.62 - puddles * 0.3, 0.7 - puddles * 0.3, pn + (1.0 - orm.r) * 0.35);
	}
	float darken = wet * (1.0 - metal) * mix(0.25, 0.45, up);
	alb *= 1.0 - darken;
	rough = mix(rough, rough * 0.4, wet);
	rough = mix(rough, 0.04, puddle);
	if (puddle > 0.02) {
		nm = mix(nm, vec3(0.5, 0.5, 1.0), puddle * 0.9);
		if (ripple_amount > 0.0) {
			nm.xy += ripples(v_wpos.xz, TIME) * puddle * ripple_amount;
		}
	}

	vec3 lm = texture(lightmap, UV2).rgb;
	lm = lm * lm * lm_max * lm_gain;
	float micro_ao = mix(1.0, orm.r, 0.85);

	ALBEDO = alb;
	ROUGHNESS = rough;
	METALLIC = metal;
	NORMAL_MAP = nm;
	SPECULAR = mix(0.5, 0.65, puddle);
	EMISSION = alb * lm * micro_ao + alb * a.a * v_data.x * emission_gain;
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
