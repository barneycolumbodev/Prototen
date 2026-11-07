shader_type spatial;
// GX-4 arm cannon beam (src/vfx/gauss_beam.gd), built once along -Z in metres
// (UV.x = distance from the muzzle) and clipped to this shot's length.
// - Core (UV2.x = 0): a white-hot line and a wider soft glow (UV2.y = 1),
//   turned to face the camera round the beam axis so it keeps its width
//   when you look straight down the shot (first person).
// - Helix (UV2.x = 1): a double corkscrew of ionized air whose band lies
//   flat to the axis, so from behind it reads as a spiral; it spreads
//   outward and lingers after the core has burnt out. Additive.
render_mode unshaded, blend_add, cull_disabled, depth_draw_never, shadows_disabled;

uniform vec4 color : source_color = vec4(0.45, 0.72, 1.0, 1.0);
uniform float age = 0.0;
uniform float life = 1.2;
uniform float beam_len = 50.0;
uniform float expand = 0.35;
uniform float core_width = 0.028;

varying float v_helix;
varying float v_glow;

void vertex() {
	v_helix = UV2.x;
	v_glow = UV2.y;
	if (v_helix < 0.5) {
		vec3 cam = (inverse(MODEL_MATRIX) * vec4(CAMERA_POSITION_WORLD, 1.0)).xyz;
		vec3 to_cam = cam - VERTEX;
		vec3 side = cross(vec3(0.0, 0.0, -1.0), to_cam);
		side = length(side) > 0.00001 ? normalize(side) : vec3(1.0, 0.0, 0.0);
		float w = mix(core_width, core_width * 6.0, v_glow) * (1.0 + age * 2.0);
		VERTEX += side * (UV.y * 2.0 - 1.0) * w;
	} else {
		VERTEX += NORMAL * expand * age;
	}
}

void fragment() {
	if (UV.x > beam_len) {
		discard;
	}
	float t = clamp(age / life, 0.0, 1.0);
	float across = abs(UV.y - 0.5) * 2.0;
	float far = clamp(1.0 - UV.x / 180.0, 0.3, 1.0);
	vec3 c;
	float a;
	if (v_helix < 0.5) {
		float soft = v_glow > 0.5 ? exp(-across * across * 3.0) * 0.55 : 1.0 - across * across;
		a = pow(1.0 - t, 4.0) * 1.8 * soft;
		c = mix(vec3(1.0), color.rgb, v_glow * 0.8);
	} else {
		float soft = 1.0 - across * across;
		float flick = 0.8 + 0.2 * sin(UV.x * 7.0 - age * 35.0);
		a = pow(1.0 - t, 1.5) * flick * soft;
		c = mix(vec3(1.0), color.rgb, 0.8);
	}
	// The first metre, right in front of the eye, is softened so it doesn't white out the screen.
	float near = smoothstep(0.0, 1.5, UV.x);
	ALBEDO = c * a * far * mix(0.4, 1.0, near);
}
