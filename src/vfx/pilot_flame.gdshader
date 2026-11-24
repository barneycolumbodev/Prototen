shader_type spatial;
// Small flickering lighter pilot flame (Triad Flamer, left hand).
// Procedural teardrop flame on a camera-facing quad; zero textures, 1 draw call.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled;

uniform float now = 0.0;
uniform float flare = 1.0;

void vertex() {
	// Y-axis cylindrical billboard so the flame always stands upright in world space.
	vec3 origin = MODEL_MATRIX[3].xyz;
	vec3 to_cam = normalize(INV_VIEW_MATRIX[3].xyz - origin);
	vec3 up = vec3(0.0, 1.0, 0.0);
	vec3 right = normalize(cross(up, to_cam));
	vec3 fwd = cross(right, up);
	float sx = length(MODEL_MATRIX[0].xyz) * mix(1.0, 1.55, clamp(flare - 1.0, 0.0, 2.0) * 0.5);
	float sy = length(MODEL_MATRIX[1].xyz) * flare;
	vec3 p = VERTEX;
	// Gentle flame dance near the tip.
	float sway = sin(now * 27.0 + origin.x * 13.0) * 0.14 + sin(now * 43.0) * 0.07;
	p.x += sway * max(p.y, 0.0) * 1.4;
	vec3 world_pos = origin + right * (p.x * sx) + up * (p.y * sy) + fwd * (p.z * sx);
	POSITION = PROJECTION_MATRIX * VIEW_MATRIX * vec4(world_pos, 1.0);
}

void fragment() {
	// UV: x in 0..1, y = 0 at top, 1 at bottom of QuadMesh. Flip so v=0 is wick base, v=1 is tip.
	float u = (UV.x - 0.5) * 2.0;
	float v = 1.0 - UV.y;
	// Teardrop width narrows smoothly to a sharp point at v=1.
	float w = sin(clamp(v, 0.0, 1.0) * 3.14159) * pow(1.0 - clamp(v, 0.0, 1.0), 0.45) * 1.15;
	float d = abs(u) / max(w, 0.001);
	float body = smoothstep(1.0, 0.12, d) * smoothstep(0.0, 0.12, v) * smoothstep(1.0, 0.72, v);
	float flicker = 0.85 + 0.15 * sin(now * 38.0 + v * 6.0);
	float core = smoothstep(0.55, 0.0, d) * smoothstep(0.05, 0.25, v) * smoothstep(0.68, 0.28, v);
	float blue = smoothstep(0.6, 0.0, d) * smoothstep(0.02, 0.14, v) * smoothstep(0.32, 0.12, v);
	vec3 col = mix(vec3(1.0, 0.36, 0.04), vec3(1.0, 0.78, 0.25), smoothstep(0.85, 0.2, v));
	col = mix(col, vec3(1.0, 0.96, 0.8), core);
	col = mix(col, vec3(0.35, 0.62, 1.0), blue * 0.75);
	ALBEDO = col * (2.6 + 1.4 * flare) * flicker * body;
	ALPHA = clamp(body, 0.0, 1.0);
}
