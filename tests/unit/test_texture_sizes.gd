extends GutTest
## The 2K texture rule as a test (optimization overhaul H-02): no imported
## texture (or texture-array layer) larger than 2048 on a side, outside a
## short list of known exceptions with a reason each.

const LIMIT: int = 2048
const WHITELIST: Dictionary[String, String] = {
	"res://assets/levels/chinatown/lightmap.png": "the baked map lightmap: one texture for the whole map",
	"res://assets/characters/triad/textures/triad_basecolor.png": "to 2K in Phase 2 (overhaul C-02), checked on the face close-up",
	"res://assets/characters/triad/textures/triad_skin.png": "to 2K in Phase 2 (overhaul C-02), checked on the face close-up",
}


func _texture_sources(dir: String, out: PackedStringArray) -> void:
	var d: DirAccess = DirAccess.open(dir)
	if d == null:
		return
	for sub: String in d.get_directories():
		_texture_sources(dir.path_join(sub), out)
	for f: String in d.get_files():
		if not f.ends_with(".import"):
			continue
		var src: String = dir.path_join(f.trim_suffix(".import"))
		var ext: String = src.get_extension().to_lower()
		if ext in ["png", "webp", "jpg", "jpeg", "exr", "hdr", "tga", "bmp", "svg"]:
			out.append(src)


func test_no_texture_over_2k() -> void:
	var files: PackedStringArray = PackedStringArray()
	_texture_sources("res://assets", files)
	assert_gt(files.size(), 50, "found the imported textures")
	var over: PackedStringArray = PackedStringArray()
	for path: String in files:
		var res: Resource = load(path)
		var w: int = 0
		var h: int = 0
		if res is Texture2D:
			w = (res as Texture2D).get_width()
			h = (res as Texture2D).get_height()
		elif res is TextureLayered:
			w = (res as TextureLayered).get_width()
			h = (res as TextureLayered).get_height()
		else:
			continue
		if maxi(w, h) > LIMIT and not WHITELIST.has(path):
			over.append("%s (%d×%d)" % [path, w, h])
	assert_eq(over.size(), 0, "textures over %d: %s" % [LIMIT, ", ".join(over)])


func test_whitelist_is_current() -> void:
	for path: String in WHITELIST:
		assert_true(ResourceLoader.exists(path), "%s still exists (drop it from the list otherwise)" % path)
