// World-space greybox grid: 1 m minor lines, 4 m major lines, picked per
// face by its dominant axis. Gives scale and speed cues in test rooms.
shader_type spatial;
render_mode cull_back;

uniform vec3 base_color : source_color = vec3(0.32, 0.33, 0.35);
uniform vec3 line_color : source_color = vec3(0.55, 0.57, 0.6);
uniform float roughness_value : hint_range(0.0, 1.0) = 0.85;

varying vec3 world_pos;
varying vec3 world_normal;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_normal = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

float grid_lines(vec2 coord, float width_px) {
	vec2 d = max(fwidth(coord), vec2(1e-4));
	vec2 g = abs(fract(coord - 0.5) - 0.5) / d;
	return 1.0 - clamp(min(g.x, g.y) - width_px + 1.0, 0.0, 1.0);
}

void fragment() {
	vec3 n = abs(world_normal);
	vec2 uv = n.y > n.x && n.y > n.z ? world_pos.xz : (n.x > n.z ? world_pos.zy : world_pos.xy);
	float minor = grid_lines(uv, 1.0) * 0.45;
	float major = grid_lines(uv / 4.0, 2.0);
	ALBEDO = mix(base_color, line_color, max(minor, major));
	ROUGHNESS = roughness_value;
}
