shader_type spatial;
// Recolours a baked texture set piece by piece (docs/design.md §3.7, the
// colour customizer). `tex_region` holds one id per texel (BodyColors
// channel + 1; tools/colors/build_regions.py); `paint[id]` is that
// channel's colour. The baked albedo keeps its detail: the new colour is
// scaled by how light the texel is against the channel's own base colour,
// so grime, edge wear and the weave still show. A part with no region map
// is painted as one piece (`single_region`).
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_lambert, specular_schlick_ggx;

// Plain trilinear: the arms and the suit face the camera, where anisotropic
// filtering adds cost and nothing visible (optimization overhaul C-04).
uniform sampler2D tex_albedo : source_color, hint_default_white, filter_linear_mipmap;
uniform sampler2D tex_orm : hint_default_white, filter_linear_mipmap;
uniform sampler2D tex_normal : hint_normal, filter_linear_mipmap;
uniform sampler2D tex_emission : source_color, hint_default_black, filter_linear_mipmap;
uniform sampler2D tex_region : hint_default_black, filter_nearest;
uniform vec4 albedo_factor = vec4(1.0);
uniform float rough_factor = 1.0;
uniform float metal_factor = 1.0;
uniform float emission_energy = 1.0;
uniform bool use_normal = true;
uniform int single_region = -1;
// rgb: colour (linear), a: how much of it (0 = keep the texture).
uniform vec4 paint[12];
// x: roughness (< 0 keeps the baked value), y: metallic (< 0 keeps it), z: the channel's reference luminance.
uniform vec4 surf[12];
// Lights: rgb = colour (linear), a = 1 when set.
uniform vec4 glow_paint = vec4(0.0);

// Lever actions (ViewmodelRig.set_hand_bend): the firing hand goes with the
// lever. Vertices are taken into weapon space, turned `bend_angle` (rad)
// about the line along Z through `bend_pivot`, weighted: full forward of
// bend_ramp.y, none behind bend_ramp.x (the forearm stays, the wrist
// bends), none past bend_ramp.z (the other hand), only below bend_max_y
// and right of bend_min_z. 0 = off (one uniform branch).
uniform float bend_angle = 0.0;
uniform mat4 bend_to_weapon;
uniform mat4 bend_from_weapon;
uniform vec3 bend_pivot;
uniform vec3 bend_ramp = vec3(-0.16, -0.085, 0.15);
uniform float bend_max_y = -0.015;
uniform float bend_min_z = -0.045;

void vertex() {
	if (bend_angle != 0.0) {
		vec3 p = (bend_to_weapon * vec4(VERTEX, 1.0)).xyz;
		float w = smoothstep(bend_ramp.x, bend_ramp.y, p.x) * (1.0 - smoothstep(bend_ramp.z - 0.02, bend_ramp.z, p.x));
		w *= 1.0 - smoothstep(bend_max_y - 0.02, bend_max_y + 0.02, p.y);
		w *= smoothstep(bend_min_z - 0.02, bend_min_z + 0.01, p.z);
		float a = bend_angle * w;
		float c = cos(a);
		float s = sin(a);
		vec3 d = p - bend_pivot;
		p = bend_pivot + vec3(d.x * c - d.y * s, d.x * s + d.y * c, d.z);
		VERTEX = (bend_from_weapon * vec4(p, 1.0)).xyz;
		vec3 n = mat3(bend_to_weapon) * NORMAL;
		n = vec3(n.x * c - n.y * s, n.x * s + n.y * c, n.z);
		NORMAL = normalize(mat3(bend_from_weapon) * n);
	}
}

void fragment() {
	vec4 a = texture(tex_albedo, UV) * albedo_factor;
	vec3 orm = texture(tex_orm, UV).rgb;
	float rough = orm.g * rough_factor;
	float metal = orm.b * metal_factor;
	// BodyColors sets single_region to 0 when no suit channel is painted, so
	// an unpainted suit skips the region read.
	int id = single_region;
	if (id < 0) {
		id = int(texture(tex_region, UV).r * 255.0 + 0.5);
	}
	id = clamp(id, 0, 11);
	vec4 p = paint[id];
	vec4 s = surf[id];
	if (p.a > 0.0) {
		float lum = dot(a.rgb, vec3(0.2126, 0.7152, 0.0722));
		float d = clamp(lum / max(s.z, 0.0004), 0.0, 2.5);
		a.rgb = mix(a.rgb, p.rgb * d, p.a);
	}
	if (s.x >= 0.0) {
		rough = s.x;
	}
	if (s.y >= 0.0) {
		metal = s.y;
	}
	vec3 em = vec3(0.0);
	if (emission_energy > 0.0) {
		em = texture(tex_emission, UV).rgb;
		if (glow_paint.a > 0.0) {
			float el = max(em.r, max(em.g, em.b));
			em = glow_paint.rgb * el;
		}
		em *= emission_energy;
	}
	ALBEDO = a.rgb;
	ROUGHNESS = rough;
	METALLIC = metal;
	AO = orm.r;
	if (use_normal) {
		NORMAL_MAP = texture(tex_normal, UV).rgb;
	}
	EMISSION = em;
}
