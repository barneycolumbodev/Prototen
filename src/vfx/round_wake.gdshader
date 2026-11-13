shader_type spatial;
// The wake of the operative's rounds while the RX-9 has the world slowed
// (src/vfx/round_wakes.gd; owner, 2026-11-13: "clearly see the round
// entering, exiting"). Grounded reading: the overclocked eye catches the
// shock-disturbed air behind a supersonic round. One quad per MultiMesh
// instance, turned round its axis to face the camera (as rail_trail does),
// from the tail to the round. A pale streak that thickens toward the round,
// a small hot point for the round itself, and once the round has stopped it
// fades in `fade` seconds of game time. Depth-tested, so it is hidden
// inside a body and seen again where the round comes out of it.
// The instance transform carries the wake:
//   origin = tail     X axis = tail -> round
//   Y axis = (stopped at (game time; 1e9 while flying), width in m, fade s)
render_mode unshaded, blend_mix, cull_disabled, depth_draw_never, shadows_disabled, skip_vertex_transform;

uniform float now = 0.0;
uniform vec4 color : source_color = vec4(0.86, 0.9, 0.95, 0.55);
uniform vec3 head_color : source_color = vec3(1.0, 0.86, 0.62);
// Never thinner than this × distance (about 1.5 px at 720p).
uniform float min_angular = 0.0024;

varying float v_along;
varying float v_len;
varying float v_fade;

void vertex() {
	vec3 axis = MODEL_MATRIX[0].xyz;
	vec3 prm = MODEL_MATRIX[1].xyz;
	vec3 tail = MODEL_MATRIX[3].xyz;
	float since = now - prm.x;
	v_fade = 1.0 - clamp(since / max(prm.z, 0.001), 0.0, 1.0);
	v_len = length(axis);
	v_along = VERTEX.y + 0.5;
	vec3 p = tail + axis * v_along;
	vec3 cam = INV_VIEW_MATRIX[3].xyz;
	vec3 side = v_len > 0.0001 ? cross(axis / v_len, normalize(cam - p)) : vec3(0.0);
	side = length(side) > 0.0001 ? normalize(side) : vec3(1.0, 0.0, 0.0);
	float w = max(prm.y, distance(cam, p) * min_angular) * mix(0.35, 1.0, v_along);
	if (v_fade <= 0.0 || v_len < 0.01) {
		p = vec3(0.0, -1000.0, 0.0);
	}
	VERTEX = (VIEW_MATRIX * vec4(p + side * VERTEX.x * w, 1.0)).xyz;
	NORMAL = vec3(0.0, 0.0, 1.0);
}

void fragment() {
	float d = abs(UV.x - 0.5) * 2.0;
	float body = exp(-d * d * 4.0);
	// The round: the last 12 cm, bright.
	float head = smoothstep(v_len - 0.12, v_len, v_along * v_len) * step(0.98, v_fade);
	ALBEDO = mix(color.rgb, head_color, head);
	ALPHA = clamp(body * color.a * (0.15 + 0.85 * v_along) + head * body, 0.0, 1.0) * v_fade;
}
