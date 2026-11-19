"""Original trailer score for GRAFT, synthesised (no samples): drone, strings,
braams, taiko, ostinato, risers, whooshes, the title impact.
Writes a 48 kHz stereo WAV. Cue times come from timeline.py."""
import sys
import numpy as np
import scipy.signal as sg
from scipy.io import wavfile

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import timeline as TL

SR = 48000
N = int(SR * TL.TOTAL)
rng = np.random.default_rng(7)
bus = {k: np.zeros((N, 2)) for k in ("dry", "verb", "post")}


def env_adsr(n, a, d, s, r, sus_t):
    t = np.arange(n) / SR
    e = np.zeros(n)
    e = np.where(t < a, t / max(a, 1e-4), 1.0)
    dd = np.clip((t - a) / max(d, 1e-4), 0, 1)
    e = np.where(t >= a, 1.0 - (1.0 - s) * dd, e)
    rel = np.clip((t - sus_t) / max(r, 1e-4), 0, 1)
    return e * (1.0 - rel)


def place(sig, t0, gain=1.0, pan=0.0, verb=0.3, post=False):
    if sig.ndim == 1:
        l = sig * np.sqrt(0.5 * (1 - pan))
        r = sig * np.sqrt(0.5 * (1 + pan))
        sig = np.stack([l, r], 1) * np.sqrt(2)
    i0 = int(t0 * SR)
    if i0 >= N:
        return
    if i0 < 0:
        sig = sig[-i0:]
        i0 = 0
    n = min(len(sig), N - i0)
    if post:
        bus["post"][i0:i0 + n] += sig[:n] * gain
        return
    bus["dry"][i0:i0 + n] += sig[:n] * gain
    bus["verb"][i0:i0 + n] += sig[:n] * gain * verb


def lp(x, fc, order=2):
    sos = sg.butter(order, min(fc, SR * 0.45), "low", fs=SR, output="sos")
    return sg.sosfilt(sos, x)


def hp(x, fc, order=2):
    sos = sg.butter(order, fc, "high", fs=SR, output="sos")
    return sg.sosfilt(sos, x)


def bp(x, lo, hi):
    sos = sg.butter(2, [lo, min(hi, SR * 0.45)], "band", fs=SR, output="sos")
    return sg.sosfilt(sos, x)


def tv_lp(x, cut_fn, block=512):
    """Time-varying 2-pole lowpass (cutoff from cut_fn(t))."""
    out = np.zeros_like(x)
    zi = np.zeros((1, 2))
    for i in range(0, len(x), block):
        fc = float(np.clip(cut_fn(i / SR), 40, SR * 0.45))
        sos = sg.butter(2, fc, "low", fs=SR, output="sos")
        out[i:i + block], zi = sg.sosfilt(sos, x[i:i + block], zi=zi)
    return out


def saw(f, n, detune=0.0, phase=None):
    t = np.arange(n) / SR
    ph = rng.random() if phase is None else phase
    return sg.sawtooth(2 * np.pi * (f * (1 + detune) * t + ph))


def supersaw(f, n, spread=0.006, voices=5):
    s = np.zeros(n)
    for v in range(voices):
        s += saw(f, n, spread * (v - (voices - 1) / 2) / ((voices - 1) / 2))
    return s / voices


NOTE = {"D1": 36.71, "A1": 55.0, "Bb1": 58.27, "C2": 65.41, "D2": 73.42, "F2": 87.31,
        "A2": 110.0, "C3": 130.81, "D3": 146.83, "F3": 174.61, "A3": 220.0, "D4": 293.66}


# ------------------------------------------------------------------ instruments

def drone(t0, t1, gain):
    n = int((t1 - t0) * SR)
    x = supersaw(NOTE["D1"], n) * 0.6 + supersaw(NOTE["D2"], n) * 0.5 + supersaw(NOTE["A2"], n) * 0.2
    x = tv_lp(x, lambda t: 140 + 260 * (t / (t1 - t0)) + 60 * np.sin(t * 0.9))
    e = np.clip(np.arange(n) / SR / 3.0, 0, 1) * np.clip((n / SR - np.arange(n) / SR) / 0.4, 0, 1)
    sub = np.sin(2 * np.pi * NOTE["D1"] * np.arange(n) / SR) * 0.5
    place(np.tanh((x + sub) * 1.5) * e, t0, gain, verb=0.4)


