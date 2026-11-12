class_name ReticleStyle
extends RefCounted
## Reticle colours for every gun (owner, 2026-11-02): seaglass green-blue
## normally, crimson while the line of sight is on an enemy. Used by the HUD
## crosshair, the PSO scope view and the rail carbine's reflex reticle.

const SEAGLASS: Color = Color(0.47, 0.86, 0.78)
const CRIMSON: Color = Color(0.86, 0.08, 0.24)


## `enemy`: 0..1 how much the line of sight is on an enemy (eased by the caller).
static func color(enemy: float) -> Color:
	return SEAGLASS.lerp(CRIMSON, clampf(enemy, 0.0, 1.0))
