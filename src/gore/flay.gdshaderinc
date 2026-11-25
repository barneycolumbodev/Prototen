// Flaying (docs/design.md §3.4e, the HV-3 Hive Gauntlet). The swarm strips a
// man of his clothes and skin and leaves the flesh underneath: striated red
// muscle running the way real muscle runs, white tendon and fascia at the
// joints and over the abdomen, a lipless grin of teeth, lidless eyes, yellow
// fat at the torn edges, wet blood in every groove.
//
// Included by the per-body special shaders (and the dog's coat, with
// FLAY_QUADRUPED defined: fibres along its spine, no human face): triad_holed, triad_tripo_holed):
// EnemyBody.set_flay() swaps them in on the one body being eaten, so the
// shader every other man wears pays nothing for it. The host defines vnoise().
//
// Everything is in rest space (CUSTOM0: metres, feet at y = 0, facing +Z, the
// triad rig's A-pose), so the pattern sticks to the body through animation
// and ragdoll, and the gibs (same material) are flayed too.

// 0 = untouched, 1 = picked clean.
uniform float flay_amount : hint_range(0.0, 1.0) = 0.0;
// Rest-space point where the swarm bit first: the eating spreads out from it.
uniform vec3 flay_origin = vec3(0.0, 1.3, 0.12);

// The triad rig's rest joints (left side; mirror x for the right).
const vec3 FL_ELBOW = vec3(0.3509, 1.1789, -0.0359);
const vec3 FL_WRIST = vec3(0.4836, 0.9536, 0.0064);
const vec3 FL_KNEE = vec3(0.102, 0.505, 0.012);
const vec3 FL_ANKLE = vec3(0.106, 0.088, -0.022);
// The face, from the head bone (1.572) and the head hitbox centre (1.665).
const float FL_EYE_Y = 1.672;
const float FL_EYE_X = 0.033;
const float FL_MOUTH_Y = 1.6;

// How far the flesh sinks once the skin and clothes are gone (m).
const float FL_SHRINK = 0.011;

// The way the muscle fibres run at rest position p. From position alone: the
// clothes' folds are still in the mesh, and their normals would scramble it.
vec3 flay_fibre(vec3 p) {
#ifdef FLAY_QUADRUPED
	// The dog (model space: +X forward): along the spine, down the legs.
	return p.y > 0.3 ? normalize(vec3(1.0, 0.25 * sin(p.x * 9.0), 0.0)) : vec3(0.0, 1.0, 0.0);
#endif
	float sx = p.x >= 0.0 ? 1.0 : -1.0;
	float ax = abs(p.x);
	vec3 f = vec3(0.0, 1.0, 0.0);
	if (p.y > 1.525) {
		// Head: the temporalis fans up and back over the skull; the masseter runs down the cheek.
		f = normalize(vec3(0.0, 1.0, -0.9 * smoothstep(1.66, 1.78, p.y)));
	} else if (ax > 0.2 && p.y > 0.7) {
		// Arm, along the bone in the A-pose.
		f = normalize(vec3(0.55 * sx, -0.83, 0.05));
	} else if (p.y < 0.66) {
		// Leg: down the bone; the sartorius crosses the front of the thigh.
		f = (p.y > 0.4 && p.z > 0.04) ? normalize(vec3(-0.35 * sx, 1.0, 0.0)) : vec3(0.0, 1.0, 0.0);
	} else if (p.y > 1.42 && ax < 0.09) {
		// Neck: the sternocleidomastoid, from behind the ear down to the collarbone.
		f = normalize(vec3(-0.45 * sx, 1.0, -0.3));
	} else if (p.z > 0.0) {
		if (p.y > 1.2) {
			// Pectoral: fans out from the sternum to the armpit.
			f = normalize(vec3(sx, 0.2 + 2.4 * (p.y - 1.3), 0.0));
		} else if (ax < 0.095) {
			// Rectus abdominis: straight up.
			f = vec3(0.0, 1.0, 0.0);
		} else {
			// External oblique: down and in.
			f = normalize(vec3(0.7 * sx, 1.0, 0.0));
		}
	} else {
		if (p.y > 1.3) {
			// Trapezius: across from the spine to the shoulder.
			f = normalize(vec3(sx, -0.5 - 3.0 * (p.y - 1.3), 0.0));
		} else if (ax < 0.055) {
			// Erector spinae: up the back either side of the spine.
			f = vec3(0.0, 1.0, 0.0);
		} else {
			// Latissimus: up and out to the armpit.
			f = normalize(vec3(sx, 0.9, 0.0));
		}
	}
	return f;
}

