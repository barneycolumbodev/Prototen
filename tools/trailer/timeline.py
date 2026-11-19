"""The trailer's edit decision list. Each segment: (kind, source, src_start, dur, opts).
kind: eng = a rendered engine shot (src_start in seconds after its warm-up),
big/a/b = the owner's recordings, black, title.
Durations in act 2 are whole beats (0.5 s at 120 bpm) so every cut lands on the drum."""

SEGMENTS = [
    # Act 1: the world, the man, the threat.
    ("black", None, 0.0, 0.5, {}),
    ("eng", "ct_street", 0.5, 3.6, {"text": "THEY ARE ONLY HUMAN.", "text_in": 0.9, "text_out": 3.3, "audio": 0.9}),
    ("eng", "menu", 0.8, 3.2, {"text": "YOU ARE NOT.", "text_in": 0.6, "text_out": 2.9, "audio": 0.9}),
    ("eng", "ho_atrium", 0.3, 2.4, {"audio": 0.8}),
    ("eng", "ho_lift", 0.9, 2.3, {"audio": 1.0, "flash": True}),
    # Act 2: 120 bpm.
    ("big", None, 101.0, 1.5, {"audio": 0.7, "flash": True}),
    ("eng", "ct_slowmo", 0.9, 2.5, {"audio": 1.0}),
    ("b", None, 18.4, 2.0, {"audio": 0.7}),
    ("eng", "ho_slagger", 2.3, 2.0, {"audio": 1.0}),
    ("eng", "ct_catch", 1.5, 2.5, {"audio": 1.0, "text": "CATCH THEIR BULLETS.", "text_in": 0.2, "text_out": 2.3}),
    ("big", None, 228.9, 1.5, {"audio": 0.7, "text": "SEND THEM BACK.", "text_in": 0.0, "text_out": 1.4}),
    ("eng", "ct_dogs", 2.1, 2.0, {"audio": 1.0, "gamma": 1.45}),
    ("a", None, 17.4, 1.5, {"audio": 0.7}),
    ("eng", "ho_governor", 0.6, 1.5, {"audio": 1.0}),
    ("big", None, 200.2, 1.5, {"audio": 0.7}),
    ("eng", "ct_mg", 1.2, 1.5, {"audio": 1.0}),
    # Act 3: the boss, the montage, silence, the title.
    ("eng", "ct_boss", 0.75, 3.6, {"audio": 1.0, "flash": True}),
    ("big", None, 153.6, 0.4, {"audio": 0.6}),
    ("eng", "ct_mg", 2.3, 0.4, {"audio": 0.9}),
    ("big", None, 142.2, 0.4, {"audio": 0.6}),
    ("eng", "ho_slagger", 3.45, 0.4, {"audio": 0.9}),
    ("b", None, 20.3, 0.4, {"audio": 0.6}),
    ("big", None, 225.0, 0.4, {"audio": 0.6}),
    ("black", None, 0.0, 0.6, {}),
    ("title", None, 0.0, 4.6, {}),
]

# Filled from the renders (seconds into the shot) by tune(); see assemble.py.
OVERRIDES = {}


def apply_overrides():
    out = []
    for i, (k, s, st, d, o) in enumerate(SEGMENTS):
        if i in OVERRIDES:
            st = OVERRIDES[i]
        out.append((k, s, st, d, o))
    return out


def starts():
    t = 0.0
    res = []
    for seg in SEGMENTS:
        res.append(t)
        t += seg[3]
    return res, t


_st, TOTAL = starts()


def _find(kind, src, nth=0):
    k = 0
    for i, seg in enumerate(SEGMENTS):
        if seg[0] == kind and seg[1] == src:
            if k == nth:
                return _st[i]
            k += 1
    raise KeyError(src)


CUES = {
    "street": _find("eng", "ct_street"),
    "menu": _find("eng", "menu"),
    "atrium": _find("eng", "ho_atrium"),
    "lift": _find("eng", "ho_lift"),
    "lift_open": _find("eng", "ho_lift") + 0.5,
    "act2": _st[5],
    "boss": _find("eng", "ct_boss"),
    "montage": _st[17],
    "silence": _st[-2],
    "title": _st[-1],
    "tagline": _st[-1] + 1.6,
}


def cut_times(t0, t1):
    return [t for t in _st if t0 < t < t1 - 0.01]
