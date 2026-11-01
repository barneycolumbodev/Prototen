class_name Spring
extends RefCounted
## Damped spring for procedural motion (recoil, sway, bob, ADS, plates).
## Tuned with a natural frequency (Hz) and a damping ratio: 1 = critically
## damped (no overshoot), below 1 = bouncy. Values stay intuitive on the
## tuning menu. Stepped with the exact solution, so it behaves the same at
## 30, 60 or 120 fps.

var value: Vector3 = Vector3.ZERO
var velocity: Vector3 = Vector3.ZERO
var target: Vector3 = Vector3.ZERO
var frequency: float = 6.0
var damping: float = 0.8


func _init(p_frequency: float = 6.0, p_damping: float = 0.8) -> void:
	frequency = p_frequency
	damping = p_damping


func step(delta: float) -> Vector3:
	if delta <= 0.0:
		return value
	# Exact solution of the damped oscillator over `delta`: frame-rate independent,
	# never loses energy to integration error, never explodes.
	var w: float = TAU * frequency
	var z: float = damping
	var x0: Vector3 = value - target
	var v0: Vector3 = velocity
	var x: Vector3
	var v: Vector3
	if absf(z - 1.0) < 0.0001:
		var e: float = exp(-w * delta)
		var b: Vector3 = v0 + x0 * w
		x = (x0 + b * delta) * e
		v = (v0 - b * (w * delta)) * e
	elif z < 1.0:
		var wd: float = w * sqrt(1.0 - z * z)
		var e2: float = exp(-z * w * delta)
		var c: float = cos(wd * delta)
		var sn: float = sin(wd * delta)
		var b2: Vector3 = (v0 + x0 * (z * w)) / wd
		x = (x0 * c + b2 * sn) * e2
		v = ((b2 * wd - x0 * (z * w)) * c - (x0 * wd + b2 * (z * w)) * sn) * e2
	else:
		var root: float = sqrt(z * z - 1.0)
		var r1: float = -w * (z - root)
		var r2: float = -w * (z + root)
		var c1: Vector3 = (v0 - x0 * r2) / (r1 - r2)
		var c2: Vector3 = x0 - c1
		var e1: float = exp(r1 * delta)
		var e3: float = exp(r2 * delta)
		x = c1 * e1 + c2 * e3
		v = c1 * (r1 * e1) + c2 * (r2 * e3)
	value = target + x
	velocity = v
	return value


## Kicks the spring so that, starting at rest, it peaks at `peak` away from
## its target, whatever the damping (tuning values are peak amounts).
func kick(peak: Vector3) -> void:
	velocity += peak * (TAU * frequency / peak_gain(damping))


## Peak displacement of a spring at rest given velocity v0, in units of v0 / omega.
static func peak_gain(z: float) -> float:
	if absf(z - 1.0) < 0.0001:
		return exp(-1.0)
	if z < 1.0:
		var k: float = sqrt(1.0 - z * z)
		var phi: float = atan2(k, z)
		return exp(-z * phi / k) * sin(phi) / k
	var root: float = sqrt(z * z - 1.0)
	var r1: float = -(z - root)
	var r2: float = -(z + root)
	var t: float = log(r2 / r1) / (r1 - r2)
	return (exp(r1 * t) - exp(r2 * t)) / (r1 - r2)


func reset(to: Vector3 = Vector3.ZERO) -> void:
	value = to
	velocity = Vector3.ZERO
	target = to


func is_settled(epsilon: float = 0.0005) -> bool:
	return (value - target).length() < epsilon and velocity.length() < epsilon * 10.0
