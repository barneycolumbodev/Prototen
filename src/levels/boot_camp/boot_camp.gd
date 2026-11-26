class_name BootCamp
extends Node
## Boot camp (docs/design.md §8.11): a guided run through the controls in
## the test range, about three minutes. Move, sprint, slide, shoot, knife,
## dropkick, the D-pad and LB (the GX-4 arm, then the RX-9), then one small
## live wave that shoots back. Each step is a card in the top right with a
## checklist; nothing pauses, the next step comes up when the last is done.
## Stuck for a while: the card adds a hint, and Pause → "Skip this step".
## At the end: Survival, stay on the range, or the main menu.
##
## TestRoom adds it (Boot camp on the main menu, or `--boot-camp`) and sets
## `room`. The operative gets the default loadout (RX-9 on D-left, GX-4 on
## D-down) and the Five-seveN; the range's own targets are cleared away.
## Tuning: data/ui/tutorial.tres.

signal finished(seconds: float)

enum Step { MOVE, SPRINT, SLIDE, SHOOT, KNIFE, DROPKICK, GAUSS, SLOWMO, LIVE, DONE }

## Step → [title, text, hint when stuck]. Button names as on the pad (CLAUDE.md §9.4).
const TEXT: Dictionary[Step, Array] = {
	Step.MOVE: ["MOVE", "Left stick moves, right stick looks. Walk to the marker.", "The marker is the green ring ahead of you."],
	Step.SPRINT: ["SPRINT", "Press the left stick in (L3) to sprint. Run to the next marker.", "Push the left stick forward and click it down."],
	Step.SLIDE: ["SLIDE", "Sprint, then press B to slide.", "Get up to a sprint first: a slide from a walk is just a crouch."],
	Step.SHOOT: ["SHOOT", "Hold LT to aim down the sights, RT to fire. Knock down the steel plates on the north wall. X reloads.", "The plates stand in a row by the far wall, past the crates."],
	Step.KNIFE: ["KNIFE", "Walk up to him and press the right stick in (R3).", "Get within a couple of metres, him in the middle of the view."],
	Step.DROPKICK: ["DROPKICK", "Run at him, jump with A, then press A again in midair.", "Jump from a few metres away. The kick pulls you onto him."],
	Step.GAUSS: ["ACTIVE PARTS", "The D-pad picks which part LB fires. Try the GX-4 Gauss arm.", "D-pad down selects it; the HUD above your health shows which part is picked."],
	Step.SLOWMO: ["RX-9", "Now the RX-9 Reflex Overclock: it slows the world, not you.", "D-pad left selects it. LB on, LB off."],
	Step.LIVE: ["LIVE FIRE", "Triad men are coming in from the edges of the room, and these shoot back. Clear the room.", "Keep moving. Health comes back once you stop taking hits."],
	Step.DONE: ["BOOT CAMP DONE", "", ""],
}
const STEPS_SHOWN: int = 9
const SKIP_HINT: String = "Stuck? Pause → Skip this step."
const GUN: WeaponData = preload("res://data/weapons/pistol_57.tres")
const GX4: StringName = &"gx4_gauss_arm"
const RX9: StringName = &"rx9_reflex_overclock"

var config: TutorialConfig = preload("res://data/ui/tutorial.tres")
var room: TestRoom
var step: Step = Step.MOVE
var card: PromptCard
var marker: Node3D
## The man the knife or the dropkick is for.
var target: Enemy
## Checklist of the step: [text, done].
var checks: Array[Array] = []
## A counted goal (metres, slides, plates); `goal` 0 = the checklist decides.
var count: float = 0.0
var goal: float = 0.0
## Seconds since boot camp began (the end card shows it).
var clock: float = 0.0
var end_screen: Control
## Seconds on this step.
var _on_step: float = 0.0
## Counting down to the next step after this one is done (-1: not done yet).
var _gap: float = -1.0
var _was_sliding: bool = false
var _plates_down: Array[bool] = []
var _kicks: int = 0
var _kick_hit: bool = false
var _struck: bool = false
var _slow_on: float = 0.0
var _respawn: float = -1.0
var _ui: CanvasLayer
var _left: int = -1
var _died: bool = false
var _beam: MeshInstance3D
## Steps skipped from the pause menu (the end card says so).
var skipped: int = 0
var _overlay_was: bool = true


