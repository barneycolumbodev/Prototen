class_name Stick
extends RefCounted
## Analog stick shaping: radial deadzone and response curve (CLAUDE.md §9.4).


## Returns the shaped stick vector, length 0..1.
## `inner`: radius below which input is ignored. `outer`: band at the rim that
## already counts as full tilt. `exponent`: 1 = linear, >1 = finer near centre.
static func shape(raw: Vector2, inner: float, outer: float, exponent: float) -> Vector2:
	var length: float = raw.length()
	if length <= inner or length <= 0.0:
		return Vector2.ZERO
	var span: float = maxf(1.0 - inner - outer, 0.001)
	var t: float = clampf((length - inner) / span, 0.0, 1.0)
	return raw / length * pow(t, exponent)
