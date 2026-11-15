class_name RunState
extends RefCounted
## One Survival run (docs/design.md §8): the body (a BodyLoadout built up
## from the doctrine's frame), the guns carried, the mark of each active,
## the wave reached, and the supply drops (§8.4, §8.5).
## Pure logic: SurvivalRun puts it on the player; tests drive it directly.

## One thing on a drop card: an item, and for actives the mark it comes at
## (a new active: 1; an upgrade: the mark after the one owned).
class Offer:
	extends RefCounted
	var item: RunItem
	var mark: int = 0
	var upgrade: bool = false
	## Parts the body would lose to fit it (a full location).
	var replaces: Array[PartData] = []
	## Why it wouldn't come online on this body ("" = it would).
	var offline: String = ""

	func title() -> String:
		if item.kind() == RunItem.Kind.ACTIVE:
			return "%s %s" % [item.display_name(), RunItem.MARK_NAMES[mark]]
		return item.display_name()

	func kind_label() -> String:
		if upgrade:
			return "UPGRADE"
		match item.kind():
			RunItem.Kind.WEAPON:
				return "WEAPON"
			RunItem.Kind.ACTIVE:
				return "ACTIVE"
		return "PASSIVE"

var config: SurvivalConfig
var doctrine: Doctrine
var loadout: BodyLoadout
var guns: Array[WeaponData] = []
## Mark of each active owned (id → 1..3).
var marks: Dictionary[StringName, int] = {}
var wave: int = 0
var kills: int = 0
var drops: int = 0
## What was taken, in order (the run-over screen).
var history: Array[String] = []
var rng: RandomNumberGenerator = RandomNumberGenerator.new()


func _init(p_config: SurvivalConfig, seed_value: int = 0) -> void:
	config = p_config
	if seed_value != 0:
		rng.seed = seed_value
	else:
		rng.randomize()


## The starting kit: a doctrine (its frame), one gun, one active at Mk I.
func start(p_doctrine: Doctrine, gun: WeaponData, active: ActivePartData) -> void:
	doctrine = p_doctrine
	loadout = LoadoutStore.LIBRARY.loadout_from_ids(PackedStringArray(), p_doctrine.display_name)
	for p: PartData in p_doctrine.parts:
		loadout.install(p)
	guns = [gun]
	marks.clear()
	wave = 0
	kills = 0
	drops = 0
	history.clear()
	if active:
		var it: RunItem = config.item_for(active)
		loadout.install(it.active_at(1) if it else active)
		marks[active.id] = 1


func body() -> BodyModel:
	return BodyModel.new(config.frame, loadout)


func owns(it: RunItem) -> bool:
	if it.kind() == RunItem.Kind.WEAPON:
		return it.item in guns
	return loadout.has_part(it.id())


func mark_of(id: StringName) -> int:
	return marks[id] if marks.has(id) else 0


## Everything owned that's in the pool (the frame's passives count).
func owned_items() -> Array[RunItem]:
	var out: Array[RunItem] = []
	for g: WeaponData in guns:
		var it: RunItem = config.item_for(g)
		if it:
			out.append(it)
	for p: PartData in loadout.parts:
		if p.fixed:
			continue
		var it2: RunItem = config.item_by_id(p.id)
		if it2:
			out.append(it2)
	return out


## Affinity (§8.5): the owned items' tags pull more of the same.
func affinity(tags: Array[StringName]) -> float:
	var best: float = 1.0
	var owned: Array[RunItem] = owned_items()
	for t: StringName in tags:
		var n: int = 0
		for it: RunItem in owned:
			if it.has_tag(t):
				n += 1
		best = maxf(best, minf(1.0 + config.affinity_per_item * float(n), config.affinity_max))
	return best


## Odds of `it` in a drop: its weight × doctrine × affinity, less if it
## wouldn't come online.
func weight_of(it: RunItem, with_doctrine: bool = true) -> float:
	var w: float = it.weight * affinity(it.tags)
	if with_doctrine and doctrine:
		w *= doctrine.bias(it.tags)
	if _offline_reason(it, 1) != "":
		w *= 0.3
	return w


## Items of `kind` that could drop now (not owned, not boss-only, unlocked,
## fits the body). MARK isn't a kind: see upgradable().
func eligible(kind: int) -> Array[RunItem]:
	var out: Array[RunItem] = []
	if kind == RunItem.Kind.WEAPON and guns.size() >= config.max_guns:
		return out
	if kind == RunItem.Kind.ACTIVE and loadout.actives().size() >= BodyLoadout.MAX_ACTIVES:
		return out
	for it: RunItem in config.pool:
		if int(it.kind()) != kind or it.boss_only or it.min_wave > maxi(wave, 1) or owns(it):
			continue
		if kind != RunItem.Kind.WEAPON and not _fits(it):
			continue
		out.append(it)
	return out


## Owned actives below Mk III.
func upgradable() -> Array[RunItem]:
	var out: Array[RunItem] = []
	for a: ActivePartData in loadout.actives():
		var it: RunItem = config.item_by_id(a.id)
		if it and mark_of(a.id) < RunItem.MAX_MARK:
			out.append(it)
	return out


## A part fits if, after installing it (and whatever it pushes out of a
## full location), no active is lost or knocked offline and the capacity
## budget holds.
func _fits(it: RunItem) -> bool:
	var lo: BodyLoadout = loadout.copy()
	var part: PartData = it.active_at(1) if it.kind() == RunItem.Kind.ACTIVE else it.item as PartData
	var out: Array[PartData] = lo.install(part)
	for p: PartData in out:
		if p.is_active():
			return false
	var now: BodyModel = body()
	var after: BodyModel = BodyModel.new(config.frame, lo)
	for a: ActivePartData in lo.actives():
		if now.is_online(a.id) and not after.is_online(a.id):
			return false
	return after.capacity_left() >= 0


