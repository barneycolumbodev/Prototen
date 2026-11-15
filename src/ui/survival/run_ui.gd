class_name RunUi
extends RefCounted
## Shared look for the Survival screens (kit, drop, run over): the main
## menu's seaglass accent on dark glass, and text helpers.

const C_ACCENT: Color = Color(0.36, 0.86, 0.78)
const C_TEXT: Color = Color(0.86, 0.88, 0.88)
const C_DIM: Color = Color(0.52, 0.58, 0.6)
const C_WARN: Color = Color(1.0, 0.62, 0.3)
const C_GOLD: Color = Color(1.0, 0.82, 0.42)
const C_GLASS: Color = Color(0.02, 0.025, 0.03, 0.86)


static func label(text: String, size: int, color: Color = C_TEXT, wrap: bool = false) -> Label:
	var l: Label = Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	if wrap:
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


static func title_font() -> FontVariation:
	var fv: FontVariation = FontVariation.new()
	fv.base_font = ThemeDB.fallback_font
	fv.spacing_glyph = 6
	fv.variation_embolden = 0.6
	return fv


static func box(lit: bool, accent: Color = C_ACCENT) -> StyleBoxFlat:
	var sb: StyleBoxFlat = StyleBoxFlat.new()
	sb.bg_color = Color(accent.r, accent.g, accent.b, 0.12) if lit else C_GLASS
	sb.border_color = accent if lit else Color(C_DIM.r, C_DIM.g, C_DIM.b, 0.35)
	sb.set_border_width_all(2 if lit else 1)
	sb.border_width_left = 5 if lit else 1
	sb.set_content_margin_all(18)
	sb.set_corner_radius_all(2)
	return sb


## A full-screen dark wash (a layer for the screens to sit on).
static func wash(alpha: float = 0.72) -> ColorRect:
	var r: ColorRect = ColorRect.new()
	r.color = Color(0.0, 0.0, 0.0, alpha)
	r.set_anchors_preset(Control.PRESET_FULL_RECT)
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r


static func tags_text(tags: Array[StringName]) -> String:
	var out: PackedStringArray = PackedStringArray()
	for t: StringName in tags:
		out.append(String(t).to_upper())
	return "  ·  ".join(out)


## Plain names for the tuning values a mark changes.
const NAMES: Dictionary[StringName, String] = {
	&"charge_max": "Charge", &"world_scale": "World speed", &"regen_per_s": "Refill per second",
	&"base_marks": "Marks", &"max_marks": "Most marks", &"strength_ref": "Strength for full damage",
	&"cavity_damage": "Cavitation damage", &"length": "Length (m)", &"damage": "Damage",
	&"dash_speed": "Burn speed (m/s)", &"ram_multiplier": "Ram force", &"reveal_m": "Seen within (m)",
	&"shot_reveal_time": "Shown after a shot (s)", &"break_cooldown": "Recovery after a break (s)",
	&"bash_bonus": "Bash", &"reach": "Reach (m)", &"max_throw": "Throw (m/s)", &"battery": "Battery (s)",
	&"blast_radius": "Blast radius (m)", &"blast_damage": "Blast damage", &"chains": "Chains",
	&"max_chains": "Most chains", &"base_capacity": "Rounds held", &"min_capacity": "Fewest rounds held",
	&"max_capacity": "Most rounds held",
}


static func _num(v: Variant) -> String:
	if v is float:
		var f: float = v
		return ("%.0f" % f) if absf(f - roundf(f)) < 0.001 else ("%.2f" % f).trim_suffix("0")
	return str(v)


## What a mark changes: "Charge max  4 → 6" per overridden property.
static func mark_changes(it: RunItem, from_mark: int, to_mark: int) -> String:
	var part: ActivePartData = it.item as ActivePartData
	if part == null:
		return ""
	var keys: Array[StringName] = []
	for k: StringName in it.overrides(from_mark):
		keys.append(k)
	for k: StringName in it.overrides(to_mark):
		if k not in keys:
			keys.append(k)
	var a: ActivePartData = it.active_at(from_mark) if from_mark > 0 else null
	var b: ActivePartData = it.active_at(to_mark)
	var lines: PackedStringArray = PackedStringArray()
	for k: StringName in keys:
		var name: String = NAMES[k] if NAMES.has(k) else String(k).replace("_", " ").capitalize()
		if a:
			lines.append("%s  %s → %s" % [name, _num(a.get(k)), _num(b.get(k))])
		else:
			lines.append("%s  %s" % [name, _num(b.get(k))])
	return "\n".join(lines)
