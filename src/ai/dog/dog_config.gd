class_name DogConfig
extends Resource
## Tuning for the attack dog (docs/design.md §8.8b). The triad's German
## shepherds: no gun, no cover, no morale. They run straight at the operative
## by scent, leap the last few metres and bite, back off a step and go again.

## Health and the share each zone takes (keys: AttackDog.ZONES).
@export var health: float = 60.0
@export var zone_multipliers: Dictionary[StringName, float] = {
	&"head": 2.2, &"neck": 1.8, &"chest": 1.2, &"body": 1.0, &"leg": 0.6,
}

@export_group("Movement")
## Full gallop (m/s). The operative sprints at 11 and walks at 6.5: a dog
## catches a walking man and loses a sprinting one.
@export var run_speed: float = 9.5
## Circling and closing the last metres (m/s).
@export var trot_speed: float = 3.6
@export var acceleration: float = 26.0
@export var turn_speed_deg: float = 520.0
## Metres the gallop and trot animations cover per cycle at playback speed 1.
@export var run_stride: float = 2.0
@export var trot_stride: float = 1.1

@export_group("Lunge")
## It leaps from this far (with a clear line), never closer than lunge_min.
@export var lunge_range: float = 4.6
@export var lunge_min: float = 1.6
## Crouch before the spring (s): the tell.
@export var lunge_windup: float = 0.16
@export var lunge_speed: float = 11.5
@export var lunge_up: float = 3.0
## Mouth within this of the operative's chest in the air: the bite lands.
@export var lunge_reach: float = 0.95
@export var lunge_damage: float = 24.0
@export var lunge_push: float = 3.5
## Seconds on the ground after landing before it can leap again.
@export var lunge_cooldown: float = 1.4

@export_group("Bite")
## Standing bite when it's already at your legs.
@export var bite_range: float = 1.35
@export var bite_damage: float = 14.0
@export var bite_push: float = 1.5
## When in the 0.5 s bite the teeth close.
@export var bite_at: float = 0.2
@export var bite_cooldown: float = 0.75

@export_group("Hits")
## Damage in one hit that makes it flinch and yelp (and breaks a windup).
@export var flinch_damage: float = 9.0
@export var flinch_time: float = 0.3
## Share of a hit's impulse that shoves it (m/s per unit impulse).
@export var knock_per_impulse: float = 0.18
@export var gore_scale: float = 0.8

@export_group("Look")
## Readability at night (dog.gdshader, as the men's): fill from the viewer, cool rim.
@export var fill_light: float = 0.45
@export var rim_strength: float = 0.8
## Coat darkens and wets this much per hit (to 1).
@export var blood_per_hit: float = 0.12

@export_group("Voice")
## Seconds between growls while it runs in (random in range).
@export var growl_gap: Vector2 = Vector2(1.2, 2.6)
@export var bark_chance: float = 0.35
