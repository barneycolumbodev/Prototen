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
##
## Open bolt (MG42, `closed_bolt = false`): the bolt waits back and strips the
## next round from the belt as it fires, so there is never a "+1" and every
## reload is the same length. Internally the round the bolt will strip next
## counts as `chambered`, so `loaded()` is simply the rounds left on the belt.
##
## Railguns (`WeaponData.charge_time > 0`): a capacitor bank recharges after
## every shot. `last_power` is the energy fraction the last shot got
## (`WeaponData.charge_power`). Every shot heats the rails in proportion to
## its energy; at full heat the gun vents for `vent_time` and can't fire
## (reloading still works). Heat bleeds off once the gun has rested.
## Shell types (guns with `WeaponData.ammo_types`, the Saiga-12K): the
## chamber and the magazine each remember which load they hold. A reload
## seats a magazine of `load_ammo`. A swap (`request_swap()`, or reload while
## another load is selected) is a magazine change followed by racking the
## bolt, which throws the old chambered shell out (EV_EJECT_CHAMBERED) and
## chambers one of the new load: the empty-reload length.
##
## Cyclic rate is exact: time left over after a cycle carries into the next
## shot, so 0.05 s (1,200 rpm) fires every third 60 Hz physics tick instead of
## drifting to every fourth.

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
## Railguns: the capacitor is full again / the rails overheated / venting finished.
const EV_CHARGED: StringName = &"charged"
const EV_OVERHEAT: StringName = &"overheat"
const EV_VENT_DONE: StringName = &"vent_done"
## A swap racked a live shell out of the chamber (eject it, of `ejected_ammo`).
const EV_EJECT_CHAMBERED: StringName = &"eject_chambered"

## Fraction of an empty reload where the slide closes.
const SLIDE_RELEASE_POINT: float = 0.86
## A reload press while the gun is busy (cycling, mid-burst) still counts this long.
const RELOAD_BUFFER: float = 0.3

var data: WeaponData
var state: State = State.DRAWING
var magazine: int = 0
var chambered: bool = false
var reserve: int = 0
## True while the current reload started from an empty gun (or is a swap).
var empty_reload: bool = false
## Railguns: rail heat 0..1, forced vent in progress, energy fraction of the last shot.
var heat: float = 0.0
var venting: bool = false
var last_power: float = 1.0
## True while the current reload is a swap to another load.
var swapping: bool = false
## Load (index into WeaponData.ammo_types) in the chamber, in the magazine,
## and the one the next magazine will hold.
var chamber_ammo: int = 0
var mag_ammo: int = 0
var load_ammo: int = 0
## Load of the round the last EV_FIRE fired, and of the shell the last swap racked out.
var fired_ammo: int = 0
var ejected_ammo: int = 0

var _state_time: float = 0.0
var _buffered: float = -1.0
## Overshoot from the last completed cycle (only used by a shot on the same tick).
var _carry: float = 0.0
var _reload_buffered: float = -1.0
var _swap_wanted: bool = false
var _mag_out_done: bool = false
var _mag_in_done: bool = false
var _slide_done: bool = false
var _since_shot: float = 999.0
var _vent_left: float = 0.0
var _charged_sent: bool = true


func _init(p_data: WeaponData) -> void:
	data = p_data
	magazine = data.magazine_size if data.closed_bolt else data.magazine_size - 1
	chambered = true
	reserve = data.reserve_ammo
	_enter(State.DRAWING)


## Starts the draw (weapon switched to). A reload in progress is abandoned.
func draw() -> void:
	_buffered = -1.0
	_enter(State.DRAWING)


## The gun is being put away: drop any buffered trigger pull and reload.
func holster() -> Array[StringName]:
	var events: Array[StringName] = []
	_buffered = -1.0
	if state == State.RELOADING:
		_cancel_reload(events)
	return events


## Rounds the player can fire before reloading.
func loaded() -> int:
	return magazine + (1 if chambered else 0)


func reload_duration() -> float:
	return data.reload_empty_time if empty_reload and data.closed_bolt else data.reload_tactical_time


## 0..1 progress through the current reload (0 when not reloading).
func reload_progress() -> float:
	if state != State.RELOADING:
		return 0.0
	return clampf(_state_time / reload_duration(), 0.0, 1.0)


func state_time() -> float:
	return _state_time


## Railguns: 0..1 how full the capacitor is (1 for other guns).
func charge() -> float:
	return data.charge_fraction(_since_shot)


## Seconds since the last shot.
func since_shot() -> float:
	return _since_shot


## 0..1 through the forced vent (0 when not venting).
func vent_progress() -> float:
	if not venting:
		return 0.0
	return clampf(1.0 - _vent_left / maxf(data.vent_time, 0.01), 0.0, 1.0)


## Holstered gun: the capacitor recharges and the rails cool, nothing else.
func idle(delta: float) -> void:
	var events: Array[StringName] = []
	_update_rail(delta, events)
## The gun holds something other than the selected load.
func needs_swap() -> bool:
	return mag_ammo != load_ammo or (chambered and chamber_ammo != load_ammo)


## Swap to `load_ammo` as soon as the gun is free (cycling, drawing). Dropped
## by a reload, or if the selection goes back to what's loaded.
func request_swap() -> void:
	_swap_wanted = true


func can_swap() -> bool:
	if state == State.RELOADING or state == State.DRAWING:
		return false
	return needs_swap() and (data.infinite_reserve or reserve > 0)


func can_reload() -> bool:
	if state == State.RELOADING or state == State.DRAWING:
		return false
	var full: bool = loaded() >= data.magazine_size + (1 if data.closed_bolt else 0)
	return not full and (data.infinite_reserve or reserve > 0)


