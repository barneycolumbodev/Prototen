shader_type spatial;
// Blood drops in flight (src/gore/blood_drops.gd): one quad per MultiMesh
// instance. The instance transform is not a transform: it carries the drop's
// launch state, and the drop's place now comes from the closed-form path
// under gravity and linear air drag:
//   X axis = launch velocity (m/s)        origin = launch point
//   Y axis = (launch time, end time, size in m)
//   Z axis = (drag k in 1/s, seed, kind: 0 blood, 1 a bit of tissue)
// The quad faces the camera and is stretched along the drop's motion on
// screen by how far it moves during one exposure, so fast drops are
// streaks and slow ones are beads. Lit and opaque (alpha-tested): blood in a
// dark alley is dark, with a wet highlight where a lamp catches it.
render_mode skip_vertex_transform, cull_disabled, shadows_disabled;

uniform float now = 0.0;
uniform vec3 tint : source_color = vec3(0.36, 0.014, 0.015);
// Seconds of motion smeared into a streak.
uniform float exposure = 0.012;
// A drop is never drawn smaller than this × its distance (≈ 2 px at 720p).
uniform float min_angular = 0.003;
// Drawn this much bigger than the drop really is, so a spray reads on a
// phone at fighting distance (owner, 2026-11-13). Its stain keeps the real size.
uniform float draw_scale = 1.5;
uniform vec3 chunk_tint : source_color = vec3(0.16, 0.02, 0.022);

varying vec2 v_axis;
varying float v_chunk;
varying float v_seed;

void vertex() {
	vec3 v0 = MODEL_MATRIX[0].xyz;
	vec3 prm = MODEL_MATRIX[1].xyz;
	float k = max(MODEL_MATRIX[2].x, 0.05);
	vec3 p0 = MODEL_MATRIX[3].xyz;
	float t = now - prm.x;
	v_axis = vec2(1.0, 0.0);
	v_chunk = MODEL_MATRIX[2].z;
	v_seed = MODEL_MATRIX[2].y;
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
		float s = max(prm.z * draw_scale * clamp(t / 0.04, 0.3, 1.0), -pv.z * min_angular);
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
	// A bit of tissue is a lump, not a bead.
	float lump = v_chunk > 0.5 ? 1.0 + 0.3 * sin(atan(q.y, q.x) * 3.0 + v_seed * 20.0) : 1.0;
	d /= lump;
	if (d > 1.0) {
		discard;
	}
	// Rounded like a bead, so a light catches one side of it.
	vec2 bulge = (v_axis * q.x + vec2(-v_axis.y, v_axis.x) * -q.y) * 0.75;
	NORMAL = normalize(vec3(bulge, sqrt(max(1.0 - d * 0.5625, 0.05))));
	ALBEDO = v_chunk > 0.5 ? chunk_tint : tint;
	ROUGHNESS = v_chunk > 0.5 ? 0.45 : 0.16;
	SPECULAR = 0.7;
}