// Distance to the nearer side's joint (left joint mirrored for x < 0).
float flay_joint(vec3 p, vec3 j) {
	return length(vec3(abs(p.x), p.y, p.z) - j);
}

// Seam lines a body has where muscles meet: the six-pack, the linea alba, the
// lower border of the pectorals, the spine, the serratus fingers. 0..1.
float flay_anatomy(vec3 p, vec3 n, out float tendon) {
	float ax = abs(p.x);
	float groove = 0.0;
	tendon = 0.0;
#ifdef FLAY_QUADRUPED
	// The dog: tendon down the lower legs, and its teeth are already bare.
	tendon = (1.0 - smoothstep(0.12, 0.2, p.y)) * 0.7;
	return groove;
#endif
	if (p.z > 0.03 && p.y > 0.95 && p.y < 1.22 && ax < 0.1) {
		// Linea alba and the tendinous intersections: white bands round the six-pack.
		float alba = 1.0 - smoothstep(0.004, 0.009, ax);
		float k = fract((p.y - 0.985) / 0.076);
		float band = (1.0 - smoothstep(0.0, 0.07, abs(k - 0.5) - 0.42)) * step(p.y, 1.17);
		tendon = max(alba, band * (1.0 - smoothstep(0.085, 0.1, ax)));
		groove = max(groove, alba * 0.6 + band * 0.4);
		groove = max(groove, 1.0 - smoothstep(0.0, 0.006, abs(ax - 0.092)));
	}
	if (p.z > 0.03 && p.y > 1.14 && p.y < 1.3 && ax > 0.02 && ax < 0.19) {
		// The pectoral's lower edge, curving up toward the armpit.
		float edge = 1.19 + 1.6 * (ax - 0.08) * (ax - 0.08) + 0.05 * smoothstep(0.12, 0.19, ax);
		groove = max(groove, 1.0 - smoothstep(0.0, 0.009, abs(p.y - edge)));
	}
	if (p.z > -0.04 && p.z < 0.08 && ax > 0.11 && ax < 0.2 && p.y > 1.05 && p.y < 1.25) {
		// Serratus anterior: fingers over the ribs.
		float s = sin((p.y - 0.35 * ax) * 160.0);
		groove = max(groove, smoothstep(0.7, 1.0, s) * 0.8);
	}
	if (p.z < -0.04 && p.y > 0.9 && p.y < 1.45) {
		// The spine's furrow, and the thoracolumbar fascia over the low back.
		groove = max(groove, 1.0 - smoothstep(0.0, 0.012, ax));
		tendon = max(tendon, (1.0 - smoothstep(0.08, 0.14, ax)) * (1.0 - smoothstep(0.98, 1.08, p.y)));
	}
	// Joints: tendon over the wrists, the back of the hand, the elbow, the knee, the ankle.
	tendon = max(tendon, 1.0 - smoothstep(0.035, 0.07, flay_joint(p, FL_WRIST)));
	tendon = max(tendon, (ax > 0.44 && p.y < 1.0) ? 0.35 : 0.0);
	tendon = max(tendon, (1.0 - smoothstep(0.03, 0.06, flay_joint(p, FL_ELBOW))) * step(p.z, -0.04));
	tendon = max(tendon, (1.0 - smoothstep(0.035, 0.07, flay_joint(p, FL_KNEE))) * step(0.05, p.z));
	tendon = max(tendon, (1.0 - smoothstep(0.03, 0.055, flay_joint(p, FL_ANKLE))) * 0.8);
	return groove;
}

