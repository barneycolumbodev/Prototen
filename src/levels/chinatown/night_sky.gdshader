shader_type sky;
// Overcast harbour night: deep blue overhead, the city's sodium glow on the
// cloud base and at the horizon, a ridge of dark hills, a hazy moon.

uniform vec3 zenith : source_color = vec3(0.035, 0.04, 0.07);
uniform vec3 horizon : source_color = vec3(0.3, 0.17, 0.11);
uniform vec3 cloud_lit : source_color = vec3(0.34, 0.2, 0.14);
uniform vec3 cloud_dark : source_color = vec3(0.06, 0.06, 0.085);
uniform vec3 hills : source_color = vec3(0.012, 0.012, 0.016);
uniform vec3 moon_dir = vec3(0.3, 0.5, 0.8);
uniform float brightness = 1.0;

float hash(vec2 p) { return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }
float noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}
float fbm(vec2 p) {
	float v = 0.0;
	float a = 0.5;
	for (int i = 0; i < 4; i++) {
		v += noise(p) * a;
		p = p * 2.03 + 11.7;
		a *= 0.5;
	}
	return v;
}

void sky() {
	vec3 d = EYEDIR;
	float y = d.y;
	vec3 c = mix(horizon, zenith, smoothstep(-0.02, 0.5, y));
	if (y > 0.0) {
		vec2 p = d.xz / (y + 0.12) * 0.9 + vec2(TIME * 0.004, TIME * 0.002);
		float n = fbm(p);
		float cover = smoothstep(0.38, 0.75, n);
		vec3 cc = mix(cloud_dark, cloud_lit, smoothstep(0.55, 0.0, y) * 0.9 + n * 0.2);
		c = mix(c, cc, cover * 0.9);
		// the moon behind thin cloud
		float m = dot(d, normalize(moon_dir));
		c += vec3(0.75, 0.8, 0.9) * smoothstep(0.99955, 0.9997, m) * (1.0 - cover * 0.8) * 2.5;
		c += vec3(0.25, 0.28, 0.35) * pow(max(m, 0.0), 120.0) * 0.35;
	}
	// hills on the far shore
	float az = atan(d.x, d.z);
	float ridge = 0.035 + 0.04 * fbm(vec2(az * 3.0, 1.0)) + 0.02 * noise(vec2(az * 12.0, 4.0));
	float hill = smoothstep(ridge + 0.002, ridge - 0.002, y) * step(-0.05, y);
	c = mix(c, hills + horizon * 0.15, hill);
	if (y < 0.0) {
		c = mix(horizon * 0.4, vec3(0.004, 0.005, 0.007), smoothstep(0.0, -0.15, y));
	}
	COLOR = c * brightness;
}
