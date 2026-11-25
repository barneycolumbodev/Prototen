shader_type spatial;
// Legacy wardrobe enemy shader with plasma burn-through holes (EnemyBody.add_hole) and the HV-3 flaying (EnemyBody.set_flay).
render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_lambert, specular_schlick_ggx;

uniform sampler2D base_tex : source_color, filter_linear_mipmap;
uniform sampler2D orm_tex : hint_default_white, filter_linear_mipmap;
uniform sampler2D normal_tex : hint_normal, filter_linear_mipmap;
uniform sampler2D mask_tex : hint_default_black, filter_linear_mipmap;
uniform sampler2D skin_tex : hint_default_black, filter_linear_mipmap;
uniform sampler2D prints_tex : hint_default_black, filter_linear_mipmap, repeat_enable;
uniform vec3 tint_main[8];
uniform vec3 tint_trim[8];
uniform int print_id[8];
uniform vec3 print_a[8];
uniform vec3 print_b[8];
uniform float print_size = 0.24;
uniform vec3 skin_tint = vec3(1.0);
uniform int tattoo_bits[3];
uniform vec3 ink_color : source_color = vec3(0.035, 0.05, 0.06);
uniform int beard = 0;
uniform vec4 holes[4];
uniform vec4 hole_dirs[4];
uniform int hole_count = 0;
uniform vec4 wounds[8];
uniform float wound_age[8];
uniform int wound_count = 0;
uniform float char_amount : hint_range(0.0, 1.0) = 0.0;
uniform float bloodied : hint_range(0.0, 1.0) = 0.0;
uniform vec3 rim_color : source_color = vec3(0.62, 0.72, 0.85);
uniform float rim_strength = 0.8;
uniform float rim_alive : hint_range(0.0, 1.0) = 1.0;
uniform float fill_light = 0.3;
uniform int severed_mask = 0;
uniform float skin_inset = 0.006;
uniform float slot_inset[8];
uniform float cover_arm = 0.0;
uniform float cover_leg = 0.0;
uniform float inset_torso = 0.0;
uniform float inset_limb = 0.0;
const vec3 J_SHOULDER = vec3(0.172, 1.418, -0.018);
const vec3 J_ELBOW = vec3(0.3509, 1.1789, -0.0359);
const vec3 J_WRIST = vec3(0.4836, 0.9536, 0.0064);
const vec3 J_HIP = vec3(0.092, 0.93, 0.0);
const vec3 J_KNEE = vec3(0.102, 0.505, 0.012);
const vec3 J_ANKLE = vec3(0.106, 0.088, -0.022);
uniform int debug_view = 0;

varying vec3 rest_pos;
varying vec3 rest_nrm;
varying float v_slot;

const float NEUTRAL = 0.2140;

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

#include "res://src/gore/flay.gdshaderinc"

float limb_s(vec3 p, vec3 a, vec3 b, vec3 c) {
	vec3 ab = b - a;
	vec3 bc = c - b;
	float t1 = clamp(dot(p - a, ab) / dot(ab, ab), 0.0, 1.0);
	float t2 = clamp(dot(p - b, bc) / dot(bc, bc), 0.0, 1.0);
	float d1 = length(p - (a + ab * t1));
	float d2 = length(p - (b + bc * t2));
	return d1 < d2 ? t1 * length(ab) : length(ab) + t2 * length(bc);
}

float covered_inset(vec3 p) {
	vec3 q = vec3(abs(p.x), p.y, p.z);
	if (q.x > 0.175 && p.y > 0.75) {
		float s = limb_s(q, J_SHOULDER, J_ELBOW, J_WRIST);
		return inset_limb * smoothstep(0.0, 0.03, cover_arm - s);
	}
	if (p.y < 0.9) {
		float s = limb_s(q, J_HIP, J_KNEE, J_ANKLE);
		return inset_limb * smoothstep(0.0, 0.03, cover_leg - s);
	}
	return inset_torso;
}

void vertex() {
	rest_pos = CUSTOM0.xyz;
	rest_nrm = CUSTOM1.xyz;
	int code = int(CUSTOM0.w + 0.5);
	int seg = code % 16;
	v_slot = float(code / 16);
	if (code < 16 && rest_pos.y < 1.45 && abs(rest_pos.x) < 0.46) {
		VERTEX -= NORMAL * (skin_inset + covered_inset(rest_pos));
	}
	VERTEX -= NORMAL * slot_inset[clamp(code / 16, 0, 7)];
	VERTEX -= NORMAL * FL_SHRINK * flay_amount;
	if (seg > 0 && ((severed_mask >> (seg - 1)) & 1) != 0) {
		VERTEX = vec3(0.0);
	}
}