def strings(t0, t1, notes, gain, bright=1400):
    n = int((t1 - t0) * SR)
    x = np.zeros(n)
    for k in notes:
        x += supersaw(NOTE[k], n, 0.004, 7)
    x = lp(x, bright, 2)
    e = env_adsr(n, 1.8, 0.1, 1.0, 0.6, n / SR - 0.6)
    trem = 1 + 0.08 * np.sin(2 * np.pi * 5.2 * np.arange(n) / SR)
    l = x * e * trem
    r = np.roll(l, 240)
    place(np.stack([l, r], 1), t0, gain, verb=0.7)


def braam(t0, gain, dur=2.8, root="D1"):
    n = int(dur * SR)
    fs = [NOTE[root], NOTE[root] * 1.5, NOTE[root] * 2, NOTE[root] * 2.38, NOTE[root] * 3, NOTE[root] * 4]
    x = np.zeros(n)
    for i, f in enumerate(fs):
        x += supersaw(f, n, 0.008, 5) * (1.0 if i < 3 else 0.6)
    x = tv_lp(x, lambda t: 180 + 2600 * np.exp(-((t - 0.25) / 0.45) ** 2) + 500 * np.exp(-t / 1.2))
    x = np.tanh(x * 2.2)
    e = env_adsr(n, 0.04, 0.4, 0.55, 1.4, dur - 1.4)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (NOTE[root] * (1 + 0.6 * np.exp(-t / 0.08))) * t) * np.exp(-t / 1.6)
    place(x * e * 0.8 + sub * 0.9, t0, gain, verb=0.45)


def taiko(t0, gain, f0=120.0, f1=46.0, pan=0.0):
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.045)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.38)
    skin = lp(rng.standard_normal(n), 900) * np.exp(-t / 0.03) * 0.8
    x = np.tanh((body + skin) * 1.8)
    place(x, t0, gain, pan, verb=0.35)


def snare(t0, gain, pan=0.0):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    x = bp(rng.standard_normal(n), 900, 7000) * np.exp(-t / 0.11) + np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05) * 0.6
    place(x, t0, gain, pan, verb=0.4)


def tick(t0, gain):
    n = int(0.08 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1850 * t) * np.exp(-t / 0.012) + bp(rng.standard_normal(n), 2500, 8000) * np.exp(-t / 0.006) * 0.5
    place(x, t0, gain, rng.uniform(-0.3, 0.3), verb=0.25)


def stab(t0, note, gain, dur=0.12):
    n = int((dur + 0.15) * SR)
    t = np.arange(n) / SR
    x = supersaw(NOTE[note], n, 0.01, 3) + supersaw(NOTE[note] * 2, n, 0.01, 3) * 0.5
    x = lp(x, 1100, 2)
    e = np.exp(-t / dur) * np.clip(t / 0.004, 0, 1)
    place(np.tanh(x * e * 2.0), t0, gain, verb=0.15)


def riser(t0, t1, gain):
    n = int((t1 - t0) * SR)
    t = np.arange(n) / SR
    u = t / (t1 - t0)
    noise = rng.standard_normal(n)
    x = tv_lp(noise, lambda tt: 300 + 9000 * (tt / (t1 - t0)) ** 2)
    x = hp(x, 200)
    f = 180 * 2 ** (u * 2.2)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR)
    e = u ** 2.2
    place((x * 0.7 + tone * 0.35) * e, t0, gain, verb=0.5)


def whoosh(t_end, gain, dur=0.32):
    n = int(dur * SR)
    t = np.arange(n) / SR
    u = t / dur
    x = tv_lp(rng.standard_normal(n), lambda tt: 400 + 7000 * (tt / dur) ** 1.5)
    e = np.sin(np.pi * np.clip(u, 0, 1)) ** 1.5 * u
    place(x * e, t_end - dur, gain, rng.uniform(-0.5, 0.5), verb=0.3)


def boom(t0, gain):
    n = int(4.5 * SR)
    t = np.arange(n) / SR
    f = 28 + 45 * np.exp(-t / 0.12)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 1.6)
    crash = lp(rng.standard_normal(n), 3500) * np.exp(-t / 0.9) * 0.5
    crack = hp(rng.standard_normal(n), 2000) * np.exp(-t / 0.04) * 0.8
    place(np.tanh((sub * 1.4 + crash + crack) * 1.4), t0, gain, verb=0.6)


def heartbeat(t0, gain, post=False):
    for dt, g in ((0.0, 1.0), (0.24, 0.7)):
        n = int(0.4 * SR)
        t = np.arange(n) / SR
        x = np.sin(2 * np.pi * (40 + 30 * np.exp(-t / 0.03)) * t) * np.exp(-t / 0.12)
        place(x, t0 + dt, gain * g, verb=0.1, post=post)


# ------------------------------------------------------------------ the cue sheet

