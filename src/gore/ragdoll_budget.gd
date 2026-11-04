extends Node
## Caps simulating ragdolls (CLAUDE.md §8: ≤ 3, frozen after about 2.5 s).
## Autoloaded as RagdollBudget. When a fourth starts, the oldest freezes.

const MAX_ACTIVE: int = 3
const FREEZE_AFTER: float = 2.5

var _active: Array[Node] = []


func started(body: Node) -> void:
	_prune()
	_active.erase(body)
	_active.append(body)
	while _active.size() > MAX_ACTIVE:
		var oldest: Node = _active.pop_front()
		if oldest.has_method(&"freeze"):
			oldest.call(&"freeze")


func stopped(body: Node) -> void:
	_prune()
	_active.erase(body)


func active_count() -> int:
	_prune()
	return _active.size()


func _prune() -> void:
	var keep: Array[Node] = []
	for x: Variant in _active:
		if is_instance_valid(x):
			var n: Node = x
			keep.append(n)
	_active = keep