float print_value(int id, vec3 p, vec3 n) {
	vec3 w = abs(n) + 0.001;
	w /= (w.x + w.y + w.z);
	vec4 a = texture(prints_tex, p.xy / print_size);
	vec4 b = texture(prints_tex, p.zy / print_size);
	vec4 c = texture(prints_tex, p.xz / print_size);
	vec4 t = a * w.z + b * w.x + c * w.y;
	return id == 0 ? t.r : (id == 1 ? t.g : (id == 2 ? t.b : t.a));
}

int region(vec3 p) {
	if (abs(p.x) > 0.465 && p.y < 1.05) {
		return 5;
	}
	if (p.y > 1.43 && p.y < 1.62 && length(vec2(p.x, p.z + 0.01)) < 0.09) {
		return 4;
	}
	if (p.x > 0.17 && p.y < 1.47) {
		return 0;
	}
	if (p.x < -0.17 && p.y < 1.47) {
		return 1;
	}
	return p.z < 0.0 ? 3 : 2;
}

void fragment() {
	float hole_char = 0.0;
	float hole_ember = 0.0;
	for (int i = 0; i < 4; i++) {
		if (i >= hole_count) {
			break;
		}
		vec3 hd = rest_pos - holes[i].xyz;
		vec3 ax = hole_dirs[i].xyz;
		float along = dot(hd, ax);
		if (abs(along) > 0.4) {
			continue;
		}
		float rad = length(hd - ax * along);
		float hr = holes[i].w;
		if (rad < hr) {
			discard;
		}
		hole_char = max(hole_char, 1.0 - smoothstep(hr, hr * 1.9, rad));
		hole_ember = max(hole_ember, (1.0 - smoothstep(hr, hr * 1.35, rad)) * hole_dirs[i].w);
	}
	int slot = clamp(int(v_slot + 0.5), 0, 7);
	vec4 m = texture(mask_tex, UV);
	vec3 col = texture(base_tex, UV).rgb;
	vec3 main_c = tint_main[slot];
	int pid = print_id[slot];
	if (pid >= 0 && m.b > 0.01) {
		float pv = print_value(pid, rest_pos, rest_nrm);
		vec3 pc = mix(main_c, print_a[slot], smoothstep(0.2, 0.3, pv) * m.b);
		main_c = mix(pc, print_b[slot], smoothstep(0.7, 0.8, pv) * m.b);
	}
	col *= mix(vec3(1.0), main_c / NEUTRAL, m.r);
	col *= mix(vec3(1.0), tint_trim[slot] / NEUTRAL, m.g);
	if (m.a > 0.01) {
		vec3 skin = col * skin_tint;
		vec4 sk = texture(skin_tex, vec2(UV.x * 2.0, UV.y));
		int bit = 1 << region(rest_pos);
		float ink = 0.0;
		ink = max(ink, (tattoo_bits[0] & bit) != 0 ? sk.r : 0.0);
		ink = max(ink, (tattoo_bits[1] & bit) != 0 ? sk.g : 0.0);
		ink = max(ink, (tattoo_bits[2] & bit) != 0 ? sk.b : 0.0);
		skin = mix(skin, ink_color * (0.8 + 0.4 * skin_tint), ink * 0.9);
		if (beard >= 1) {
			skin = mix(skin, vec3(0.05, 0.045, 0.045), clamp((sk.a - 0.15) * 1.2, 0.0, 0.28));
		}
		if (beard >= 2) {
			skin = mix(skin, vec3(0.015, 0.013, 0.012), smoothstep(0.62, 0.75, sk.a) * 0.9);
		}
		col = mix(col, skin, m.a);
	}
	vec3 orm = texture(orm_tex, UV).rgb;
	float rough = orm.g;
	float metal = orm.b;
	float n1 = 0.0;
	if (bloodied > 0.0 || char_amount > 0.0) {
		n1 = vnoise(rest_pos * 90.0);
	}
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
		float len = length(d);
		float soak_r = r * (exit_w ? (1.7 + 1.6 * clamp(age / 3.0, 0.0, 1.0)) : (1.5 + 1.4 * clamp(age / 3.0, 0.0, 1.0)))
				* mix(1.35, 1.0, m.a);
		float pop = 1.0 + 0.45 * (1.0 - smoothstep(0.0, 0.12, age));
		float below = w.y - rest_pos.y;
		float run_len = r * (2.5 + 9.0 * clamp(age / 5.0, 0.0, 1.0));
		if (len >= max(soak_r * 1.2, r * 1.34 * pop) && (below < 0.0 || below >= run_len || length(d.xz) >= r * 0.5 + 0.006)) {
			continue;
		}
		vec3 tn = normalize(cross(rest_nrm, vec3(0.0, 1.0, 0.0)) + vec3(0.0, 0.0, 0.001));
		vec3 bn = cross(rest_nrm, tn);
		float ang = atan(dot(d, bn), dot(d, tn));
		float seed = fract(w.x * 91.7 + w.z * 37.3) * 6.2832;
		float lobe = exit_w ? 1.0 + 0.22 * sin(5.0 * ang + seed) + 0.12 * sin(9.0 * ang + 2.0 * seed)
				: 1.0 + 0.07 * sin(3.0 * ang + seed);
		float dist = len / (lobe * pop);
		float wick = 1.0 + 0.13 * sin(4.0 * ang + seed * 1.7) + 0.07 * sin(7.0 * ang + seed * 3.1);
		float soak = 1.0 - smoothstep(soak_r * 0.8, soak_r, len / wick);
		float wob = length(d.xz + vec2(0.004 * sin(rest_pos.y * 120.0), 0.0));
		float run = (1.0 - smoothstep(r * 0.22, r * 0.45, wob)) * step(0.0, below) * (1.0 - smoothstep(run_len * 0.7, run_len, below));
		float stain = max(soak, run * 0.9);
		vec3 soaked = mix(vec3(0.07, 0.003, 0.003), blood, smoothstep(r * 0.8, soak_r, len));
		col = mix(col, soaked, stain);
		wet = max(wet, stain);
		float rim = 1.0 - smoothstep(r * 0.92, r, dist);
		col = mix(col, exit_w ? vec3(0.42, 0.035, 0.03) : vec3(0.15, 0.012, 0.012), rim);
		if (exit_w) {
			col = mix(col, vec3(0.2, 0.01, 0.012), (1.0 - smoothstep(r * 0.55, r * 0.75, dist)) * rim);
		}
		float hole_r = r * (exit_w ? 0.42 : 0.5);
		float hole = 1.0 - smoothstep(hole_r * 0.85, hole_r, dist);
		col = mix(col, vec3(0.015, 0.0, 0.0), hole);
		wet = max(wet, rim);
	}
	col = mix(col, blood * (0.8 + 0.4 * n1), bloodied * smoothstep(0.35, 0.75, n1) * 0.8);
	wet = max(wet, bloodied * 0.6);
	float flay_h = 0.0;
	float flay_m = flay_apply(flay_amount, rest_pos, rest_nrm, col, rough, metal, wet, flay_h);
	float c = char_amount * smoothstep(0.25, 0.75, n1 + 0.35 * char_amount);
	col = mix(col, vec3(0.03, 0.025, 0.02), c);
	col = mix(col, vec3(0.025, 0.018, 0.012), hole_char);
	if (!FRONT_FACING) {
		col *= 0.35;
	}
	if (debug_view > 0) {
		vec4 dk = texture(skin_tex, vec2(UV.x * 2.0, UV.y));
		col = debug_view == 1 ? vec3(dk.a) : (debug_view == 2 ? dk.rgb : m.rgb + vec3(0.0, 0.0, m.a * 0.5));
	}
	if (flay_amount > 0.0) {
		NORMAL = normalize(mix(NORMAL, flay_bump(NORMAL, VERTEX, flay_h, 0.0022), flay_m));
	}
	ALBEDO = col;
	float facing = clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float fres = 1.0 - facing;
	float dist = length(VERTEX);
	float rim = fres * fres * fres * rim_strength * rim_alive * (0.25 + 0.75 * smoothstep(4.0, 24.0, dist)) * (1.0 - c);
	float fill = fill_light * (0.35 + 0.65 * facing) * (0.5 + 0.5 * smoothstep(3.0, 20.0, dist)) * (0.35 + 0.65 * rim_alive);
	EMISSION = rim_color * rim + col * fill * (1.0 - c) + vec3(1.0, 0.32, 0.05) * hole_ember * 4.0;
	ROUGHNESS = mix(mix(rough, 0.18, wet), 0.95, c);
	METALLIC = metal * (1.0 - wet);
	SPECULAR = mix(0.5, 0.65, wet);
	AO = mix(orm.r, 1.0, flay_m);
	AO_LIGHT_AFFECT = 0.4;
	NORMAL_MAP = mix(texture(normal_tex, UV).rgb, vec3(0.5, 0.5, 1.0), flay_m);
}
