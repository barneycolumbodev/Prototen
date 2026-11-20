#!/usr/bin/env python3
"""Generates data/run/survival.tres: the Survival mode's tuning (docs/design.md §8).

This table is the source of truth: change a number here and rerun
  python3 tools/run/gen_pool.py
rather than editing the .tres by hand.

- POOL: every gun and part a supply drop can bring, with its tags (§8.5), weight, first wave, and for
  actives the Mk I / Mk II overrides (§8.3; Mk III is the part as built). Override values must have the
  property's type (int for ints): tests/unit/test_run_marks.gd checks every key against the part.
- DOCTRINES: the baseline characters (§8.2): starting passives, the actives they can start with, the
  tags they favour.
- ROSTER: Chinatown's enemy types for the wave director (§8.6, §8.8).
- BOSSES: who comes on each boss wave, in order (§8.7): wave 5 the first, wave 10 the second... Past the
  end of the list a boss wave is a lieutenant wave.
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "data", "run", "survival.tres")

W = "weapon"
P = "part"

# (kind, id, tags, weight, min_wave, boss_only, blurb, mk1, mk2)
POOL = [
    # ---------------------------------------------------------- guns
    (W, "pistol_57", ["stealth", "precision"], 1.0, 1, False, "Suppressed 5.7 mm. Quiet, precise, fast follow-ups; rounds go through one man into the next.", {}, {}),
    (W, "mp5", ["mobility", "stealth", "close"], 1.0, 1, False, "Suppressed 9 mm with a green laser: the tightest hip fire on the run, even mid-jump.", {}, {}),
    (W, "saiga12k", ["close", "heavy"], 1.0, 1, False, "Semi-auto 12-gauge. Buck, slugs or Dragon's Breath on D-pad up.", {}, {}),
    (W, "glock22", ["close", "mobility"], 1.0, 2, False, "A switched Glock: .40 at 1,200 rpm, 22 rounds gone in a second. Climbs hard.", {}, {}),
    (W, "m14p", ["precision", "stealth"], 1.0, 2, False, "Suppressed 7.62 mm battle rifle. Heavy, controllable, kills in one or two.", {}, {}),
    (W, "mg42", ["heavy"], 0.9, 4, False, "1,200 rpm of 7.62 mm from a 150-round box. Loose from the hip, slows you down.", {}, {}),
    (W, "m32", ["heavy", "tech"], 0.8, 5, False, "Six 40 mm grenades. Lase a wall with LT and they burst over the men behind it.", {}, {}),
    (W, "rail_carbine", ["precision", "tech"], 0.7, 7, False, "A personal railgun. Any torso hit kills; the slug goes on through walls and men.", {}, {}),
    (W, "governor", ["precision", "heavy"], 0.9, 3, False, "The Governor: a .45-70 lever action. Seven rounds that throw men off their feet; work the lever between shots.", {}, {}),
    (W, "aug", ["precision", "mobility"], 1.0, 2, False, "Steyr AUG: 5.56 mm bullpup with a 1.5x scope. Squeeze for single shots, pull through for automatic.", {}, {}),
    (W, "spas12", ["close", "heavy"], 1.0, 2, False, "SPAS-12, pump only: slower than the Saiga, but every shell hits harder, flies further and groups tighter.", {}, {}),
    (W, "slagger", ["tech", "close"], 0.8, 4, False, "SL-9 plasma pistol. Hold to charge, let go to fire: grazes set men alight, a full charge burns through them.", {}, {}),
    # ---------------------------------------------------------- actives (mk1, mk2 overrides)
    (P, "rx9_reflex_overclock", ["precision", "mobility"], 1.0, 1, False, "",
     {"charge_max": 4.0, "world_scale": 0.4, "regen_per_s": 0.3},
     {"charge_max": 6.0, "world_scale": 0.32, "regen_per_s": 0.38}),
    (P, "sx8_urticating_setae", ["precision", "tech"], 1.0, 1, False, "",
     {"base_marks": 2, "max_marks": 2, "strength_ref": 1.5, "cavity_damage": 240.0, "regen_per_s": 0.06},
     {"base_marks": 3, "max_marks": 4, "strength_ref": 1.3, "cavity_damage": 290.0, "regen_per_s": 0.07}),
    (P, "mw7_monofilament_whip", ["close", "mobility"], 1.0, 1, False, "",
     {"length": 4.2, "damage": 70.0},
     {"length": 5.4, "damage": 85.0}),
    (P, "kr5_ram_thrusters", ["mobility", "heavy"], 1.0, 1, False, "",
     {"charge_max": 1.0, "dash_speed": 21.0, "ram_multiplier": 1.3, "regen_per_s": 0.16},
     {"charge_max": 2.0, "dash_speed": 24.0, "ram_multiplier": 1.55, "regen_per_s": 0.19}),
    (P, "tc4_thermoptic_shroud", ["stealth"], 1.0, 1, False, "",
     {"charge_max": 4.0, "reveal_m": 5.0, "shot_reveal_time": 1.8},
     {"charge_max": 7.0, "reveal_m": 4.0, "shot_reveal_time": 1.4}),
    (P, "bw6_fan_shield", ["heavy", "close"], 1.0, 1, False, "",
     {"charge_max": 7.0, "break_cooldown": 8.0, "bash_bonus": 1.2},
     {"charge_max": 10.5, "break_cooldown": 6.5, "bash_bonus": 1.4}),
    (P, "nt5_mesh_arm", ["close", "tech"], 1.0, 1, False, "",
     {"reach": 10.0, "charge_max": 2.0, "max_throw": 22.0},
     {"reach": 14.0, "charge_max": 3.0, "max_throw": 28.0}),
    (P, "sd3_shrike_drone", ["tech", "stealth"], 1.0, 2, False, "",
     {"charge_max": 1.0, "battery": 12.0, "blast_radius": 4.5, "blast_damage": 220.0},
     {"charge_max": 2.0, "battery": 17.0, "blast_radius": 5.5, "blast_damage": 260.0}),
    (P, "ad2_arc_projector", ["tech", "close"], 1.0, 2, False, "",
     {"chains": 0, "max_chains": 2, "charge_max": 1.0, "damage": 100.0},
     {"chains": 1, "max_chains": 4, "damage": 115.0}),
    (P, "gx4_gauss_arm", ["heavy", "tech"], 1.0, 1, True, "",
     {"charge_max": 4.0, "regen_per_s": 0.18},
     {"charge_max": 7.0, "regen_per_s": 0.22}),
    (P, "lc6_lorentz_catcher", ["heavy", "tech"], 1.0, 1, True, "",
     {"base_capacity": 15, "min_capacity": 10, "max_capacity": 30, "charge_max": 3.0},
     {"base_capacity": 26, "min_capacity": 15, "max_capacity": 60, "charge_max": 4.5}),
    # ---------------------------------------------------------- passives
    (P, "nl3_cortical_uplink", ["tech"], 1.0, 1, False, "", {}, {}),
    (P, "tg6_threat_graph", ["precision", "tech"], 1.0, 3, False, "", {}, {}),
    (P, "ob5_ocular_ballistics", ["precision"], 1.0, 1, False, "", {}, {}),
    (P, "ir3_thermographic_retinas", ["precision", "stealth"], 1.0, 1, False, "", {}, {}),
    (P, "vs1_vestibular_stabilizer", ["mobility", "precision"], 1.0, 1, False, "", {}, {}),
    (P, "sa2_synaptic_accelerator", ["precision", "tech"], 1.0, 1, False, "", {}, {}),
    (P, "er2_reflex_bypass", ["close", "mobility"], 1.0, 1, False, "", {}, {}),
    (P, "mr1_mesh_relay", ["tech"], 1.0, 1, False, "", {}, {}),
    (P, "tl3_titanium_skeleton", ["heavy"], 1.0, 1, False, "", {}, {}),
    (P, "cb1_carbon_sheathing", ["heavy", "mobility"], 1.0, 1, False, "", {}, {}),
    (P, "tn9_tungsten_cores", ["heavy"], 0.8, 6, False, "", {}, {}),
    (P, "em2_myofibrils", ["mobility", "close"], 1.0, 1, False, "", {}, {}),
    (P, "hm5_hydraulic_myomer", ["heavy", "close"], 0.9, 4, False, "", {}, {}),
    (P, "ft1_fast_twitch", ["mobility", "close"], 1.0, 1, False, "", {}, {}),
    (P, "hp4_hyperoxic_lungs", ["mobility"], 1.0, 1, False, "", {}, {}),
    (P, "ch2_cardiac_pump", ["heavy", "close"], 1.0, 1, False, "", {}, {}),
    (P, "pc3_power_cell", ["tech"], 1.0, 1, False, "", {}, {}),
    (P, "fb1_fuel_bladder", ["tech"], 0.8, 3, False, "", {}, {}),
    (P, "nw4_nanoweave", ["stealth", "close"], 1.0, 1, False, "", {}, {}),
    (P, "ct7_trauma_plating", ["heavy"], 0.9, 3, False, "", {}, {}),
    (P, "rp2_ram_plating", ["heavy", "close"], 1.0, 2, False, "", {}, {}),
    (P, "ab1_ablative_shell", ["stealth", "heavy"], 1.0, 2, False, "", {}, {}),
    (P, "sr3_recoil_struts", ["heavy", "precision"], 1.0, 1, False, "", {}, {}),
    (P, "ks2_striker_rams", ["close"], 1.0, 1, False, "", {}, {}),
    (P, "fc1_fire_control", ["precision"], 1.0, 1, False, "", {}, {}),
    (P, "dg3_dexterity_grafts", ["precision", "close"], 1.0, 1, False, "", {}, {}),
    (P, "gp1_setal_pads", ["mobility"], 1.0, 1, False, "", {}, {}),
    (P, "kd2_kinetic_dampers", ["stealth", "mobility"], 1.0, 1, False, "", {}, {}),
    (P, "sp6_sprint_pistons", ["mobility"], 1.0, 1, False, "", {}, {}),
    (P, "lf8_leg_frame", ["heavy"], 1.0, 2, False, "", {}, {}),
    (P, "dl1_dorsal_load_frame", ["heavy"], 0.8, 4, False, "", {}, {}),
    (P, "sb2_spinal_bus", ["tech"], 0.7, 5, False, "", {}, {}),
    (P, "hs5_heat_sinks", ["tech", "heavy"], 1.0, 1, False, "", {}, {}),
    (P, "cm1_chromatophore_mesh", ["stealth"], 1.0, 1, False, "", {}, {}),
    (P, "ds2_dermal_lattice", ["heavy"], 1.0, 1, False, "", {}, {}),
    (P, "hn1_hemostatic_nanites", ["close", "heavy"], 1.0, 2, False, "", {}, {}),
    (P, "oc2_respirocytes", ["mobility", "stealth"], 1.0, 1, False, "", {}, {}),
]

# (name, description, parts, starter actives, primary, secondary)
DOCTRINES = [
    ("Ghost", "Quiet and quick: the synaptic accelerator, chromatophore skin, respirocytes. Drops lean to stealth and mobility.",
     ["sa2_synaptic_accelerator", "cm1_chromatophore_mesh", "oc2_respirocytes"],
     ["rx9_reflex_overclock", "tc4_thermoptic_shroud", "sx8_urticating_setae"], "stealth", "mobility"),
    ("Reaper", "Close work: a titanium frame, myofibrils, the accelerator. Drops lean to close quarters and mobility.",
     ["tl3_titanium_skeleton", "em2_myofibrils", "sa2_synaptic_accelerator"],
     ["mw7_monofilament_whip", "kr5_ram_thrusters", "nt5_mesh_arm"], "close", "mobility"),
    ("Juggernaut", "Takes the hits: carbon sheathing, trauma plating, the leg frame. Drops lean to heavy hardware.",
     ["cb1_carbon_sheathing", "ct7_trauma_plating", "lf8_leg_frame"],
     ["bw6_fan_shield", "kr5_ram_thrusters"], "heavy", "close"),
    ("Marksman", "Every round placed: the accelerator, ballistic eyes, the threat graph. Drops lean to precision.",
     ["sa2_synaptic_accelerator", "ob5_ocular_ballistics", "tg6_threat_graph"],
     ["rx9_reflex_overclock", "sx8_urticating_setae"], "precision", "tech"),
    ("Handler", "Fights through machines: the cortical uplink, a power cell, the mesh relay. Drops lean to tech.",
     ["nl3_cortical_uplink", "pc3_power_cell", "mr1_mesh_relay"],
     ["sd3_shrike_drone", "ad2_arc_projector"], "tech", "precision"),
]

STARTER_WEAPONS = ["pistol_57", "mp5", "saiga12k"]

# (role, cost, first wave, weight, weight per wave, min weight, max count, max count late, late wave)
ROSTER = [
    ("blue_lantern", 1.0, 1, 3.0, -0.15, 0.4, 0, 0, 10),
    ("gunman", 2.0, 1, 2.0, 0.0, 0.05, 0, 0, 10),
    ("enforcer", 3.0, 2, 0.8, 0.06, 0.05, 0, 0, 10),
    ("hatchet_man", 2.0, 4, 1.1, 0.04, 0.05, 3, 5, 10),
    ("red_pole", 4.0, 3, 0.35, 0.02, 0.05, 1, 2, 10),
    # Attack dogs (owner, 2026-11-17; design §8.8b): cheap, fast, come in twos and threes.
    ("attack_dog", 1.5, 6, 1.0, 0.03, 0.1, 3, 5, 12),
]

# Boss roles, in order (data/enemies/<role>.tres, each with a BossConfig).
BOSSES = ["incense_master"]


def f(x):
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        s = repr(x)
        return s if "." in s or "e" in s else s + ".0"
    return x


def esc(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def sn_array(items):
    return "Array[StringName]([" + ", ".join('&"%s"' % t for t in items) + "])"


def vdict(d):
    if not d:
        return "Dictionary[StringName, Variant]({})"
    body = ",\n".join('&"%s": %s' % (k, f(v)) for k, v in d.items())
    return "Dictionary[StringName, Variant]({\n" + body + "\n})"


def main():
    ext = []  # (type, path, id)
    ids = {}

    def ext_id(typ, path):
        if path not in ids:
            ids[path] = "e%d" % (len(ids) + 1)
            ext.append((typ, path, ids[path]))
        return ids[path]

    s_cfg = ext_id("Script", "res://src/run/survival_config.gd")
    s_item = ext_id("Script", "res://src/run/run_item.gd")
    s_doc = ext_id("Script", "res://src/run/doctrine.gd")
    s_enemy = ext_id("Script", "res://src/run/wave_enemy.gd")
    s_part = ext_id("Script", "res://src/body/part_data.gd")
    s_active = ext_id("Script", "res://src/augments/active_part_data.gd")
    s_weapon = ext_id("Script", "res://src/weapons/weapon_data.gd")
    frame = ext_id("Resource", "res://data/player/body_default.tres")

    def res(kind, id):
        path = "res://data/weapons/%s.tres" % id if kind == W else "res://data/body/parts/%s.tres" % id
        if not os.path.exists(os.path.join(ROOT, path[6:])):
            raise SystemExit("missing " + path)
        return ext_id("Resource", path)

    subs = []
    pool_ids = []
    for i, (kind, id, tags, weight, min_wave, boss, blurb, mk1, mk2) in enumerate(POOL):
        sid = "item_%d" % i
        lines = ['[sub_resource type="Resource" id="%s"]' % sid, 'script = ExtResource("%s")' % s_item,
                 'item = ExtResource("%s")' % res(kind, id), "tags = " + sn_array(tags), "weight = " + f(weight),
                 "min_wave = %d" % min_wave, "boss_only = " + f(boss)]
        if blurb:
            lines.append("blurb = " + esc(blurb))
        if mk1:
            lines.append("mk1 = " + vdict(mk1))
        if mk2:
            lines.append("mk2 = " + vdict(mk2))
        subs.append("\n".join(lines))
        pool_ids.append(sid)
    doc_ids = []
    for i, (name, desc, parts, starters, prim, sec) in enumerate(DOCTRINES):
        sid = "doctrine_%d" % i
        lines = ['[sub_resource type="Resource" id="%s"]' % sid, 'script = ExtResource("%s")' % s_doc,
                 "display_name = " + esc(name), "description = " + esc(desc),
                 'parts = Array[ExtResource("%s")]([' % s_part + ", ".join('ExtResource("%s")' % res(P, p) for p in parts) + "])",
                 'starter_actives = Array[ExtResource("%s")]([' % s_active + ", ".join('ExtResource("%s")' % res(P, p) for p in starters) + "])",
                 'primary_tag = &"%s"' % prim, 'secondary_tag = &"%s"' % sec]
        subs.append("\n".join(lines))
        doc_ids.append(sid)
    for b in BOSSES:
        if not os.path.exists(os.path.join(ROOT, "data", "enemies", b + ".tres")):
            raise SystemExit("missing boss " + b)
    ros_ids = []
    for i, (role, cost, first, w, wpw, wmin, cap, cap_late, late) in enumerate(ROSTER):
        if not os.path.exists(os.path.join(ROOT, "data", "enemies", role + ".tres")):
            raise SystemExit("missing enemy " + role)
        sid = "enemy_%d" % i
        subs.append("\n".join(['[sub_resource type="Resource" id="%s"]' % sid, 'script = ExtResource("%s")' % s_enemy,
                               "role = " + esc(role), "cost = " + f(cost), "first_wave = %d" % first, "weight = " + f(w),
                               "weight_per_wave = " + f(wpw), "min_weight = " + f(wmin), "max_count = %d" % cap,
                               "max_count_late = %d" % cap_late, "late_wave = %d" % late]))
        ros_ids.append(sid)
    starters = [res(W, w) for w in STARTER_WEAPONS]
    main_lines = ["[resource]", 'script = ExtResource("%s")' % s_cfg, 'frame = ExtResource("%s")' % frame,
                  'doctrines = Array[ExtResource("%s")]([' % s_doc + ", ".join('SubResource("%s")' % d for d in doc_ids) + "])",
                  'starter_weapons = Array[ExtResource("%s")]([' % s_weapon + ", ".join('ExtResource("%s")' % w for w in starters) + "])",
                  'pool = Array[ExtResource("%s")]([' % s_item + ", ".join('SubResource("%s")' % p for p in pool_ids) + "])",
                  'roster = Array[ExtResource("%s")]([' % s_enemy + ", ".join('SubResource("%s")' % r for r in ros_ids) + "])",
                  "bosses = Array[String]([" + ", ".join(esc(b) for b in BOSSES) + "])"]
    out = ['[gd_resource type="Resource" script_class="SurvivalConfig" load_steps=%d format=3]' % (len(ext) + len(subs) + 1), ""]
    for typ, path, eid in ext:
        out.append('[ext_resource type="%s" path="%s" id="%s"]' % (typ, path, eid))
    out.append("")
    for sb in subs:
        out.append(sb)
        out.append("")
    out.append("\n".join(main_lines))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        fh.write("\n".join(out) + "\n")
    print("wrote", OUT, len(POOL), "items,", len(DOCTRINES), "doctrines,", len(ROSTER), "enemy types")


if __name__ == "__main__":
    main()