func _ready() -> void:
	card = PromptCard.new()
	card.name = "BootCampCard"
	add_child(card)
	marker = _make_marker()
	room.add_child(marker)
	marker.visible = false
	room.shooting_range.clear_targets()
	var p: Player = room.player
	p.weapon().set_guns([GUN] as Array[WeaponData])
	p.augments.status.locked = true
	p.melee.struck.connect(_on_struck)
	p.dropkicked.connect(func() -> void: _kicks += 1)
	EventBus.dropkick_impact.connect(_on_kick_impact)
	EventBus.wave_changed.connect(_on_wave)
	EventBus.player_died.connect(_on_player_died)
	room.wave_mode.one_wave_cleared.connect(_on_wave_cleared)
	_begin(Step.MOVE)
	# Cloud captures: --boot-camp-step=N starts on step N, staged for the shot.
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--boot-camp-step="):
			_stage.call_deferred(a.get_slice("=", 1).to_int() as Step)


func _stage(s: Step) -> void:
	var p: Player = room.player
	clock = 168.0
	_begin(s)
	match s:
		Step.SHOOT:
			p.global_position = Vector3(-1.5, 0, 0.5)
			p.set_view(0.0, 0.0)
		Step.KNIFE:
			p.global_position = config.knife_spot + Vector3(0.3, 0, 2.4)
			p.set_view(0.1, -0.12)
		Step.DROPKICK:
			p.global_position = config.kick_spot + Vector3(0, 0, 4.0)
			p.set_view(0.0, -0.05)
		Step.GAUSS:
			p.global_position = Vector3(-1.5, 0, 0.5)
			p.set_view(0.0, 0.0)
			var gx: ActivePart = p.augments.find(GX4)
			if gx:
				p.augments.select(gx.slot)
				p.augments.use_selected()


func _exit_tree() -> void:
	if EventBus.dropkick_impact.is_connected(_on_kick_impact):
		EventBus.dropkick_impact.disconnect(_on_kick_impact)
	if EventBus.wave_changed.is_connected(_on_wave):
		EventBus.wave_changed.disconnect(_on_wave)
	if EventBus.player_died.is_connected(_on_player_died):
		EventBus.player_died.disconnect(_on_player_died)
	if is_instance_valid(marker):
		marker.queue_free()


# ------------------------------------------------------------------ steps

func _begin(s: Step) -> void:
	step = s
	_on_step = 0.0
	_gap = -1.0
	count = 0.0
	goal = 0.0
	checks = []
	marker.visible = false
	var p: Player = room.player
	match s:
		Step.MOVE:
			_put_marker(config.walk_marker)
		Step.SPRINT:
			_put_marker(config.sprint_marker)
			goal = config.sprint_metres
		Step.SLIDE:
			goal = config.slides
			_was_sliding = p.is_sliding()
		Step.SHOOT:
			goal = config.plates
			_plates_down.clear()
			for pl: SteelPlate in room.shooting_range.plates:
				_plates_down.append(pl.down)
		Step.KNIFE:
			_struck = false
			_place_target(config.knife_spot)
		Step.DROPKICK:
			_kicks = 0
			_kick_hit = false
			_place_target(config.kick_spot)
		Step.GAUSS:
			checks = [["D-pad down: select the GX-4", false], ["LB: deploy it", false], ["RT: fire a slug", false], ["LB: put it away", false]]
		Step.SLOWMO:
			_slow_on = 0.0
			checks = [["D-pad left: select the RX-9", false], ["LB: slow the world down", false], ["LB again: back to full speed", false]]
		Step.LIVE:
			_clear_target()
			_left = -1
			_died = false
			room.wave_mode.one_wave = config.wave.duplicate()
			room.wave_mode.start()
		Step.DONE:
			_finish()
			return
	_show_card()


## Pause → Skip this step: counts it as done now.
func skip_step() -> void:
	if step == Step.LIVE:
		room.wave_mode.stop()
		room.shooting_range.clear_targets()
	if step != Step.DONE and _gap < 0.0:
		skipped += 1
		_complete()


