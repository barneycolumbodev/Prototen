shader_type spatial;
// Gun smoke puffs (src/vfx/barrel_smoke.gd): one camera-facing quad per
// MultiMesh instance. The instance transform carries the puff's place and
// size (origin, basis X length = size in m); COLOR.a its opacity now;
// INSTANCE_CUSTOM = (age 0..1, seed, spin, 0). Lit, so it is dark in a dark
// alley and bright where the muzzle flash or a lamp catches it.
render_mode skip_vertex_transform, cull_disabled, shadows_disabled, depth_draw_never, diffuse_lambert, specular_disabled;

uniform vec3 tint : source_color = vec3(0.72, 0.72, 0.74);

varying float v_seed;
varying float v_age;

void vertex() {
	float size = length(MODEL_MATRIX[0].xyz);
	vec3 centre = (VIEW_MATRIX * vec4(MODEL_MATRIX[3].xyz, 1.0)).xyz;
	float spin = INSTANCE_CUSTOM.z;
	vec2 c = VERTEX.xy;
	vec2 r = vec2(c.x * cos(spin) - c.y * sin(spin), c.x * sin(spin) + c.y * cos(spin));
	VERTEX = centre + vec3(r * size, 0.0);
	NORMAL = vec3(0.0, 0.0, 1.0);
	v_seed = INSTANCE_CUSTOM.y;
	v_age = INSTANCE_CUSTOM.x;
}

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float r = length(p);
	// Billows: two octaves of noise eat into the edge, more as the puff ages.
	vec2 q = UV * 3.0 + vec2(v_seed * 17.0, v_seed * 5.0 + v_age * 0.6);
	float n = noise(q) * 0.65 + noise(q * 2.3 + 4.0) * 0.35;
	float edge = 1.0 - smoothstep(0.25, 1.0, r + (n - 0.5) * (0.55 + 0.4 * v_age));
	ALBEDO = tint * (0.85 + 0.3 * n);
	ALPHA = clamp(edge * COLOR.a, 0.0, 1.0);
	ROUGHNESS = 1.0;
}
