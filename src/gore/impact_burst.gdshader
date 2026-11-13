shader_type spatial;
// The moment a round goes into or out of a body (src/gore/impact_bursts.gd):
// one quad per MultiMesh instance, facing the camera, drawn as a burst of
// thick blood thrown out of the wound: a lump at the wound, rays that shoot
// out to full length, then break into beads and are gone. Opaque and lit,
// like the drops (blood_drop.gdshader), so it reads as liquid, never as a
// cloud. Game time: in RX-9 slow motion it plays four times slower and the
// rays are seen growing; at full speed it is a sharp spurt of a few frames.
// The instance transform carries the burst, not a transform:
//   origin = the wound      X axis = direction it is thrown (unit)
//   Y axis = (start time, life, size in m)
//   Z axis = (fan: 1 thrown one way, 0 all round; seed; rise time)
render_mode skip_vertex_transform, cull_disabled, shadows_disabled;

uniform float now = 0.0;
uniform vec3 tint : source_color = vec3(0.40, 0.016, 0.016);

varying vec2 v_l;
varying float v_t;
varying float v_rise;
varying float v_fan;
varying float v_seed;

float h1(float n) {
	return fract(sin(n * 12.9898) * 43758.5453);
}

void vertex() {
	vec3 dir = MODEL_MATRIX[0].xyz;
	vec3 prm = MODEL_MATRIX[1].xyz;
	vec3 opt = MODEL_MATRIX[2].xyz;
	vec3 p0 = MODEL_MATRIX[3].xyz;
	float age = now - prm.x;
	v_t = age / max(prm.y, 0.001);
	v_seed = opt.y;
	v_rise = max(opt.z, 0.001) / max(prm.y, 0.001);
	if (age < 0.0 || v_t >= 1.0 || prm.z <= 0.0) {
		VERTEX = vec3(0.0, 0.0, 10.0);
		v_l = vec2(0.0);
		v_fan = 0.0;
	} else {
		vec3 pv = (VIEW_MATRIX * vec4(p0, 1.0)).xyz;
		vec3 dv = (VIEW_MATRIX * vec4(dir, 0.0)).xyz;
		float f = length(dv.xy);
		// Thrown at or away from the camera, a fan is seen end-on: draw it all round.
		v_fan = opt.x * smoothstep(0.3, 0.6, f);
		vec2 ax = f > 0.001 ? dv.xy / f : vec2(1.0, 0.0);
		vec2 q = VERTEX.xy + 0.5;
		// Fan: from just behind the wound out along the axis. Round: centred.
		float lx = mix(mix(-1.0, 1.0, q.x), mix(-0.18, 1.0, q.x), v_fan);
		float ly = (q.y * 2.0 - 1.0) * mix(1.0, 0.62, v_fan);
		v_l = vec2(lx, ly);
		vec2 perp = vec2(-ax.y, ax.x);
		pv.xy += (ax * lx + perp * ly) * prm.z;
		// Slightly toward the camera, so it isn't cut by the body it leaves.
		pv *= 0.985;
		VERTEX = pv;
	}
	NORMAL = vec3(0.0, 0.0, 1.0);
}

void fragment() {
	float t = v_t;
	// Out fast, then slowing (the sheet of blood pushed out by the round).
	float grow = 1.0 - pow(1.0 - clamp(t / v_rise, 0.0, 1.0), 2.0);
	float thin = 1.0 - smoothstep(0.55, 1.0, t);
	float r = length(v_l);
	float th = atan(v_l.y, v_l.x);
	// The lump at the wound, shrinking as it is spent.
	float core_r = 0.16 * (1.0 - 0.75 * smoothstep(0.0, 0.7, t)) * (1.0 + 0.18 * sin(5.0 * th + v_seed * 6.28));
	float cover = step(r, core_r * min(grow * 3.0, 1.0));
	float shade = 0.0;
	for (int i = 0; i < 9; i++) {
		float fi = float(i);
		float hs = h1(v_seed * 31.0 + fi * 7.13);
		float ai = v_fan > 0.5 ? (hs - 0.5) * 1.15 : (fi + 0.6 * hs) * 0.6981;
		float li = (0.45 + 0.55 * h1(v_seed * 17.0 + fi * 3.7)) * grow;
		float wi = (0.045 + 0.04 * h1(v_seed * 5.0 + fi * 11.1)) * thin;
		vec2 dir_i = vec2(cos(ai), sin(ai));
		vec2 perp_i = vec2(-dir_i.y, dir_i.x);
		float along = dot(v_l, dir_i);
		float across = abs(dot(v_l, perp_i));
		float k = clamp(along / max(li, 0.001), 0.0, 1.0);
		// A jet: broad where it leaves the lump, narrowing to a neck behind
		// its head. Late in its life it breaks into drops from the root out.
		float w = wi * mix(1.15, 0.35, sqrt(k));
		float freq = 6.0 + 6.0 * h1(v_seed * 3.0 + fi);
		float broken = smoothstep(0.4, 0.95, t) * (1.0 - 0.7 * k);
		float gaps = step(broken, fract(along * freq + hs * 3.0) * 0.999);
		float jet = step(0.0, along) * step(along, li) * step(across, w) * gaps;
		// Its head: a drop drawn out along the way it is going.
		vec2 hd = v_l - dir_i * (li - wi * 0.6);
		float head = step(length(vec2(dot(hd, dir_i) / 2.1, dot(hd, perp_i))), wi * 1.05);
		float c = max(jet, head);
		cover = max(cover, c);
		shade = max(shade, c * k);
	}
	if (cover < 0.5) {
		discard;
	}
	// Thinner toward the ends, so a little lighter there.
	ALBEDO = tint * (0.85 + 0.45 * shade);
	// A wet highlight that catches the light.
	NORMAL = normalize(vec3(v_l * 0.25, 1.0));
	ROUGHNESS = 0.18;
	SPECULAR = 0.65;
}