func _complete() -> void:
	if _gap >= 0.0:
		return
	_gap = config.step_gap
	marker.visible = false
	var title: String = TEXT[step][0]
	card.title = "✓  " + title
	card.hint = ""
	card.progress = float(int(step) + 1) / STEPS_SHOWN
	card.refresh()
	card.flash()
	Sfx.play_ui(&"sd3_link", -4.0, 0.0)


func _process(delta: float) -> void:
	if step == Step.DONE:
		return
	clock += delta
	_on_step += delta
	if _gap >= 0.0:
		_gap -= delta
		if _gap < 0.0:
			_begin((int(step) + 1) as Step)
		return
	if _respawn >= 0.0:
		_respawn -= delta
		if _respawn < 0.0:
			_place_target(config.knife_spot if step == Step.KNIFE else config.kick_spot)
	_check(delta)
	if marker.visible:
		marker.rotation.y += delta * 1.2
		var k: float = 0.5 + 0.5 * sin(clock * 4.0)
		marker.scale = Vector3.ONE * (1.0 + 0.06 * k)
	var stuck: bool = _on_step > config.hint_after and step != Step.LIVE
	var want_hint: String = ("%s\n%s" % [TEXT[step][2], SKIP_HINT]) if stuck else ""
	if step == Step.LIVE and _died:
		want_hint = "Down. The wave starts again."
	if want_hint != card.hint:
		card.hint = want_hint
		card.refresh()


func _check(delta: float) -> void:
	var p: Player = room.player
	match step:
		Step.MOVE:
			if _flat(p.global_position).distance_to(_flat(config.walk_marker)) < config.marker_radius:
				_complete()
		Step.SPRINT:
			if p.is_sprinting() and p.is_on_floor():
				_add(Vector2(p.velocity.x, p.velocity.z).length() * delta)
		Step.SLIDE:
			var sl: bool = p.is_sliding()
			if sl and not _was_sliding:
				_add(1.0)
			_was_sliding = sl
		Step.SHOOT:
			var plates: Array[SteelPlate] = room.shooting_range.plates
			for i: int in plates.size():
				if plates[i].down and not _plates_down[i]:
					_add(1.0)
				_plates_down[i] = plates[i].down
		Step.KNIFE:
			if _struck:
				_complete()
			else:
				_watch_target()
		Step.DROPKICK:
			if _kick_hit or _kicks >= config.kick_attempts:
				_complete()
			else:
				_watch_target()
		Step.GAUSS:
			var gx: ActivePart = p.augments.find(GX4)
			if gx == null:
				_complete()
				return
			_tick(0, p.augments.selected == gx.slot)
			_tick(1, gx.is_running())
			var shots: int = gx.get(&"shots") if &"shots" in gx else 0
			_tick(2, shots >= config.gauss_shots)
			_tick(3, not gx.is_running())
		Step.SLOWMO:
			var rx: ActivePart = p.augments.find(RX9)
			if rx == null:
				_complete()
				return
			_tick(0, p.augments.selected == rx.slot)
			if rx.is_running():
				_slow_on += delta
			_tick(1, _slow_on >= config.slowmo_seconds)
			_tick(2, not rx.is_running())


## Latches checklist row `i` once `ok` holds and every row before it is done.
func _tick(i: int, ok: bool) -> void:
	var done: bool = checks[i][1]
	if done or not ok:
		return
	for j: int in i:
		var before: bool = checks[j][1]
		if not before:
			return
	checks[i][1] = true
	card.checks = checks
	card.refresh()
	card.flash()
	Sfx.play_ui(&"wheel_tick", -6.0, 0.0)
	var all: bool = true
	for c: Array in checks:
		var d: bool = c[1]
		all = all and d
	if all:
		_complete()


func _add(amount: float) -> void:
	count = minf(count + amount, goal)
	_show_progress()
	if count >= goal - 0.001:
		_complete()


# ------------------------------------------------------------------ the card

