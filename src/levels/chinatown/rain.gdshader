shader_type spatial;
// Rain streaks, camera-facing but upright. Drops above a roof (roof_map: the
// highest solid surface per 1 m cell) vanish once they fall below it, so it
// doesn't rain inside the market or the restaurant.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec4 color : source_color = vec4(0.62, 0.66, 0.75, 0.22);
uniform sampler2D roof_map : filter_nearest, repeat_disable;
uniform vec2 roof_origin = vec2(-60.0, -50.0);
uniform vec2 roof_size = vec2(120.0, 110.0);

varying float hide;

void vertex() {
	vec3 centre = MODEL_MATRIX[3].xyz;
	vec2 ruv = (centre.xz - roof_origin) / roof_size;
	float roof = -50.0;
	if (ruv.x >= 0.0 && ruv.y >= 0.0 && ruv.x <= 1.0 && ruv.y <= 1.0) {
		roof = texture(roof_map, ruv).r;
	}
	hide = step(centre.y, roof);
	// upright billboard: keep Y, face the camera around it
	vec3 cam = INV_VIEW_MATRIX[3].xyz;
	vec3 to_cam = normalize(vec3(cam.x - centre.x, 0.0, cam.z - centre.z));
	vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), to_cam));
	vec3 w = centre + right * VERTEX.x + vec3(0.0, 1.0, 0.0) * VERTEX.y;
	POSITION = PROJECTION_MATRIX * VIEW_MATRIX * vec4(w, 1.0);
}

void fragment() {
	float edge = 1.0 - abs(UV.x - 0.5) * 2.0;
	float fade = smoothstep(0.0, 0.3, UV.y) * smoothstep(1.0, 0.6, UV.y);
	ALBEDO = color.rgb;
	ALPHA = color.a * edge * fade * (1.0 - hide);
}
