#!/usr/bin/env python3
"""Adds any WeaponData export missing from a weapon .tres, using the code default.
Existing (tuned) values are kept. Usage: tools/sync_weapon_tres.py data/weapons/pistol_57.tres"""
import re, sys
src = open("src/weapons/weapon_data.gd").read()
path = sys.argv[1]
tres = open(path).read()
have = set(re.findall(r'^(\w+) = ', tres, re.M))
add = []
for m in re.finditer(r'^@export(?:_range\([^)]*\))? var (\w+): (\w+) = (.+)$', src, re.M):
    name, typ, val = m.groups()
    if name in have:
        continue
    if typ == "float" and re.fullmatch(r'-?\d+', val):
        val += ".0"
    add.append(f"{name} = {val}")
open(path, "w").write(tres.rstrip("\n") + "\n" + "".join(l + "\n" for l in add))
print(f"{path}: added {len(add)} values")
