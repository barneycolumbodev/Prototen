#!/usr/bin/env python3
"""Every remaining firearm's shot and tail from real recordings (CC0; see CREDITS.md).

Owner, 2026-11-27 (the audio pass): "replace all the firearms that use Python
to generate a synthetic sound effect for the firing ... find and locate real
recordings of those firearms being fired, and then modify those ... all of the
firearms need to have distinct, realistic, real sounds."

The MG42, the SPAS-12 and the .44 Magnum already had real shots
(build_mg42_real_sfx.py, build_spas12_real_sfx.py, build_magnum44_sfx.py).
This does the rest. Each gun gets the recording of the closest real gun that
could be found under CC0, and no two guns share a source take:

  gun (prefix)          recording(s)
  Five-seveN (shared)   SIG Sauer P226, suppressed, 9 mm (areniporgen)
  MP5/SD-L (mp5_)       FN FNX-45 + SilencerCo Osprey, and a Springfield 1911
                        Operator, suppressed, .45 ACP (areniporgen)
  M14/P (m14_)          Tikka T3 .30-06 bolt gun (library), with a can's
                        effect applied (no usable suppressed .308 recording)
  Glock 22 (glock_)     a Walther PPQ's range report (Free Firearm Sound
                        Library) over a Glock 19X (areniporgen; a phone's
                        limiter squashed its crack), a little lower for .40;
                        the tail a 9 mm pistol 15 m out on a range (johanwestling)
  AUG (aug_)            AR-15, 5.56 (library)
  Saiga-12K (saiga_)    Winchester Model 12, 12-gauge (library)
    Dragon's Breath     the Model 12's other take, the bang held lower, with a
                        synthesized roar of the burning jet over it (no
                        recording of a real Dragon's Breath round was found)
  Governor (governor_)  Marlin 336 lever action (library) over a Mosin-Nagant's
                        boom (library): a .45-70 is a big, slow round
  M32A1 (m32_)          M203 40 mm launches: a US Navy training video (public
                        domain, via qubodup) and LeMudCrab's recording
  Enemy Type 56         AK-47, 7.62x39 (library): a Type 56 is a Chinese AK
  Enemy Type 85 SMG     PPSh-41 (library): the same 7.62x25 Tokarev round
  Enemy pump shotgun    Benelli Nova and Mossberg near takes (library; the
                        SPAS-12 uses the mid-distance takes), racked after
                        each shot with the SPAS-12's real Remington 870 strokes

Processing (raw_assets/audio/_real_gun.py): each shot is cut from its onset,
its 1 ms spike held down so the blast and body come up (a phone plays those),
the range's slap-backs ducked, 150-250 Hz pushed and the lows saturated for
weight on a small speaker, and automatic guns' shots shortened with a decay
after the body so back-to-back rounds don't smear. Tails are the same guns'
own range decay, darker, faded in under the shot.

The rail carbine, the SL-9 Slagger and the GX-4 are not firearms (a railgun,
plasma, a Gauss arm): they keep their synthesized sounds.

Usage: python3 raw_assets/audio/build_real_guns_sfx.py [out_dir] [--only=prefix,...]
Needs numpy, scipy, ffmpeg.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _real_gun as g  # noqa: E402

SR = g.SR
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT = ARGS[0] if ARGS else "assets/audio/sfx"
ONLY = next((a.split("=", 1)[1].split(",") for a in sys.argv[1:] if a.startswith("--only=")), None)

FA = os.path.join(HERE, "fetched", "firearms")
LIB = os.path.join(FA, "oga_Prepared_SFX_Library")
LIB_OLD = os.path.join(HERE, "fetched", "oga_Prepared_SFX_Library")

P226 = (FA, "fs_828790_*")
FNX = (FA, "fs_693855_*")
M1911S = (FA, "fs_827945_*")
JW9 = (FA, "fs_377789_*")
# The SPAS-12's real pump strokes, already cut (for the enemy pump gun's rack).
OUT_REF = os.path.join(HERE, "..", "..", "assets", "audio", "sfx")
G19X = (FA, "fs_828786_*")
M203_Q = (FA, "fs_162402_*")
M203_L = (FA, "fs_163458_*")


def lib(name, old=False):
    return (LIB_OLD if old else LIB, f"*{name}*")


def L(src, index, gain=1.0, pitch=1.0, delay=0.0, lp=0.0, hp=35.0, squash=None, gap=0.8, fx=None):
    """One layer of a shot: the `index`th shot in `src`; `fx` runs after the squash."""
    return dict(src=src, index=index, gain=gain, pitch=pitch, delay=delay, lp=lp, hp=hp, squash=squash, gap=gap,
                fx=fx)


# Loudness of each bank (RMS dB over the window in s): the levels the
# synthesized sounds were mixed at, so the game's mix and each gun's
# shot_volume_db stay as tuned. Two exceptions: the Governor's synthesized shot
# was a sustained low ring at -4 dB RMS and the M32's at -11, which a real
# report can't match without being crushed by the limiter. Tails over 1 s.
LEVELS = {
    "shot": (-20.7, 0.25), "tail": (-26.1, 1.0),
    "mp5_shot": (-23.2, 0.25), "mp5_tail": (-30.0, 1.0),
    "m14_shot": (-18.5, 0.25), "m14_tail": (-25.4, 1.0),
    "glock_shot": (-22.4, 0.25), "glock_tail": (-26.8, 1.0),
    "aug_shot": (-22.5, 0.25), "aug_tail": (-24.6, 1.0),
    "saiga_shot": (-17.9, 0.25), "saiga_tail": (-24.3, 1.0),
    "saiga_db_shot": (-16.4, 0.25), "saiga_db_tail": (-23.2, 1.0),
    "governor_shot": (-13.0, 0.25), "governor_tail": (-21.5, 1.0),
    "m32_shot": (-13.0, 0.25), "m32_tail": (-22.5, 1.0),
    "enemy_t56_shot": (-21.9, 0.25), "enemy_smg_shot": (-24.4, 0.25), "enemy_pump_shot": (-17.1, 0.25),
}


def put(name, x, peak_db=-0.5, mono=False):
    g.save(OUT, name, x, peak_db, mono=mono, level=LEVELS[name.rsplit("_", 1)[0]])


def suppressed(x, keep_ms=1.2, db=9.0, lp=2200.0):
    """What a can does to a supersonic rifle at the shooter: the bullet's crack
    (the first millisecond) stays, the muzzle blast behind it drops and darkens."""
    n = int(keep_ms * 0.001 * SR)
    xf = int(0.0008 * SR)
    body = (g.lowpass(x, lp, 2) * 0.7 + x * 0.3) * 10 ** (-db / 20)
    w = np.ones(len(x))
    w[:n] = 0.0
    w[n:n + xf] = np.linspace(0, 1, xf)
    return x * (1 - w)[:, None] + body * w[:, None]


def layer(spec, length, squash_db):
    x = g.load(*spec["src"])
    seg, at = g.shot_at(x, spec["index"], length / spec["pitch"] + 0.01, rel=0.5, gap=spec["gap"])
    if spec["pitch"] != 1.0:
        seg = g.pitch(seg, spec["pitch"])
    seg = seg[:int(length * SR)]
    if len(seg) < int(length * SR):
        seg = np.pad(seg, ((0, int(length * SR) - len(seg)), (0, 0)))
    if spec["hp"]:
        seg = g.highpass(seg, spec["hp"])
    seg = g.squash(seg, squash_db if spec["squash"] is None else spec["squash"])
    if spec["fx"]:
        seg = spec["fx"](seg)
    if spec["lp"]:
        seg = g.lowpass(seg, spec["lp"], 2)
    if spec["delay"]:
        seg = np.roll(seg, int(spec["delay"] * SR), axis=0)
        seg[:int(spec["delay"] * SR)] = 0
    print(f"    {spec['src'][1]} #{spec['index']} at {at / SR:.2f} s, pitch {spec['pitch']}")
    return g.normalize(seg, -1.0) * spec["gain"]


def shot(layers, length, squash_db=12.0, echo=(0.06, 0.08, 6.0), weight=None, dec=None, fade_out=0.25):
    mix = sum(layer(s, length, squash_db) for s in layers)
    if echo:
        mix = g.duck_echo(g.normalize(mix, -1.0), *echo)
    mix = g.normalize(mix, -1.0)
    if weight is not None:
        mix = g.weight(mix, **weight)
    if dec:
        mix = g.decay(mix, *dec)
    return g.fade(mix, 0.0005, fade_out)


def tail(src, index, length, lp=2600.0, fade_in=0.15, pitch=1.0, gap=0.8):
    x = g.load(*src)
    seg, _ = g.shot_at(x, index, length / pitch + 0.01, rel=0.5, gap=gap)
    if pitch != 1.0:
        seg = g.pitch(seg, pitch)
    seg = g.lowpass(g.highpass(seg[:int(length * SR)], 40), lp, 2)
    env = np.ones(len(seg))
    k = int(fade_in * SR)
    env[:k] = np.linspace(0, 1, k) ** 2  # the shot itself plays the first moments
    return g.fade(seg * env[:, None], 0.0, length * 0.35)


def roar(n, variant):
    """The Dragon's Breath jet: burning metal roaring out for half a second
    (synthesized; laid over the real shot)."""
    rng = np.random.default_rng(40 + variant)
    t = np.arange(n) / SR
    swell = np.clip((t - 0.006) / 0.08, 0, 1) * np.exp(-np.maximum(t - 0.086, 0) / 0.24)
    noise = rng.standard_normal((n, 2))
    body = g.lowpass(g.highpass(noise, 180, 2), 2600, 2)
    rumble = g.lowpass(g.highpass(noise[:, ::-1], 40, 2), 260, 2)
    flutter = 0.75 + 0.25 * np.sin(2 * np.pi * (23 + 3 * variant) * t)
    pops = np.zeros((n, 2))
    for _ in range(120):
        p = int(rng.uniform(0, 1) ** 1.6 * (n - 400))
        burst = g.highpass(rng.standard_normal((260, 2)), 1500, 2) * np.exp(-np.arange(260) / 50)[:, None]
        pops[p:p + 260] += burst * rng.uniform(0.2, 1.0) * np.exp(-p / SR / 0.35)
    return g.normalize((body * 1.1 + rumble * 0.9) * (swell * flutter)[:, None] + pops * 0.5, -1.0)


# Weight presets (see _real_gun.weight).
W_PISTOL = dict(body_hz=210, body_db=3.5, low_drive=2.6, low_gain=0.45, thump_gain=0.18, thump_hz=60, thump_tau=0.03)
W_SUPP = dict(body_hz=230, body_db=4.0, low_drive=2.2, low_gain=0.4, thump_gain=0.12, thump_hz=66, thump_tau=0.03, sat=1.2)
W_RIFLE = dict(body_hz=190, body_db=4.0, low_drive=3.0, low_gain=0.5, thump_gain=0.24, thump_hz=55, thump_tau=0.04)
W_SHOTGUN = dict(body_hz=170, body_db=5.0, low_drive=3.2, low_gain=0.6, thump_gain=0.36, thump_hz=48, thump_tau=0.06)
W_BIG = dict(body_hz=160, body_db=5.0, low_drive=3.4, low_gain=0.6, thump_gain=0.42, thump_hz=46, thump_tau=0.07, sat=1.5)
W_LAUNCH = dict(body_hz=150, body_db=6.0, low_drive=3.0, low_gain=0.7, thump_gain=0.5, thump_hz=58, thump_tau=0.05, sat=1.3)


def five_seven():
    print("Five-seveN (suppressed; the shared shot bank):")
    for v, i in enumerate((0, 1, 2), 1):
        put(f"shot_{v}", shot([L(P226, i, gap=0.5, hp=80)], 0.42, 4.0, None, W_SUPP, (0.06, 0.06), 0.15), -1.0)
    # The third shot's own decay (the P226 was fired outdoors, by a building).
    put("tail_1", tail(P226, 2, 0.7, lp=3000, fade_in=0.06, gap=0.5), -6.0)


def mp5():
    print("MP5/SD-L (suppressed .45s for the SD's low thump):")
    specs = [
        [L(FNX, 0, hp=90)],
        [L(FNX, 0, hp=90, pitch=1.04)],
        [L(M1911S, 0, hp=90)],
        [L(M1911S, 0, hp=90, pitch=0.96)],
    ]
    for v, s in enumerate(specs, 1):
        put(f"mp5_shot_{v}", shot(s, 0.32, 4.0, None, W_SUPP, (0.07, 0.06), 0.08), -1.0)
    put("mp5_tail_1", tail(M1911S, 0, 0.6, lp=2400, fade_in=0.08), -8.0)


def m14():
    # No usable CC0 recording of a suppressed .308 rifle was found (the one
    # suppressed rifle, a Tac-50 on a phone, is a wall of clipped noise). So:
    # a real .30-06 bolt gun (Tikka T3, nearly the M14's round) with the can's
    # effect applied: the crack kept, the blast behind it down 9 dB and darker.
    print("M14/P (Tikka T3 .30-06, suppressed in processing):")
    specs = [
        [L(lib("Tikka__W_29P"), 0, gap=2.0, fx=suppressed)],
        [L(lib("Tikka__W_29P"), 1, gap=2.0, fx=suppressed)],
        [L(lib("Tikka__W_24P"), 0, gap=2.0, fx=suppressed)],
    ]
    for v, s in enumerate(specs, 1):
        put(f"m14_shot_{v}", shot(s, 0.6, 12.0, (0.06, 0.08, 5.0), W_RIFLE, (0.14, 0.12), 0.2), -1.0)
    put("m14_tail_1", tail(lib("Tikka__W_24P"), 1, 1.6, lp=2000, fade_in=0.18, gap=2.0), -4.0)


def glock():
    print("Glock 22 (a Walther PPQ's range report over a Glock 19X, a touch lower for .40):")
    specs = [
        [L(lib("Walther_PPQ__X_39P"), 0, pitch=0.95), L(G19X, 0, gain=0.5, pitch=0.95, lp=5000, delay=0.001)],
        [L(lib("Walther_PPQ__X_39P"), 1, pitch=0.95), L(G19X, 0, gain=0.5, pitch=0.93, lp=5000, delay=0.001)],
        [L(lib("Walther_PPQ__X_39P"), 2, pitch=0.95), L(G19X, 0, gain=0.45, pitch=0.97, lp=5000, delay=0.001)],
    ]
    for v, s in enumerate(specs, 1):
        put(f"glock_shot_{v}", shot(s, 0.3, 6.0, (0.04, 0.04, 6.0), W_PISTOL, (0.06, 0.05), 0.08), -1.0)
    # A 9 mm pistol's range decay, recorded 15 m out (johanwestling).
    put("glock_tail_1", tail(JW9, 0, 0.9, lp=2600, gap=2.0), -8.0)


def aug():
    print("AUG (AR-15, 5.56):")
    specs = [
        [L(lib("AR-15__D_32P"), 0, gap=2.0)],
        [L(lib("AR-15__D_32P"), 1, gap=2.0)],
        [L(lib("AR-15__D_24P"), 0, gap=2.0)],
        [L(lib("AR-15__D_24P"), 1, gap=2.0)],
    ]
    for v, s in enumerate(specs, 1):
        put(f"aug_shot_{v}", shot(s, 0.55, 13.0, (0.05, 0.06, 6.0), W_RIFLE, (0.1, 0.09), 0.1), -0.5)
    put("aug_tail_1", tail(lib("AR-15__D_24P"), 1, 1.5, gap=2.0), -5.0)


def saiga():
    print("Saiga-12K (Winchester Model 12, 12-gauge):")
    specs = [
        [L(lib("Model_12__K_22P"), 0, gap=2.0)],
        [L(lib("Model_12__K_22P"), 1, gap=2.0)],
        [L(lib("Model_12__K_17P"), 0, gap=2.0)],
    ]
    for v, s in enumerate(specs, 1):
        put(f"saiga_shot_{v}", shot(s, 0.7, 15.0, (0.06, 0.08, 6.0), W_SHOTGUN, None, 0.25), -1.0)
    put("saiga_tail_1", tail(lib("Model_12__K_17P"), 1, 2.2, gap=2.0), -3.0)
    print("  Dragon's Breath (the other take under a synthesized jet):")
    for v, (src, i) in enumerate(((lib("Model_12__K_17P"), 1), (lib("Model_12__K_22P"), 1)), 1):
        bang = shot([L(src, i, gap=2.0)], 1.1, 15.0, (0.06, 0.08, 6.0), W_SHOTGUN, None, 0.35)
        mix = bang * 0.7 + roar(len(bang), v) * 0.55
        put(f"saiga_db_shot_{v}", g.fade(mix, 0.0005, 0.3), -1.0)
    rt = tail(lib("Model_12__K_17P"), 1, 2.2, gap=2.0)
    crack = roar(len(rt), 7) * np.exp(-np.arange(len(rt)) / SR / 0.6)[:, None]
    put("saiga_db_tail_1", g.fade(rt + g.highpass(crack, 1500) * 0.15, 0.0, 0.8), -4.0)


def governor():
    print("Governor (.45-70: a Marlin 336 lever gun over a Mosin-Nagant's boom):")
    mosin = dict(gain=0.6, lp=3000, pitch=1.06, delay=0.002, gap=2.0)
    specs = [
        [L(lib("Marlin_336__I_22P"), 0, gap=2.0), L(lib("Mosin_Nagant__M_21P"), 0, **mosin)],
        [L(lib("Marlin_336__I_22P"), 1, gap=2.0), L(lib("Mosin_Nagant__M_21P"), 1, **mosin)],
        [L(lib("Marlin_336__I_17P"), 0, gap=2.0), L(lib("Mosin_Nagant__M_21P"), 2, **mosin)],
    ]
    for v, s in enumerate(specs, 1):
        put(f"governor_shot_{v}", shot(s, 1.1, 14.0, (0.07, 0.1, 6.0), W_BIG, None, 0.35), -0.5)
    put("governor_tail_1", tail(lib("Mosin_Nagant__M_26P"), 1, 3.2, lp=2200, gap=2.0), -3.0)


def m32():
    # Both recordings are rough (one a camera's limiter, one clipped), so the
    # cleaner one leads and the clipped one only adds its low end.
    print("M32A1 (real M203 40 mm launches):")
    low = dict(gap=0.3, gain=0.55, lp=1600, delay=0.002)
    specs = [
        [L(M203_Q, 0, gap=0.3, lp=7000), L(M203_L, 0, **low)],
        [L(M203_Q, 0, gap=0.3, lp=6000, pitch=0.94), L(M203_L, 0, **low)],
        [L(M203_Q, 0, gap=0.3, lp=7500, pitch=1.05), L(M203_L, 0, **low)],
    ]
    for v, s in enumerate(specs, 1):
        put(f"m32_shot_{v}", shot(s, 0.45, 0.0, None, W_LAUNCH, None, 0.2), -1.0)
    # No 40 mm recording runs long enough for a tail: a 12-gauge's range decay
    # (the Model 12 mid-distance take), darker still, as the open ground.
    put("m32_tail_1", tail(lib("Model_12__K_17P"), 0, 1.6, lp=1500, fade_in=0.12, pitch=1.15, gap=2.0), -4.0)


def rack(n):
    """The enemy pump gun is racked after each shot: the real Remington 870
    strokes the SPAS-12 uses (build_spas12_real_sfx.py), quieter, behind it."""
    out = np.zeros((n, 2))
    for at, name in ((0.30, "spas12_pump_back_2"), (0.46, "spas12_pump_forward_2")):
        x = g.load(OUT_REF, name + ".wav")
        a = int(at * SR)
        k = min(len(x), n - a)
        out[a:a + k] += x[:k] * 0.32
    return out


def enemies():
    print("Enemy guns (mono, played in 3D):")
    t56 = [L(lib("AK-47__C_28P"), 0, gap=2.0), L(lib("AK-47__C_28P"), 1, gap=2.0), L(lib("AK-47__C_31P"), 0, gap=2.0)]
    for v, s in enumerate(t56, 1):
        put(f"enemy_t56_shot_{v}", shot([s], 0.5, 12.0, (0.06, 0.08, 4.0), W_RIFLE, (0.12, 0.12), 0.12), -2.0,
            mono=True)
    smg = [L(lib("PPSh__P_30P"), 0, gap=2.0), L(lib("PPSh__P_30P"), 1, gap=2.0), L(lib("PPSh__P_30P"), 2, gap=2.0)]
    for v, s in enumerate(smg, 1):
        put(f"enemy_smg_shot_{v}", shot([s], 0.32, 12.0, (0.05, 0.05, 5.0), W_PISTOL, (0.07, 0.06), 0.06), -4.0,
            mono=True)
    pump = [L(lib("Nova__O_21P", True), 0, gap=2.0), L(lib("Nova__O_21P", True), 1, gap=2.0),
            L(lib("Mossberg__N_30P", True), 0, gap=2.0)]
    for v, s in enumerate(pump, 1):
        x = shot([s], 0.75, 14.0, (0.06, 0.08, 5.0), W_SHOTGUN, (0.22, 0.1), 0.2)
        put(f"enemy_pump_shot_{v}", x + rack(len(x)), -1.0, mono=True)


GUNS = {"shot": five_seven, "mp5": mp5, "m14": m14, "glock": glock, "aug": aug, "saiga": saiga,
        "governor": governor, "m32": m32, "enemy": enemies}

if __name__ == "__main__":
    for k, f in GUNS.items():
        if ONLY is None or k in ONLY:
            f()