func _offline_reason(it: RunItem, mark: int) -> String:
	if it.kind() == RunItem.Kind.WEAPON:
		return ""
	var lo: BodyLoadout = loadout.copy()
	var part: PartData = it.active_at(mark) if it.kind() == RunItem.Kind.ACTIVE else it.item as PartData
	if not lo.has_part(part.id):
		lo.install(part)
	var m: BodyModel = BodyModel.new(config.frame, lo)
	return m.unmet(part)


func make_offer(it: RunItem, upgrade: bool = false) -> Offer:
	var o: Offer = Offer.new()
	o.item = it
	if it.kind() == RunItem.Kind.ACTIVE:
		o.upgrade = upgrade or owns(it)
		o.mark = mark_of(it.id()) + 1 if o.upgrade else 1
	if it.kind() == RunItem.Kind.PASSIVE:
		var lo: BodyLoadout = loadout.copy()
		o.replaces = lo.install(it.item as PartData)
	o.offline = _offline_reason(it, maxi(o.mark, 1))
	return o


# ------------------------------------------------------------------ drops

## The drop after a wave (§8.4): one offer (picked for you) or two to choose
## from. The first drop of a run is always a choice; the second offer is a
## different item, of another kind if there is one, drawn without the
## doctrine's bias so there's always a way to pivot.
func roll_drop() -> Array[Offer]:
	var out: Array[Offer] = []
	var choice: bool = drops == 0 or rng.randf() < config.choice_chance
	var first: Offer = _roll(true, -1, null)
	if first == null:
		return out
	out.append(first)
	if choice:
		var second: Offer = _roll(false, _kind_key(first), first.item)
		if second == null:
			second = _roll(false, -1, first.item)
		if second:
			out.append(second)
	return out


## A boss's drop (§8.7): until bosses exist, a lieutenant wave's. A mark
## for an owned active if one can go up, else an active you don't have
## (boss-only ones included).
func roll_boss_drop() -> Offer:
	var ups: Array[RunItem] = upgradable()
	if not ups.is_empty():
		return make_offer(ups[rng.randi() % ups.size()], true)
	if loadout.actives().size() < BodyLoadout.MAX_ACTIVES:
		var news: Array[RunItem] = []
		for it: RunItem in config.pool:
			if it.kind() == RunItem.Kind.ACTIVE and not owns(it):
				news.append(it)
		var pick: RunItem = _weighted(news, true)
		if pick:
			return make_offer(pick)
	return null


## Kind keys: RunItem.Kind for new items, 3 for a mark.
const MARK_KEY: int = 3


func _kind_key(o: Offer) -> int:
	return MARK_KEY if o.upgrade else int(o.item.kind())


func _roll(with_doctrine: bool, avoid_kind: int, avoid: RunItem) -> Offer:
	var lists: Dictionary[int, Array] = {}
	var odds: Dictionary[int, float] = {
		int(RunItem.Kind.WEAPON): config.weapon_odds,
		int(RunItem.Kind.ACTIVE): config.active_odds,
		int(RunItem.Kind.PASSIVE): config.passive_odds,
	}
	for k: int in odds.keys():
		var l: Array[RunItem] = eligible(k)
		l.erase(avoid)
		if not l.is_empty():
			lists[k] = l
	if wave >= config.mark_from_wave:
		var ups: Array[RunItem] = upgradable()
		ups.erase(avoid)
		if not ups.is_empty():
			lists[MARK_KEY] = ups
			odds[MARK_KEY] = config.mark_odds
	if lists.size() > 1 and lists.has(avoid_kind):
		lists.erase(avoid_kind)
	if lists.is_empty():
		return null
	var total: float = 0.0
	for k: int in lists:
		total += odds[k]
	var x: float = rng.randf() * total
	var kind: int = -1
	for k: int in lists:
		if kind < 0:
			kind = k
	for k: int in lists:
		x -= odds[k]
		if x <= 0.0:
			kind = k
			break
	var items: Array[RunItem] = []
	items.assign(lists[kind])
	var it: RunItem = _weighted(items, with_doctrine)
	return make_offer(it, kind == MARK_KEY) if it else null


func _weighted(items: Array[RunItem], with_doctrine: bool) -> RunItem:
	if items.is_empty():
		return null
	var total: float = 0.0
	var ws: Array[float] = []
	for it: RunItem in items:
		var w: float = weight_of(it, with_doctrine)
		ws.append(w)
		total += w
	var x: float = rng.randf() * total
	for i: int in items.size():
		x -= ws[i]
		if x <= 0.0:
			return items[i]
	return items[items.size() - 1]


## Takes an offer into the run. Returns the parts the body lost to fit it.
func take(o: Offer) -> Array[PartData]:
	var removed: Array[PartData] = []
	drops += 1
	match o.item.kind():
		RunItem.Kind.WEAPON:
			guns.append(o.item.item as WeaponData)
		RunItem.Kind.PASSIVE:
			removed = loadout.install(o.item.item as PartData)
		RunItem.Kind.ACTIVE:
			var id: StringName = o.item.id()
			var part: ActivePartData = o.item.active_at(o.mark)
			if loadout.has_part(id):
				# Same D-pad slot: replace in place.
				var i: int = loadout.parts.find(loadout.find(id))
				loadout.parts[i] = part
			else:
				removed = loadout.install(part)
			marks[id] = o.mark
	for p: PartData in removed:
		marks.erase(p.id)
	history.append("W%d  %s" % [wave, o.title()])
	return removed
