class_name GunMechanism
extends RefCounted
## The gun as a machine: magazine, chamber, trigger, reload. No visuals or
## input, so it can be tested on its own. The weapon controller feeds it
## inputs each frame and reacts to the events it returns.
##
## Closed bolt: a round sits in the chamber separately from the magazine, so
## a tactical reload gives 20 + 1. When the last round fires the slide locks
## back and the next reload is the longer empty one (with a slide release).
## Ammo only changes when the new magazine seats, so a reload cancelled
## before that loses nothing.

enum State { DRAWING, READY, CYCLING, RELOADING }

const EV_FIRE: StringName = &"fire"
const EV_DRY_FIRE: StringName = &"dry_fire"
const EV_RELOAD_START: StringName = &"reload_start"
const EV_MAG_OUT: StringName = &"mag_out"
const EV_MAG_IN: StringName = &"mag_in"
const EV_SLIDE_RELEASE: StringName = &"slide_release"
const EV_RELOAD_DONE: StringName = &"reload_done"
const EV_RELOAD_CANCEL: StringName = &"reload_cancel"
const EV_LAST_ROUND: StringName = &"last_round"

## Fraction of an empty reload where the slide closes.
const SLIDE_RELEASE_POINT: float = 0.86

var data: WeaponData
var state: State = State.DRAWING
var magazine: int = 0
var chambered: bool = false
var reserve: int = 0
## True while the current reload started from an empty gun.
var empty_reload: bool = false

var _state_time: float = 0.0
var _buffered: float = -1.0
var _mag_out_done: bool = false
var _mag_in_done: bool = false
var _slide_done: bool = false


func _init(p_data: WeaponData) -> void:
	data = p_data
	# Closed bolt only for now (the open-bolt MG42 comes in M3).
	magazine = data.magazine_size
	chambered = true
	reserve = data.reserve_ammo
	_enter(State.DRAWING)


## Rounds the player can fire before reloading.
func loaded() -> int:
	return magazine + (1 if chambered else 0)


func reload_duration() -> float:
	return data.reload_empty_time if empty_reload else data.reload_tactical_time


## 0..1 progress through the current reload (0 when not reloading).
func reload_progress() -> float:
	if state != State.RELOADING:
		return 0.0
	return clampf(_state_time / reload_duration(), 0.0, 1.0)


func state_time() -> float:
	return _state_time


func can_reload() -> bool:
	if state == State.RELOADING or state == State.DRAWING:
		return false
	var full: bool = magazine >= data.magazine_size and (chambered or not data.closed_bolt)
	return not full and (data.infinite_reserve or reserve > 0)


## Advances the mechanism.
## `pull`: the trigger was pressed this frame. `held`: it is down.
## `reload`: reload pressed. `blocked`: can't shoot right now (sprinting).
## `cancel`: interrupt a reload (sprint, switch, or a trigger pull with a round ready).
func update(delta: float, pull: bool, held: bool, reload: bool, blocked: bool, cancel: bool = false) -> Array[StringName]:
	var events: Array[StringName] = []
	_state_time += delta
	if pull:
		_buffered = data.fire_buffer
	elif _buffered >= 0.0:
		_buffered -= delta
	var wants_shot: bool = _buffered >= 0.0 or (data.automatic and held)

	match state:
		State.DRAWING:
			if _state_time >= data.draw_time:
				_enter(State.READY)
		State.CYCLING:
			if _state_time >= data.fire_interval:
				_enter(State.READY)
		State.RELOADING:
			var interrupt: bool = cancel or (pull and (chambered or _mag_in_done))
			if interrupt and not _mag_in_done:
				_cancel_reload(events)
			else:
				_advance_reload(events)
				if interrupt and state == State.RELOADING:
					# Past the point of no return: finish instantly (augmented hands).
					_finish_reload(events)

	if state == State.READY and not blocked:
		if reload and can_reload():
			_start_reload(events)
		elif wants_shot:
			_buffered = -1.0
			if chambered:
				_fire(events)
			else:
				events.append(EV_DRY_FIRE)
				if can_reload():
					_start_reload(events)
	elif state == State.READY and reload and can_reload():
		_start_reload(events)
	return events


func _fire(events: Array[StringName]) -> void:
	events.append(EV_FIRE)
	if magazine > 0:
		magazine -= 1
		chambered = true
	else:
		chambered = false
		events.append(EV_LAST_ROUND)
	_enter(State.CYCLING)


func _start_reload(events: Array[StringName]) -> void:
	empty_reload = not chambered
	_mag_out_done = false
	_mag_in_done = false
	_slide_done = false
	_enter(State.RELOADING)
	events.append(EV_RELOAD_START)


func _advance_reload(events: Array[StringName]) -> void:
	var t: float = reload_progress()
	if not _mag_out_done and t >= data.mag_out_point:
		_mag_out_done = true
		events.append(EV_MAG_OUT)
	if not _mag_in_done and t >= data.mag_in_point:
		_mag_in_done = true
		_seat_magazine()
		events.append(EV_MAG_IN)
	if empty_reload and _mag_in_done and not _slide_done and t >= SLIDE_RELEASE_POINT:
		_release_slide(events)
	if t >= 1.0:
		_finish_reload(events)


func _finish_reload(events: Array[StringName]) -> void:
	if not _mag_in_done:
		_mag_in_done = true
		_seat_magazine()
		events.append(EV_MAG_IN)
	if empty_reload and not _slide_done:
		_release_slide(events)
	events.append(EV_RELOAD_DONE)
	_enter(State.READY)


func _cancel_reload(events: Array[StringName]) -> void:
	events.append(EV_RELOAD_CANCEL)
	_enter(State.READY)


func _seat_magazine() -> void:
	# The old magazine's rounds go back into reserve; a fresh one comes out.
	if not data.infinite_reserve:
		reserve += magazine
	var take: int = data.magazine_size if data.infinite_reserve else mini(data.magazine_size, reserve)
	if not data.infinite_reserve:
		reserve -= take
	magazine = take


func _release_slide(events: Array[StringName]) -> void:
	_slide_done = true
	if magazine > 0 and not chambered:
		magazine -= 1
		chambered = true
	events.append(EV_SLIDE_RELEASE)


func _enter(s: State) -> void:
	state = s
	_state_time = 0.0