func _show_card() -> void:
	var t: Array = TEXT[step]
	card.heading = "BOOT CAMP  ·  %d / %d" % [int(step) + 1, STEPS_SHOWN]
	card.title = t[0]
	card.body = t[1]
	card.hint = ""
	card.checks = checks
	card.accent = RunUi.C_WARN if step == Step.LIVE else RunUi.C_ACCENT
	card.progress = float(int(step)) / STEPS_SHOWN
	_show_progress()
	card.present()


func _show_progress() -> void:
	match step:
		Step.SPRINT:
			card.checks = [["Sprinted %d / %d m" % [floori(count), roundi(goal)], count >= goal]]
		Step.SLIDE:
			card.checks = [["Slides %d / %d" % [roundi(count), roundi(goal)], count >= goal]]
		Step.SHOOT:
			card.checks = [["Plates down %d / %d" % [roundi(count), roundi(goal)], count >= goal]]
		Step.LIVE:
			card.checks = [["Hostiles left: %s" % ("…" if _left < 0 else str(_left)), _left == 0]]
	card.refresh()


# ------------------------------------------------------------------ targets

## A passive triad man (he reacts and falls, but never fires) at `at`, facing the operative.
func _place_target(at: Vector3) -> void:
	_clear_target()
	_respawn = -1.0
	var e: Enemy = Enemy.new()
	e.config = load("res://data/enemies/gunman.tres") as EnemyConfig
	e.passive = true
	e.name = "BootCampTarget"
	room.shooting_range.squad.add(e)
	room.add_child(e)
	e.global_position = at
	var to: Vector3 = room.player.global_position - at
	e.face(atan2(to.x, to.z))
	target = e
	_put_marker(at, true)


func _clear_target() -> void:
	if target and is_instance_valid(target):
		target.queue_free()
	target = null


## Shot dead before the step was done: he stands up again in a moment.
func _watch_target() -> void:
	if _respawn < 0.0 and (target == null or not is_instance_valid(target) or not target.alive):
		_respawn = config.target_respawn


func _on_struck(t: Node, _damage: float, _push: float) -> void:
	if step == Step.KNIFE and t is Enemy:
		_struck = true


func _on_kick_impact(_enemy: Node, _push: float) -> void:
	if step == Step.DROPKICK:
		_kick_hit = true


# ------------------------------------------------------------------ live fire

func _on_wave(wave: int, left: int) -> void:
	if step != Step.LIVE or wave <= 0:
		return
	if left > 0:
		_died = false
	_left = left if left >= 0 else _left
	_show_progress()


func _on_player_died() -> void:
	_died = true


func _on_wave_cleared() -> void:
	if step == Step.LIVE:
		_left = 0
		_show_progress()
		_complete()


# ------------------------------------------------------------------ the end

func _finish() -> void:
	TutorialStore.mark(&"boot_camp_done")
	card.dismiss()
	finished.emit(clock)
	_build_end_screen()


func _build_end_screen() -> void:
	_ui = CanvasLayer.new()
	_ui.layer = 45
	add_child(_ui)
	var root: Control = Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_ui.add_child(root)
	root.add_child(RunUi.wash(0.6))
	end_screen = root
	var center: CenterContainer = CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_child(center)
	var panel: PanelContainer = PanelContainer.new()
	panel.add_theme_stylebox_override("panel", RunUi.box(false))
	center.add_child(panel)
	var v: VBoxContainer = VBoxContainer.new()
	v.add_theme_constant_override("separation", 8)
	v.custom_minimum_size = Vector2(460, 0)
	panel.add_child(v)
	var h: Label = RunUi.label("BOOT CAMP DONE", 34, RunUi.C_TEXT)
	h.add_theme_font_override("font", RunUi.title_font())
	v.add_child(h)
	var how: String = "every step cleared" if skipped == 0 else "%d of %d steps, %d skipped" % [STEPS_SHOWN - skipped, STEPS_SHOWN, skipped]
	v.add_child(RunUi.label("%d:%02d  ·  %s" % [floori(clock / 60.0), floori(fmod(clock, 60.0)), how], 16, RunUi.C_ACCENT))
	v.add_child(RunUi.label("Survival is the main mode: waves on a map, a supply drop after each. Tips come up the first time something new happens.", 15, RunUi.C_DIM, true))
	var gap: Control = Control.new()
	gap.custom_minimum_size = Vector2(0, 8)
	v.add_child(gap)
	var first: Button = _end_button(v, "SURVIVAL", _to_survival)
	_end_button(v, "STAY ON THE RANGE", stay)
	_end_button(v, "MAIN MENU", _to_menu)
	room.player.input_enabled = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	# The debug numbers would sit over the card.
	_overlay_was = DebugOverlay.visible
	DebugOverlay.visible = false
	first.grab_focus.call_deferred()


