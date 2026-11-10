#!/usr/bin/env python3
"""Generates the passive part library (docs/design.md §3.6) as Godot resources.

Writes data/body/parts/<id>.tres for every passive below, data/body/part_library.tres (every part,
passives and actives, in loadout-screen order) and the presets in data/body/presets/. The first two
actives (rx9_reflex_overclock, gx4_gauss_arm) are hand-edited .tres files; only their library entries
are written here. The seven actives of 2026-11-10 are written from the ACTIVE_DEFS table below (their
behaviour-specific tuning is listed as extra lines; the defaults live in each *_data.gd).

This table is the source of truth for the passives: change a number here and rerun
  python3 tools/parts/gen_parts.py
rather than editing the generated .tres by hand.

Location numbers follow PartData.Location. Modifiers are (stat, add, mul): stat = (base + Σadd) × Πmul.
Requirements are (stat, at_least, reason). Visuals are placeholders (socket, shape, size, offset, finish;
shape 1 box, 2 capsule, 3 cylinder) or a modelled scene (socket=None, scene=res path).
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HEAD, EYES, NERVOUS, SKELETON, MUSCLE, TORSO, ARMS, HANDS, LEGS, SPINE, SKIN, BLOOD, EARS, ORGANS, SUIT, BACK = range(16)
BOX, CAPSULE, CYL = 1, 2, 3


def pair(socket, shape, size, offset, finish="hardware", rot=(0, 0, 0)):
    """The same piece on the left and right bone (X mirrored)."""
    x, y, z = offset
    return [(socket + ".L", shape, size, (x, y, z), finish, rot), (socket + ".R", shape, size, (-x, y, z), finish, rot)]


def scene(path, *fallback):
    """A modelled scene; until its glTF exists, the placeholder pieces in `fallback`."""
    return [(None, path, list(fallback))]


P = []


def part(id, name, loc, mass, power, heat, cap, mods, desc, reqs=(), synergy="", vis=(), fixed=False):
    P.append(dict(id=id, name=name, loc=loc, mass=mass, power=power, heat=heat, cap=cap, mods=mods, desc=desc,
                  reqs=reqs, synergy=synergy, vis=list(vis), fixed=fixed))


# ============================================================== suit (fixed)
part("cs1_carapace", "GS-2 Graft Suit", SUIT, 6.0, 15, 20, 0, [],
     "The base suit: a sealed nanoweave undersuit with thin, flat ceramic-polymer plates grafted onto it over the chest, "
     "abdomen, back, shoulders, arms, thighs and shins, and hardpoint pads where part hardware docks. Spreads impacts across the plates.",
     fixed=True)

# ============================================================== neural
part("sa2_synaptic_accelerator", "SA-2 Synaptic Accelerator", NERVOUS, 0.3, 35, 30, 2,
     [("processing", 0.2, 1), ("aim_speed", 0, 1.2), ("reload_speed", 0, 1.1), ("handling", 0, 1.05)],
     "A myelin-sheath co-processor wrapped round the brainstem. Speeds up every motor loop: sights come up and magazines go in faster.",
     synergy="Processing ×1.20 meets the RX-9 Reflex Overclock's requirement on its own and stretches its charge. Needed by the SB-2 bus.",
     vis=scene("res://assets/augments/passives/sa2_synaptic_accelerator/sa2_synaptic_accelerator.gltf", *[("neck", BOX, (0.05, 0.03, 0.02), (0, 0.01, -0.098), "hardware")]))
part("er2_reflex_bypass", "ER-2 Reflex Arc Bypass", NERVOUS, 0.2, 20, 20, 2,
     [("agility", 0, 1.12), ("melee_speed", 0, 1.3), ("handling", 0, 1.15), ("recoil", 0, 1.08)],
     "Spinal shunts that route trained motor reflexes past the brain. The body moves before you decide to; the hands overcorrect under recoil.",
     synergy="Competes with SA-2 and RX-9 for the two nervous-system slots.",
     vis=[("spine", BOX, (0.03, 0.12, 0.012), (0, 0.06, -0.11), "glow")])
part("mr1_mesh_relay", "MR-1 Mesh Relay Lattice", NERVOUS, 0.1, 30, 15, 1,
     [("connectivity", 1.5, 1), ("processing", 0.05, 1), ("signature", 0, 1.05)],
     "A filament lattice laid over the motor cortex that relays signals to external hardware. Leaks a little RF.",
     synergy="Connectivity 1.5 on its own: enough for an FC-1 link. With an NL-3 it reaches 4.5 (180 m of drone range).",
     vis=scene("res://assets/augments/passives/mr1_mesh_relay/mr1_mesh_relay.gltf", *[("head", CYL, (0.006, 0.004, 0.006), (0, 0.11, -0.07), "glow")]))
part("nl3_cortical_uplink", "NL-3 Cortical Uplink", HEAD, 0.6, 25, 20, 2,
     [("connectivity", 3.0, 1), ("perception", 0, 1.05), ("signature", 0, 1.12)],
     "A skull-mounted transceiver module at the base of the skull: a phased antenna array in two blades and a fibre trunk into the cervical spine. "
     "Your brain talks to drones, turrets and smart weapons directly.",
     synergy="Connectivity 3: required by remote-controlled hardware (drones); link range 40 m per point (120 m). Links the FC-1 to the gun.",
     vis=scene("res://assets/augments/passives/nl3_cortical_uplink/nl3_cortical_uplink.gltf",
               ("neck", BOX, (0.06, 0.05, 0.03), (0, 0.0, -0.1), "hardware"), ("head", BOX, (0.008, 0.07, 0.03), (0.025, 0.02, -0.1), "hardware"),
               ("head", BOX, (0.008, 0.07, 0.03), (-0.025, 0.02, -0.1), "hardware")))
part("tg6_threat_graph", "TG-6 Threat-Graph Co-processor", HEAD, 0.5, 45, 45, 2,
     [("perception", 0, 1.35), ("processing", 0.1, 1), ("rifle", 0, 1.05)],
     "A cranial co-processor that tracks every body in view and predicts where it will be. Runs hot.",
     synergy="Shares the cranial slot with the NL-3: perception or connectivity, not both.",
     vis=[("head", BOX, (0.07, 0.012, 0.05), (0, 0.15, -0.03), "hardware")])
part("ob5_ocular_ballistics", "OB-5 Ocular Ballistics Suite", EYES, 0.05, 20, 10, 2,
     [("perception", 0, 1.2), ("rifle", 0, 1.12), ("handgun", 0, 1.05), ("aim_speed", 0, 1.05)],
     "Replacement eyes with a rangefinder and a ballistic solver. Holdover and lead are drawn straight onto the retina.",
     vis=scene("res://assets/augments/passives/ob5_ocular_ballistics/ob5_ocular_ballistics.gltf", *[("head", CYL, (0.008, 0.004, 0.008), (0.032, 0.07, 0.085), "glow"), ("head", CYL, (0.008, 0.004, 0.008), (-0.032, 0.07, 0.085), "glow")]))
part("ir3_thermographic_retinas", "IR-3 Thermographic Retinas", EYES, 0.05, 15, 5, 1,
     [("perception", 0, 1.15)],
     "Cooled microbolometer retinas. Bodies glow through smoke and darkness. Cheap and simple.",
     vis=[("head", CYL, (0.007, 0.004, 0.007), (0.032, 0.07, 0.085), "glow"), ("head", CYL, (0.007, 0.004, 0.007), (-0.032, 0.07, 0.085), "glow")])
part("vs1_vestibular_stabilizer", "VS-1 Vestibular Stabilizer", EARS, 0.02, 10, 0, 1,
     [("stability", 0, 1.6), ("wallrun", 0, 1.15), ("agility", 0, 1.03)],
     "Gyroscopic inner-ear grafts. The horizon stays level whatever the body does: full accuracy while sliding, wall-running and in the air.",
     vis=scene("res://assets/augments/passives/vs1_vestibular_stabilizer/vs1_vestibular_stabilizer.gltf", *[("head", CYL, (0.012, 0.006, 0.012), (0.075, 0.05, -0.01), "hardware", (0, 0, 90)), ("head", CYL, (0.012, 0.006, 0.012), (-0.075, 0.05, -0.01), "hardware", (0, 0, 90))]))

# ============================================================== skeleton
part("tl3_titanium_skeleton", "TL-3 Titanium-Lattice Skeleton", SKELETON, 9.0, 0, 0, 2,
     [("structure", 0.45, 1), ("carry_kg", 25, 1), ("recoil", 0, 0.9), ("max_health", 20, 1), ("damage_per_kj", 0, 0.95)],
     "Long bones laced with a printed titanium lattice; anchor bolts show at the wrists and knuckles. The frame for heavy muscle and heavy guns.",
     synergy="Structure ×1.45: meets the GX-4 Gauss arm's requirement, lifts the strength cap to ×1.89 and steadies heavy weapons.",
     vis=scene("res://assets/augments/passives/tl3_titanium_skeleton/tl3_titanium_skeleton.gltf", *pair("hand", CYL, (0.008, 0.008, 0.008), (0.0, 0.03, 0.025))))
part("cb1_carbon_sheathing", "CB-1 Carbon-Weave Bone Sheathing", SKELETON, 2.5, 0, 0, 1,
     [("structure", 0.25, 1), ("carry_kg", 10, 1), ("max_health", 10, 1)],
     "Carbon-fibre sleeves bonded round the long bones. Light; just enough for a Gauss arm.",
     synergy="Structure ×1.25: exactly the GX-4's requirement, for builds that can't spare the mass of TL-3.")
part("tn9_tungsten_cores", "TN-9 Tungsten Long-Bone Cores", SKELETON, 18.0, 0, 0, 3,
     [("structure", 0.9, 1), ("carry_kg", 45, 1), ("recoil", 0, 0.8), ("impact", 0, 1.3), ("max_health", 35, 1),
      ("damage_per_kj", 0, 0.92), ("jump", 0, 0.88), ("agility", 0, 0.92)],
     "The marrow is replaced with tungsten-alloy cores. Nearly unbreakable, and you hit like a falling engine block. You also weigh like one.",
     synergy="18 kg: without strong muscle (HM-5) the load slows you. Structure ×1.9 lifts the strength cap to ×2.47.",
     vis=scene("res://assets/augments/passives/tn9_tungsten_cores/tn9_tungsten_cores.gltf", *pair("forearm", CYL, (0.01, 0.02, 0.01), (0.0, 0.25, 0.03))))

# ============================================================== muscle
part("em2_myofibrils", "EM-2 Electroactive Myofibrils", MUSCLE, 3.0, 60, 80, 2,
     [("move_speed", 0, 1.1), ("jump", 0, 1.15), ("strength", 0.15, 1), ("agility", 0, 1.06)],
     "Synthetic muscle bands woven through the limbs, glowing faintly through vents in the forearms. Faster, springier; draws power and runs hot.",
     synergy="Heat 80 W: with HS-5 heat sinks you never build up heat; without cooling, sustained actives push you towards overheating.",
     vis=scene("res://assets/augments/passives/em2_myofibrils/em2_myofibrils.gltf", *pair("forearm", BOX, (0.03, 0.16, 0.012), (0, 0.12, -0.04), "glow")))
part("hm5_hydraulic_myomer", "HM-5 Hydraulic Myomer Bundles", MUSCLE, 9.0, 90, 120, 3,
     [("strength", 0.65, 1), ("melee_power", 0, 1.3), ("carry_kg", 15, 1), ("impact", 0, 1.15), ("agility", 0, 0.9), ("noise", 0, 1.25)],
     "Pressurised myomer bundles over the shoulders, back and thighs. Enormous force, slow to change direction, and you can hear the pumps.",
     reqs=[("structure", 1.2, "the bundles would snap organic bone")],
     synergy="Usable strength is capped at structure × 1.3: TL-3 or TN-9 lets it use all of it. Strength divides the load, so it carries heavy armour.",
     vis=scene("res://assets/augments/passives/hm5_hydraulic_myomer/hm5_hydraulic_myomer.gltf", *pair("upper_arm", CAPSULE, (0.04, 0.18, 0.04), (0.02, 0.14, -0.035), "hardware")))
part("ft1_fast_twitch", "FT-1 Fast-Twitch Fiber Graft", MUSCLE, 1.0, 15, 35, 1,
     [("agility", 0, 1.2), ("move_speed", 0, 1.05), ("melee_speed", 0, 1.2), ("handling", 0, 1.1), ("strength", -0.1, 1), ("max_health", -15, 1)],
     "Engineered type IIx fibres replace slow muscle. Explosive and quick, but less force and less meat between you and a bullet.")

# ============================================================== organs (2 slots)
part("hp4_hyperoxic_lungs", "HP-4 Hyperoxic Lung Lining", ORGANS, 0.4, 10, 0, 1,
     [("regen_delay", 0, 0.8), ("move_speed", 0, 1.03), ("heat_dissipation_w", 40, 1)],
     "A gas-exchange membrane that triples the lungs' oxygen uptake and dumps heat with every breath.")
part("ch2_cardiac_pump", "CH-2 Auxiliary Cardiac Pump", ORGANS, 1.2, 40, 35, 1,
     [("regen_rate", 0, 1.3), ("max_health", 25, 1)],
     "A second heart: a magnetically levitated rotary pump beside the first. Keeps pressure up through wounds.")
part("pc3_power_cell", "PC-3 Betavoltaic Power Cell", ORGANS, 4.0, 0, 70, 2,
     [("power_supply_w", 200, 1), ("signature", 0, 1.08)],
     "A sealed tritium cell under the ribs. Two hundred watts more, forever, and a little warmer.",
     synergy="Power headroom recharges the GX-4's rounds faster and keeps power-hungry builds out of brown-out.",
     vis=scene("res://assets/augments/passives/pc3_power_cell/pc3_power_cell.gltf", *[("spine", BOX, (0.08, 0.06, 0.02), (0, 0.04, 0.115), "hardware")]))
part("fb1_fuel_bladder", "FB-1 Glucose Fuel Bladder", ORGANS, 3.0, 0, 0, 1,
     [("power_capacity_j", 60000, 1), ("profile", 0, 1.02)],
     "A glucose reservoir and fuel cell in the abdomen. Doubles the stored energy for actives.")

# ============================================================== torso armour
part("nw4_nanoweave", "NW-4 Nanoweave Fiber Vest", TORSO, 4.0, 0, 0, 1,
     [("damage_per_kj", 0, 0.85)],
     "A close-fitting vest of shear-thickening nanoweave under the plates. Stops pistol rounds cold; light and silent.",
     vis=[("chest", BOX, (0.3, 0.005, 0.2), (0, 0.14, 0.0), "plate", (90, 0, 0))])
part("ct7_trauma_plating", "CT-7 Ceramic Trauma Plating", TORSO, 18.0, 0, 0, 3,
     [("damage_per_kj", 0, 0.62), ("max_health", 40, 1), ("impact", 0, 1.25), ("profile", 0, 1.18), ("noise", 0, 1.15), ("heat_dissipation_w", -40, 1)],
     "Boron-carbide trauma plates bolted over the graft suit: a breastplate, a back plate, shoulder pauldrons and a collar. Stops rifle rounds; "
     "makes you a bigger, louder target and traps heat.",
     synergy="18 kg: carried by strength (load = mass ÷ usable strength). Its mass and impact make slides hit much harder.",
     vis=scene("res://assets/augments/passives/ct7_trauma_plating/ct7_trauma_plating.gltf",
               ("chest", BOX, (0.34, 0.24, 0.04), (0, 0.1, 0.13), "plate"), ("chest", BOX, (0.34, 0.26, 0.04), (0, 0.1, -0.13), "plate")))
part("rp2_ram_plating", "RP-2 Reactive Ram Plating", TORSO, 11.0, 0, 0, 2,
     [("impact", 0, 1.7), ("damage_per_kj", 0, 0.88), ("melee_power", 0, 1.15), ("profile", 0, 1.1), ("agility", 0, 0.95)],
     "Wedge plates on the shoulders and a prow down the sternum, faced with reactive tiles that fire on contact. Built for going through people.",
     synergy="Impact multiplies slide and melee knockback: with mass and strength, slides break bodies.",
     vis=scene("res://assets/augments/passives/rp2_ram_plating/rp2_ram_plating.gltf", *pair("clavicle", BOX, (0.12, 0.03, 0.12), (0.0, 0.12, 0.0), "plate")))
part("ab1_ablative_shell", "AB-1 Ablative Polymer Shell", TORSO, 7.0, 0, 0, 2,
     [("damage_per_kj", 0, 0.75), ("signature", 0, 0.85), ("regen_rate", 0, 0.85), ("heat_dissipation_w", -60, 1)],
     "A radar-absorbent polymer shell that boils away under hits instead of passing the energy on. Quiet to sensors, hot inside, slow to repair.",
     vis=[("chest", BOX, (0.32, 0.22, 0.02), (0, 0.1, 0.12), "plate")])

# ============================================================== arms (2 slots, the GX-4 takes one)
part("sr3_recoil_struts", "SR-3 Servo-Recoil Forearm Struts", ARMS, 3.5, 25, 15, 2,
     [("recoil", 0, 0.75), ("heavy", 0, 1.15), ("rifle", 0, 1.05), ("handling", 0, 0.92)],
     "Servo struts along the forearms that fire against the recoil impulse. The muzzle barely moves; the hands are a little slower.",
     vis=pair("forearm", CYL, (0.008, 0.2, 0.008), (0.03, 0.13, 0.03), "hardware"))
part("ks2_striker_rams", "KS-2 Kinetic Striker Rams", ARMS, 4.0, 20, 20, 2,
     [("melee_power", 0, 1.7), ("impact", 0, 1.1), ("reload_speed", 0, 0.93)],
     "Pneumatic rams in the forearms that drive the fist forward at the moment of impact.",
     reqs=[("structure", 1.15, "the rams fire through the forearm bones")],
     vis=scene("res://assets/augments/passives/ks2_striker_rams/ks2_striker_rams.gltf", *pair("forearm", CYL, (0.018, 0.12, 0.018), (0.0, 0.16, -0.035), "hardware")))

# ============================================================== hands
part("fc1_fire_control", "FC-1 Fire-Control Link", HANDS, 0.2, 15, 5, 2,
     [("recoil", 0, 0.85), ("handgun", 0, 1.15), ("rifle", 0, 1.1), ("shotgun", 0, 1.05), ("heavy", 0, 1.05), ("handling", 0, 1.1)],
     "Contact pads in the palms that talk to the gun's fire-control chip: the hand knows where the bore points and corrects for it.",
     reqs=[("connectivity", 1.0, "the pads need a neural link to talk to the gun")],
     synergy="Needs connectivity 1 (MR-1 or NL-3).",
     vis=scene("res://assets/augments/passives/fc1_fire_control/fc1_fire_control.gltf", *pair("hand", BOX, (0.04, 0.05, 0.004), (0.0, 0.04, -0.012), "glow")))
part("dg3_dexterity_grafts", "DG-3 Dexterity Grafts", HANDS, 0.3, 0, 0, 1,
     [("reload_speed", 0, 1.3), ("handling", 0, 1.2), ("handgun", 0, 1.05)],
     "Rebuilt tendons and joint sensors in the hands and wrists. Magazines and grips just happen.",
     vis=scene("res://assets/augments/passives/dg3_dexterity_grafts/dg3_dexterity_grafts.gltf"))
part("gp1_setal_pads", "GP-1 Setal Grip Pads", HANDS, 0.2, 0, 0, 1,
     [("climb", 0, 1.25), ("wallrun", 0, 1.3), ("reload_speed", 0, 0.95)],
     "Gecko-style setal pads on the palms and fingers. Hold on to walls and ledges; fiddly with magazines.",
     vis=pair("fingers", BOX, (0.04, 0.05, 0.004), (0.0, 0.03, -0.01), "hardware"))

# ============================================================== legs
part("kd2_kinetic_dampers", "KD-2 Kinetic Dampers", LEGS, 4.0, 10, 0, 2,
     [("noise", 0, 0.55), ("slide", 0, 1.3), ("jump", 0, 1.05)],
     "Magnetorheological dampers at the knees and ankles: chrome piston rods in sealed sleeves. Soft, silent landings and long, smooth slides.",
     vis=scene("res://assets/augments/passives/kd2_kinetic_dampers/kd2_kinetic_dampers.gltf",
               *pair("shin", CYL, (0.012, 0.14, 0.012), (0.05, 0.06, 0.0)), *pair("shin", CYL, (0.012, 0.1, 0.012), (0.05, 0.42, 0.0))))
part("sp6_sprint_pistons", "SP-6 Calf Sprint Pistons", LEGS, 6.0, 50, 60, 2,
     [("move_speed", 0, 1.15), ("jump", 0, 1.25), ("slide", 0, 1.1), ("noise", 0, 1.4)],
     "Gas pistons along the calves that kick on every stride. Very fast, very loud.",
     vis=scene("res://assets/augments/passives/sp6_sprint_pistons/sp6_sprint_pistons.gltf", *pair("shin", CYL, (0.014, 0.24, 0.014), (0.0, 0.2, -0.05), "hardware")))
part("lf8_leg_frame", "LF-8 Load-Bearing Leg Frame", LEGS, 10.0, 0, 0, 2,
     [("carry_kg", 25, 1), ("impact", 0, 1.2), ("structure", 0.1, 1), ("slide", 0, 0.85), ("agility", 0, 0.9), ("jump", 0, 0.92)],
     "An external frame from hip to ankle that takes weight off the legs. Stable as a tripod, and about as nimble.",
     vis=pair("thigh", BOX, (0.02, 0.38, 0.02), (0.07, 0.2, 0.0), "hardware"))

# ============================================================== spine
part("dl1_dorsal_load_frame", "DL-1 Dorsal Load Frame", SPINE, 14.0, 20, 0, 3,
     [("carry_kg", 55, 1), ("heavy", 0, 1.35), ("recoil", 0, 0.88), ("wallrun", 0, 0.0), ("profile", 0, 1.2)],
     "A spinal exoframe with shoulder outriggers and an ammunition feed over the shoulder: hip-fire a machine gun at full speed. Too rigid to wall-run.",
     reqs=[("structure", 1.2, "the frame anchors to the vertebrae")],
     synergy="Carry +55 kg removes the MG42's handling penalty; no wall-running at all.",
     vis=scene("res://assets/augments/passives/dl1_dorsal_load_frame/dl1_dorsal_load_frame.gltf", *[("spine", BOX, (0.2, 0.36, 0.06), (0, 0.18, -0.14), "hardware"), ("chest", BOX, (0.44, 0.04, 0.05), (0, 0.18, -0.13), "hardware")]))
part("sb2_spinal_bus", "SB-2 Spinal Bus Extender", SPINE, 1.0, 40, 35, 0,
     [("capacity", 3, 1)],
     "A second data and power trunk along the spine: room for three more capacity of hardware.",
     reqs=[("processing", 1.1, "the bus needs a co-processor to arbitrate it")],
     synergy="Costs no capacity and adds 3; needs processing ×1.10 (SA-2, MR-1 + TG-6...).",
     vis=[("spine", BOX, (0.02, 0.3, 0.012), (0, 0.12, -0.12), "glow")])

# ============================================================== skin
part("hs5_heat_sinks", "HS-5 Subdermal Heat Sinks", SKIN, 3.0, 0, 0, 1,
     [("heat_dissipation_w", 260, 1), ("signature", 0, 1.3), ("profile", 0, 1.03)],
     "Copper-graphene heat spreaders under the skin, venting through rows of fins along the forearms. Sheds heat fast and glows on thermal sights.",
     synergy="Cooling +260 W: hot builds (EM-2, HM-5, TG-6) never overheat. Raises your signature.",
     vis=scene("res://assets/augments/passives/hs5_heat_sinks/hs5_heat_sinks.gltf",
               *pair("forearm", BOX, (0.006, 0.14, 0.03), (0.045, 0.12, 0.0))))
part("cm1_chromatophore_mesh", "CM-1 Chromatophore Skin Mesh", SKIN, 0.8, 30, 10, 2,
     [("signature", 0, 0.55), ("profile", 0, 0.92), ("damage_per_kj", 0, 1.1)],
     "An electrochromic mesh under the suit that matches the background and masks body heat. Thin where the plates used to bond.",
     vis=scene("res://assets/augments/passives/cm1_chromatophore_mesh/cm1_chromatophore_mesh.gltf", *[("chest", BOX, (0.04, 0.04, 0.004), (0.1, 0.15, 0.13), "glow")]))
part("ds2_dermal_lattice", "DS-2 Dermal Armour Lattice", SKIN, 5.0, 0, 0, 1,
     [("damage_per_kj", 0, 0.86), ("max_health", 15, 1), ("heat_dissipation_w", -60, 1), ("agility", 0, 0.97)],
     "A hexagonal ceramic lattice in the dermis. Tougher skin that holds heat in.")

# ============================================================== blood
part("hn1_hemostatic_nanites", "HN-1 Hemostatic Nanites", BLOOD, 0.1, 25, 15, 3,
     [("regen_rate", 0, 1.5), ("regen_delay", -1.0, 1)],
     "Clotting nanites in the bloodstream. Wounds visibly close; the body heals sooner and faster after a fight.")
part("oc2_respirocytes", "OC-2 Respirocyte Blood", BLOOD, 0.1, 10, 0, 2,
     [("move_speed", 0, 1.04), ("regen_delay", 0, 0.85), ("heat_dissipation_w", 80, 1)],
     "Synthetic oxygen-carrier cells and a coolant fraction in the blood. More endurance, and the blood itself carries heat away.")

# ============================================================== actives (hand-edited files) and presets
ACTIVES = ["rx9_reflex_overclock", "gx4_gauss_arm", "mw7_monofilament_whip", "nt5_mesh_arm", "bw6_fan_shield", "sd3_shrike_drone",
           "ad2_arc_projector", "kr5_ram_thrusters", "tc4_thermoptic_shroud"]
ORDER = [SUIT, HEAD, EYES, EARS, NERVOUS, SKELETON, MUSCLE, ORGANS, TORSO, ARMS, HANDS, LEGS, SPINE, BACK, SKIN, BLOOD]
ACTIVE_LOC = {"rx9_reflex_overclock": NERVOUS, "gx4_gauss_arm": ARMS, "mw7_monofilament_whip": ARMS, "nt5_mesh_arm": ARMS,
              "bw6_fan_shield": ARMS, "sd3_shrike_drone": BACK, "ad2_arc_projector": BACK, "kr5_ram_thrusters": BACK,
              "tc4_thermoptic_shroud": SKIN}

PRESETS = {
    "loadout_default": ("Operator", "The all-rounder: titanium frame, fast muscle, cooling, the synaptic accelerator; RX-9 and the GX-4 arm.",
                        ["cs1_carapace", "tl3_titanium_skeleton", "sa2_synaptic_accelerator", "em2_myofibrils", "hs5_heat_sinks",
                         "rx9_reflex_overclock", "gx4_gauss_arm"]),
    "presets/ghost": ("Ghost", "Silent and quick: chromatophore skin, dampers, fast-twitch muscle, stabilised aim. Pistol and slow motion; no Gauss arm (structure too low).",
                      ["cs1_carapace", "sa2_synaptic_accelerator", "rx9_reflex_overclock", "cm1_chromatophore_mesh", "kd2_kinetic_dampers",
                       "ft1_fast_twitch", "vs1_vestibular_stabilizer", "dg3_dexterity_grafts", "ob5_ocular_ballistics", "hp4_hyperoxic_lungs"]),
    "presets/juggernaut": ("Juggernaut", "Tungsten bones, hydraulic muscle, trauma plating and the dorsal frame: the MG42 from the hip, slides that break bodies. No slow motion, no wall-running.",
                           ["cs1_carapace", "ct7_trauma_plating", "tn9_tungsten_cores", "hm5_hydraulic_myomer", "dl1_dorsal_load_frame",
                            "gx4_gauss_arm", "ch2_cardiac_pump"]),
    "presets/marksman": ("Marksman", "Linked: the cortical uplink and mesh relay feed the fire-control link and the ballistic eyes. Rifles and the Gauss arm on a light carbon frame.",
                         ["cs1_carapace", "nl3_cortical_uplink", "mr1_mesh_relay", "fc1_fire_control", "ob5_ocular_ballistics",
                          "vs1_vestibular_stabilizer", "sa2_synaptic_accelerator", "cb1_carbon_sheathing", "gx4_gauss_arm", "pc3_power_cell"]),
}


def f(x):
    return repr(float(x))


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def write_part(p):
    ext = ['[ext_resource type="Script" path="res://src/body/part_data.gd" id="1"]',
           '[ext_resource type="Script" path="res://src/body/stat_modifier.gd" id="2"]',
           '[ext_resource type="Script" path="res://src/body/part_visual.gd" id="3"]',
           '[ext_resource type="Script" path="res://src/body/stat_requirement.gd" id="4"]']
    subs, mods, reqs, vis = [], [], [], []
    for i, (stat, add, mul) in enumerate(p["mods"]):
        subs.append(f'[sub_resource type="Resource" id="mod_{i}"]\nscript = ExtResource("2")\nstat = &"{stat}"\nadd = {f(add)}\nmul = {f(mul)}\n')
        mods.append(f'SubResource("mod_{i}")')
    for i, (stat, least, why) in enumerate(p["reqs"]):
        subs.append(f'[sub_resource type="Resource" id="req_{i}"]\nscript = ExtResource("4")\nstat = &"{stat}"\nat_least = {f(least)}\nreason = "{esc(why)}"\n')
        reqs.append(f'SubResource("req_{i}")')
    n_ext = 5
    pieces = []
    for v in p["vis"]:
        if v[0] is None and not os.path.exists(os.path.join(ROOT, v[1].replace("res://", ""))):
            pieces += v[2]  # not modelled yet: placeholders
        else:
            pieces.append(v)
    for i, v in enumerate(pieces):
        if v[0] is None:
            ext.append(f'[ext_resource type="PackedScene" path="{v[1]}" id="{n_ext}"]')
            subs.append(f'[sub_resource type="Resource" id="vis_{i}"]\nscript = ExtResource("3")\nsocket = &"root"\nscene = ExtResource("{n_ext}")\nmodel_space = true\n')
            n_ext += 1
        else:
            sock, shape, size, off, finish = v[:5]
            rot = v[5] if len(v) > 5 else (0, 0, 0)
            subs.append(f'[sub_resource type="Resource" id="vis_{i}"]\nscript = ExtResource("3")\nsocket = &"{sock}"\nshape = {shape}\n'
                        f'size = Vector3({f(size[0])}, {f(size[1])}, {f(size[2])})\noffset = Vector3({f(off[0])}, {f(off[1])}, {f(off[2])})\n'
                        f'rotation_deg = Vector3({f(rot[0])}, {f(rot[1])}, {f(rot[2])})\nfinish = "{finish}"\n')
        vis.append(f'SubResource("vis_{i}")')
    out = [f'[gd_resource type="Resource" script_class="PartData" load_steps={len(ext) + len(subs) + 1} format=3]', ""]
    out += ext + [""]
    for s in subs:
        out += [s]
    out += ["[resource]", 'script = ExtResource("1")', f'id = &"{p["id"]}"', f'display_name = "{esc(p["name"])}"',
            f'description = "{esc(p["desc"])}"', f'location = {p["loc"]}']
    if p["fixed"]:
        out.append("fixed = true")
    out += [f'mass_kg = {f(p["mass"])}', f'power_draw_w = {f(p["power"])}', f'heat_w = {f(p["heat"])}', f'capacity = {p["cap"]}',
            f'modifiers = Array[ExtResource("2")]([{", ".join(mods)}])',
            f'requirements = Array[ExtResource("4")]([{", ".join(reqs)}])',
            f'synergy = "{esc(p["synergy"])}"',
            f'visuals = Array[ExtResource("3")]([{", ".join(vis)}])', ""]
    with open(os.path.join(ROOT, "data", "body", "parts", p["id"] + ".tres"), "w") as fh:
        fh.write("\n".join(out))


def write_list(path, script, script_class, fields, ids):
    ext = [f'[ext_resource type="Script" path="{script}" id="1"]',
           '[ext_resource type="Script" path="res://src/body/part_data.gd" id="2"]']
    refs = []
    for i, pid in enumerate(ids):
        ext.append(f'[ext_resource type="Resource" path="res://data/body/parts/{pid}.tres" id="p{i}"]')
        refs.append(f'ExtResource("p{i}")')
    out = [f'[gd_resource type="Resource" script_class="{script_class}" load_steps={len(ext) + 1} format=3]', ""] + ext + [""]
    out += ["[resource]", 'script = ExtResource("1")'] + fields + [f'parts = Array[ExtResource("2")]([{", ".join(refs)}])', ""]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write("\n".join(out))


# ============================================================== actives written from here (2026-11-10)
def vm(eye, look):
    return dict(eye=eye, look=look)


A = []


def active(id, name, short, loc, script, data_script, mass, power, heat, cap, desc, reqs, synergy, timing, charge, load,
           mount="", scene=None, view=None, vis=(), extra=()):
    A.append(dict(id=id, name=name, short=short, loc=loc, script=script, data_script=data_script, mass=mass, power=power, heat=heat,
                  cap=cap, desc=desc, reqs=reqs, synergy=synergy, timing=timing, charge=charge, load=load, mount=mount, scene=scene,
                  view=view, vis=list(vis), extra=list(extra)))


active("mw7_monofilament_whip", "MW-7 Monofilament Whip", "MW-7", ARMS, "whip/whip.gd", "whip/whip_data.gd", 2.2, 10, 5, 2,
       "A reel on the back of the right wrist pays out six and a half metres of monomolecular filament with a tungsten bead on the end. "
       "Whatever it crosses at speed is cut: limbs, heads, bodies. Select it on the D-pad, LB to draw it or reel it in. Hold LT: the view "
       "holds still and the right stick swings the whip. RT lashes across the crosshair.",
       [("processing", 1.1, "the filament is steered by a guidance loop; without a co-processor it takes your own arm off")],
       "Needs processing ×1.10 (SA-2). Melee speed sets how fast it swings and lashes; melee power how deep it bites. Takes the right arm: "
       "not with the GX-4, and guns go away while it's out.",
       (0.6, 0.4, 0.2), (1.0, 0.0, 1.0, 0.0, 0.0), (60, 40), mount="arm_right",
       scene="res://assets/augments/mw7_monofilament_whip/mw7_monofilament_whip.gltf", view=vm((-0.42, 0.27, -0.3), (1.0, -0.06, -0.08)),
       vis=[("forearm.R", BOX, (0.06, 0.07, 0.05), (0.0, 0.2, 0.05), "hardware"), ("forearm.R", CYL, (0.022, 0.05, 0.022), (0.0, 0.2, 0.075), "glow", (0, 0, 90))])
active("nt5_mesh_arm", "NT-5 Prehensile Mesh Arm", "NT-5", ARMS, "mesh_arm/mesh_arm.gd", "mesh_arm/mesh_arm_data.gd", 5.5, 25, 15, 3,
       "The left forearm is a braid of carbon-nanotube muscle mesh. Unbraided it pays out as an eighteen-metre tendril with a four-fingered "
       "claw. Select it on the D-pad, LB to unbraid or fold it. RT shoots it at whoever is under the crosshair and hauls him in; he hangs in "
       "front of you and takes the rounds meant for you. RT again throws him: he breaks whoever he hits and dies where he lands.",
       [("strength", 1.15, "the braid pulls with whatever the shoulder gives it"), ("structure", 1.2, "a thrown man would take an organic shoulder with him")],
       "Needs strength ×1.15 (EM-2, HM-5) and structure ×1.20. Throw speed = 17 m/s × usable strength ÷ 1.15 × √impact: the Juggernaut "
       "throws a man through a wall. Takes the left arm: not with the BW-6 shield; guns go away while it's out, the GX-4 doesn't.",
       (0.7, 0.45, 0.25), (4.0, 0.0, 0.2, 2.0, 1.0), (150, 120), mount="arm_left",
       scene="res://assets/augments/nt5_mesh_arm/nt5_mesh_arm.gltf", view=vm((-0.42, 0.27, 0.3), (1.0, -0.06, 0.08)),
       vis=[("forearm.L", CAPSULE, (0.048, 0.26, 0.048), (0.0, 0.13, 0.0), "hardware"), ("forearm.L", CYL, (0.052, 0.012, 0.052), (0.0, 0.02, 0.0), "glow")])
active("bw6_fan_shield", "BW-6 Bulwark Fan Shield", "BW-6", ARMS, "shield/fan_shield.gd", "shield/fan_shield_data.gd", 8.0, 5, 0, 2,
       "Seven boron-carbide leaves on a hub on the left forearm. They fan out into half a disc of shield in half a second. Rounds from the "
       "front are stopped and their energy comes out of the shield's integrity; at zero it breaks and needs five seconds. Select it on the "
       "D-pad, LB to raise or fold it. The R3 strike becomes a shield bash.",
       [("structure", 1.15, "every round it stops goes through the forearm into the skeleton")],
       "Needs structure ×1.15. Integrity = 14 kJ × structure ÷ 1.45. Takes the left arm: two-handed guns go away, so pair it with the GX-4 "
       "or the whip in the right arm, or bash (R3: shove ×1.6, so mass, strength and impact).",
       (0.5, 0.35, 0.3), (14.0, 0.0, 1.2, 3.0, 3.0), (0, 0), mount="arm_left",
       scene="res://assets/augments/bw6_fan_shield/bw6_fan_shield.gltf", view=vm((0.03, 0.42, 0.44), (0.03, 0.42, -1.0)),
       vis=[("forearm.L", BOX, (0.1, 0.38, 0.03), (-0.05, 0.2, 0.0), "plate"), ("forearm.L", CYL, (0.034, 0.05, 0.034), (-0.06, 0.14, 0.0), "hardware", (0, 0, 90))])
active("sd3_shrike_drone", "SD-3 Shrike Drone Pod", "SD-3", BACK, "drone/shrike_drone.gd", "drone/shrike_drone_data.gd", 4.5, 20, 5, 3,
       "A three-tube pod behind the left shoulder. Each tube holds a Shrike: a folding quadcopter with a shaped charge in its nose. Select it "
       "on the D-pad, LB launches one and you see through its camera. Left stick flies, right stick looks, A and B climb and sink, RT "
       "detonates, LB cuts the link. Fly it into anyone and it goes off. Your body stands where you left it.",
       [("connectivity", 3.0, "flying it takes a full neural uplink")],
       "Needs connectivity 3 (NL-3). Link range = connectivity × 40 m (120 m; 180 m with an MR-1 as well): the picture breaks up near the "
       "limit and the drone drops beyond it. Processing sharpens its turning. New drones are printed one every 30 s.",
       (0.75, 0.25, 0.6), (3.0, 0.0, 0.033, 2.0, 1.0), (120, 40),
       scene="res://assets/augments/sd3_shrike_drone/sd3_shrike_drone.gltf",
       vis=[("chest", BOX, (0.12, 0.2, 0.09), (0.13, 0.2, -0.16), "hardware"), ("chest", CYL, (0.03, 0.02, 0.03), (0.13, 0.31, -0.16), "glow")])
active("ad2_arc_projector", "AD-2 Arc Projector", "AD-2", BACK, "arc/arc_projector.gd", "arc/arc_projector_data.gd", 5.0, 15, 10, 3,
       "An electrolaser on a mast over the right shoulder. A UV laser ionizes a channel to whoever you're looking at and a capacitor bank "
       "dumps down it; the arc jumps on to the next body in reach, and the next. The gun stays in your hands. Select it on the D-pad; LB "
       "raises it and fires, LB again fires the second charge. Each discharge takes 18 kJ straight out of the power reserve.",
       [("power_supply_w", 600.0, "the capacitor bank won't charge off less than 600 W")],
       "Needs a 600 W supply (PC-3 power cell). Each arc costs 18 kJ of reserve: a 60 kJ reserve holds three. An FB-1 fuel bladder doubles "
       "the reserve and adds two links to the chain. Spare power refills its charges faster.",
       (0.4, 0.3, 0.3), (2.0, 0.0, 0.1, 1.5, 1.0), (0, 0),
       scene="res://assets/augments/ad2_arc_projector/ad2_arc_projector.gltf", view=vm((-0.42, -0.13, -0.26), (1.0, -0.13, -0.26)),
       vis=[("chest", BOX, (0.08, 0.05, 0.08), (-0.16, 0.3, -0.1), "hardware"), ("chest", CYL, (0.028, 0.14, 0.028), (-0.16, 0.37, -0.08), "plate", (90, 0, 0))])
active("kr5_ram_thrusters", "KR-5 Ram Thrusters", "KR-5", BACK, "ram/ram_thrusters.gd", "ram/ram_thrusters_data.gd", 7.0, 10, 0, 2,
       "Two cold-gas thrusters on the shoulder blades. One press throws you forward along your view at up to 27 m/s for a quarter of a "
       "second, through anyone in the way. Two burns stored. Select it on the D-pad, LB fires.",
       [("structure", 1.3, "the thrust goes through the spine")],
       "Needs structure ×1.30 (TL-3, TN-9). The hit is the slide hit × 1.8: mass × usable strength × impact, so a heavy plated body kills "
       "with it and a light one only shoves. Lighter bodies fly faster. Each burn costs 7 kJ of reserve and 4.5 kJ of heat.",
       (0.05, 0.12, 0.15), (2.0, 0.0, 0.22, 0.8, 1.0), (0, 0),
       vis=[("chest", CAPSULE, (0.045, 0.2, 0.045), (0.09, 0.14, -0.17), "hardware"), ("chest", CAPSULE, (0.045, 0.2, 0.045), (-0.09, 0.14, -0.17), "hardware"),
            ("chest", CYL, (0.04, 0.012, 0.04), (0.09, 0.03, -0.17), "glow"), ("chest", CYL, (0.04, 0.012, 0.04), (-0.09, 0.03, -0.17), "glow")])
active("tc4_thermoptic_shroud", "TC-4 Thermoptic Shroud", "TC-4", SKIN, "cloak/thermoptic_shroud.gd", "cloak/thermoptic_shroud_data.gd", 1.5, 20, 10, 3,
       "A skin of phased emitters that bends light round the body and holds its heat in. While it's up nobody sees you beyond three metres; "
       "they still hear you. Firing breaks it for a second and costs charge. Select it on the D-pad, LB raises or drops it.",
       [("heat_dissipation_w", 420.0, "it holds your heat in; without extra cooling it cooks you")],
       "Needs 420 W of cooling (HP-4 lungs or OC-2 blood; it takes the skin slot, so no HS-5 heat sinks). It traps 2.4 kW while it's up: a "
       "full ten seconds leaves the body at about three quarters heat (a hot signature afterwards); overheat and it fails. A low signature "
       "shortens the distance they see through it.",
       (0.5, 0.4, 0.8), (10.0, 1.0, 0.5, 2.0, 2.0), (180, 2400),
       vis=[("chest", CYL, (0.012, 0.004, 0.012), (0.09, 0.2, 0.125), "glow", (90, 0, 0)), ("chest", CYL, (0.012, 0.004, 0.012), (-0.09, 0.2, 0.125), "glow", (90, 0, 0)),
            ("upper_arm.L", CYL, (0.01, 0.004, 0.01), (0.05, 0.12, 0.0), "glow", (0, 0, 90)), ("upper_arm.R", CYL, (0.01, 0.004, 0.01), (-0.05, 0.12, 0.0), "glow", (0, 0, 90)),
            ("thigh.L", CYL, (0.01, 0.004, 0.01), (0.07, 0.2, 0.02), "glow", (0, 0, 90)), ("thigh.R", CYL, (0.01, 0.004, 0.01), (-0.07, 0.2, 0.02), "glow", (0, 0, 90))])


def body_scene(pid):
    """The part's hardware modelled on the operative, if it has been built."""
    rel = f"assets/augments/actives_body/{pid}/{pid}.gltf"
    return "res://" + rel if os.path.exists(os.path.join(ROOT, rel)) else None


