class_name SurvivalWaves
extends RefCounted
## Who comes in each Survival wave (docs/design.md §8.6): the wave's threat
## budget is spent on the roster types unlocked by then, each costing its
## `cost`. A type's first wave brings at least one of it, so every new man
## gets a wave to be learned. Every `boss_every`-th wave is a boss wave:
## the boss (SurvivalConfig.bosses; the director brings him in, not this
## list) with escorts on `boss_escort_budget` of the budget, or, past the
## last boss, a lieutenant wave (`lieutenant_roles` first).


static func budget(wave: int, cfg: SurvivalConfig) -> float:
	var n: float = float(maxi(wave, 1) - 1)
	var b: float = cfg.budget_base + cfg.budget_per_wave * n + cfg.budget_accel * n * n
	# The block after a boss starts lower and climbs past it.
	if cfg.boss_every > 0 and wave > cfg.boss_every and (wave - 1) % cfg.boss_every == 0:
		b *= 1.0 - cfg.after_boss_dip
	return b


static func cost_of(role: String, cfg: SurvivalConfig) -> float:
	for e: WaveEnemy in cfg.roster:
		if e.role == role:
			return e.cost
	return 1.0


## Roles for wave `wave`, in spawn order.
static func compose(wave: int, cfg: SurvivalConfig, rng: RandomNumberGenerator) -> Array[String]:
	var out: Array[String] = []
	var left: float = budget(wave, cfg)
	var counts: Dictionary[String, int] = {}
	var lieutenants: bool = cfg.is_boss_wave(wave) and cfg.boss_for(wave) == ""
	if cfg.is_boss_wave(wave) and not lieutenants:
		left *= cfg.boss_escort_budget
	if lieutenants:
		left *= cfg.lieutenant_budget
		for r: String in cfg.lieutenant_roles:
			out.append(r)
			counts[r] = counts.get(r, 0) + 1
			left -= cost_of(r, cfg)
	# Debuts first.
	for e: WaveEnemy in cfg.roster:
		if e.first_wave == wave and not counts.has(e.role):
			out.append(e.role)
			counts[e.role] = 1
			left -= e.cost
	while true:
		var picks: Array[WaveEnemy] = []
		var ws: Array[float] = []
		var total: float = 0.0
		for e: WaveEnemy in cfg.roster:
			var w: float = e.weight_at(wave)
			var cap: int = e.cap_at(wave)
			if w <= 0.0 or e.cost > left + 0.001 or (cap > 0 and counts.get(e.role, 0) >= cap):
				continue
			picks.append(e)
			ws.append(w)
			total += w
		if picks.is_empty():
			break
		var x: float = rng.randf() * total
		var pick: WaveEnemy = picks[picks.size() - 1]
		for i: int in picks.size():
			x -= ws[i]
			if x <= 0.0:
				pick = picks[i]
				break
		out.append(pick.role)
		counts[pick.role] = counts.get(pick.role, 0) + 1
		left -= pick.cost
	# Cheap men first, so a wave opens soft and hardens as it goes; officers
	# early enough to lead.
	var order: Dictionary[String, float] = {}
	for e: WaveEnemy in cfg.roster:
		order[e.role] = e.cost
	var head: Array[String] = []
	var tail: Array[String] = []
	for r: String in out:
		if r in cfg.lieutenant_roles and lieutenants and head.size() < cfg.lieutenant_roles.size():
			head.append(r)
		else:
			tail.append(r)
	tail.sort_custom(func(a: String, b: String) -> bool: return order.get(a, 1.0) < order.get(b, 1.0))
	# Interleave: one dearer man every few cheap ones.
	var mixed: Array[String] = []
	var cheap: Array[String] = []
	var dear: Array[String] = []
	for r: String in tail:
		if order.get(r, 1.0) <= 2.0:
			cheap.append(r)
		else:
			dear.append(r)
	while not cheap.is_empty() or not dear.is_empty():
		for i: int in 2:
			if not cheap.is_empty():
				mixed.append(cheap.pop_front())
		if not dear.is_empty():
			mixed.append(dear.pop_front())
	return head + mixed
