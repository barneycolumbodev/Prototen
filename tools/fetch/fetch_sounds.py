#!/usr/bin/env python3
"""Fetch candidate CC0 sound recordings from hosts the cloud session can't reach
(CLAUDE.md §10.1: blocked downloads run in GitHub Actions).

Reads tools/fetch/sound_sources.json, writes everything under the output dir
(default raw_assets/audio/fetched/) with a manifest.json giving, for each
file, the page, author, license as the page states it, and title. Only files
whose page states CC0 / public domain are downloaded; everything else is
listed in the manifest as skipped, with its license, so nothing non-CC0 lands
in the repo.
"""
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
import io

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
MAX_BYTES = 900 * 1024 * 1024
# Big archives: only members whose path matches this are kept (sound_sources.json "keep").
KEEP_DEFAULT = r"shotgun|870|mossberg|pump|12 ?ga|benelli|spas"


def get(url: str, binary: bool = False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise RuntimeError("too large")
    return data if binary else data.decode("utf-8", "replace")


def safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:120]


def is_cc0(text: str) -> bool:
    t = text.lower()
    return "publicdomain/zero" in t or "cc0" in t or "creative commons 0" in t


def save_file(data: bytes, path: str, keep: str) -> dict:
    """Small files as they are; archives over 20 MB only their matching members."""
    if path.lower().endswith(".zip") and len(data) > 20 * 1024 * 1024:
        z = zipfile.ZipFile(io.BytesIO(data))
        base = path[:-4]
        os.makedirs(base, exist_ok=True)
        kept = []
        for n in z.namelist():
            if n.endswith("/") or not re.search(keep, n, re.I):
                continue
            if not re.search(r"\.(wav|ogg|mp3|flac|aif|aiff|txt|pdf)$", n, re.I):
                continue
            dst = os.path.join(base, safe(n.replace("/", "__")))
            open(dst, "wb").write(z.read(n))
            kept.append(dst)
        return {"path": base, "bytes": len(data), "kept": kept, "all_members": z.namelist()[:2000]}
    open(path, "wb").write(data)
    return {"path": path, "bytes": len(data)}


def oga_page(url: str, out: str, manifest: list, keep: str = KEEP_DEFAULT) -> None:
    page = get(url)
    m = re.search(r'field-name-field-art-licenses.*?</div>\s*</div>\s*</div>', page, re.S)
    lic_block = m.group(0) if m else ""
    lic = ", ".join(sorted(set(re.findall(r'title="([^"]+)"', lic_block)) | set(re.findall(r'>(CC[^<]{0,30}|GPL[^<]{0,20}|OGA-BY[^<]{0,10})<', lic_block))))
    author = re.search(r'field-name-author-submitter.*?<a[^>]*>([^<]+)</a>', page, re.S)
    title = re.search(r"<title>([^<]+)</title>", page)
    files = sorted(set(re.findall(r'href="(https://opengameart\.org/sites/default/files/[^"]+)"', page)))
    files = [f for f in files if re.search(r"\.(wav|ogg|mp3|flac|zip|7z|rar)$", f, re.I)]
    desc = re.search(r'field-name-body.*?<div class="field-item[^>]*>(.*?)</div>', page, re.S)
    entry = {"source": "opengameart", "page": url, "title": html.unescape(title.group(1)) if title else "",
             "author": html.unescape(author.group(1)) if author else "", "license": lic,
             "description": re.sub(r"<[^>]+>", " ", desc.group(1))[:1500] if desc else "",
             "files": []}
    ok = is_cc0(lic_block)
    for f in files:
        name = safe(urllib.parse.unquote(f.rsplit("/", 1)[1]))
        if not ok:
            entry["files"].append({"url": f, "skipped": "not CC0"})
            continue
        try:
            data = get(f, True)
            info = save_file(data, os.path.join(out, "oga_" + name), keep)
            info["url"] = f
            entry["files"].append(info)
        except Exception as e:  # noqa: BLE001
            entry["files"].append({"url": f, "error": str(e)})
        time.sleep(1)
    manifest.append(entry)


def freesound_search(query: str, limit: int) -> list:
    q = urllib.parse.urlencode({"q": query, "f": 'license:"Creative Commons 0"', "s": "Rating highest first"})
    page = get("https://freesound.org/search/?" + q)
    ids = []
    for user, sid in re.findall(r'/people/([^/"]+)/sounds/(\d+)/', page):
        if (user, sid) not in ids:
            ids.append((user, sid))
    return ids[:limit]


def freesound_sound(user: str, sid: str, out: str, manifest: list, seen: set) -> None:
    if sid in seen:
        return
    seen.add(sid)
    url = f"https://freesound.org/people/{user}/sounds/{sid}/"
    page = get(url)
    title = re.search(r'<meta property="og:title" content="([^"]*)"', page)
    audio = re.search(r'<meta property="og:audio" content="([^"]*)"', page)
    lic = re.search(r'href="(https?://creativecommons\.org/[^"]+)"', page)
    desc = re.search(r'<meta property="og:description" content="([^"]*)"', page)
    hq = audio.group(1) if audio else ""
    if hq.startswith("/"):
        hq = "https://freesound.org" + hq
    hq = re.sub(r"^https://freesound\.org(?=https?://)", "", hq)
    entry = {"source": "freesound", "page": url, "id": sid, "author": user,
             "title": html.unescape(title.group(1)) if title else "",
             "license": lic.group(1) if lic else "",
             "description": html.unescape(desc.group(1))[:800] if desc else "", "files": []}
    if hq and lic and "publicdomain/zero" in lic.group(1):
        hq = hq.replace("-lq.mp3", "-hq.mp3")
        try:
            data = get(hq, True)
            path = os.path.join(out, f"fs_{sid}_{safe(entry['title'])[:60]}.mp3")
            open(path, "wb").write(data)
            entry["files"].append({"url": hq, "path": path, "bytes": len(data)})
        except Exception as e:  # noqa: BLE001
            entry["files"].append({"url": hq, "error": str(e)})
    else:
        entry["files"].append({"url": hq, "skipped": "not CC0 or no preview"})
    manifest.append(entry)
    time.sleep(1.5)


def main() -> int:
    cfg = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "tools/fetch/sound_sources.json"))
    out = cfg.get("out", "raw_assets/audio/fetched")
    os.makedirs(out, exist_ok=True)
    manifest: list = []
    errors: list = []
    for url in cfg.get("opengameart", []):
        try:
            oga_page(url, out, manifest, cfg.get("keep", KEEP_DEFAULT))
        except Exception as e:  # noqa: BLE001
            errors.append({"page": url, "error": str(e)})
        time.sleep(1)
    seen: set = set()
    for item in cfg.get("freesound_ids", []):
        user, sid = item.split("/")
        try:
            freesound_sound(user, sid, out, manifest, seen)
        except Exception as e:  # noqa: BLE001
            errors.append({"page": item, "error": str(e)})
    for query in cfg.get("freesound_queries", []):
        try:
            for user, sid in freesound_search(query, cfg.get("per_query", 8)):
                try:
                    freesound_sound(user, sid, out, manifest, seen)
                except Exception as e:  # noqa: BLE001
                    errors.append({"page": sid, "error": str(e)})
        except Exception as e:  # noqa: BLE001
            errors.append({"query": query, "error": str(e)})
    json.dump({"entries": manifest, "errors": errors}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(f"{len(manifest)} entries, {len(errors)} errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