## Advances the mechanism.
## `pull`: the trigger was pressed this frame. `held`: it is down.
## `reload`: reload pressed. `blocked`: can't shoot right now (sprinting).
## `cancel`: interrupt a reload (sprint, switch, or a trigger pull with a round ready).
func update(delta: float, pull: bool, held: bool, reload: bool, blocked: bool, cancel: bool = false) -> Array[StringName]:
	var events: Array[StringName] = []
	_state_time += delta
	_update_rail(delta, events)
	if pull:
		_buffered = data.fire_buffer
	elif _buffered >= 0.0:
		_buffered -= delta
	var wants_shot: bool = _buffered >= 0.0 or (data.automatic and held)
	if reload:
		_reload_buffered = RELOAD_BUFFER
	elif _reload_buffered >= 0.0:
		_reload_buffered -= delta
	reload = _reload_buffered >= 0.0

	match state:
		State.DRAWING:
			if _state_time >= data.draw_time:
				_enter(State.READY)
		State.CYCLING:
			if _state_time + 0.00001 >= data.fire_interval:
				var over: float = _state_time - data.fire_interval
				_enter(State.READY)
				_carry = clampf(over, 0.0, data.fire_interval)
		State.RELOADING:
			var interrupt: bool = cancel or (pull and (chambered or _mag_in_done))
			if interrupt and not _mag_in_done:
				_cancel_reload(events)
			else:
				_advance_reload(events)
				if interrupt and state == State.RELOADING:
					# Past the point of no return: finish instantly (augmented hands).
					_finish_reload(events)

	if _swap_wanted and not needs_swap():
		_swap_wanted = false
	if state == State.READY and not blocked:
		if (reload or _swap_wanted) and can_swap():
			_start_reload(events, true)
		elif reload and can_reload():
			_start_reload(events)
		elif wants_shot and venting:
			# Rails too hot: the trigger only clicks (once per pull, buffered pulls included).
			if _buffered >= 0.0:
				events.append(EV_DRY_FIRE)
			_buffered = -1.0
		elif wants_shot:
			_buffered = -1.0
			if chambered:
				_fire(events)
			else:
				events.append(EV_DRY_FIRE)
				if can_reload():
					_start_reload(events)
	elif state == State.READY and (reload or _swap_wanted) and can_swap():
		_start_reload(events, true)
	elif state == State.READY and reload and can_reload():
		_start_reload(events)
	# The press was only held for a busy gun; a ready gun that didn't reload (full) drops it.
	if state == State.READY and not blocked:
		_reload_buffered = -1.0
	return events


func _update_rail(delta: float, events: Array[StringName]) -> void:
	_since_shot += delta
	if not data.is_rail():
		return
	if not _charged_sent and charge() >= 1.0:
		_charged_sent = true
		events.append(EV_CHARGED)
	if venting:
		_vent_left -= delta
		heat = clampf(_vent_left / maxf(data.vent_time, 0.01), 0.0, 1.0)
		if _vent_left <= 0.0:
			venting = false
			heat = 0.0
			events.append(EV_VENT_DONE)
	elif _since_shot > data.heat_cool_delay:
		heat = maxf(0.0, heat - data.heat_cool_per_s * delta)


func _fire(events: Array[StringName]) -> void:
	last_power = data.charge_power(_since_shot)
	_since_shot = 0.0
	_charged_sent = not data.is_rail()
	events.append(EV_FIRE)
	if data.heat_per_shot > 0.0 and not venting:
		heat += data.heat_per_shot * last_power
		if heat >= 1.0:
			heat = 1.0
			venting = true
			_vent_left = data.vent_time
			events.append(EV_OVERHEAT)
	fired_ammo = chamber_ammo
	if magazine > 0:
		magazine -= 1
		chambered = true
		chamber_ammo = mag_ammo
	else:
		chambered = false
		events.append(EV_LAST_ROUND)
	# Fired on the tick the last cycle finished: keep that cycle's overshoot.
	var carry: float = _carry if _state_time <= 0.0 else 0.0
	_enter(State.CYCLING)
	_state_time = carry


func _start_reload(events: Array[StringName], swap: bool = false) -> void:
	_reload_buffered = -1.0
	_swap_wanted = false
	swapping = swap and data.closed_bolt
	empty_reload = (not chambered or swapping) and data.closed_bolt
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
	swapping = false
	_enter(State.READY)


func _seat_magazine() -> void:
	# The old magazine's rounds go back into reserve; a fresh one comes out.
	if not data.closed_bolt:
		# Open bolt: the old belt (including the round the bolt would strip) comes out with the box.
		if not data.infinite_reserve:
			reserve += loaded()
		chambered = false
		magazine = 0
	elif not data.infinite_reserve:
		reserve += magazine
	var take: int = data.magazine_size if data.infinite_reserve else mini(data.magazine_size, reserve)
	if not data.infinite_reserve:
		reserve -= take
	magazine = take
	mag_ammo = load_ammo
	if not data.closed_bolt and magazine > 0:
		magazine -= 1
		chambered = true
		chamber_ammo = mag_ammo


func _release_slide(events: Array[StringName]) -> void:
	_slide_done = true
	if swapping and chambered and magazine > 0:
		# Racked: the live shell flies out and one of the new load goes in.
		ejected_ammo = chamber_ammo
		events.append(EV_EJECT_CHAMBERED)
		magazine -= 1
		chamber_ammo = mag_ammo
	elif magazine > 0 and not chambered:
		magazine -= 1
		chambered = true
		chamber_ammo = mag_ammo
	swapping = false
	events.append(EV_SLIDE_RELEASE)


func _enter(s: State) -> void:
	state = s
	_state_time = 0.0
	_carry = 0.0
