class_name HarvesterSwarm
extends MultiMeshInstance3D
## The HV-3's harvesters in flight (docs/design.md §3.4e): a few hundred
## microdrones in one draw call. Nothing is moved on the CPU: each one's
## path is a function of time and its own random numbers in the vertex
## shader, and the part only feeds it a handful of uniforms per frame (where
## the vent is, the target's body as a capsule, the swarm clock, the phase
## times). Out of the vent in a stream that fans and bends, round the body
## in a shell that tightens as they eat, back to the palm in a stream that
## converges, darker and red with what they carry.

const SHADER: String = """
shader_type spatial;
render_mode world_vertex_coords, cull_disabled, shadows_disabled;

uniform vec3 vent = vec3(0.0);
uniform vec3 vent_dir = vec3(0.0, 0.0, -1.0);
uniform vec3 cap_a = vec3(0.0);
uniform vec3 cap_b = vec3(0.0, 1.8, 0.0);
uniform float cap_r = 0.3;
// Swarm clock (world seconds since launch) and its phases.
uniform float t = -1.0;
uniform float t_out = 0.3;
uniform float spread_out = 0.12;
uniform float t_ret = 1e6;
uniform float t_back = 0.3;
uniform float spread_back = 0.14;
// 0 = loose round the body, 1 = on it.
uniform float squeeze = 0.0;
uniform float fly_size = 0.014;
// Minimum size in pixels: px_per_m is metres per pixel per metre of distance.
uniform float min_px = 2.5;
uniform float px_per_m = 0.0019;
uniform vec4 eye_col : source_color = vec4(1.0, 0.22, 0.12, 1.0);
uniform vec4 full_col : source_color = vec4(0.5, 0.02, 0.015, 1.0);

varying float v_eye;
varying float v_full;

float h1(float n) {
	return fract(sin(n * 12.9898 + 78.233) * 43758.5453);
}

vec3 bez(vec3 a, vec3 b, vec3 c, float u) {
	return mix(mix(a, b, u), mix(b, c, u), u);
}

vec3 orbit(float tm, float id) {
	vec3 axis = cap_b - cap_a;
	float len = max(length(axis), 0.01);
	vec3 ax = axis / len;
	vec3 u = normalize(cross(ax, abs(ax.y) < 0.9 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0)));
	vec3 v = cross(ax, u);
	float r1 = h1(id * 1.3);
	float r2 = h1(id * 2.7);
	float r3 = h1(id * 3.1);
	float r4 = h1(id * 4.9);
	float dir = r4 < 0.5 ? -1.0 : 1.0;
	float ang = r2 * 6.2832 + dir * (2.6 + 3.2 * r3) * tm + 0.6 * sin(tm * 7.0 + r1 * 20.0);
	float hh = clamp(r1 * 1.08 - 0.04 + 0.06 * sin(tm * 5.3 + r3 * 30.0), -0.05, 1.05);
	// Narrower at the head and the feet.
	float taper = 0.55 + 0.45 * sqrt(clamp(sin(clamp(hh, 0.0, 1.0) * 3.1416), 0.0, 1.0));
	float rad = cap_r * taper * mix(2.0 + 0.9 * r4, 0.72 + 0.4 * r4, squeeze) + 0.035 * sin(tm * 13.0 + r3 * 40.0);
	vec3 p = cap_a + ax * (hh * len) + (u * cos(ang) + v * sin(ang)) * rad;
	return p + 0.025 * vec3(sin(tm * 31.0 + r2 * 50.0), sin(tm * 27.0 + r1 * 50.0), sin(tm * 29.0 + r4 * 50.0));
}

// The swarm moves as one animal: every harvester follows the same arc
// (bowed up and to the side), snaking, inside a tube that's pinched at the
// vent and at the body and fat in the middle.
vec3 stream(vec3 a, vec3 b, float k, float tm, float id, vec3 side, float sgn) {
	vec3 ab = b - a;
	float d = max(length(ab), 0.01);
	vec3 f = ab / d;
	vec3 r = normalize(cross(f, abs(f.y) < 0.95 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0)));
	vec3 u = cross(r, f);
	vec3 ctrl = mix(a, b, 0.45) + u * d * 0.06 + r * d * 0.08 * sgn + vent_dir * d * 0.06 * sgn;
	vec3 p = bez(a, ctrl, b, k);
	float bulge = sin(clamp(k, 0.0, 1.0) * 3.1416);
	float snake = sin(k * 9.0 - tm * 16.0 + h1(id * 0.37) * 0.8);
	p += (r * snake * 0.16 + u * cos(k * 7.0 - tm * 13.0) * 0.08) * bulge;
	p += side * (0.04 + 0.13 * bulge) * (0.3 + 0.7 * h1(id * 11.3));
	return p;
}

// Where harvester `id` is at swarm time `tm`; w = 0 when it's in the hive (not drawn).
vec4 where(float tm, float id) {
	float dl = h1(id * 5.7) * spread_out;
	float db = h1(id * 6.3) * spread_back;
	vec3 side = normalize(vec3(h1(id * 7.1) - 0.5, h1(id * 8.3) - 0.5, h1(id * 9.7) - 0.5) + vec3(0.0, 0.001, 0.0));
	if (tm < dl) {
		return vec4(vent, 0.0);
	}
	float left = t_ret + db;
	if (tm < left) {
		float tau = tm - dl;
		if (tau < t_out) {
			float k = tau / t_out;
			k = k * (2.0 - k);
			vec3 end = orbit(tm, id);
			return vec4(stream(vent, end, k, tm, id, side, 1.0), 1.0);
		}
		return vec4(orbit(tm, id), 1.0);
	}
	float k = (tm - left) / t_back;
	if (k >= 1.0) {
		return vec4(vent, 0.0);
	}
	k = k * k * (3.0 - 2.0 * k);
	vec3 start = orbit(left, id);
	return vec4(stream(start, vent, k, tm, id, side, -1.0), 1.0);
}

void vertex() {
	float id = float(INSTANCE_ID) + 1.0;
	vec4 now = where(t, id);
	vec4 before = where(t - 0.012, id);
	v_eye = COLOR.g;
	v_full = t > t_ret + h1(id * 6.3) * spread_back ? 1.0 : 0.0;
	vec3 fwd = now.xyz - before.xyz;
	fwd = length(fwd) > 1e-5 ? normalize(fwd) : vec3(0.0, 0.0, 1.0);
	vec3 right = normalize(cross(fwd, abs(fwd.y) < 0.95 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0)));
	vec3 up = cross(right, fwd);
	vec3 l = VERTEX;
	// Wings beat (COLOR.r marks a wing tip): too fast to see, a blur of positions.
	l.y += COLOR.r * sin(TIME * 260.0 + id * 3.0) * 0.45;
	float d = distance(now.xyz, CAMERA_POSITION_WORLD);
	float s = fly_size * max(1.0, min_px * d * px_per_m / fly_size) * now.w;
	VERTEX = now.xyz + (fwd * l.x + up * l.y + right * l.z) * s;
	NORMAL = normalize(fwd * NORMAL.x + up * NORMAL.y + right * NORMAL.z);
}

void fragment() {
	vec3 body = mix(vec3(0.05, 0.052, 0.058), full_col.rgb * 0.35, v_full);
	ALBEDO = body;
	METALLIC = 0.8;
	ROUGHNESS = mix(0.32, 0.2, v_full);
	EMISSION = (v_full > 0.5 ? full_col.rgb * 2.5 : eye_col.rgb * 4.0) * v_eye + eye_col.rgb * 0.08;
}
"""