// The eating front: 1 where it has been eaten, 0 where the skin is still on;
// `edge` > 0 at the torn edge (fresh, bleeding), `fat` at the skin side of it.
float flay_mask(float amount, vec3 p, out float edge, out float fat) {
	float big = vnoise(p * 6.0 + vec3(7.3, 1.1, 4.2));
	float mid = vnoise(p * 19.0 + vec3(1.7, 9.4, 3.3));
	float fine = vnoise(p * 61.0);
	float spread = clamp(length(p - flay_origin) * 0.55, 0.0, 0.5);
	float order = 0.1 + 0.5 * (big * 0.35 + mid * 0.4 + fine * 0.25) + spread;
	// A few rags of skin and cloth hang on where the swarm left them.
	order += 0.6 * smoothstep(0.9, 0.94, vnoise(p * 30.0 + vec3(11.0, 2.0, 5.0))) * step(0.66, p.y);
	float front = amount * 1.22;
	float d = front - order;
	edge = (1.0 - smoothstep(0.0, 0.05, d)) * step(0.0, d) * (1.0 - smoothstep(0.85, 1.0, amount) * 0.6);
	fat = (1.0 - smoothstep(0.0, 0.016, -d)) * step(d, 0.0) * step(0.001, amount);
	return step(0.0, d);
}

