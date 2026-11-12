class_name ActivePart
extends Node
## Behaviour of an active part (docs/design.md §3.4, §9.2 proposal).
##
## States: IDLE → DEPLOYING (deploy_time) → ACTIVE → RECOVERING
## (recover_time) → COOLDOWN (cooldown_time) → IDLE. The button toggles:
## pressed while idle starts it, pressed while deploying or active stops it
## (owner, 2026-11-05: "no holding... press it again to disable it, or it'll
## just go till it runs out"). It also stops when its charge runs out, or
## when something interrupts it (interrupt(): EMP, being downed).
##
## Charge drains in real time while deploying/active and refills after a
## delay once it's stopped. Subclasses override the _on_* hooks; `blend` goes
## 0 → 1 while deploying and 1 → 0 while recovering, for effects that ease
## in and out.

signal state_changed(state: State)

enum State { IDLE, DEPLOYING, ACTIVE, RECOVERING, COOLDOWN }

var data: ActivePartData
var body: BodyModel
var player: Player
## Its D-pad slot (1 = left, 2 = down, 3 = right), set by Augments.
var slot: int = 0
var state: State = State.IDLE
var charge: float = 0.0
## 0..1: how far the effect is in (eases in on deploy, out on recover).
var blend: float = 0.0

var _t: float = 0.0
var _since_stop: float = 99.0


func setup(p_data: ActivePartData, p_body: BodyModel, p_player: Player) -> void:
	data = p_data
	body = p_body
	player = p_player
	charge = charge_capacity()


func _ready() -> void:
	# Keeps running (and keeps real time) while the world is slowed or paused.
	process_mode = Node.PROCESS_MODE_PAUSABLE


func _exit_tree() -> void:
	if body:
		body.remove_active_load(self)
	if player and is_instance_valid(player) and hand() != &"":
		player.release_hand(hand(), self)


func is_running() -> bool:
	return state == State.DEPLOYING or state == State.ACTIVE


## Name on the HUD row (the first word of the display name by default).
func hud_name() -> String:
	return data.short_name if data.short_name != "" else data.display_name.get_slice(" ", 0)


## The player can act (alive, not paused, input on): parts read their own
## buttons (RT, LT, sticks) only while this is true.
func can_input() -> bool:
	return player != null and player.input_enabled and not player.look_blocked and not player.dead and not get_tree().paused


## The level the operative is in: where a part puts things that live in the
## world (a drone, a bolt, a flash of light).
func world() -> Node:
	if player and player.get_parent():
		return player.get_parent()
	return get_tree().current_scene


func rumble(weak: float, strong: float, seconds: float) -> void:
	for pad: int in Input.get_connected_joypads():
		Input.start_joy_vibration(pad, weak, strong, seconds)


## Which hand it needs while it runs (&"right", &"left"; &"" = none). Two
## running parts can't share a hand, and the gun needs both: it's put away
## while either hand is taken (Player.claim_hand).
func hand() -> StringName:
	return &""


## > 0: the HUD draws the charge as this many pips (one per use) instead of a bar.
func hud_pips() -> int:
	return 0


func charge_fraction() -> float:
	return charge / maxf(charge_capacity(), 0.001)


## Full charge. Subclasses scale it with body stats (RX-9: processing).
func charge_capacity() -> float:
	return data.charge_max


## Multiplier on the refill rate (GX-4: power headroom).
func regen_scale() -> float:
	return 1.0


## Why it can't run at all: its requirements aren't met (docs/design.md
## §3.6), or the power reserve is empty and it draws power. "" = fine.
func offline_reason() -> String:
	if body == null:
		return ""
	if body.offline.has(data.id):
		return body.offline[data.id]
	if data.active_power_w > 0.0 and body.brownout():
		return "power reserve empty"
	return ""


func is_offline() -> bool:
	return offline_reason() != ""


func can_start() -> bool:
	if hand() != &"" and player and not player.hand_free(hand(), self):
		return false
	return state == State.IDLE and charge >= data.min_to_start and (player == null or not player.dead) and not is_offline()


## The loadout changed (body stats may differ): keep the charge in range.
func refresh_stats() -> void:
	charge = minf(charge, charge_capacity())


## The button was pressed: start if idle, stop if running.
func toggle() -> void:
	if is_running():
		stop()
	elif can_start():
		_enter(State.DEPLOYING)
	else:
		_on_denied()


func stop() -> void:
	if is_running():
		_enter(State.RECOVERING)


## Forced off (EMP, downed): straight to cooldown, no ease-out.
func interrupt() -> void:
	if state != State.IDLE and state != State.COOLDOWN:
		blend = 0.0
		_enter(State.COOLDOWN)
		_on_blend(0.0)


func _process(delta: float) -> void:
	var real: float = TimeControl.real_delta(delta)
	_t += real
	match state:
		State.DEPLOYING:
			_drain(real)
			blend = clampf(_t / maxf(data.deploy_time, 0.001), 0.0, 1.0)
			_on_blend(blend)
			if _t >= data.deploy_time:
				_enter(State.ACTIVE)
		State.ACTIVE:
			_drain(real)
			_on_active(real)
		State.RECOVERING:
			blend = 1.0 - clampf(_t / maxf(data.recover_time, 0.001), 0.0, 1.0)
			_on_blend(blend)
			if _t >= data.recover_time:
				_enter(State.COOLDOWN)
		State.COOLDOWN:
			if _t >= data.cooldown_time:
				_enter(State.IDLE)
	if not is_running():
		_since_stop += real
		if _since_stop >= data.regen_delay:
			charge = minf(charge + data.regen_per_s * regen_scale() * real, charge_capacity())


func _drain(real: float) -> void:
	charge = maxf(charge - data.drain_per_s * real, 0.0)
	if charge <= 0.0:
		_on_depleted()
		stop()


func _enter(s: State) -> void:
	var prev: State = state
	state = s
	_t = 0.0
	match s:
		State.DEPLOYING:
			if body:
				body.add_active_load(self, data.active_power_w, data.active_heat_w)
			if hand() != &"" and player:
				player.claim_hand(hand(), self)
			_on_start()
		State.ACTIVE:
			blend = 1.0
			_on_blend(1.0)
		State.RECOVERING, State.COOLDOWN:
			if prev == State.DEPLOYING or prev == State.ACTIVE:
				_since_stop = 0.0
				if body:
					body.remove_active_load(self)
				_on_stop()
			if s == State.COOLDOWN:
				blend = 0.0
				if hand() != &"" and player:
					player.release_hand(hand(), self)
	state_changed.emit(s)


# ------------------------------------------------------------------ hooks

## Deploy began (charge already checked).
func _on_start() -> void:
	pass


## Every frame while ACTIVE (real seconds).
func _on_active(_real_delta: float) -> void:
	pass


## The effect's strength changed (0..1), while deploying and recovering.
func _on_blend(_amount: float) -> void:
	pass


## Began recovering (by the button, empty charge or interruption).
func _on_stop() -> void:
	pass


## Charge hit zero.
func _on_depleted() -> void:
	pass


## The button was pressed but it can't start (not enough charge, cooling down).
func _on_denied() -> void:
	pass
