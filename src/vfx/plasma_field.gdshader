shader_type spatial;
// The magnetic field holding a plasma charge (src/vfx/plasma_charge.gd):
// thin bands round the ball, broken into flickering dashes that crawl
// round it. `strain` 0..1 (near overload) makes them break up and jitter.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, shadows_disabled, fog_disabled;

uniform vec4 field_color : source_color = vec4(1.0, 0.55, 0.2, 1.0);
uniform sampler2D noise_tex : hint_default_white, filter_linear_mipmap, repeat_enable;
uniform float intensity = 2.0;
uniform float strain : hint_range(0.0, 1.0) = 0.0;
uniform float speed = 1.0;

void fragment() {
	float t = TIME * speed;
	float n = texture(noise_tex, vec2(UV.x * 3.0 + t * 0.6, UV.y * 0.5 + t * 0.13)).r;
	float dash = smoothstep(0.35 + 0.25 * strain, 0.65, n);
	float edge = 1.0 - abs(UV.y - 0.5) * 2.0;
	ALBEDO = field_color.rgb * intensity * dash * edge * (1.0 + strain * 1.5);
}
