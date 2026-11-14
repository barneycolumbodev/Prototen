shader_type spatial;
// Cigarette smoke in the main menu: a soft, thin billboard wisp (the
// steam puff of the Chinatown map, lighter and bluer).
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled;

uniform vec3 tint : source_color = vec3(0.62, 0.66, 0.72);
uniform float opacity = 0.25;

varying float life;
varying float seed;

void vertex() {
	life = INSTANCE_CUSTOM.y;
	seed = INSTANCE_CUSTOM.x;
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(INV_VIEW_MATRIX[0], INV_VIEW_MATRIX[1], INV_VIEW_MATRIX[2], MODEL_MATRIX[3]);
	MODELVIEW_MATRIX = MODELVIEW_MATRIX * mat4(vec4(length(MODEL_MATRIX[0].xyz), 0.0, 0.0, 0.0), vec4(0.0, length(MODEL_MATRIX[1].xyz), 0.0, 0.0), vec4(0.0, 0.0, length(MODEL_MATRIX[2].xyz), 0.0), vec4(0.0, 0.0, 0.0, 1.0));
}

void fragment() {
	vec2 p = UV - 0.5;
	// A wisp: a soft blob bent by two slow waves, thinner when young.
	p.x += 0.12 * sin(p.y * 7.0 + seed * 9.0 + life * 4.0);
	float r = length(p * vec2(1.0 + (1.0 - life) * 0.8, 1.0)) * 2.0;
	float n = 0.7 + 0.3 * sin(UV.x * 9.0 + seed * 5.1) * sin(UV.y * 7.0 - seed * 2.3);
	float a = smoothstep(1.0, 0.1, r) * n * smoothstep(0.0, 0.08, life) * smoothstep(1.0, 0.35, life);
	ALBEDO = tint;
	ALPHA = a * opacity;
}