// Flays the surface at rest position p (normal n). Rewrites col / rough /
// metal / wet where the flesh shows; returns the mask (0 skin .. 1 flesh) and,
// in `h`, a height for flay_bump().
float flay_apply(float amount, vec3 p, vec3 n, inout vec3 col, inout float rough, inout float metal, inout float wet, out float h) {
	h = 0.0;
	if (amount <= 0.0) {
		return 0.0;
	}
	float edge;
	float fat;
	float m = flay_mask(amount, p, edge, fat);
	// The skin-side edge: yellow subcutaneous fat, torn and lifting. What's
	// left of the skin and clothes soaks up the blood as the swarm works.
	col = mix(col, col * vec3(0.32, 0.06, 0.05), smoothstep(0.35, 1.0, amount) * 0.85);
	col = mix(col, vec3(0.66, 0.47, 0.26), fat * 0.6);
	if (m <= 0.0) {
		wet = max(wet, amount * 0.5);
		return 0.0;
	}
	vec3 f = flay_fibre(p);
	float along = dot(p, f);
	vec3 across = p - f * along;
	// Bundles ~3 cm across, split by dark crevices that run with the fibre;
	// fibres inside them in two octaves (~6 mm, ~2.5 mm), each faded out once
	// it gets smaller than a pixel (fwidth), so close up you see the grain and
	// at range it averages out instead of shimmering.
	float fasc = vnoise(across * 34.0 + vec3(along * 1.2, along * 0.9, along * 1.1));
	vec3 q1 = across * 160.0 + vec3(along * 5.0);
	vec3 q2 = across * 400.0 + vec3(along * 9.0, along * 8.0, along * 10.0);
	float k1 = 1.0 - smoothstep(0.4, 1.2, length(fwidth(q1)));
	float k2 = 1.0 - smoothstep(0.4, 1.2, length(fwidth(q2)));
	float streak = mix(0.5, vnoise(q1), k1) * 0.62 + mix(0.5, vnoise(q2), k2) * 0.38;
	float crevice = 1.0 - smoothstep(0.0, 0.04, abs(fasc - 0.5));
	float belly = smoothstep(0.15, 0.85, fasc);
	float tendon;
	float seams = flay_anatomy(p, n, tendon);
	// Muscle groups part along seams of their own as well.
	float g = vnoise(p * 6.0 + vec3(3.1, 0.7, 5.5));
	float groove = max(seams, (1.0 - smoothstep(0.0, 0.02, abs(g - 0.5))) * 0.55);
	// Thin fascia laid over some of the muscle.
	float sheet = smoothstep(0.8, 0.9, vnoise(p * 5.0 + vec3(2.0, 8.0, 1.0))) * 0.3;

	float lit = belly * 0.45 + smoothstep(0.2, 0.8, streak) * 0.55;
	vec3 meat = mix(vec3(0.17, 0.016, 0.016), vec3(0.56, 0.095, 0.07), lit);
	meat = mix(meat, vec3(0.72, 0.29, 0.23), smoothstep(0.66, 0.9, streak) * belly * 0.35);
	meat = mix(meat, vec3(0.07, 0.005, 0.005), crevice * 0.7);
	vec3 white = vec3(0.74, 0.65, 0.57) * (0.8 + 0.35 * streak);
	meat = mix(meat, white, max(tendon * 0.85, sheet));
	meat = mix(meat, vec3(0.06, 0.004, 0.004), groove * 0.9);
	float rgh = mix(0.68 - 0.22 * streak, 0.45, tendon);

	// Head: lidless eyes and a lipless grin.
#ifndef FLAY_QUADRUPED
	if (p.y > 1.525 && n.z > 0.35 && p.z > 0.02) {
		float ex = abs(abs(p.x) - FL_EYE_X);
		float ey = p.y - FL_EYE_Y;
		float er = length(vec2(ex, ey * 1.25));
		if (er < 0.0118) {
			// A bloody socket rim, then the bare eyeball: yellowed, veined, a dark iris, a wet shine.
			float vein = smoothstep(0.8, 0.95, vnoise(vec3(p.x * 900.0, p.y * 900.0, 3.0)));
			vec3 eye = mix(vec3(0.66, 0.56, 0.5), vec3(0.45, 0.06, 0.05), vein * smoothstep(0.004, 0.008, er));
			float r0 = length(vec2(ex, ey));
			eye = mix(eye, vec3(0.2, 0.12, 0.06), 1.0 - smoothstep(0.005, 0.006, r0));
			eye = mix(eye, vec3(0.01), 1.0 - smoothstep(0.0018, 0.0026, r0));
			float lid = smoothstep(0.0085, 0.0118, er);
			meat = mix(eye, vec3(0.12, 0.0, 0.0), lid);
			rgh = mix(0.05, 0.3, lid);
			groove = lid * 0.5;
			tendon = 0.0;
		}
		float mx = abs(p.x);
		float my = p.y - FL_MOUTH_Y;
		if (mx < 0.04 && abs(my) < 0.017) {
			// Upper and lower rows, each tooth its own block, black between them; the gums above and below.
			float cols = fract(p.x / 0.0078 + 0.5);
			float gap = 1.0 - smoothstep(0.08, 0.16, abs(cols - 0.5) - 0.34);
			float bite = 1.0 - smoothstep(0.0008, 0.0016, abs(my));
			float gum = smoothstep(0.0105, 0.013, abs(my));
			float side = smoothstep(0.03, 0.04, mx);
			vec3 tooth = vec3(0.86, 0.81, 0.67) * (0.9 + 0.12 * vnoise(p * 400.0));
			tooth = mix(tooth, vec3(0.03, 0.0, 0.0), max(gap * 0.9, bite));
			tooth = mix(tooth, vec3(0.5, 0.1, 0.1), gum);
			meat = mix(tooth, meat, side);
			rgh = mix(0.18, rgh, max(side, gum));
			groove = mix(max(gap, bite), groove, side);
			tendon = mix(0.0, tendon, side);
		}
	}

#endif
	// Fresh blood: pooled in the grooves, a wet film over the rest, bright at the torn edge.
	float pool = smoothstep(0.55, 0.78, vnoise(p * 13.0 + vec3(4.0, 0.5, 2.0)));
	float blood = max(groove * 0.7, pool * 0.6);
	meat = mix(meat, vec3(0.2, 0.005, 0.005), blood * 0.7);
	meat = mix(meat, vec3(0.45, 0.02, 0.015), edge);

	col = meat;
	rough = rgh;
	metal = 0.0;
	wet = max(wet, 0.12 + 0.7 * max(blood * blood, edge));
	h = belly * 0.55 + (streak - 0.5) * 0.7 + tendon * 0.3 - crevice * 0.3 - groove * 0.8 - edge * 0.4;
	return m;
}

// Perturbs the view-space normal by the screen-space slope of height h (m ×
// strength): the striations and seams catch the light without a texture.
vec3 flay_bump(vec3 normal, vec3 vertex, float h, float strength) {
	vec3 dpdx = dFdx(vertex);
	vec3 dpdy = dFdy(vertex);
	float hx = dFdx(h) * strength;
	float hy = dFdy(h) * strength;
	vec3 r1 = cross(dpdy, normal);
	vec3 r2 = cross(normal, dpdx);
	float det = dot(dpdx, r1);
	vec3 grad = sign(det) * (hx * r1 + hy * r2);
	return normalize(abs(det) * normal - grad);
}
