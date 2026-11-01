class_name Spring
extends RefCounted
## Damped spring for procedural motion (recoil, sway, bob, ADS, plates).
## Tuned with a natural frequency (Hz) and a damping ratio: 1 = critically
## damped (no overshoot), below 1 = bouncy. Values stay intuitive on the
## tuning menu. Substeps keep stiff springs stable at low frame rates.

const MAX_STEP: float = 1.0 / 240.0

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
	var omega: float = TAU * frequency
	var k: float = omega * omega
	var c: float = 2.0 * damping * omega
	var steps: int = maxi(1, ceili(delta / MAX_STEP))
	var dt: float = delta / steps
	for i: int in steps:
		var accel: Vector3 = -k * (value - target) - c * velocity
		velocity += accel * dt
		value += velocity * dt
	return value


## Kicks the spring so that, starting at rest, it peaks at about `peak` away
## from its target. Exact for critical damping (peak = v0 / (omega * e)).
func kick(peak: Vector3) -> void:
	velocity += peak * TAU * frequency * exp(1.0)


func reset(to: Vector3 = Vector3.ZERO) -> void:
	value = to
	velocity = Vector3.ZERO
	target = to


func is_settled(epsilon: float = 0.0005) -> bool:
	return (value - target).length() < epsilon and velocity.length() < epsilon * 10.0
