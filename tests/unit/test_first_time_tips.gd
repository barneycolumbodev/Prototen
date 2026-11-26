extends GutTest
## Survival's first-time tips (docs/design.md §8.11) show once ever, one at a time.

var tips: FirstTimeTips


func before_each() -> void:
	TutorialStore.clear_for_tests()
	tips = FirstTimeTips.new()
	add_child_autofree(tips)


func test_a_tip_shows_once_then_never_again() -> void:
	tips.trigger(&"drop")
	tips.trigger(&"drop")
	tips.trigger(&"new_gun")
	assert_eq(tips.queue.size(), 2, "no duplicates in the queue")
	await wait_process_frames(2)
	assert_eq(tips.showing, &"drop")
	assert_true(tips.card.is_presented())
	assert_true(TutorialStore.seen(&"drop"))
	var again: FirstTimeTips = FirstTimeTips.new()
	add_child_autofree(again)
	again.trigger(&"drop")
	assert_true(again.queue.is_empty(), "seen before: not shown again")
	TutorialStore.reset_tips()
	again.trigger(&"drop")
	assert_eq(again.queue.size(), 1, "show again brings it back")


func test_tips_take_turns() -> void:
	tips.trigger(&"run_start")
	tips.trigger(&"mark_one")
	await wait_process_frames(2)
	assert_eq(tips.showing, &"run_start")
	await wait_seconds(tips.config.tip_seconds + tips.config.tip_gap + 0.3)
	assert_eq(tips.showing, &"mark_one", "the next one after the first goes")
