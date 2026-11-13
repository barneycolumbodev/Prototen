shader_type spatial;
// Soft steam puff from drains and kitchen vents (billboarded particle).
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, shadows_disabled;

uniform vec3 tint : source_color = vec3(0.32, 0.33, 0.36);

// A puff the camera is inside (closer than this many of its own radii)
// fades out and stops drawing: from inside, one puff covers the whole
// screen several times over (optimization overhaul E-01).
uniform float near_fade_start = 1.2;
uniform float near_fade_end = 0.6;

varying float life;
varying float seed;
varying float near_fade;

void vertex() {
	life = INSTANCE_CUSTOM.y;
	seed = INSTANCE_CUSTOM.x;
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(INV_VIEW_MATRIX[0], INV_VIEW_MATRIX[1], INV_VIEW_MATRIX[2], MODEL_MATRIX[3]);
	float size = length(MODEL_MATRIX[0].xyz);
	// Half the quad is the puff's radius.
	float d = length((VIEW_MATRIX * vec4(MODEL_MATRIX[3].xyz, 1.0)).xyz) / max(size * 0.5, 1e-4);
	near_fade = smoothstep(near_fade_end, near_fade_start, d);
	float shown = near_fade > 0.0 ? 1.0 : 0.0;  // fully faded: no pixels at all
	MODELVIEW_MATRIX = MODELVIEW_MATRIX * mat4(vec4(size * shown, 0.0, 0.0, 0.0), vec4(0.0, length(MODEL_MATRIX[1].xyz) * shown, 0.0, 0.0), vec4(0.0, 0.0, length(MODEL_MATRIX[2].xyz) * shown, 0.0), vec4(0.0, 0.0, 0.0, 1.0));
}

void fragment() {
	float r = length(UV - 0.5) * 2.0;
	// Cheap puff (big overlapping quads: every instruction counts on Mali).
	float n = 0.75 + 0.25 * sin(UV.x * 5.0 + seed * 6.3) * sin(UV.y * 4.0 - seed * 3.1);
	float a = smoothstep(1.0, 0.2, r) * n * smoothstep(0.0, 0.15, life) * smoothstep(1.0, 0.5, life);
	ALBEDO = tint;
	ALPHA = a * 0.22 * near_fade;
}
