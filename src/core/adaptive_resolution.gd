class_name AdaptiveResolution
extends Node
## Holds the frame rate by trading 3D resolution when the GPU falls behind
## (playtest 2026-11-05: Chinatown ran at 28-29 fps on the Moto G). The HUD
## and text always render at full resolution; only the 3D view scales.
##
## Every WINDOW seconds it averages the GPU frame time (and the real frame
## time, in case the driver doesn't report GPU time). Over budget: scale
## down in proportion (pixels ∝ scale²). Comfortably under budget for a
## while: step back up toward the player's chosen render scale. Never below
## MIN_SCALE. Off in the pause menu (Render scale: fixed), and held still
## during benchmarks.

const WINDOW: float = 0.5
const MIN_SCALE: float = 0.6
const STEP_UP: float = 0.05
## Budget as a share of the frame (leaves room for the CPU and vsync jitter).
const BUDGET_SHARE: float = 0.88
## Missed frames only count against resolution when the GPU timer is silent
## or says the GPU is busy (above this share of its budget). With the GPU at
## half load, a missed frame is the CPU's or the pacing's: fewer pixels
## wouldn't bring it back, only blur the picture (2026-11-12: the owner saw
## 45 fps at 70 % and at the 60 % floor alike, and a grainier image).
const GPU_BUSY: float = 0.75
## A GPU this far under budget may climb back up even while frames miss.
const GPU_IDLE: float = 0.6

var enabled: bool = true
## The player's render scale: the most this will use.
var max_scale: float = 1.0
## Benchmarks set this so they measure a fixed resolution.
var held: bool = false
var scale: float = 1.0

var _t: float = 0.0
var _gpu_sum: float = 0.0
var _frame_sum: float = 0.0
var _n: int = 0
var _calm_windows: int = 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
	scale = max_scale


func configure(on: bool, user_scale: float) -> void:
	enabled = on
	max_scale = user_scale
	scale = user_scale if not on else minf(scale, user_scale)
	_apply()


func _process(delta: float) -> void:
	if not enabled or held or get_tree().paused:
		return
	_t += delta
	_frame_sum += delta * 1000.0
	_gpu_sum += RenderingServer.viewport_get_measured_render_time_gpu(get_viewport().get_viewport_rid())
	_n += 1
	if _t < WINDOW:
		return
	var gpu: float = _gpu_sum / _n
	var frame: float = _frame_sum / _n
	_t = 0.0
	_gpu_sum = 0.0
	_frame_sum = 0.0
	_n = 0
	var budget: float = frame_budget_ms()
	var next: float = clampf(step(scale, gpu, frame, budget, _calm_windows), MIN_SCALE, max_scale)
	_calm_windows = _calm_windows + 1 if is_calm(gpu, frame, budget) else 0
	if not is_equal_approx(next, scale):
		scale = next
		_calm_windows = 0
		_apply()


func frame_budget_ms() -> float:
	var fps: int = Engine.max_fps if Engine.max_fps > 0 else 60
	return 1000.0 / fps


static func is_calm(gpu_ms: float, frame_ms: float, budget_ms: float) -> bool:
	var gpu_ok: bool = gpu_ms <= 0.0 or gpu_ms < budget_ms * BUDGET_SHARE * 0.72
	var gpu_idle: bool = gpu_ms > 0.0 and gpu_ms < budget_ms * BUDGET_SHARE * GPU_IDLE
	return gpu_ok and (frame_ms < budget_ms * 1.06 or gpu_idle)


## The next scale for one window of measurements. Pure, for tests.
static func step(current: float, gpu_ms: float, frame_ms: float, budget_ms: float, calm_windows: int) -> float:
	var target: float = budget_ms * BUDGET_SHARE
	var load_ms: float = gpu_ms if gpu_ms > 0.0 else 0.0
	# Missed frames show in the frame time even when the GPU timer is silent.
	if frame_ms > budget_ms * 1.2 and (gpu_ms <= 0.0 or gpu_ms > target * GPU_BUSY):
		load_ms = maxf(load_ms, frame_ms * BUDGET_SHARE)
	if load_ms > target:
		var k: float = sqrt(target / load_ms)
		return maxf(MIN_SCALE, maxf(current * k, current - 0.15))
	if is_calm(gpu_ms, frame_ms, budget_ms) and calm_windows >= 3:
		return current + STEP_UP
	return current


func _apply() -> void:
	get_tree().root.scaling_3d_scale = scale
