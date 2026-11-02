shader_type spatial;
// Railgun ionized-air trail (src/weapons/ballistics.gd). Each segment is a
// 1x1 quad stretched along its local Y (MODEL_MATRIX[1] = the segment, its
// X column length = half width). The vertex stage turns it to face the
// camera around that axis, so it keeps its width even when you look straight
// down the shot (first person). White-hot core, saturated halo, faint beads
// drifting along it; it fades and spreads as it ages. Alpha-blended so it
// reads against bright skies too.
render_mode unshaded, blend_mix, cull_disabled, depth_draw_never, shadows_disabled, skip_vertex_transform;

uniform vec4 color : source_color = vec4(0.55, 0.85, 1.0, 1.0);
uniform float fade = 1.0;
uniform float age = 0.0;

varying vec3 world_pos;

void vertex() {
	vec3 axis = MODEL_MATRIX[1].xyz;
	float half_width = length(MODEL_MATRIX[0].xyz);
	vec3 p = MODEL_MATRIX[3].xyz + axis * VERTEX.y;
	vec3 cam = INV_VIEW_MATRIX[3].xyz;
	vec3 side = cross(normalize(axis), normalize(cam - p));
	side = length(side) > 0.0001 ? normalize(side) : vec3(1.0, 0.0, 0.0);
	world_pos = p + side * VERTEX.x * 2.0 * half_width;
	VERTEX = (VIEW_MATRIX * vec4(world_pos, 1.0)).xyz;
	NORMAL = vec3(0.0, 0.0, 1.0);
}

void fragment() {
	float d = abs(UV.x - 0.5) * 2.0;
	float core = pow(max(1.0 - d * 2.2, 0.0), 2.0) * max(0.0, 1.0 - age * 2.0);
	float halo = exp(-d * d * 3.5) - 0.03;
	float beads = 0.75 + 0.25 * sin(dot(world_pos, vec3(23.0, 29.0, 31.0)) - age * 25.0);
	vec3 hue = color.rgb * vec3(0.45, 0.8, 1.0);
	ALBEDO = mix(hue, vec3(1.0), clamp(core, 0.0, 1.0));
	ALPHA = clamp(max(halo, 0.0) * 0.9 * beads + core, 0.0, 1.0) * fade;
}
