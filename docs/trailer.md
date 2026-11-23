# Trailer (2026-11-23)

Owner, 2026-11-23: a completely new 30-second trailer for social media, made with Godot's Movie Maker. Every gameplay clip is the real game, choreographed by Claude and rendered headless at 1080p60; the non-gameplay shots (the street crane, the atrium tilt, the bullet-time replay) are cameras flown through the real maps. "It has to look like a trailer."

## The cut (30.0 s, 1920×1080, 60 fps)

| Time | Shot | What happens |
|---|---|---|
| 0.0 | `establish` | Crane down the Chinatown street at night in the rain; triad men in the road look up at the lens. **THEY'RE ONLY HUMAN.** |
| 3.0 | `atrium` | Dolly through the Golden Dragon's arch, tilting up to the coffered ceiling and chandeliers. |
| 4.5 | `catcher` | First person: rounds from three gunmen stopping in the LC-6 field. **YOU'RE NOT.** (braam) |
| 6.0 | `slide` | Drop. Sprint, slide into a gunman, he's launched; RX-9; Saiga-12K into him in midair, then his partner. |
| 7.75 | `slagger` | The SL-9 charged to full in the rain; the bolt through a man's chest, he burns. |
| 9.6 | `catcher` | A lift chimes and opens on a Hatchet Man; he charges; let go of LB and forty caught rounds go back into him. |
| 11.4 | `gauss` + `gauss_side` | RX-9 on, the GX-4 unfolds, one round through three men; cut to the bullet-time replay beside the line as they come apart. |
| 14.8 | `corridor` | The hotel's west corridor: the Governor, one man per round, lever thrown between; vault the room-service trolley; KR-5 ram into the last man. |
| 18.3 | `dropkick` | Into the atrium at a run, jump, RX-9, dropkick; the Governor into him while he's in the air (canted dive pose). |
| 20.1 | `boss` | The Incense Master charging his Gauss prosthetic; then down on one knee and the first-person execution, the head goes. |
| 24.0 | black | Half a second of silence. |
| 24.5 | end card | **GRAFT** slams in, a cyan rule, **COMING SOON**. |

Hardware callouts (lower left) name each part as it plays: RX-9, SL-9, LC-6, GX-4, the Governor, KR-5, the Incense Master.

## How it's made

- `src/trailer/trailer_shot.gd` (`TrailerShot`): the base of every shot. A map scene started with `-- --trailer=<shot>` (hooked in `ChinatownMap._start_game`, so the hotel too) loads like Sandbox with no spawns and adds the shot. It stages men on marks (`spawn`, `alert`, `enemy_fire` through the enemy's own `_fire_at`), sets the operative's body (`loadout`) and gun, and drives him only through the controller's actions (`press`/`tap` on Input actions), the gun's and parts' script hooks, and a look steered like a thumb on the stick (`aim`). It hides the HUD (crosshair, ammo, bars, subtitles, debug overlay) but keeps screen effects (RX-9's tint, the ram streaks). It drops the master bus 9 dB for headroom (fights clipped at 0 dBFS). Global RNG seeded, so takes repeat exactly at any resolution.
- `src/trailer/shots/*.gd`: one script per shot; each starts with `## scene:` (the map) and `## frames:` (how many frames to record). `scout.gd` / `scout_hotel.gd` frame camera positions for planning (`--scout=x,y,z,tx,ty,tz,fov/...` in Blender coordinates).
- `tools/trailer/render.sh <shot> [preview|final]`: Movie Maker (`--write-movie`, `--fixed-fps 60`) under Xvfb on lavapipe, Forward+ renderer, into `trailer_out/<quality>/<shot>/` (PNG per frame + the game's own audio as `f.wav`). Preview is 960×540 (about 0.4 s/frame); final is 1920×1080 with MSAA 4×, 4096 shadow atlases, anisotropic 4×, LOD threshold 0.5 (about 2.5 s/frame), set through a temporary `settings_override.cfg` that's restored afterwards. `TRAILER_ARGS` passes shot arguments (`--cam=side` for the Gauss replay), `TRAILER_TAG` names the output folder.
- `tools/trailer/sheet.py`: contact sheets of a rendered shot (how every take was checked).
- `tools/trailer/cut.py` → `tools/trailer/edit.json`: the clip list (shot, in/out frames); captions, score cues and the end card are derived from the frame counts.
- `tools/trailer/titles.py`: the captions, the hardware callouts and the end card as PNG sequences (Rajdhani, SIL OFL, `raw_assets/trailer/fonts/`).
- `raw_assets/trailer/score.py`: the music, synthesized with numpy (no samples): drone, guzheng plucks (Karplus-Strong), braams, risers, impacts, a 120 BPM distorted bass ostinato, kick/clap/taiko/hats, a string ostinato, timed to the cut.
- `tools/trailer/assemble.py [preview|final]`: cuts the PNG sequences and WAVs by frame, grades (contrast, teal shadows and warm highs, vignette, fine grain), overlays the text, levels each clip's game audio to the same loudness, ducks the score under gunfire, limits, and encodes H.264 high (CRF 14) + AAC 256k to `trailer_out/graft_trailer_<quality>.mp4`.

Rebuild everything: render each shot (`tools/trailer/render.sh <shot> final`, plus `TRAILER_TAG=side TRAILER_ARGS=--cam=side` for `gauss`), then `tools/trailer/cut.py && tools/trailer/assemble.py final`.

## Game changes that came with it

- **Movie-aware clock** (`TimeControl.now_msec()` / `now_sec()`): hit-stop and the rate limits (callouts, death screams, ricochets, smoke, fire, the catcher's "full" sound) used the wall clock. Under Movie Maker a frame takes seconds of real time, so hit-stop vanished and voice lines stacked. Now they count the unscaled time of the frames drawn when the `movie` feature is on; on a device nothing changes.
- **Enemy muzzle flash**: its mesh had no UVs, so the soft flash texture sampled one texel and every flash drew as a flat white card (most visible in slow motion). Now UV-mapped and alpha-blended additively: an orange glowing tongue.

## Notes

- Lighting is the real maps' baked lighting; the renderer is Forward+ at PC quality, not the phone's Mobile renderer, and the image is graded in the edit. Simulation, models, animation and effects are the same as on the phone.
- The working title GRAFT is on the end card (`tools/trailer/cut.py`, `title.name`); change it there when the title is decided.
- The operative's helmet-off close-up (the main menu figure, with the owner's face) was tried and left out: it looked stiff, and the owner's face shouldn't go public without asking.
