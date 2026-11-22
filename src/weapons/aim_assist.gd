class_name AimAssist
extends RefCounted
## Layered aim assist: slowdown near targets, and a gentle pull toward the
## nearest aim point while aiming down sights. Only ever modifies the
## player's own stick input; a still stick is never moved.
## Targets must be in line of sight (one ray per candidate).

const GROUP: StringName = &"aim_assist_targets"

var config: AimAssistConfig
## Set by the weapon: 0..1 aim-down-sights amount.
var ads: float = 0.0
## Last frame's state, for the HUD/debug.
var on_target: bool = false


func _init(p_config: AimAssistConfig) -> void:
	config = p_config


## Returns the adjusted look rate (degrees/s, x = right, y = down).
func apply(player: Player, rate: Vector2, delta: float) -> Vector2:
	on_target = false
	if config == null or not config.enabled:
		return rate
	var cam: Camera3D = player.camera()
	var eye: Vector3 = cam.global_position
	var forward: Vector3 = -cam.global_basis.z
	var best: Vector3 = Vector3.ZERO
	var best_angle: float = INF
	var best_radius: float = 0.0
	var max_d: float = config.max_distance
	var coarse_d2: float = (max_d + 2.5) * (max_d + 2.5)
	var cos_coarse: float = cos(deg_to_rad(minf(config.slowdown_radius_deg * 2.5 + 14.0, 85.0)))
	for node: Node in player.get_tree().get_nodes_in_group(GROUP):
		var n3: Node3D = node as Node3D
		if n3 != null:
			var coarse_to: Vector3 = n3.global_position + Vector3.UP - eye
			var d2: float = coarse_to.length_squared()
			if d2 > coarse_d2:
				continue
			if d2 > 16.0 and forward.dot(coarse_to) < cos_coarse * sqrt(d2):
				continue
		var enemy: Enemy = node as Enemy
		if enemy != null:
			if not enemy.alive or enemy.state == Enemy.State.SURRENDER:
				continue
			for k: int in 2:
				var p: Vector3 = enemy.body.head_position() if k == 0 else enemy.body.chest_position()
				var to: Vector3 = p - eye
				var dist: float = to.length()
				if dist > max_d or dist < 0.3:
					continue
				var angle: float = rad_to_deg(forward.angle_to(to))
				var radius: float = config.slowdown_radius_deg * clampf(10.0 / dist, 0.35, 2.5)
				if angle < radius and angle < best_angle and _visible(player, eye, p, node):
					best_angle = angle
					best = p
					best_radius = radius
			continue
		var dog: AttackDog = node as AttackDog
		if dog != null:
			if not dog.alive:
				continue
			for k: int in 2:
				var p: Vector3 = dog.head_position() if k == 0 else dog.chest_position()
				var to: Vector3 = p - eye
				var dist: float = to.length()
				if dist > max_d or dist < 0.3:
					continue
				var angle: float = rad_to_deg(forward.angle_to(to))
				var radius: float = config.slowdown_radius_deg * clampf(10.0 / dist, 0.35, 2.5)
				if angle < radius and angle < best_angle and _visible(player, eye, p, node):
					best_angle = angle
					best = p
					best_radius = radius
			continue
		if not node.has_method(&"aim_points"):
			continue
		var points: PackedVector3Array = node.call(&"aim_points")
		for p: Vector3 in points:
			var to: Vector3 = p - eye
			var dist: float = to.length()
			if dist > max_d or dist < 0.3:
				continue
			var angle: float = rad_to_deg(forward.angle_to(to))
			var radius: float = config.slowdown_radius_deg * clampf(10.0 / dist, 0.35, 2.5)
			if angle < radius and angle < best_angle and _visible(player, eye, p, node):
				best_angle = angle
				best = p
				best_radius = radius
	if best_angle == INF:
		return rate
	on_target = true
	# The body's perception stat (target tracking, docs/design.md §3.6) scales
	# how much the assist slows and pulls.
	var perc: float = player.body.stat(&"perception") if player.body else 1.0
	var slow: float = clampf(1.0 - (1.0 - config.slowdown) * perc, 0.05, 1.0)
	var out: Vector2 = rate * lerpf(slow, 1.0, best_angle / best_radius)
	# Pull while aimed, only when the player is moving the stick.
	if ads > 0.5 and rate.length() > config.pull_needs_input and best_angle < config.pull_radius_deg * clampf(10.0 / eye.distance_to(best), 0.35, 2.5):
		var local: Vector3 = cam.global_basis.inverse() * (best - eye)
		var want: Vector2 = Vector2(rad_to_deg(atan2(local.x, -local.z)), -rad_to_deg(atan2(local.y, -local.z)))
		var step: Vector2 = want.limit_length(config.pull_deg_s * perc * ads * delta)
		out += step / maxf(delta, 0.0001)
	return out


func _visible(player: Player, eye: Vector3, point: Vector3, target: Node) -> bool:
	var q: PhysicsRayQueryParameters3D = PhysicsRayQueryParameters3D.create(eye, point, Ballistics.LAYER_WORLD | Ballistics.LAYER_PROPS)
	var res: Dictionary = player.get_world_3d().direct_space_state.intersect_ray(q)
	if res.is_empty():
		return true
	var obj: Object = res["collider"]
	var hit: Node = obj as Node
	return hit != null and (hit == target or target.is_ancestor_of(hit))
