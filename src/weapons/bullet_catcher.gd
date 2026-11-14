class_name BulletCatcher
extends RefCounted
## A sphere that stops rounds entering it from its open side (within `arc_deg`
## of `facing`), fired by anyone but `owner`. `on_catch(weapon: WeaponData,
## point: Vector3, velocity: Vector3, shooter: Node) -> bool`: true = taken
## (the round ends there), false = full (it flies on).
var center: Vector3 = Vector3.ZERO
var radius: float = 1.0
var facing: Vector3 = Vector3.FORWARD
var cos_arc: float = 0.25
var owner: Node
var on_catch: Callable
var enabled: bool = true

## Distance along the segment (from `a`, unit `dir`, length `length`) where
## it enters the sphere, or -1.
func entry(a: Vector3, dir: Vector3, length: float) -> float:
	if -dir.dot(facing) < cos_arc:
		return -1.0
	var oc: Vector3 = a - center
	var c: float = oc.length_squared() - radius * radius
	if c <= 0.0:
		return 0.0
	var b: float = oc.dot(dir)
	if b > 0.0:
		return -1.0
	var disc: float = b * b - c
	if disc < 0.0:
		return -1.0
	var t: float = -b - sqrt(disc)
	return t if t <= length else -1.0
