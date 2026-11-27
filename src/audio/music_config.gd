class_name MusicConfig
extends Resource
## Tuning for the adaptive score (MusicDirector, docs/design.md §6.4).
## Volumes are dB on the stem inside the Music bus; fades are real seconds.

@export_group("Layers")
## Tension Pulse while armed and nothing is happening (breathers, sneaking).
@export var tension_db: float = -4.0
## Tension under Combat Drive (it stays as the floor of the mix).
@export var tension_combat_db: float = -9.0
## Tension under a boss fight.
@export var tension_boss_db: float = -14.0
## Combat Drive while men are engaged.
@export var combat_db: float = -2.0
## Combat Drive under the Boss Threat layer.
@export var combat_boss_db: float = -6.0
## Boss Threat while a boss is up and fighting.
@export var boss_db: float = -1.0
## Tension lowered by this much between fights where lounge music plays
## (the Golden Dragon's speakers), so the jazz carries the breather.
@export var lounge_tension_db: float = -8.0

@export_group("Fades")
@export var fade_in: float = 1.6
@export var fade_out: float = 4.0
## Boss Threat comes in harder than the rest.
@export var boss_fade_in: float = 0.8
## Combat Drive stays this long after the last man stops engaging or the last hit taken.
@export var combat_hold: float = 7.0
## Score fade after death / the mode stopping.
@export var stop_fade: float = 3.0

@export_group("Engagement")
## A man counts as engaged in COMBAT within this distance of the operative.
@export var engage_range: float = 70.0
## ...or ALERT with at least this much awareness.
@export var engage_awareness: float = 0.85
## Seconds between scans of the enemies group.
@export var scan_interval: float = 0.25

@export_group("Time dilation")
## Music bus low-pass at full RX-9 dilation (the underwater throb).
@export var dilation_cutoff_hz: float = 340.0
## Filter resonance (a bump at the cutoff makes the kick and sub throb).
@export var dilation_resonance: float = 1.4
## Pitch/tempo of the score at full dilation (1 = normal).
@export var dilation_pitch: float = 0.86
## How much of the weapon wheel's slow motion reaches the score (0..1).
@export var slowmo_weight: float = 0.5
## Real seconds to ease into and out of the dilated sound.
@export var dilation_ease: float = 0.25

@export_group("Lounge")
## Lounge speakers (hotel lobby and bar jazz) during a wave or a fight.
@export var lounge_duck_db: float = -16.0
## Low-pass on the lounge while ducked (it goes behind the fight).
@export var lounge_duck_cutoff_hz: float = 900.0
@export var lounge_duck_time: float = 1.2
@export var lounge_swell_time: float = 5.0

@export_group("Stingers")
## dB per stinger (sting_<name>.ogg).
@export var stinger_db: Dictionary[StringName, float] = {
	&"wave_start": -2.0,
	&"wave_cleared": -3.0,
	&"supply_drop": -5.0,
	&"mk3": -2.0,
	&"boss_kneel": -1.0,
	&"run_over": -1.0,
}
## The layers dip by this much while a stinger rings, so it reads.
@export var stinger_duck_db: float = -6.0
@export var stinger_duck_time: float = 1.6
