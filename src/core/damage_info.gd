class_name DamageInfo
extends RefCounted
## Everything a hit carries (CLAUDE.md §9.2). Filled by weapons, read by
## damage zones, gore, AI and feedback.

enum Type { BALLISTIC, EXPLOSIVE, BLADE, BLUNT, EMP, FALL }

enum Flags {
	NONE = 0,
	HEADSHOT = 1,
	PENETRATED = 2,  ## the round passed through something before this hit
	PASS_THROUGH = 4,  ## the round exits the victim
	HEAVY = 8,  ## triggers hit-stop and stronger reactions
}

var amount: float = 0.0
var type: Type = Type.BALLISTIC
var penetration: float = 0.0
var impulse: float = 0.0
var zone: StringName = &""
var bone: StringName = &""
var point: Vector3 = Vector3.ZERO
var normal: Vector3 = Vector3.UP
var source: Node = null
var flags: int = Flags.NONE


func has_flag(flag: Flags) -> bool:
	return (flags & flag) != 0
