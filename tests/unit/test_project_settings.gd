extends GutTest
## Guards the engine settings CLAUDE.md §9.1 decides on.


func _setting(path: String) -> String:
	return str(ProjectSettings.get_setting(path))


func test_uses_jolt_physics() -> void:
	assert_eq(_setting("physics/3d/physics_engine"), "Jolt Physics")


func test_default_renderer_is_mobile() -> void:
	assert_eq(_setting("rendering/renderer/rendering_method"), "mobile")


func test_android_texture_compression_enabled() -> void:
	assert_eq(_setting("rendering/textures/vram_compression/import_etc2_astc"), "true")


func test_static_typing_warnings_are_errors() -> void:
	for warning: String in ["untyped_declaration", "unsafe_property_access", "unsafe_method_access", "unsafe_cast", "unsafe_call_argument"]:
		assert_eq(_setting("debug/gdscript/warnings/" + warning), "2", warning)
