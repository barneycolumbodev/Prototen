class_name HotelMap
extends ChinatownMap
## Map 2 (owner, 2026-11-18): the Golden Dragon Grand Hotel, an abandoned
## five-star lobby, still lit. Built by raw_assets/levels/hotel/ (build.py →
## bake.py) the same way as Chinatown, which this extends: the glTF and baked
## lightmap, colliders, spawn points, lights and cameras from layout.json, its
## own texture array (assets/env/hotel), the atmosphere indoors.
##
## Where the enemy comes from (docs/design.md §7.2): the six lifts in the
## lift hall, and the street, through the porte-cochère and the glass doors.
## A man (or dog) who spawns in a car waits behind its doors; the car chimes,
## the doors roll open and let them out, and close again once the car is
## empty (never on the operative). Closed doors hide a car from the player,
## so the spawner's "out of sight" rule picks cars the player isn't watching
## open.

const HOTEL_LAYOUT: String = "res://assets/levels/hotel/layout.json"
const HOTEL_SCENE: String = "res://assets/levels/hotel/hotel.gltf"
const HOTEL_LIGHTMAP: String = "res://assets/levels/hotel/lightmap.png"
const HOTEL_SPAWNS: String = "res://data/levels/hotel_spawns.tres"
const HOTEL_ATMOS: String = "res://data/levels/hotel_interior.tres"

var lifts: Array[Lift] = []


func layout_path() -> String:
	return HOTEL_LAYOUT


func map_scene_path() -> String:
	return HOTEL_SCENE


func lightmap_path() -> String:
	return HOTEL_LIGHTMAP


func spawn_config_path() -> String:
	return HOTEL_SPAWNS


func atmos_config_path() -> String:
	return HOTEL_ATMOS


func world_texture_prefix() -> String:
	return "res://assets/env/hotel/hotel_"


func room_size() -> float:
	return 0.6


## The menu lives on Chinatown; the hotel is always started from it (or directly by tests).
func wants_menu() -> bool:
	return force_menu


## Cover everywhere on the ground floor, and up on the mezzanine.
func level_cover_regions() -> Array:
	return [[b2g([0.0, 2.5, 0.0]), 40.0], [b2g([0.0, 6.0, 4.5]), 34.0]]


## Both storeys (the mezzanine floor is at 4.5 m), the street outside.
func nav_bounds() -> AABB:
	return AABB(Vector3(-40.0, -1.0, -34.0), Vector3(80.0, 9.0, 63.0))


func bench_point() -> Vector3:
	return b2g([0.0, -6.0, 0.0])


## The lifts go in after the navigation mesh is baked from the level, so the
## mesh runs into the cars (their doors would cut them off).
func _build_navigation() -> void:
	super._build_navigation()
	if lifts.is_empty():
		_build_lifts()


func _build_lifts() -> void:
	for m: Dictionary in layout["markers"]:
		if fstr(m, "kind") != "lift":
			continue
		var lift: Lift = Lift.new()
		lift.name = "Lift%d" % int(fnum(m, "index"))
		lift.door_centre = fpos(m)
		lift.width = fnum(m, "width", 2.0)
		lift.height = fnum(m, "height", 2.6)
		var car: Array = m["car"]
		lift.car_centre = b2g(car)
		add_child(lift)
		lifts.append(lift)


func _on_spawner(spawner: RollingSpawner) -> void:
	spawner.spawned.connect(func(e: Enemy) -> void: _arrived(e))
	spawner.dog_spawned.connect(func(d: AttackDog) -> void: _arrived(d))


## Someone appeared: if it was in a car, that car comes down and opens.
func _arrived(who: Node3D) -> void:
	var lift: Lift = lift_at(who.global_position)
	if lift:
		lift.call_down()


## The lift whose car holds `p`, or null.
func lift_at(p: Vector3) -> Lift:
	for l: Lift in lifts:
		if l.contains(p):
			return l
	return null
