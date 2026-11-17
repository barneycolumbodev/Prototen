"""Triad men and the Incense Master made with Tripo3D (owner, 2026-11-17: "remake the models you're
not impressed by with Tripo... one attempted generation per asset").

Each man is two paid calls, made once, no retries:
  1. POST /generation/text-to-image  (seedream_v5, template t_pose)    about 5 credits  -> concept.png
  2. POST /generation/image-to-model (v3.1, detailed geometry and PBR)  about 60 credits -> model.glb
then build.py fits him to the triad rig (no Tripo rig: the skeleton is ours, so every triad clip plays).

The API key is not in this file: in the cloud session a network secret adds the Authorization header
for openapi.tripo3d.ai. Outside it, set TRIPO_API_KEY.

Usage (python3, no Blender):
  python3 tripo_generate.py image <id> [<id> ...]   # text-to-image, waits, saves <id>/tripo/concept.png
  python3 tripo_generate.py model <id> [<id> ...]   # image-to-model from the concept task, saves model.glb
  python3 tripo_generate.py wait-model <id> ...     # resume polling a submitted model task
Records: <id>/tripo/{image_task.json, model_request.json, model_task.json, concept.png, model.glb, tripo_preview.*}
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://openapi.tripo3d.ai/v3"
HERE = Path(__file__).resolve().parent

# Said once for every man so they read as one cast: grounded, photographic, on a clean background that
# image-to-model can separate, and in a T-pose so the arms come out clear of the body for the rig.
POSE = (
    "wide shot with empty margins all round, the whole figure inside the frame including both hands and "
    "fingertips and both shoes, full body from the top of the head to the soles of the shoes, standing in a T-pose with both arms "
    "straight out to the sides at shoulder height, palms down, fingers straight and together, legs straight "
    "and slightly apart, feet flat, facing the camera, front view, plain light grey studio background, soft "
    "even lighting with no harsh shadows, photorealistic, realistic human proportions, sharp detail"
)
NO = "--no cartoon, anime, stylized, toy, chibi, weapon, gun, knife, bag, props, cropped, extra limbs, text, watermark"

# id -> (role note for the docs, the man)
CAST: dict[str, tuple[str, str]] = {
    "gun_bomber": ("Gunman, Street", (
        "Hong Kong Chinese triad gunman in his twenties, lean, short black undercut hair, light stubble, hard "
        "unfriendly stare; bright red satin MA-1 bomber jacket zipped half open over a white t-shirt, thin gold "
        "chain, slim black jeans, white sneakers; black-and-grey dragon tattoo climbing the side of his neck")),
    "gun_track": ("Gunman, Street", (
        "Hong Kong Chinese triad gunman in his thirties, buzz cut, scar through his left eyebrow, stubble, scowl; "
        "zipped royal blue track jacket with three white stripes down each sleeve, matching royal blue track "
        "pants with white side stripes, black sneakers; Chinese character tattoos on the backs of both hands")),
    "gun_hoodie": ("Gunman, Street", (
        "Hong Kong Chinese triad gunman in his twenties, slicked-back black hair, thin moustache, cold eyes; "
        "mustard yellow pullover hoodie with the hood down, olive green cargo trousers with side pockets, tan "
        "leather work boots; small black koi fish tattoo on the side of his neck, silver watch")),
    "sum_hawaii": ("Gunman, Summer", (
        "wiry Hong Kong Chinese triad gunman in his twenties, spiky bleached blond hair with dark roots, "
        "sneer; open short-sleeved white shirt with a big red hibiscus flower print worn unbuttoned over a "
        "bare chest, chest, stomach and both forearms covered in black-and-grey dragon and cloud tattoos, "
        "beige cargo shorts, white sneakers with white socks, thin gold chain")),
    "sum_singlet": ("Gunman, Summer", (
        "muscular Hong Kong Chinese triad gunman in his thirties, shaved head with dark stubble, broad "
        "shoulders, menacing look; white ribbed singlet tank top, both arms fully sleeved to the wrists in "
        "black-and-grey koi fish and crashing wave tattoos, a tiger tattoo on the chest showing above the "
        "singlet; faded blue jeans with a black belt, black sneakers")),
    "enf_hoodie": ("Enforcer, Muscle", (
        "big heavyset Hong Kong Chinese triad enforcer in his thirties, very short black hair, goatee, thick "
        "neck, intimidating; black ballistic plate carrier vest with rifle magazine pouches strapped tightly "
        "over a charcoal grey hoodie with the hood down, black cargo trousers, black combat boots, black "
        "fingerless gloves")),
    "enf_track": ("Enforcer, Muscle", (
        "broad muscular Hong Kong Chinese triad enforcer in his forties, shaved head, thick neck, scar across "
        "his cheek, brutal expression; olive green ballistic plate carrier vest with pouches strapped over a "
        "red track jacket with white stripes on the sleeves, black track pants with white side stripes, "
        "black boots")),
    "hatchet": ("Hatchet Man", (
        "lean muscular Hong Kong Chinese triad hatchet man in his thirties, black hair tied back in a short "
        "ponytail, red cloth headband, wild fierce eyes; shirtless under an open black waistcoat vest, torso "
        "and both arms covered in dense black-and-grey dragon, tiger and Chinese calligraphy tattoos, loose "
        "black kung fu trousers, black cloth shoes, white cloth wraps around the hands and wrists")),
    "red_pole": ("Red Pole (lieutenant)", (
        "Hong Kong Chinese triad Red Pole lieutenant in his forties, slicked-back black hair going grey at the "
        "temples, thin moustache and goatee, cold arrogant expression; open black leather jacket over a "
        "crimson silk shirt with a gold dragon print, heavy gold chain, gold watch and gold rings, dark "
        "charcoal slacks, polished black leather shoes")),
    # Second round (same day): the Blue Lantern recruits get their own look (young, in blue, so the type
    # reads apart from the gunmen), and an older gunman for age among the five.
    "lantern_denim": ("Blue Lantern (recruit)", (
        "skinny Hong Kong Chinese teenage triad recruit about nineteen years old, messy dyed brown hair, "
        "nervous defiant scowl, acne scars; oversized light blue denim jacket over a white hoodie with the hood "
        "down, baggy black jeans, chunky white sneakers; a cheap blue paper lantern charm on a string around "
        "his neck")),
    "lantern_sport": ("Blue Lantern (recruit)", (
        "thin Hong Kong Chinese teenage triad recruit about eighteen years old, bowl haircut, boyish face, "
        "tough expression; sky blue nylon windbreaker zipped up, grey sweatpants, black sports slides with "
        "white socks, a blue bandana tied around his left wrist")),
    "gun_older": ("Gunman, Street", (
        "wiry Hong Kong Chinese triad gunman in his fifties, short grey crew cut, lined weathered face, scar "
        "on his chin, hard eyes; faded olive green work jacket open over a navy and white striped polo shirt, "
        "brown slacks, black leather shoes; old faded blue-black tattoos on the backs of his hands")),
    "incense_master": ("Boss: the Incense Master", (
        "enormous bald Hong Kong Chinese triad enforcer, huge and massively muscular, heavy belly and thick "
        "neck, shaved head, cold brutal stare, stubble and a short goatee; sleeveless black leather vest worn "
        "open over a bare chest, chest and both arms covered in black-and-grey dragon and curling incense "
        "smoke tattoos; black leather trousers, wide black leather belt with a heavy gold buckle, heavy black "
        "boots")),
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
        with urllib.request.urlopen(req, timeout=90) as r:
            out = json.load(r)
    except urllib.error.HTTPError as e:
        out = json.loads(e.read() or b"{}")
    if out.get("code") != 0:
        raise SystemExit(f"Tripo error on {method} {path}: {json.dumps(out)}")
    return out["data"]


def _wait(task_id: str, timeout_s: int = 1500) -> dict:
    t0 = time.time()
    while True:
        d = _call("GET", f"/tasks/{task_id}")
        st = d.get("status")
        print(f"  [{int(time.time() - t0):4d}s] {task_id[:8]} {st} {d.get('progress')}", flush=True)
        if st == "success":
            return d
        if st not in ("queued", "running"):
            raise SystemExit(f"task ended: {json.dumps(d)}")
        if time.time() - t0 > timeout_s:
            raise SystemExit("timed out")
        time.sleep(10)


def _dir(cid: str) -> Path:
    d = HERE / cid / "tripo"
    d.mkdir(parents=True, exist_ok=True)
    return d


def image(cid: str) -> None:
    out = _dir(cid)
    if (out / "image_task.json").exists():
        print(cid, "already has a concept image: not generating again")
        return
    # hatchet (the first) used template t_pose: it framed him 1:2 and cut his hands off. The rest are
    # square, no template, with the framing asked for in the prompt (POSE).
    body = {"prompt": f"{CAST[cid][1]}, {POSE} {NO}", "model": "seedream_v5", "size": "2048x2048",
            "output_format": "png"}
    tid = _call("POST", "/generation/text-to-image", body)["task_id"]
    (out / "image_request.json").write_text(json.dumps({"task_id": tid, **body}, indent=2) + "\n")
    print(cid, "image task", tid, flush=True)
    d = _wait(tid)
    (out / "image_task.json").write_text(json.dumps(d, indent=2) + "\n")
    urllib.request.urlretrieve(d["output"]["generated_image_url"], out / "concept.png")
    print(cid, "saved concept.png, credits", d.get("credits_consumed"))


def model(cid: str) -> None:
    out = _dir(cid)
    if (out / "model_request.json").exists():
        print(cid, "already has a model task: use wait-model")
        return
    img = json.loads((out / "image_task.json").read_text())
    body = {"input": img["task_id"], "model": "v3.1-20260211", "texture": True, "pbr": True,
            "texture_quality": "detailed", "geometry_quality": "detailed", "auto_size": True}
    tid = _call("POST", "/generation/image-to-model", body)["task_id"]
    (out / "model_request.json").write_text(json.dumps({"task_id": tid, **body}, indent=2) + "\n")
    print(cid, "model task", tid, flush=True)
    wait_model(cid)


def wait_model(cid: str) -> None:
    out = _dir(cid)
    tid = json.loads((out / "model_request.json").read_text())["task_id"]
    d = _wait(tid)
    (out / "model_task.json").write_text(json.dumps(d, indent=2) + "\n")
    o = d["output"]
    for key, name in (("model_url", "model.glb"), ("pbr_model_url", "model_pbr.glb"),
                      ("rendered_image_url", "tripo_preview.webp")):
        url = o.get(key)
        if url:
            urllib.request.urlretrieve(url, out / name)  # signed CDN links: no auth header
            print(cid, "saved", name)
    print(cid, "credits", d.get("credits_consumed"))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    fn = {"image": image, "model": model, "wait-model": wait_model}[sys.argv[1]]
    for c in sys.argv[2:]:
        if c not in CAST:
            raise SystemExit(f"unknown id {c}")
        fn(c)
