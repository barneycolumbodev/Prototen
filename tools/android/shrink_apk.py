#!/usr/bin/env python3
"""Repack a Godot Android APK so its .ctex textures are deflated.

Godot's Android exporter always stores .ctex files uncompressed (it assumes they
are already compressed). VRAM-compressed (ETC2) textures still deflate to about
45 % of their size, so storing them was most of a 390 MB APK (2026-11-11), and a
download that big failed on the phone ("There was a problem parsing the package").

Godot reads assets through AAssetManager streaming, which handles deflated
entries: the .ctexarray, .gdc, .res and audio files in the same APK were
already deflated and load fine.

The output is unsigned: run zipalign, then apksigner sign, on it (see ci.yml).

Usage: shrink_apk.py <in.apk> <out.apk>
"""

import sys
import zipfile

# Old v1 signature files: apksigner writes new ones.
_SIGNATURE_SUFFIXES = (".SF", ".RSA", ".DSA", ".EC")


def _is_old_signature(name: str) -> bool:
    if not name.startswith("META-INF/") or name.count("/") != 1:
        return False
    return name == "META-INF/MANIFEST.MF" or name.upper().endswith(_SIGNATURE_SUFFIXES)


def _should_deflate(name: str) -> bool:
    return name.startswith("assets/") and name.lower().endswith(".ctex")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    src_path, dst_path = sys.argv[1], sys.argv[2]
    deflated = 0
    with zipfile.ZipFile(src_path) as src, zipfile.ZipFile(dst_path, "w") as dst:
        for info in src.infolist():
            if _is_old_signature(info.filename):
                continue
            data = src.read(info)
            out = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            out.external_attr = info.external_attr
            out.create_system = info.create_system
            # Drop the old extra field: it holds zipalign padding, which
            # zipalign recomputes.
            out.extra = b""
            if info.compress_type == zipfile.ZIP_STORED and _should_deflate(info.filename):
                out.compress_type = zipfile.ZIP_DEFLATED
                deflated += 1
            else:
                out.compress_type = info.compress_type
            dst.writestr(out, data, compresslevel=9 if out.compress_type == zipfile.ZIP_DEFLATED else None)
    with zipfile.ZipFile(dst_path) as check:
        bad = check.testzip()
        if bad is not None:
            print(f"shrink_apk: corrupt entry after repack: {bad}", file=sys.stderr)
            return 1
    print(f"shrink_apk: deflated {deflated} .ctex entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
