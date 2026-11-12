class_name GoreConfig
extends Resource
## Dismemberment and gibbing (docs/design.md §5.5; owner, 2026-11-11:
## Soldier of Fortune style, "decapitations, dismemberments, gibbing, based
## on ballistic impact and location"). data/gore/gore_default.tres.
##
## How a hit takes a body apart (Dismemberment):
## - The body comes apart at cuts: the neck (head), 60 % down each upper arm,
##   the forearms, the wrists (hands), 65 % down each thigh (above the knee)
##   and below the knees. Cuts nest: an arm off at the upper arm takes the
##   forearm and hand with it.
## - A hit's violence at a zone = energy it left there + a share of the energy
##   it arrived with (a fast round going through still tears: the ballistics
##   only take ~11 J per cm out of a rifle round, far less than the cavity it
##   makes), × the damage type's factor (blades cut far above their energy).
## - It acts on the cut nearest where it landed: full strength within
##   `full_m`, falling to nothing `reach_m` away. A thigh hit near the knee
##   takes the leg off below the knee; near the hip, above it. A hit on the
##   head itself acts on the head at full strength.
## - One volley (a shot, a shotgun shell) past a cut's threshold severs it.
##   Hits of at least `min_share` of the threshold add up, and the sum severs
##   at threshold × `accumulate_factor`: a few pistol rounds take a hand or a
##   forearm, sustained fire saws a leg off.
## - Energy that stays in the piece destroys it instead (chunks, no limb):
##   past threshold × `pulp_factor` left in it by one volley (buckshot at
##   arm's length, a blast). A round that goes clean through severs.
## - The head: a hit on it past `head_destroy_j` breaks it apart (skull cap,
##   jaw, chunks); between `head_j` and that it comes off whole; a neck hit
##   past `head_j` takes it off whole.
## - The torso has no cut: a big enough volley into it (or into a corpse over
##   time) bursts the whole body. Blasts sever by distance and gib up close.
## Only at Maximum gore; Standard keeps wounds and blood.
##
## Retuned 2026-11-11 (owner's playtest: "no heads, arms, or anything else is
## coming off"). Measured with every gun at every zone: with the first
## numbers only the rail carbine and the Gauss arm ever met a threshold.

## × every threshold below (Pause → Tuning → Gore). Under 1: bodies come
## apart more easily.
@export_range(0.2, 4.0) var toughness: float = 1.0
## × how much blood a hit throws (Pause → Tuning → Gore).
@export_range(0.2, 3.0) var blood_amount: float = 1.0
@export_group("Cut thresholds (J)")
@export var head_j: float = 600.0
@export var upper_arm_j: float = 1000.0
@export var forearm_j: float = 600.0
@export var hand_j: float = 300.0
@export var thigh_j: float = 1300.0
@export var shin_j: float = 750.0
@export_group("Violence of a hit")
## Share of the energy a round arrived with that counts on top of what it left.
@export_range(0.0, 1.0) var arrival_share: float = 0.3
## × for blades (the monofilament whip) and blunt (strikes, slides).
@export var blade_factor: float = 2.2
@export var blunt_factor: float = 0.5
@export var explosive_factor: float = 1.0
## Cuts within this distance of the hit feel it (m); full strength within
## `full_m`.
@export var reach_m: float = 0.4
@export var full_m: float = 0.1
@export_group("Severing")
## Past threshold × this left in the piece by one volley, it is destroyed,
## not severed.
@export var pulp_factor: float = 2.6
## A hit on the head past this breaks it apart (J): skull and jaw fragments.
@export var head_destroy_j: float = 800.0
## Hits under this share of a threshold don't add up toward it...
@export_range(0.0, 1.0) var min_share: float = 0.2
## ...and the sum of those that do severs at threshold × this.
@export var accumulate_factor: float = 1.25
## Speed a severed piece flies at per kJ of the hit (m/s), and the most.
@export var fling_per_kj: float = 0.9
@export var fling_min: float = 2.0
@export var fling_max: float = 6.5
@export_group("Gibbing")
## One volley into the torso (chest, stomach, pelvis) past this bursts the body.
@export var gib_volley_j: float = 12000.0
## A corpse that has taken this much in total bursts (sustained fire on a body).
@export var gib_corpse_j: float = 8000.0
## Blasts: a cut this close to the blast (1 = at the centre, 0 = at the edge
## of the radius) comes off; this close to the chest, the body bursts.
@export_range(0.0, 1.0) var blast_sever_f: float = 0.45
@export_range(0.0, 1.0) var blast_gib_f: float = 0.8
## Speed the pieces of a burst body fly at (m/s).
@export var gib_speed: float = 7.5
## Organ, rib and meat pieces thrown by a burst torso.
@export_range(0, 16) var gib_torso_pieces: int = 8


## Threshold for a segment (J).
func threshold(segment: StringName) -> float:
	var s: String = String(segment)
	if s == "head":
		return head_j * toughness
	if s.begins_with("upper_arm"):
		return upper_arm_j * toughness
	if s.begins_with("forearm"):
		return forearm_j * toughness
	if s.begins_with("hand"):
		return hand_j * toughness
	if s.begins_with("thigh"):
		return thigh_j * toughness
	if s.begins_with("shin"):
		return shin_j * toughness
	return INF


## × for a damage type.
func type_factor(type: DamageInfo.Type) -> float:
	match type:
		DamageInfo.Type.BLADE:
			return blade_factor
		DamageInfo.Type.EXPLOSIVE:
			return explosive_factor
		DamageInfo.Type.BLUNT, DamageInfo.Type.FALL:
			return blunt_factor
	return 1.0


## How much of a hit reaches a cut `d` metres away (0..1).
func falloff(d: float) -> float:
	if d <= full_m:
		return 1.0
	return clampf(1.0 - (d - full_m) / maxf(reach_m - full_m, 0.001), 0.0, 1.0)
