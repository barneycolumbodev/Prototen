// Studio "sky" for the body-status stage: dark, with softbox strips that the
// gloss carapace reflects (key front right, two cool rims behind, a top box).
shader_type sky;

float strip(float az, float el, float az0, float width, float el0, float el1) {
	float a = abs(mod(az - az0 + PI, TAU) - PI);
	return exp(-pow(a / width, 2.0)) * smoothstep(el0, el0 + 0.08, el) * (1.0 - smoothstep(el1 - 0.08, el1, el));
}

void sky() {
	vec3 d = normalize(EYEDIR);
	float az = atan(d.x, d.z);
	float el = asin(clamp(d.y, -1.0, 1.0));
	vec3 col = vec3(0.012, 0.014, 0.018) + vec3(0.02, 0.024, 0.03) * smoothstep(-0.2, 0.6, el);
	col += vec3(1.0, 0.93, 0.85) * 1.2 * strip(az, el, 0.75, 0.16, 0.05, 1.0);
	col += vec3(0.55, 0.85, 1.0) * 1.6 * strip(az, el, -2.45, 0.1, -0.15, 0.9);
	col += vec3(0.85, 0.92, 1.0) * 1.3 * strip(az, el, 2.5, 0.1, -0.15, 0.9);
	col += vec3(0.9, 0.95, 1.0) * 0.35 * smoothstep(1.15, 1.3, el);
	COLOR = col;
}