var mat: ShaderMaterial


func _init() -> void:
	name = "HarvesterSwarm"
	top_level = true
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	custom_aabb = AABB(Vector3(-1000, -1000, -1000), Vector3(2000, 2000, 2000))
	var sh: Shader = Shader.new()
	sh.code = SHADER
	mat = ShaderMaterial.new()
	mat.shader = sh
	material_override = mat
	multimesh = MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.mesh = fly_mesh()
	visible = false


## `count` harvesters (instance transforms are unused: identity).
func setup(count: int, cfg: HarvesterHiveData) -> void:
	multimesh.instance_count = count
	for i: int in count:
		multimesh.set_instance_transform(i, Transform3D.IDENTITY)
	mat.set_shader_parameter(&"fly_size", cfg.fly_size)
	mat.set_shader_parameter(&"min_px", cfg.min_pixels)
	mat.set_shader_parameter(&"spread_out", cfg.launch_spread)
	mat.set_shader_parameter(&"spread_back", cfg.return_spread)
	mat.set_shader_parameter(&"eye_col", cfg.eye_color)
	mat.set_shader_parameter(&"full_col", cfg.full_color)


func set_param(key: StringName, value: Variant) -> void:
	mat.set_shader_parameter(key, value)


## One harvester, ~1 unit long along +X (scaled by fly_size in the shader):
## a faceted body, a head with a lit eye (COLOR.g), two wings (COLOR.r at the tips).
static func fly_mesh() -> ArrayMesh:
	var st: SurfaceTool = SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	# Body: an elongated octahedron, the head a smaller one in front.
	var parts: Array = [[Vector3(-0.5, 0, 0), Vector3(0.25, 0, 0), 0.16, 0.0], [Vector3(0.22, 0, 0), Vector3(0.5, 0, 0), 0.11, 1.0]]
	for p: Array in parts:
		var a: Vector3 = p[0]
		var b: Vector3 = p[1]
		var r: float = p[2]
		var eye: float = p[3]
		var mid: Vector3 = a.lerp(b, 0.4)
		var ring: Array[Vector3] = [mid + Vector3(0, r, 0), mid + Vector3(0, 0, r), mid + Vector3(0, -r, 0), mid + Vector3(0, 0, -r)]
		for k: int in 4:
			var c0: Vector3 = ring[k]
			var c1: Vector3 = ring[(k + 1) % 4]
			for tri: PackedVector3Array in [PackedVector3Array([a, c1, c0]), PackedVector3Array([b, c0, c1])]:
				var n: Vector3 = (tri[1] - tri[0]).cross(tri[2] - tri[0]).normalized()
				for v: Vector3 in tri:
					st.set_color(Color(0, eye, 0))
					st.set_normal(n)
					st.add_vertex(v)
	# Wings: two thin blades from the thorax, swept back.
	for s: float in [-1.0, 1.0]:
		var root0: Vector3 = Vector3(0.12, 0.08, 0.0)
		var root1: Vector3 = Vector3(-0.08, 0.08, 0.0)
		var tip: Vector3 = Vector3(-0.32, 0.12, 0.62 * s)
		var n2: Vector3 = Vector3.UP
		for v: Vector3 in [root0, root1, tip]:
			st.set_color(Color(1.0 if v == tip else 0.0, 0, 0))
			st.set_normal(n2)
			st.add_vertex(v)
	return st.commit()
