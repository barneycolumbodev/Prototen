shader_type spatial;
// Blood drops in flight (src/gore/blood_drops.gd): one quad per MultiMesh
// instance. The instance transform is not a transform: it carries the drop's
// launch state, and the drop's place now comes from the closed-form path
// under gravity and linear air drag:
//   X axis = launch velocity (m/s)        origin = launch point
//   Y axis = (launch time, end time, size in m)
//   Z axis = (drag k in 1/s, seed, 0)
// The quad faces the camera and is stretched along the drop's motion on
// screen by how far it moves during one exposure, so fast drops are
// streaks and slow ones are beads. Lit and opaque (alpha-tested): blood in a
// dark alley is dark, with a wet highlight where a lamp catches it.
render_mode skip_vertex_transform, cull_disabled, shadows_disabled;

uniform float now = 0.0;
uniform vec3 tint : source_color = vec3(0.30, 0.012, 0.014);
// Seconds of motion smeared into a streak.
uniform float exposure = 0.012;
// A drop is never drawn smaller than this × its distance (≈ 1.5 px at 720p).
uniform float min_angular = 0.0022;

varying vec2 v_axis;

void vertex() {
	vec3 v0 = MODEL_MATRIX[0].xyz;
	vec3 prm = MODEL_MATRIX[1].xyz;
	float k = max(MODEL_MATRIX[2].x, 0.05);
	vec3 p0 = MODEL_MATRIX[3].xyz;
	float t = now - prm.x;
	v_axis = vec2(1.0, 0.0);
	if (t < 0.0 || now >= prm.y || prm.z <= 0.0) {
		// Not launched yet, or landed: nothing to draw.
		VERTEX = vec3(0.0, 0.0, 10.0);
	} else {
		vec3 vt = vec3(0.0, -9.8 / k, 0.0);
		float e = exp(-k * t);
		vec3 p = p0 + vt * t + (v0 - vt) * ((1.0 - e) / k);
		vec3 v = vt + (v0 - vt) * e;
		vec3 pv = (VIEW_MATRIX * vec4(p, 1.0)).xyz;
		vec3 vv = (VIEW_MATRIX * vec4(v, 0.0)).xyz;
		float sp = length(vv.xy);
		if (sp > 0.001) {
			v_axis = vv.xy / sp;
		}
		// It leaves the wound as a point and is full size 40 ms on.
		float s = max(prm.z * clamp(t / 0.04, 0.3, 1.0), -pv.z * min_angular);
		float smear = min(sp * exposure, s * 4.0);
		float half_len = 0.5 * (s + smear);
		float half_w = 0.5 * s * mix(1.0, 0.65, clamp(smear / (s * 4.0), 0.0, 1.0));
		vec2 q = VERTEX.xy * 2.0;
		pv.xy += v_axis * (q.x * half_len) + vec2(-v_axis.y, v_axis.x) * (q.y * half_w);
		VERTEX = pv;
	}
	NORMAL = vec3(0.0, 0.0, 1.0);
}

void fragment() {
	vec2 q = UV * 2.0 - 1.0;
	float d = dot(q, q);
	if (d > 1.0) {
		discard;
	}
	// Rounded like a bead, so a light catches one side of it.
	vec2 bulge = (v_axis * q.x + vec2(-v_axis.y, v_axis.x) * -q.y) * 0.75;
	NORMAL = normalize(vec3(bulge, sqrt(max(1.0 - d * 0.5625, 0.05))));
	ALBEDO = tint;
	ROUGHNESS = 0.16;
	SPECULAR = 0.7;
}
