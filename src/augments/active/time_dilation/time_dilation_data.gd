class_name TimeDilationData
extends ActivePartData
## RX-9 Reflex Overclock (owner, 2026-11-05): the first active part. Grounded
## reading: a neural co-processor overclocks perception and motor control,
## so the world seems to crawl while the operative still moves fast. Tuning
## in data/body/parts/rx9_reflex_overclock.tres.

@export_group("Time")
## How fast the world runs while it's on (0.3 = 30 %).
@export_range(0.05, 1.0) var world_scale: float = 0.3
## How fast the operative runs (movement, gun, reloads). Looking is always real time.
@export_range(0.05, 1.0) var player_scale: float = 0.65

@export_group("Feel")
## Ragdoll and limb impulses, and blood sprays, are this much heavier while
## dilated (F.E.A.R.-style impacts; docs/design.md §3.4).
@export var impact_boost: float = 1.8
## Colour saturation of the world while dilated (1 = normal).
@export_range(0.0, 1.0) var saturation: float = 0.55
## Everything you hear is muffled to this low-pass cutoff (Hz).
@export var lowpass_hz: float = 2400.0
## Field of view widens by this many degrees as it kicks in.
@export var fov_kick_deg: float = 3.0
@export var tint: Color = Color(0.45, 0.85, 0.95, 0.16)
