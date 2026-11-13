# Credits and licenses

Every third-party file in the repository, with its source and license (CLAUDE.md §7).

| What | Where in repo | Source | Version | License |
|---|---|---|---|---|
| GUT (Godot Unit Test) | `addons/gut/` | https://github.com/bitwes/Gut | 9.7.1 | MIT (`addons/gut/LICENSE.md`) |
| Noto Serif TC (Black) and Noto Sans TC (Bold), only the unicode-range chunks the signs use | `raw_assets/env/fonts/serif/`, `raw_assets/env/fonts/sans/` | npm `@fontsource/noto-serif-tc`, `@fontsource/noto-sans-tc` (Adobe/Google Noto CJK) | 5.1.0 | SIL OFL 1.1 (`OFL.txt` in each folder). Used to draw the sign textures, neon tubes and the triads' tattooed characters; no font file ships in the game. |
| Kokoro-82M text-to-speech model (int8 ONNX) and its voice style vectors, used to speak the enemy callouts (tool only; the model doesn't ship, the clips it made do) | not in repo | hexgrad/Kokoro-82M via `onnx-community/Kokoro-82M-v1.0-ONNX`, fetched from npm: `kokoro-q8-shards` 1.0.0 (the model in six pieces, sha256 `fbae9257…a1478` checked) and `kokoro-js` 1.2.1 (voices); run with `kokoro-onnx` 0.6.1 (MIT) | v1.0 | Apache-2.0 |
| Whisper small (CTranslate2 int8), used only to check that every generated callout says its line (tool only, not shipped) | not in repo | OpenAI Whisper via npm `@skillninja/shortmovie-telop-model-p0..p3` 1.0.0 (sha256 checked), run with `faster-whisper` | small | MIT |
| GodotPrompter skills (12 of them) | `.claude/skills/` (all except the six project skills) | https://github.com/jame581/GodotPrompter @ d7b26cd | 2026-10-24 | MIT (`.claude/skills/GODOTPROMPTER-LICENSE.txt`) |

## Original assets (no third-party content)

| What | Where | How it was made |
|---|---|---|
| Gunplay sounds (29: shots, tail, reload, shells, impacts, confirms) | `assets/audio/sfx/` | Synthesized by `raw_assets/audio/build_weapon_sfx.py` (numpy/scipy). |
| Pistol 57 (model v2, 2K baked textures, body/slide/magazine parts) | `assets/weapons/pistol_57/` | `raw_assets/weapons/pistol_57/build.py` (Blender/bpy, procedural materials, high→low bake). |
| MG42/A machine gun (model, 4K baked textures, moving parts) | `assets/weapons/mg42/` | `raw_assets/weapons/mg42/build.py` (Blender/bpy, procedural materials, high→low bake). |
| First-person arms holding the MG42 | `assets/characters/fp_arms_mg42/` | `raw_assets/characters/fp_arms_mg42/build.py`. |
| MG42 sounds (13: shots, tail, belt reload beats, draw/holster) | `assets/audio/sfx/mg42_*`, `draw_1`, `holster_1` | Synthesized by `raw_assets/audio/build_mg42_sfx.py` (numpy/scipy). |
| Bullet hole, flash and particle textures | generated at runtime | `src/vfx/fx.gd` |
| RC-6 rail carbine (model, 4K baked textures, magazine/vent/glow/lens parts) | `assets/weapons/rail_carbine/` | `raw_assets/weapons/rail_carbine/build.py` (Blender/bpy, procedural materials, high→low bake). |
| First-person arms holding the rail carbine | `assets/characters/fp_arms_rail/` | `raw_assets/characters/fp_arms_rail/build.py`. |
| Rail carbine sounds (13: shots, tail, charge, ready, vent, overheat, reload beats, dry fire) | `assets/audio/sfx/rail_*` | Synthesized by `raw_assets/audio/build_rail_sfx.py` (numpy/scipy). |
| Railgun trail shader | `src/vfx/rail_trail.gdshader` | Written for this project. |
| Saiga-12K shotgun with PSO-pattern 1x optic (model, 4K baked textures, moving parts, tinted shell markers) | `assets/weapons/saiga12k/` | `raw_assets/weapons/saiga12k/build.py` (Blender/bpy, procedural materials, high→low bake). |
| First-person arms holding the Saiga-12K | `assets/characters/fp_arms_saiga/` | `raw_assets/characters/fp_arms_saiga/build.py`. |
| Saiga-12K sounds (17: shots, Dragon's Breath roar, tails, AK magazine and charging-handle beats, 12-gauge hulls, ember fire, shell-type click) | `assets/audio/sfx/saiga_*`, `shotshell_*`, `burn_1`, `ammo_select_1` | Synthesized by `raw_assets/audio/build_saiga_sfx.py` (numpy/scipy). |
| Bullet hole, flash, particle, ember and fire textures | generated at runtime | `src/vfx/fx.gd`, `src/weapons/ballistics.gd` |
| M14/P battle rifle (model, 4K baked textures, slide/magazine/stock parts) | `assets/weapons/m14p/` | `raw_assets/weapons/m14p/build.py` (Blender/bpy, procedural materials, high→low bake). |
| First-person arms holding the M14/P | `assets/characters/fp_arms_m14p/` | `raw_assets/characters/fp_arms_m14p/build.py`. |
| M14/P sounds (9: shots, tail, reload beats, dry fire) | `assets/audio/sfx/m14_*` | Synthesized by `raw_assets/audio/build_m14_sfx.py` (numpy/scipy). |
| MP5 with red-dot sight, suppressor and green laser (model, 4K baked textures, bolt/cocking handle/magazine/stock/lens/reticle/laser parts) | `assets/weapons/mp5/` | `raw_assets/weapons/mp5/build.py` (Blender/bpy, procedural materials, high→low bake). |
| First-person arms holding the MP5 | `assets/characters/fp_arms_mp5/` | `raw_assets/characters/fp_arms_mp5/build.py`. |
| MP5 sounds (11: shots, tail, reload beats, HK slap, dry fire) | `assets/audio/sfx/mp5_*` | Synthesized by `raw_assets/audio/build_mp5_sfx.py` (numpy/scipy). |
| Laser beam and dot shaders | `src/vfx/laser_beam.gdshader`, `src/vfx/laser_dot.gdshader` | Written for this project. |
| Weapon wheel icons (6) | `assets/ui/weapon_icons/` | Rendered from the game models by `raw_assets/ui/weapon_icons/build.py`. |
| Weapon wheel sounds (2) | `assets/audio/sfx/wheel_*` | Synthesized by `raw_assets/audio/build_ui_sfx.py`. |
| Triad enemy (rebuilt 2026-11-11): rigged body, a 24-item wardrobe (clothes, hair, hats, jewellery) as shells over it, one 4K atlas with painted skin, face, cloth and three tattoo sets, 17 animation clips, severable parts of the body and of every garment | `assets/characters/triad/` (`triad.gltf`, `triad_wardrobe.gltf`, `textures/`) | `raw_assets/characters/triad/build.py` with `body.py`, `wardrobe.py`, `paint.py`, `tattoos.py`, `common.py` (Blender/bpy metaballs, voxel remesh, garment shells cut along scalar fields, numpy painting from baked position maps, PIL-drawn tattoo designs; IK-posed clips). No MakeHuman/MPFB or Quaternius assets: their sites aren't reachable from the session. |
| Clothing prints (Hawaiian hibiscus, camo, check, cloud brocade), tileable | `assets/characters/triad/textures/triad_prints.png` | `raw_assets/characters/triad/build_prints.py` (numpy, PIL, scipy). |
| Wardrobe and outfit data | `data/enemies/wardrobe/`, `data/enemies/outfits/` | Written by `raw_assets/characters/triad/wardrobe_data.py`, then tuned as data. |
| Enemy callout voices (46 lines × 6 voices) | `assets/audio/voice/` | Spoken by Kokoro-82M (see above) in its male voices `am_michael`, `am_fenrir`, `am_puck`, `am_onyx`, `am_echo`, `bm_george`, then pitched and shaped into shouts by `raw_assets/audio/build_callout_voices.py` (numpy/scipy, ffmpeg Vorbis). The clips are outputs of the Apache-2.0 model; no recordings of anyone. |
| Enemy guns: Type 56 rifle, pump shotgun, SMG (low-poly, factor materials) | `assets/weapons/enemy/` | `raw_assets/weapons/enemy_guns/build.py`. |
| Blood textures (splat atlas, pool, droplet, mist) | `assets/gore/` | `raw_assets/gore/build_blood_textures.py` (numpy). |
| Enemy body shader (per-man tints, prints, tattoos, facial hair, painted wounds, char, fill and rim light), blood decal shader | `src/ai/triad.gdshader`, `src/gore/blood_decal.gdshader` | Written for this project. |
| Enemy and gore sounds (enemy shots ×3 guns, whizz/crack, pain, body fall, sever, reload; slide, mantle) | `assets/audio/sfx/enemy_*`, `whizz_*`, `body_fall_1`, `gore_sever_1`, `slide_1`, `mantle_1` | Synthesized by `raw_assets/audio/build_enemy_sfx.py` (numpy/scipy). |
| Environment material library (31 layers: brick, plaster, concrete, wet asphalt, pavers, granite, terrazzo, pier planks, dark wood, lacquer, cardboard, corrugated sheet, painted metal, roller shutter, rust, galvanised steel, grating, mosaic tile, glazed roof tile, roofing felt, epoxy floor, canvas, plastic, glass, damask wallpaper, emissive, lantern paper, and the sign/window/prop atlases) | `assets/env/world/` | `raw_assets/env/materials/build.py` and `raw_assets/env/atlases/build.py` (numpy/scipy/Pillow, procedural, tileable). |
| Chinatown docks map (geometry, colliders, spawn points, baked lightmap) | `assets/levels/chinatown/` | `raw_assets/levels/chinatown/build.py` + `bake.py` (Blender/bpy, Cycles CPU bake). |
| Night sky, harbour water, far-shore skyline, rain and steam shaders | `src/levels/chinatown/*.gdshader` | Written for this project. |
| Chinatown ambience (rain, harbour with ship horn, neon hum, kitchen extractor, radio tune) | `assets/audio/sfx/amb_*` | Synthesized by `raw_assets/audio/build_ambience.py` (numpy). |
| Enemy death voices (screams, choking, groans, last breath) and ricochet whines | `assets/audio/sfx/death_*`, `ricochet_*` | Synthesized by `raw_assets/audio/build_voice_sfx.py` (source-filter voice model) and `build_enemy_sfx.py` (numpy/scipy). No recordings. |
| Harbour night sky panorama | `assets/env/sky/harbour_night.png` | `raw_assets/env/sky/build_night_sky.py` (numpy, procedural). |
| RX-9 time-slowdown sounds (engage, release, heartbeat loop, denied) | `assets/audio/sfx/td_*` | Synthesized by `raw_assets/audio/build_augment_sfx.py` (numpy/scipy). |
| GX-4 Gauss arm sounds (shots, tail, crack, deploy and stow sequences, hum loop, recharge, empty, dry, zaps) | `assets/audio/sfx/gx4_*` | Synthesized by `raw_assets/audio/build_gauss_sfx.py` (numpy/scipy). |
| Dull casing, shutter, sheet-metal and ricochet sounds (replace the ringing ones) | `assets/audio/sfx/shell_*`, `impact_metal_1`, `impact_can_1`, `ricochet_*` | Synthesized by `raw_assets/audio/build_metal_sfx.py` (numpy/scipy). |
| GX-4 Gauss arm (prosthetic forearm coilgun, transform animation) | `assets/augments/gx4_gauss_arm/` | `raw_assets/augments/gx4_gauss_arm/build.py` (Blender/bpy, procedural hard-surface, keyframed object animation). |
| Active parts of 2026-11-10: first-person models with deploy clips (whip arm, mesh arm, fan shield, arc projector, Shrike drone) | `assets/augments/{mw7_monofilament_whip,nt5_mesh_arm,bw6_fan_shield,ad2_arc_projector,sd3_shrike_drone}/` | `raw_assets/augments/actives/<id>/build.py` with the shared `_kit.py` (Blender/bpy, procedural hard-surface, keyframed object animation). |
| Active parts of 2026-11-10: hardware on the body (seven baked sets) | `assets/augments/actives_body/` | `raw_assets/augments/actives/body_hardware.py` (Blender/bpy with the passive-hardware kit, baked with Cycles). |
| Active parts' sounds (whip, mesh arm, shield, drone, explosion, arc, thrusters, shroud: 42 files) | `assets/audio/sfx/{mw7,nt5,bw6,sd3,ad2,kr5,tc4}_*`, `explosion_*` | Synthesized by `raw_assets/audio/build_actives_sfx.py` (numpy/scipy). |
| SX-8 Urticating Setae: first-person forearm with deploy clip; hardware on the body | `assets/augments/sx8_urticating_setae/`, `assets/augments/actives_body/sx8_urticating_setae/` | `raw_assets/augments/actives/sx8_urticating_setae/build.py` (with `_kit.py`) and `body_hardware.py --part sx8_urticating_setae` (Blender/bpy). The fibres and needles are generated in code (`src/augments/active/setae/setae.gd`). |
| SX-8 sounds (13: deploy, stow, mark, denied, dead-eye loop, windup, throw, punctures, cavities) | `assets/audio/sfx/sx8_*` | Synthesized by `raw_assets/audio/build_setae_sfx.py` (numpy/scipy). |
| Region maps for the colour customizer | `assets/characters/*/textures/*_regions.png` | Derived from this project's own baked textures and meshes by `tools/colors/build_regions.py`. |
| Augment hardware on the operative: 20 passives (CT-7, HS-5, NL-3, KD-2, EM-2, TL-3, SA-2, DL-1, HM-5, TN-9, FC-1, VS-1, PC-3, SP-6, KS-2, RP-2, OB-5, MR-1, CM-1, DG-3) and the RX-9 module (1024² baked texture sets) | `assets/augments/passives/`, `assets/augments/rx9_reflex_overclock/` | `raw_assets/augments/passives/<id>/build.py` sharing `_common.py`, and `raw_assets/augments/rx9_reflex_overclock/build.py` (Blender/bpy, modelled on the operative, procedural materials, HIGH → LOW Cycles bake). Stencil lettering uses Blender's built-in default font, baked into the textures; no font file ships. |
| The operative: player base body in the GS-2 graft suit, helmet, and bare head with the owner's face (rigged, same skeleton as the triad) | `assets/characters/operative/` | `raw_assets/characters/operative/build.py` (signed distance fields in numpy meshed with surface nets via `raw_assets/_lib/sdf.py`, HIGH → LOW Cycles bake, analytic weights). Face from the owner's own photos (used with permission; photos not committed) via `likeness/capture.py`. |
| Face landmark model used to capture the owner's face (tool only, not shipped) | not in repo | MediaPipe Face Landmarker `face_landmarker.task`, Google, Apache-2.0 (storage.googleapis.com/mediapipe-models). |
| Canonical face mesh topology and UV layout (468 vertices, 898 triangles) | `raw_assets/characters/operative/likeness/face_tris.npy`, `face_uv.npy` | MediaPipe `canonical_face_model.obj`, Google, Apache-2.0 (github.com/google-ai-edge/mediapipe, `mediapipe/modules/face_geometry/data`). |