def write_active(p):
    base = "res://src/augments/active/"
    ext = [f'[ext_resource type="Script" path="{base}{p["data_script"]}" id="1"]',
           '[ext_resource type="Script" path="res://src/body/stat_modifier.gd" id="2"]',
           '[ext_resource type="Script" path="res://src/body/part_visual.gd" id="3"]',
           f'[ext_resource type="Script" path="{base}{p["script"]}" id="4"]',
           '[ext_resource type="Script" path="res://src/body/stat_requirement.gd" id="5"]']
    subs, reqs, vis, tail = [], [], [], []
    if p["scene"]:
        ext.append(f'[ext_resource type="PackedScene" path="{p["scene"]}" id="6"]')
        tail.append('scene = ExtResource("6")')
    if p["view"]:
        ext.append('[ext_resource type="Script" path="res://src/player/viewmodel_config.gd" id="7"]')
        e, l = p["view"]["eye"], p["view"]["look"]
        subs.append(f'[sub_resource type="Resource" id="view"]\nscript = ExtResource("7")\neye_position = Vector3({f(e[0])}, {f(e[1])}, {f(e[2])})\n'
                    f'look_target = Vector3({f(l[0])}, {f(l[1])}, {f(l[2])})\n')
        tail.append('viewmodel = SubResource("view")')
    for i, (stat, least, why) in enumerate(p["reqs"]):
        subs.append(f'[sub_resource type="Resource" id="req_{i}"]\nscript = ExtResource("5")\nstat = &"{stat}"\nat_least = {f(least)}\nreason = "{esc(why)}"\n')
        reqs.append(f'SubResource("req_{i}")')
    modelled = body_scene(p["id"])
    if modelled:
        ext.append(f'[ext_resource type="PackedScene" path="{modelled}" id="8"]')
        subs.append('[sub_resource type="Resource" id="vis_0"]\nscript = ExtResource("3")\nsocket = &"root"\nscene = ExtResource("8")\nmodel_space = true\n')
        vis.append('SubResource("vis_0")')
    else:
        for i, v in enumerate(p["vis"]):
            sock, shape, size, off, finish = v[:5]
            rot = v[5] if len(v) > 5 else (0, 0, 0)
            subs.append(f'[sub_resource type="Resource" id="vis_{i}"]\nscript = ExtResource("3")\nsocket = &"{sock}"\nshape = {shape}\n'
                        f'size = Vector3({f(size[0])}, {f(size[1])}, {f(size[2])})\noffset = Vector3({f(off[0])}, {f(off[1])}, {f(off[2])})\n'
                        f'rotation_deg = Vector3({f(rot[0])}, {f(rot[1])}, {f(rot[2])})\nfinish = "{finish}"\n')
            vis.append(f'SubResource("vis_{i}")')
    cls = {"whip/whip_data.gd": "WhipData", "mesh_arm/mesh_arm_data.gd": "MeshArmData", "shield/fan_shield_data.gd": "FanShieldData",
           "drone/shrike_drone_data.gd": "ShrikeDroneData", "arc/arc_projector_data.gd": "ArcProjectorData",
           "ram/ram_thrusters_data.gd": "RamThrustersData", "cloak/thermoptic_shroud_data.gd": "ThermopticShroudData"}[p["data_script"]]
    out = [f'[gd_resource type="Resource" script_class="{cls}" load_steps={len(ext) + len(subs) + 1} format=3]', ""] + ext + [""] + subs
    dep, rec, cd = p["timing"]
    cmax, drain, regen, delay, least = p["charge"]
    out += ["[resource]", 'script = ExtResource("1")', f'id = &"{p["id"]}"', f'display_name = "{esc(p["name"])}"',
            f'description = "{esc(p["desc"])}"', f'location = {p["loc"]}']
    if p["mount"]:
        out.append(f'mount = &"{p["mount"]}"')
    out += [f'mass_kg = {f(p["mass"])}', f'power_draw_w = {f(p["power"])}', f'heat_w = {f(p["heat"])}', f'capacity = {p["cap"]}',
            'modifiers = Array[ExtResource("2")]([])', f'requirements = Array[ExtResource("5")]([{", ".join(reqs)}])',
            f'synergy = "{esc(p["synergy"])}"', f'visuals = Array[ExtResource("3")]([{", ".join(vis)}])',
            'behaviour = ExtResource("4")', f'short_name = "{p["short"]}"',
            f'deploy_time = {f(dep)}', f'recover_time = {f(rec)}', f'cooldown_time = {f(cd)}',
            f'charge_max = {f(cmax)}', f'drain_per_s = {f(drain)}', f'regen_per_s = {f(regen)}', f'regen_delay = {f(delay)}',
            f'min_to_start = {f(least)}', f'active_power_w = {f(p["load"][0])}', f'active_heat_w = {f(p["load"][1])}']
    out += tail + p["extra"] + [""]
    with open(os.path.join(ROOT, "data", "body", "parts", p["id"] + ".tres"), "w") as fh:
        fh.write("\n".join(out))


def main():
    for p in P:
        write_part(p)
    for p in A:
        write_active(p)
    locs = {p["id"]: p["loc"] for p in P}
    locs.update(ACTIVE_LOC)
    ordered = sorted(list(locs), key=lambda i: (ORDER.index(locs[i]), i in ACTIVES))
    write_list(os.path.join(ROOT, "data", "body", "part_library.tres"), "res://src/body/part_library.gd", "PartLibrary", [], ordered)
    for key, (name, desc, ids) in PRESETS.items():
        for pid in ids:
            assert pid in locs, pid
        write_list(os.path.join(ROOT, "data", "body", key + ".tres"), "res://src/body/body_loadout.gd", "BodyLoadout",
                   [f'display_name = "{esc(name)}"', f'description = "{esc(desc)}"'], ids)
    print(f"{len(P)} parts ({len(P) - 1} passives), library of {len(ordered)}, {len(PRESETS)} presets")


if __name__ == "__main__":
    main()
