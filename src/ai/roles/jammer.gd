class_name Jammer
extends RefCounted
## The anti-augment specialist's jammer backpack (docs/design.md §8.8g).
## Within `radius` of him the Shrike drone loses its link and drops (it
## can't be flown in) and the thermoptic shroud can't hold (it fails and
## shows you). The pack is a hitbox of its own on his back: shoot it and it
## dies with a pop and a shower of sparks, lamps out, and the jamming stops.
## So does his death.

var e: Enemy
var jcfg: JammerConfig
var alive: bool = true
var health: float = 60.0
var box: StaticBody3D
var jammed_drones: int = 0
var jammed_shrouds: int = 0
var _tick: float = 0.0


func _init(enemy: Enemy) -> void:
	e = enemy
	jcfg = enemy.config.jammer
	health = jcfg.health


func build() -> void:
	box = StaticBody3D.new()
	box.name = "JammerPack"
	box.collision_layer = Ballistics.LAYER_HITBOX
	box.collision_mask = 0
	box.set_meta(&"surface", &"sheet_metal")
	box.set_meta(&"dynamic_holes", true)
	box.set_meta(&"jammer", true)
	box.set_script(preload("res://src/ai/armor_plate.gd"))
	box.set(&"target", e)
	var cs: CollisionShape3D = CollisionShape3D.new()
	var b: BoxShape3D = BoxShape3D.new()
	b.size = jcfg.box_size
	cs.shape = b
	box.add_child(cs)
	box.position = jcfg.box_center
	e.body.bone_attachment(&"chest").add_child(box)
	e.body.add_plate(box)


## A round in the pack.
func on_hit(hit: BallisticHit) -> void:
	if not alive:
		return
	health -= hit.damage.amount if hit.damage else 20.0
	Fx._emit(&"sparks", hit.point, hit.normal, Color(0.6, 0.85, 1.0, 1.0), 6, 1.0)
	if health <= 0.0:
		kill()


func kill() -> void:
	if not alive:
		return
	alive = false
	if box:
		box.collision_layer = 0
	var at: Vector3 = box.global_position if box and box.is_inside_tree() else e.body.chest_position()
	Fx._emit(&"sparks", at, Vector3.UP, Color(0.6, 0.85, 1.0, 1.0), 26, 1.8)
	Sfx.play_at(&"sd3_lost", at, 2.0, 0.05)
	Sfx.play_at(&"impact_metal", at, 0.0, 0.1)
	# Lamps out: the pack's glow goes dark.
	var mi: MeshInstance3D = e.gear.piece(&"jammer") if e.gear else null
	if mi:
		var m: Material = mi.get_active_material(0)
		var bm: BaseMaterial3D = m as BaseMaterial3D
		if bm:
			var dark: BaseMaterial3D = bm.duplicate() as BaseMaterial3D
			dark.emission_enabled = false
			mi.material_override = dark


func is_jamming() -> bool:
	return alive and e.alive and not e.held


## Every physics frame he's alive: knock out what's in range.
func update(delta: float) -> void:
	_tick -= delta
	if _tick > 0.0 or not is_jamming():
		return
	_tick = 0.2
	var p: Player = e.squad.player() if e.squad else null
	if p == null or p.augments == null:
		return
	var here: Vector3 = e.global_position
	for part: ActivePart in p.augments.parts.values():
		if not part.is_running():
			continue
		var drone: ShrikeDrone = part as ShrikeDrone
		if drone:
			if drone.craft and is_instance_valid(drone.craft) and drone.craft.global_position.distance_to(here) <= jcfg.radius:
				jammed_drones += 1
				drone.jam_link()
			continue
		if part is ThermopticShroud and p.global_position.distance_to(here) <= jcfg.radius:
			jammed_shrouds += 1
			part.interrupt()
			Sfx.play_at(&"tc4_fail", p.global_position + Vector3.UP, 0.0, 0.05)
