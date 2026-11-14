shader_type spatial;
// Explosion puffs (ExplosionFx): one MultiMesh of low spheres for every live
// burst. INSTANCE_CUSTOM = (birth, seed, kind, life), birth and `now` in game
// seconds, so slow motion slows it. Kinds: 0 fireball (a white-hot flash that
// cools through yellow and orange, sooting over from the outside, and breaks
// up), 1 smoke lobe (lit soot that rises and swells, glowing from inside at
// first), 2 dust ring (flattened along the surface it burst on).
// Opaque pipeline: smoke and dust are see-through by dithering (a per-pixel
// threshold against their density), so nothing is blended or sorted and the
// phone's GPU draws each pixel once.
render_mode cull_back, depth_draw_opaque, diffuse_lambert, specular_disabled, shadows_disabled;

uniform float now = 0.0;

varying float v_t;
varying float v_life;
varying float v_kind;
varying float v_seed;
varying vec3 v_obj;

float hash13(vec3 p) {
	p = fract(p * 0.1031);
	p += dot(p, p.zyx + 31.32);
	return fract((p.x + p.y) * p.z);
}

float vnoise(vec3 p) {
	vec3 i = floor(p);
	vec3 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = mix(hash13(i), hash13(i + vec3(1.0, 0.0, 0.0)), f.x);
	float b = mix(hash13(i + vec3(0.0, 1.0, 0.0)), hash13(i + vec3(1.0, 1.0, 0.0)), f.x);
	float c = mix(hash13(i + vec3(0.0, 0.0, 1.0)), hash13(i + vec3(1.0, 0.0, 1.0)), f.x);
	float d = mix(hash13(i + vec3(0.0, 1.0, 1.0)), hash13(i + vec3(1.0, 1.0, 1.0)), f.x);
	return mix(mix(a, b, f.y), mix(c, d, f.y), f.z);
}

float fbm(vec3 p) {
	return 0.55 * vnoise(p) + 0.3 * vnoise(p * 2.07 + vec3(7.3, 1.7, 4.1)) + 0.15 * vnoise(p * 4.31 + vec3(2.9, 8.1, 0.6));
}

// Hot to cool: white-yellow, orange, deep red, nothing.
vec3 blackbody(float h) {
	vec3 c = vec3(0.85, 0.16, 0.02) * smoothstep(0.0, 0.25, h);
	c = mix(c, vec3(1.0, 0.48, 0.1), smoothstep(0.22, 0.6, h));
	c = mix(c, vec3(1.0, 0.82, 0.5), smoothstep(0.65, 1.1, h));
	return c;
}

// Interleaved gradient noise: a screen-space dither threshold in 0..1.
float dither(vec2 p) {
	return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715))));
}

void vertex() {
	v_t = now - INSTANCE_CUSTOM.r;
	v_seed = INSTANCE_CUSTOM.g;
	v_kind = INSTANCE_CUSTOM.b;
	v_life = INSTANCE_CUSTOM.a;
	vec3 n = normalize(VERTEX);
	v_obj = n;
	float t = max(v_t, 0.0);
	float grow;
	float lumps;
	float rise = 0.0;
	if (v_kind < 0.5) {
		grow = 0.15 + 0.85 * (1.0 - exp(-t / 0.035)) + 0.25 * t;
		lumps = 0.38;
	} else if (v_kind < 1.5) {
		grow = 0.35 + 0.65 * (1.0 - exp(-t / 0.4)) + 0.09 * t;
		rise = 1.1 * (1.0 - exp(-t / 1.3)) + 0.12 * t;
		lumps = 0.42;
	} else {
		grow = 0.06 + 0.94 * (1.0 - exp(-t / 0.1));
		lumps = 0.5;
	}
	float d = fbm(n * 2.6 + vec3(v_seed * 17.0, -t * 0.7, v_seed * 5.0));
	vec3 p = n * grow * (1.0 + lumps * (d - 0.5));
	float s = max(length(MODEL_MATRIX[0].xyz), 0.001);
	p.y += rise / s;
	if (v_t < 0.0 || v_t > v_life) {
		p = vec3(0.0);
	}
	VERTEX = p;
	NORMAL = n;
}

void fragment() {
	float t = max(v_t, 0.0);
	float u = t / max(v_life, 0.001);
	float coarse = fbm(v_obj * 3.4 + vec3(v_seed * 31.0, -t * 1.2, v_seed * 7.0));
	float fine = vnoise(v_obj * 11.0 + vec3(v_seed * 3.0, -t * 2.5, 0.0));
	float noise = coarse * 0.75 + fine * 0.25;
	float rim = 1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0);
	float edge = dither(FRAGCOORD.xy);
	vec3 albedo;
	vec3 emit = vec3(0.0);
	if (v_kind < 0.5) {
		// Fireball: hot in the middle of the view, cooler and sooty at the rim.
		float heat = exp(-t / 0.085) * (0.45 + 1.1 * noise) - rim * 0.45 - smoothstep(0.35, 1.0, u) * 0.3;
		heat = clamp(heat, 0.0, 1.4);
		emit = blackbody(heat) * (0.6 + 7.0 * heat * heat);
		emit += vec3(4.0, 3.6, 2.9) * max(0.0, 1.0 - t / 0.035) * 3.0;
		albedo = mix(vec3(0.025, 0.022, 0.02), vec3(0.11, 0.095, 0.08), fine);
		float body = 1.0 - smoothstep(0.35, 1.0, u + (0.5 - noise) * 0.5) - rim * rim * 0.4;
		if (body < edge) {
			discard;
		}
	} else if (v_kind < 1.5) {
		// Smoke: soft-edged by dithering its density; glows from the fire at first.
		float glow = exp(-t / 0.2) * smoothstep(0.45, 0.85, noise);
		emit = vec3(1.0, 0.38, 0.08) * glow * 2.5;
		albedo = mix(vec3(0.07, 0.065, 0.06), vec3(0.2, 0.19, 0.18), coarse) * (0.85 + 0.3 * fine);
		float density = smoothstep(0.22, 0.62, noise) * (1.0 - rim * rim) * (1.0 - smoothstep(0.25, 1.0, u));
		if (density * 0.95 < edge) {
			discard;
		}
	} else {
		// Dust thrown along the ground.
		albedo = mix(vec3(0.17, 0.155, 0.13), vec3(0.32, 0.29, 0.25), noise);
		float density = smoothstep(0.3, 0.7, noise) * (1.0 - rim) * (1.0 - smoothstep(0.08, 1.0, u));
		if (density * 0.9 < edge) {
			discard;
		}
	}
	ALBEDO = albedo;
	EMISSION = emit;
	ROUGHNESS = 1.0;
}
