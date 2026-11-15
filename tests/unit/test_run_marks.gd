extends GutTest
## Active marks in Survival (docs/design.md §8.3): Mk III is the part as
## built, Mk I and Mk II are tuning overrides only, and every override names
## a real property with the right type.

var cfg: SurvivalConfig = preload("res://data/run/survival.tres")
var lib: PartLibrary = preload("res://data/body/part_library.tres")


func _active_items() -> Array[RunItem]:
	var out: Array[RunItem] = []
	for it: RunItem in cfg.pool:
		if it.kind() == RunItem.Kind.ACTIVE:
			out.append(it)
	return out


func test_every_active_has_mk1_and_mk2() -> void:
	var items: Array[RunItem] = _active_items()
	assert_eq(items.size(), lib.actives().size(), "every active is in the pool")
	for it: RunItem in items:
		assert_false(it.mk1.is_empty(), "%s has Mk I" % it.id())
		assert_false(it.mk2.is_empty(), "%s has Mk II" % it.id())


func test_overrides_name_real_properties_of_the_same_type() -> void:
	for it: RunItem in _active_items():
		var part: ActivePartData = it.item as ActivePartData
		for mark: int in [1, 2]:
			var o: Dictionary[StringName, Variant] = it.overrides(mark)
			for k: StringName in o:
				assert_true(k in part, "%s Mk %d: %s is a property" % [it.id(), mark, k])
				assert_eq(typeof(o[k]), typeof(part.get(k)), "%s Mk %d: %s has the property's type" % [it.id(), mark, k])


func test_mk3_is_the_part_as_built_and_lower_marks_are_copies() -> void:
	for it: RunItem in _active_items():
		var part: ActivePartData = it.item as ActivePartData
		assert_same(it.active_at(3), part, "%s Mk III is the Sandbox part" % it.id())
		var mk1: ActivePartData = it.active_at(1)
		assert_ne(mk1, part)
		assert_eq(mk1.id, part.id, "same id: the loadout and D-pad still know it")
		assert_string_contains(mk1.display_name, "Mk I")
		for k: StringName in it.mk1:
			assert_eq(str(mk1.get(k)), str(it.mk1[k]), "%s Mk I %s applied" % [it.id(), k])
	# The resource on disk is untouched.
	var rx9: ActivePartData = lib.find(&"rx9_reflex_overclock") as ActivePartData
	assert_eq(rx9.charge_max, 8.0)


func test_owner_examples() -> void:
	# "the needle throwing thing, the first version of it might only have 2 needles... a higher
	# strength requirement for damage. The slowdown time might only last 4 seconds at a full charge."
	var setae: RunItem = cfg.item_by_id(&"sx8_urticating_setae")
	var s1: SetaeData = setae.active_at(1) as SetaeData
	var s3: SetaeData = setae.active_at(3) as SetaeData
	assert_eq(s1.max_marks, 2)
	assert_gt(s1.strength_ref, s3.strength_ref)
	var rx: RunItem = cfg.item_by_id(&"rx9_reflex_overclock")
	assert_eq(rx.active_at(1).charge_max, 4.0)
	assert_lt(rx.active_at(1).charge_max, rx.active_at(2).charge_max)
	assert_lt(rx.active_at(2).charge_max, rx.active_at(3).charge_max)


func test_charges_climb_mark_by_mark() -> void:
	for it: RunItem in _active_items():
		var c: Array[float] = [it.active_at(1).charge_max, it.active_at(2).charge_max, it.active_at(3).charge_max]
		assert_true(c[0] <= c[1] and c[1] <= c[2], "%s charge %s" % [it.id(), c])