func _end_button(parent: Control, text: String, cb: Callable) -> Button:
	var b: Button = Button.new()
	b.text = text
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.custom_minimum_size = Vector2(0, 44)
	b.add_theme_font_size_override("font_size", 20)
	b.add_theme_stylebox_override("normal", RunUi.box(false))
	b.add_theme_stylebox_override("focus", RunUi.box(true))
	b.add_theme_stylebox_override("hover", RunUi.box(true))
	b.add_theme_stylebox_override("pressed", RunUi.box(true))
	b.pressed.connect(cb)
	b.mouse_entered.connect(b.grab_focus)
	parent.add_child(b)
	return b


func _to_survival() -> void:
	MainMenu.open_kit_on_load = true
	_to_menu()


func _to_menu() -> void:
	DebugOverlay.visible = _overlay_was
	ChinatownMap.menu_on_load = true
	get_tree().change_scene_to_file.call_deferred("res://src/levels/chinatown/chinatown.tscn")


## Stay on the range: the range targets come back, all the guns, the loadout screen.
func stay() -> void:
	DebugOverlay.visible = _overlay_was
	room.player.input_enabled = true
	room.player.augments.status.locked = false
	room.player.weapon().set_guns(room.player.weapon().loadout)
	room.wave_mode.one_wave = []
	room.wave_mode.stop()
	queue_free()


# ------------------------------------------------------------------ marker

## A ring on the floor and a faint column of light above it.
func _make_marker() -> Node3D:
	var root: Node3D = Node3D.new()
	root.name = "BootCampMarker"
	var mat: StandardMaterial3D = StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color(RunUi.C_ACCENT.r, RunUi.C_ACCENT.g, RunUi.C_ACCENT.b, 0.9)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	var ring: MeshInstance3D = MeshInstance3D.new()
	var tm: TorusMesh = TorusMesh.new()
	tm.inner_radius = config.marker_radius - 0.12
	tm.outer_radius = config.marker_radius
	tm.rings = 32
	tm.ring_segments = 6
	ring.mesh = tm
	ring.material_override = mat
	ring.position.y = 0.04
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(ring)
	var beam_mat: StandardMaterial3D = mat.duplicate() as StandardMaterial3D
	beam_mat.albedo_color.a = 0.22
	beam_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	# Fades out upward (the cylinder's V runs top to bottom).
	var g: Gradient = Gradient.new()
	g.set_color(0, Color(1, 1, 1, 0))
	g.set_color(1, Color(1, 1, 1, 1))
	var gt: GradientTexture2D = GradientTexture2D.new()
	gt.gradient = g
	gt.fill_from = Vector2(0, 0)
	gt.fill_to = Vector2(0, 1)
	gt.width = 4
	gt.height = 64
	beam_mat.albedo_texture = gt
	var beam: MeshInstance3D = MeshInstance3D.new()
	var cm: CylinderMesh = CylinderMesh.new()
	cm.top_radius = config.marker_radius * 0.9
	cm.bottom_radius = config.marker_radius
	cm.height = 3.0
	cm.radial_segments = 24
	cm.cap_top = false
	cm.cap_bottom = false
	beam.mesh = cm
	beam.material_override = beam_mat
	beam.position.y = 1.5
	beam.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(beam)
	_beam = beam
	return root


## A place to go (ring and column), or a man to go for (`ring_only`: the column would hide him).
func _put_marker(at: Vector3, ring_only: bool = false) -> void:
	marker.position = Vector3(at.x, at.y, at.z)
	marker.visible = true
	_beam.visible = not ring_only


static func _flat(v: Vector3) -> Vector2:
	return Vector2(v.x, v.z)
