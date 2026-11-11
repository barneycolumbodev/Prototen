shader_type spatial;
// Triad enemy body (assets/characters/triad). One atlas for the whole man.
// - Jacket and trousers are tinted per role through the mask texture
//   (R = jacket, G = trousers, B = skin).
// - Wounds are painted here, not with decals: each wound is a point in the
//   mesh's rest pose (CUSTOM0 holds every vertex's rest position, filled by
//   EnemyBody), so they sit exactly on the skin or cloth and follow every
//   bend of the skinned body. Entry wounds are small and dark, exits torn
//   open; blood soaks out around them over time and runs down.
// - Burning chars the body.
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2D base_tex : source_color, filter_linear_mipmap;
uniform sampler2D orm_tex : hint_default_white, filter_linear_mipmap;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap;
uniform sampler2D mask_tex : hint_default_black, filter_linear_mipmap;
uniform vec3 jacket_tint : source_color = vec3(0.07, 0.072, 0.078);
uniform vec3 trousers_tint : source_color = vec3(0.16, 0.16, 0.15);
uniform vec3 skin_tint : source_color = vec3(1.0);
// xyz = rest position, w = radius (negative = exit wound).
uniform vec4 wounds[8];
// Seconds since each wound (blood soaks out and runs).
uniform float wound_age[8];
uniform int wound_count = 0;
uniform float char_amount : hint_range(0.0, 1.0) = 0.0;
// Overall blood on the body (heavy hits, lying in a pool).
uniform float bloodied : hint_range(0.0, 1.0) = 0.0;
// Readability (owner, 2026-11-05): a cool rim that outlines the silhouette
// against dark streets, growing with distance so far men still read on a
// phone screen and near ones look natural. Faded out on death.
uniform vec3 rim_color : source_color = vec3(0.62, 0.72, 0.85);
uniform float rim_strength = 0.8;
uniform float rim_alive : hint_range(0.0, 1.0) = 1.0;

varying vec3 rest_pos;

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

// Severed pieces (EnemyBody.SEGMENT_ORDER): bit i hides segment i + 1.
// CUSTOM0.w holds each vertex's segment in the merged mesh (0 = the body).
uniform int severed_mask = 0;

void vertex() {
	rest_pos = CUSTOM0.xyz;
	int seg = int(CUSTOM0.w + 0.5);
	if (seg > 0 && ((severed_mask >> (seg - 1)) & 1) != 0) {
		VERTEX = vec3(0.0);  // collapsed: nothing to draw
	}
}

void fragment() {
	vec4 m = texture(mask_tex, UV);
	vec3 col = texture(base_tex, UV).rgb;
	// Base is neutral grey (0.5) where tinted: tint * 2 gives the tint colour.
	col *= mix(vec3(1.0), jacket_tint * 2.0, m.r);
	col *= mix(vec3(1.0), trousers_tint * 2.0, m.g);
	col *= mix(vec3(1.0), skin_tint, m.b);
	vec3 orm = texture(orm_tex, UV).rgb;
	float rough = orm.g;
	float metal = orm.b;

	float n1 = vnoise(rest_pos * 90.0);
	float n2 = vnoise(rest_pos * 260.0);
	vec3 blood = vec3(0.22, 0.008, 0.008);
	float wet = 0.0;
	for (int i = 0; i < 8; i++) {
		if (i >= wound_count) {
			break;
		}
		vec4 w = wounds[i];
		float r = abs(w.w);
		bool exit_w = w.w < 0.0;
		float age = wound_age[i];
		vec3 d = rest_pos - w.xyz;
		float dist = length(d) * (0.75 + 0.5 * n1);
		// Blood soaking out (bigger on cloth than skin, grows for a few seconds).
		float soak_r = r * (2.2 + 2.6 * clamp(age / 4.0, 0.0, 1.0)) * (exit_w ? 1.5 : 1.0) * mix(1.4, 1.0, m.b);
		float soak = 1.0 - smoothstep(soak_r * 0.55, soak_r, dist);
		// A run of blood below the wound.
		float below = w.y - rest_pos.y;
		float wob = length(d.xz + vec2(0.006 * sin(rest_pos.y * 120.0), 0.0));
		float run_len = r * (3.0 + 10.0 * clamp(age / 5.0, 0.0, 1.0));
		float run = (1.0 - smoothstep(r * 0.25, r * 0.55, wob)) * step(0.0, below) * (1.0 - smoothstep(run_len * 0.6, run_len, below));
		float stain = max(soak, run * 0.9);
		col = mix(col, blood * (0.7 + 0.5 * n2), stain * 0.85);
		wet = max(wet, stain);
		// Torn flesh and the hole itself.
		float torn_r = r * (exit_w ? 1.0 : 0.55);
		float torn = 1.0 - smoothstep(torn_r * 0.75, torn_r, dist + 0.15 * r * n2);
		col = mix(col, vec3(0.38, 0.03, 0.025) * (0.7 + 0.6 * n2), torn);
		float hole = 1.0 - smoothstep(torn_r * 0.32, torn_r * 0.5, dist);
		col = mix(col, vec3(0.03, 0.0, 0.0), hole);
	}
	col = mix(col, blood * (0.8 + 0.4 * n1), bloodied * smoothstep(0.35, 0.75, n1) * 0.8);
	wet = max(wet, bloodied * 0.6);
	// Fire chars cloth and skin unevenly.
	float c = char_amount * smoothstep(0.25, 0.75, n1 + 0.35 * char_amount);
	col = mix(col, vec3(0.03, 0.025, 0.02), c);
	ALBEDO = col;
	float fres = 1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float dist = length(VERTEX);
	float rim = fres * fres * fres * rim_strength * rim_alive * (0.25 + 0.75 * smoothstep(4.0, 24.0, dist)) * (1.0 - c);
	EMISSION = rim_color * rim;
	ROUGHNESS = mix(mix(rough, 0.18, wet), 0.95, c);
	METALLIC = metal * (1.0 - wet);
	SPECULAR = mix(0.5, 0.65, wet);
	AO = orm.r;
	AO_LIGHT_AFFECT = 0.4;
	NORMAL_MAP = texture(normal_tex, UV).rgb;
}
