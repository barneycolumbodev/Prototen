class_name BallisticHit
extends RefCounted
## One contact between a round and a surface. Built by Ballistics, passed to
## the thing that was hit (`on_ballistic_hit(hit)`) and broadcast on
## EventBus.ballistic_hit for effects, sound and stats.

enum Result { STOPPED, PENETRATED, RICOCHET }

var shot_id: int = 0
var weapon: WeaponData
var shooter: Node
var collider: Object
var surface: SurfaceMaterial
var result: Result = Result.STOPPED
var point: Vector3 = Vector3.ZERO
var normal: Vector3 = Vector3.UP
var direction: Vector3 = Vector3.FORWARD
## Where the round left the material (PENETRATED only).
var exit_point: Vector3 = Vector3.ZERO
var exit_normal: Vector3 = Vector3.UP
var thickness: float = 0.0
var speed_in: float = 0.0
var speed_out: float = 0.0
var energy_in: float = 0.0
var energy_out: float = 0.0
## Surfaces crossed before this one.
var prior_penetrations: int = 0
var distance: float = 0.0
var damage: DamageInfo


func deposited() -> float:
	return maxf(0.0, energy_in - energy_out)


func zone() -> StringName:
	return damage.zone if damage else &""
