"""Generate the triad attack dog (German shepherd) with the Tripo3D v3 API.

Paid API (about 20-40 credits per text-to-model task). The API key is not in
this file: in the cloud session a network secret adds the Authorization header
for openapi.tripo3d.ai. Outside it, set TRIPO_API_KEY.

Usage:
  python3 tripo_generate.py create <variant> [<variant> ...]   # submit tasks, print ids
  python3 tripo_generate.py wait <task_id> <out_dir>           # poll, then download model + preview

Results land in raw_assets/characters/attack_dog/tripo/<variant>/ (source GLB,
Tripo's preview render, task.json with the prompt, seed and credits).

The dog in the game is NOT one of these text-to-model variants (their faces
came out panting, not snarling). It is tripo/snarl_image/, made in two calls:
  1. POST /generation/text-to-image  {prompt: see t2i_task.json "input",
     model: "seedream_v5", size: "2K", output_format: "png"}      -> concept.png
  2. POST /generation/image-to-model {model: "v3.1-20260211",
     file: {type: "png", url: <generated_image_url>}, plus the fields in
     snarl_image/request.json}                                     -> model.glb
then reduce.py makes the 150k master and the 15k game mesh.
Credits used 2026-11-17: 50 + 50 (text variants) + 5 (image) + 60 (image-to-model).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://openapi.tripo3d.ai/v3"
HERE = Path(__file__).resolve().parent

NEGATIVE = (
    "cartoon, stylized, anime, toy, plush, chibi, low detail, extra legs, "
    "extra tail, two heads, pedestal, base, ground plane, saddle, armor, rider"
)

VARIANTS: dict[str, dict] = {
    # Snarl in the face, body in a standing pose that rigs cleanly.
    "snarl_stand": {
        "prompt": (
            "Realistic adult German Shepherd attack dog, full body, standing on all four legs "
            "in a tense forward-leaning stance, head low and level, aggressive snarl with lips "
            "curled back baring long fangs and gums, wrinkled muzzle, ears pricked forward, "
            "hackles raised along the back, classic black and tan saddle coat, coarse realistic fur, "
            "worn black leather collar with steel studs and a short chain, scarred muzzle, "
            "lean muscular working dog, photorealistic"
        ),
        "model_seed": 4117,
    },
    # Same dog, mid-charge look: lower and longer, mouth open wider.
    "snarl_charge": {
        "prompt": (
            "Photorealistic German Shepherd guard dog in a crouched aggressive stance about to "
            "charge, all four paws on the ground, body low, head thrust forward, mouth open wide "
            "snarling with bared teeth and wrinkled snout, ears forward, tail low and straight, "
            "black and tan coat with dark saddle, realistic dense fur, heavy black leather "
            "studded collar with a broken chain link, lean powerful muscles, triad street gang dog"
        ),
        "model_seed": 2093,
    },
}


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    key = os.environ.get("TRIPO_API_KEY")
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


def _call(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            out = json.load(r)
    except urllib.error.HTTPError as e:
        out = json.loads(e.read() or b"{}")
    if out.get("code") != 0:
        raise SystemExit(f"Tripo error on {method} {path}: {json.dumps(out)}")
    return out["data"]


def create(variant: str) -> str:
    v = VARIANTS[variant]
    body = {
        "prompt": v["prompt"],
        "negative_prompt": NEGATIVE,
        "model": "v3.1-20260211",
        "model_seed": v["model_seed"],
        "texture": True,
        "pbr": True,
        "texture_quality": "detailed",
        "geometry_quality": "detailed",
        "auto_size": True,
    }
    tid = _call("POST", "/generation/text-to-model", body)["task_id"]
    out = HERE / "tripo" / variant
    out.mkdir(parents=True, exist_ok=True)
    (out / "request.json").write_text(json.dumps({"task_id": tid, **body}, indent=2) + "\n")
    print(f"{variant} {tid}")
    return tid


def wait(task_id: str, out_dir: str, timeout_s: int = 900) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    while True:
        d = _call("GET", f"/tasks/{task_id}")
        st = d.get("status")
        print(f"[{int(time.time() - t0):4d}s] {st} {d.get('progress')}", flush=True)
        if st == "success":
            break
        if st not in ("queued", "running"):
            raise SystemExit(f"task ended: {json.dumps(d)}")
        if time.time() - t0 > timeout_s:
            raise SystemExit("timed out")
        time.sleep(10)
    (out / "task.json").write_text(json.dumps(d, indent=2) + "\n")
    o = d["output"]
    for key, name in (("model_url", "model.glb"), ("pbr_model_url", "model_pbr.glb"),
                      ("rendered_image_url", "tripo_preview.webp")):
        url = o.get(key)
        if url:
            # CDN links are signed; no auth header needed.
            urllib.request.urlretrieve(url, out / name)
            print("saved", out / name)
    print("credits", d.get("credits_consumed"))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "create":
        for v in sys.argv[2:]:
            create(v)
    elif cmd == "wait":
        wait(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