c = TL.CUES
# Act 1: the drone and the clock.
drone(0.2, c["act2"] + 0.3, 0.85)
strings(c["menu"], c["act2"] + 0.4, ["D3", "F3", "A3"], 0.42)
heartbeat(0.9, 1.3)
heartbeat(2.9, 1.2)
t = c["atrium"]
k = 0
while t < c["act2"] - 0.05:
    tick(t, 0.10 + 0.25 * (t - c["atrium"]) / (c["act2"] - c["atrium"]))
    t += 0.5 if t < c["lift"] else 0.25
    k += 1
braam(c["menu"] + 0.05, 0.55, 3.2)
braam(c["lift_open"], 0.75, 2.4, "D1")
riser(c["lift"], c["act2"], 0.45)

# Act 2: 120 bpm, a hit on every cut.
beat = 0.5
b0 = c["act2"]
pattern = ["D2", "D2", "D2", "D2", "F2", "D2", "D2", "D2", "C2", "D2", "D2", "D2", "Bb1", "D2", "A1", "D2"]
t = b0
i = 0
while t < c["boss"] - 0.02:
    stab(t, pattern[i % 16], 0.32 if i % 4 == 0 else 0.2)
    t += beat / 4
    i += 1
t = b0
j = 0
while t < c["boss"] - 0.02:
    taiko(t, 0.7 if j % 2 == 0 else 0.5, pan=0.0)
    if j % 2 == 1:
        snare(t, 0.32)
    if j % 4 == 3:
        taiko(t + beat * 0.5, 0.45, 160, 60, 0.4)
    t += beat
    j += 1
strings(b0, c["boss"], ["D3", "F3", "A3", "D4"], 0.20, 2600)
for ct in TL.cut_times(b0, c["boss"]):
    whoosh(ct, 0.30)
    taiko(ct, 0.55, 140, 40)
braam(b0, 0.8, 2.6)
riser(c["boss"] - 3.0, c["boss"], 0.6)

# Act 3: the boss, half time, then the montage.
braam(c["boss"], 1.0, 3.0)
boom(c["boss"], 0.5)
t = c["boss"] + 1.0
while t < c["montage"] - 0.05:
    taiko(t, 0.85, 110, 38)
    snare(t + 0.5, 0.25)
    t += 1.0
strings(c["boss"], c["silence"], ["D2", "A2", "D3", "F3"], 0.28, 1800)
t = c["montage"]
while t < c["silence"] - 0.02:
    taiko(t, 0.8)
    snare(t + 0.1, 0.3)
    stab(t, "D2", 0.3)
    t += 0.2
for ct in TL.cut_times(c["montage"], c["silence"]):
    whoosh(ct, 0.25, 0.18)
riser(c["montage"] - 0.4, c["silence"], 0.7)
heartbeat(c["silence"] + 0.12, 0.45, post=True)

# The title.
boom(c["title"], 1.1)
braam(c["title"], 1.0, 4.2)
strings(c["title"] + 0.3, TL.TOTAL, ["D2", "A2", "D3", "F3", "A3"], 0.25, 1200)
taiko(c["tagline"], 0.6, 100, 35)

# ------------------------------------------------------------------ mix

ir_n = int(2.6 * SR)
tt = np.arange(ir_n) / SR
ir = np.stack([rng.standard_normal(ir_n), rng.standard_normal(ir_n)], 1) * np.exp(-tt / 0.75)[:, None]
ir[:, 0] = lp(ir[:, 0], 6000)
ir[:, 1] = lp(ir[:, 1], 6000)
ir /= np.sqrt((ir ** 2).sum(0))
wet = np.stack([sg.fftconvolve(bus["verb"][:, ch], ir[:, ch])[:N] for ch in range(2)], 1)
mix = bus["dry"] + wet * 0.9
# Hard silence before the title.
s0, s1 = int(c["silence"] * SR), int((c["silence"] + 0.12) * SR)
fade = np.ones(N)
fade[s0:s1] = np.linspace(1, 0.0, s1 - s0)
fade[s1:int(c["title"] * SR) - 1] = 0.0
mix *= fade[:, None]
hb = np.zeros((N, 2))
mix = mix / np.max(np.abs(mix)) * 1.25
mix = np.tanh(mix) * 0.9
mix += bus["post"]
# Fade out at the end.
fo = int(1.2 * SR)
mix[-fo:] *= np.linspace(1, 0, fo)[:, None]
wavfile.write(sys.argv[1], SR, (mix * 32767).astype(np.int16))
print("score", sys.argv[1], TL.TOTAL)
