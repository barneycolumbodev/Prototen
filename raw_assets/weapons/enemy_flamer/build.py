"""Triad Flamer weapons (third person): pressurized aerosol can + flip-top lighter.

Two separate glTFs exported to assets/weapons/enemy/:
- aerosol_can.gltf: held in the right hand on the weapon socket (same frame as
  raw_assets/weapons/enemy_guns and enemy_melee: +X forward toward the lighter,
  +Z up, +Y left, origin = top of the right-hand grip). Industrial red spray
  canister with a high-visibility yellow hazard band so the player can spot and
  shoot it as a weak point.
- lighter.gltf: held in the left hand (bone space of hand.L, matching
  raw_assets/characters/triad/common.py GRIP_L, pre-rotated +90 deg about X so
  it attaches directly to BoneAttachment3D("hand.L") with identity transform).
  Classic brushed-brass flip-top windproof lighter with open lid, perforated
  chimney, flint wheel, and a `wick` empty marking where the pilot flame sits.

Plain PBR factors (no textures), so GunFlatten collapses each into one draw call.

Run:
  tools/blender.sh raw_assets/weapons/enemy_flamer/build.py \
      --out assets/weapons/enemy \
      --preview docs/previews/enemy_flamer_kit.png
"""
import argparse
import math
import os
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "_lib"))
import hardsurface as hs  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="assets/weapons/enemy")
ap.add_argument("--preview", default="")
ap.add_argument("--samples", type=int, default=48)
args = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
hs.set_detail(hs.LOW)

# Materials (plain PBR factors -> GunFlatten merges to 1 surface / 1 draw call)
CAN_RED = hs.material("flamer_can_red", (0.78, 0.06, 0.04), 0.26, 0.30)
CAN_BAND = hs.material("flamer_can_yellow", (0.96, 0.70, 0.04), 0.30, 0.14)
CAN_BLACK = hs.material("flamer_can_black", (0.045, 0.045, 0.048), 0.42, 0.15)
TINPLATE = hs.material("flamer_tinplate", (0.76, 0.78, 0.80), 0.22, 0.96)
NOZZLE_WHITE = hs.material("flamer_nozzle_white", (0.88, 0.87, 0.84), 0.44, 0.0)
NOZZLE_TIP = hs.material("flamer_nozzle_red", (0.84, 0.08, 0.04), 0.38, 0.0)

BRASS = hs.material("flamer_brass", (0.80, 0.60, 0.22), 0.22, 0.96)
CHROME = hs.material("flamer_chrome", (0.78, 0.80, 0.82), 0.18, 0.98)
STEEL_DARK = hs.material("flamer_steel_dark", (0.14, 0.14, 0.15), 0.40, 0.85)
WICK_MAT = hs.material("flamer_wick", (0.30, 0.26, 0.20), 0.90, 0.0)


def _frame(origin, y_axis, z_hint):
    y = Vector(y_axis).normalized()
    x = y.cross(Vector(z_hint)).normalized()
    z = x.cross(y).normalized()
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


# Matches raw_assets/characters/triad/common.py GRIP_L (hand.L in gun space).
GRIP_L = _frame((0.248, 0.062, -0.012), (0.42, -0.9, 0.05), (0.0, 0.25, -1.0))

# Right hand holds the can high and slightly right so it clears the left forearm
# cleanly from the front, giving the player an unobstructed weak-point target!
CAN_TILT = math.radians(8.0)
CAN_CENTER = Vector((0.020, -0.026, 0.024))
CAN_XFORM = Matrix.Translation(CAN_CENTER) @ Matrix.Rotation(CAN_TILT, 4, "Y")

# Lighter sits upright flush in the left palm ~21 cm ahead of the aerosol nozzle.
LIGHTER_POS = Vector((0.265, -0.008, 0.020))


def tri(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def lathe_z(name, profile, verts=24, open_ends=False):
    """Surface of revolution around Z: profile = [(z, r), ...] from bottom to top."""
    bm = bmesh.new()
    rings = []
    for z, r in profile:
        if r <= 1e-6:
            rings.append([bm.verts.new((0.0, 0.0, z))])
        else:
            ring = [bm.verts.new((r * math.cos(2 * math.pi * k / verts),
                                  r * math.sin(2 * math.pi * k / verts), z))
                    for k in range(verts)]
            rings.append(ring)
    for a, b in zip(rings[:-1], rings[1:]):
        if len(a) == 1 and len(b) > 1:
            for k in range(verts):
                bm.faces.new([a[0], b[(k + 1) % verts], b[k]])
        elif len(b) == 1 and len(a) > 1:
            for k in range(verts):
                bm.faces.new([a[k], a[(k + 1) % verts], b[0]])
        elif len(a) > 1 and len(b) > 1:
            for k in range(verts):
                bm.faces.new([a[k], a[(k + 1) % verts], b[(k + 1) % verts], b[k]])
    if not open_ends:
        if len(rings[0]) > 1:
            bm.faces.new(list(reversed(rings[0])))
        if len(rings[-1]) > 1:
            bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return hs.mesh_object(name, bm)


def xform_obj(ob, mat):
    ob.data.transform(mat)
    return ob


def finish_cyl(ob, mat):
    """Clean radial shading: smooth sides, sharp caps/steps (no dark vertical normal bleed)."""
    hs.finish(ob, mat, bevel=0.0, angle=32.0, smooth=True)


def build_aerosol_can():
    """Tall industrial pressurized aerosol spray can (~24.5 cm tall, 7.4 cm wide)."""
    r = 0.037

    # Bottom rolled tinplate seam & recessed base
    finish_cyl(xform_obj(lathe_z("can_bot_rim", [
        (-0.094, r * 0.80),
        (-0.096, r * 0.95),
        (-0.093, r * 1.025),
        (-0.087, r * 1.025),
        (-0.085, r * 0.99),
    ], verts=24), CAN_XFORM), TINPLATE)

    # Lower red cylinder (open ends -> pure radial normals, zero cap bleed)
    finish_cyl(xform_obj(lathe_z("can_bot_red", [
        (-0.086, r),
        (-0.008, r),
    ], verts=24, open_ends=True), CAN_XFORM), CAN_RED)

    # Lower black border stripe
    finish_cyl(xform_obj(lathe_z("can_stripe_lo", [
        (-0.008, r * 1.004),
        (0.002, r * 1.004),
    ], verts=24, open_ends=True), CAN_XFORM), CAN_BLACK)

    # High-visibility yellow hazard band (crisp flat cylindrical strip)
    finish_cyl(xform_obj(lathe_z("can_band", [
        (0.002, r * 1.005),
        (0.058, r * 1.005),
    ], verts=24, open_ends=True), CAN_XFORM), CAN_BAND)

    # Thin red caution accent line bisecting the lower yellow band
    finish_cyl(xform_obj(lathe_z("can_band_accent", [
        (0.025, r * 1.008),
        (0.033, r * 1.008),
    ], verts=24, open_ends=True), CAN_XFORM), CAN_RED)

    # Upper black border stripe
    finish_cyl(xform_obj(lathe_z("can_stripe_hi", [
        (0.058, r * 1.004),
        (0.068, r * 1.004),
    ], verts=24, open_ends=True), CAN_XFORM), CAN_BLACK)

    # Upper red shoulder collar
    finish_cyl(xform_obj(lathe_z("can_top_red", [
        (0.068, r),
        (0.089, r),
    ], verts=24, open_ends=True), CAN_XFORM), CAN_RED)

    # Brushed tinplate top rolled rim + smooth dome + crimped valve mounting cup
    finish_cyl(xform_obj(lathe_z("can_dome", [
        (0.087, r * 0.99),
        (0.089, r * 1.032),
        (0.094, r * 1.032),
        (0.096, r * 0.96),
        (0.104, r * 0.84),
        (0.112, r * 0.68),
        (0.119, r * 0.50),
        (0.123, r * 0.43),
        (0.127, r * 0.46),
        (0.132, r * 0.43),
        (0.132, r * 0.24),
    ], verts=24), CAN_XFORM), TINPLATE)

    # Valve stem
    finish_cyl(xform_obj(lathe_z("valve_stem", [
        (0.128, 0.0055),
        (0.138, 0.0055),
    ], verts=12), CAN_XFORM), NOZZLE_WHITE)

    # White press-top spray actuator button
    cap = lathe_z("actuator_cap", [
        (0.134, 0.0135),
        (0.136, 0.0158),
        (0.153, 0.0154),
        (0.156, 0.0138),
        (0.156, 0.0),
    ], verts=18)
    finish_cyl(xform_obj(cap, CAN_XFORM), NOZZLE_WHITE)

    # Red directional spray nozzle insert facing straight forward (+X)
    tip = hs.cyl_x("nozzle_insert", 0.0058, 0.008, 0.0185, verts=14, z=0.146, fixed=True)
    finish_cyl(xform_obj(tip, CAN_XFORM), NOZZLE_TIP)
    orifice = hs.cyl_x("nozzle_hole", 0.0023, 0.0165, 0.0192, verts=10, z=0.146, fixed=True)
    finish_cyl(xform_obj(orifice, CAN_XFORM), CAN_BLACK)

    nozzle_gun = CAN_XFORM @ Vector((0.019, 0.0, 0.146))
    return hs.join_parts("aerosol_can"), nozzle_gun


def build_lighter():
    """Classic flip-top windproof brass lighter (Zippo-style), built at LIGHTER_POS.

    Oriented so the broad brass faces face ±Y (readable from the side) and the
    hinged lid flips open backward toward -X (or toward the user's thumb side +Y),
    leaving the perforated chimney and wick completely clear!
    """
    cx, cy, cz = LIGHTER_POS
    w_x = 0.044   # width along X (classic Zippo silhouette from the side!)
    w_y = 0.020   # thickness across Y
    h_body = 0.046

    # Lower brass case
    body = hs.box("lighter_body", (w_x, w_y, h_body), (cx, cy, cz))
    hs.finish(body, BRASS, bevel=0.0025, segments=1)

    # Recessed brass bottom trim
    base = hs.box("lighter_base", (w_x + 0.001, w_y + 0.001, 0.005), (cx, cy, cz - h_body * 0.5 + 0.0025))
    hs.finish(base, BRASS, bevel=0.001, segments=1)

    # Hinge barrel on the front-far edge (+X side, away from the aerosol nozzle so open lid doesn't block spray!)
    # Wait: put hinge on the +X edge so the open lid swings forward/down away from the incoming mist,
    # OR on the -X edge? On +X (far side) or side: actually on +X swung open ~125 deg tilts forward-right
    # cleanly below the flame line! Let's put hinge on +X at top of case, open 115 deg!
    hinge_x = cx + w_x * 0.5 + 0.001
    hinge_z = cz + h_body * 0.5
    hinge = hs.cyl_y("lighter_hinge", 0.0032, 0.012, (hinge_x, cy, hinge_z), verts=10)
    hs.finish(hinge, CHROME, bevel=0.0)

    # Hinged flip-top lid: built from hinge at origin extending toward -X (closed), then rotated +118 deg about Y
    # so it swings UP and OUT to the +X side (classic open Zippo silhouette!).
    lid_h = 0.022
    lid = hs.box("lighter_lid", (w_x, w_y, lid_h), (-w_x * 0.5, 0.0, lid_h * 0.5))
    lid_m = (Matrix.Translation((hinge_x, cy, hinge_z))
             @ Matrix.Rotation(math.radians(118.0), 4, "Y"))
    xform_obj(lid, lid_m)
    hs.finish(lid, BRASS, bevel=0.0022, segments=1)

    # Chrome inner insert plate
    insert = hs.box("lighter_insert", (w_x * 0.88, w_y * 0.84, 0.008), (cx, cy, cz + h_body * 0.5 + 0.003))
    hs.finish(insert, CHROME, bevel=0.0008, segments=1)

    # Windproof chimney hood on the -X side (facing the aerosol spray!)
    chim_x = cx - 0.007
    chim_z = cz + h_body * 0.5 + 0.015
    chim = hs.box("lighter_chimney", (0.019, w_y * 0.72, 0.021), (chim_x, cy, chim_z))
    hs.finish(chim, CHROME, bevel=0.001, segments=1)

    # Dark recessed interior & air vent slots on the chimney sides
    chim_in = hs.box("lighter_chimney_in", (0.014, w_y * 0.52, 0.018), (chim_x, cy, chim_z + 0.003))
    hs.finish(chim_in, STEEL_DARK, bevel=0.0, smooth=False)
    for dx in (-0.0045, 0.0, 0.0045):
        for dz in (-0.0035, 0.0035):
            vent = hs.cyl_y(f"vent_{dx}_{dz}", 0.0018, w_y * 0.76, (chim_x + dx, cy, chim_z + dz), verts=8)
            hs.finish(vent, STEEL_DARK, bevel=0.0)

    # Cam lever next to the hinge
    cam = hs.box("lighter_cam", (0.011, 0.006, 0.012), (cx + 0.011, cy, cz + h_body * 0.5 + 0.009))
    hs.finish(cam, CHROME, bevel=0.0008, segments=1)

    # Flint striker wheel between cam and chimney
    wheel = hs.cyl_y("lighter_wheel", 0.0065, 0.008, (cx + 0.008, cy, cz + h_body * 0.5 + 0.017), verts=14)
    hs.finish(wheel, STEEL_DARK, bevel=0.0)

    # Braided cotton wick poking out of the chimney center
    wick_z = chim_z + 0.011
    wick = hs.cyl_z("lighter_wick", 0.0022, 0.011, (chim_x, cy, wick_z - 0.002), verts=8)
    hs.finish(wick, WICK_MAT, bevel=0.0)

    wick_pos_gun = Vector((chim_x, cy, wick_z + 0.005))
    return hs.join_parts("lighter"), wick_pos_gun


os.makedirs(args.out, exist_ok=True)

can_ob, nozzle_gun = build_aerosol_can()
lighter_ob, wick_gun = build_lighter()

print(f"aerosol_can: {tri(can_ob)} tris, nozzle_gun=({nozzle_gun.x:.4f}, {nozzle_gun.y:.4f}, {nozzle_gun.z:.4f})")
print(f"lighter: {tri(lighter_ob)} tris, wick_gun=({wick_gun.x:.4f}, {wick_gun.y:.4f}, {wick_gun.z:.4f})")

if args.preview:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    world = bpy.data.worlds.new("w")
    world.color = (0.36, 0.38, 0.42)
    scene.world = world

    # Small glowing pilot flame preview cone above the wick (removed before export)
    flame_mat = hs.material("preview_flame", (1.0, 0.55, 0.1), 1.0, 0.0, emission=((1.0, 0.62, 0.15), 14.0))
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.007, radius2=0.0, depth=0.032,
                                    location=(wick_gun.x, wick_gun.y, wick_gun.z + 0.014))
    preview_flame = bpy.context.active_object
    preview_flame.data.materials.append(flame_mat)

    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    target = Vector((0.14, 0.0, 0.065))
    cam.location = Vector((0.16, -0.72, 0.19))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 52
    scene.camera = cam

    key = bpy.data.objects.new("key", bpy.data.lights.new("key", "SUN"))
    key.data.energy = 3.8
    key.rotation_euler = (math.radians(48), math.radians(-18), math.radians(32))
    scene.collection.objects.link(key)

    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "POINT"))
    fill.data.energy = 14.0
    fill.location = Vector((-0.25, -0.45, 0.25))
    scene.collection.objects.link(fill)

    os.makedirs(os.path.dirname(os.path.abspath(args.preview)), exist_ok=True)
    scene.render.filepath = args.preview
    bpy.ops.render.render(write_still=True)
    print("preview:", args.preview)

    bpy.data.objects.remove(preview_flame, do_unlink=True)

# Export aerosol_can.gltf in gun space (just like enemy_guns & enemy_melee)
bpy.ops.object.select_all(action="DESELECT")
can_ob.select_set(True)
bpy.context.view_layer.objects.active = can_ob
bpy.ops.export_scene.gltf(
    filepath=os.path.join(args.out, "aerosol_can.gltf"),
    export_format="GLTF_SEPARATE",
    use_selection=True,
    export_apply=True,
)

# Transform lighter into hand.L bone space (+90 deg X so glTF export lands in Godot BoneAttachment3D space)
TO_HAND_L_GLTF = Matrix.Rotation(math.pi / 2.0, 4, "X") @ GRIP_L.inverted()
lighter_ob.data.transform(TO_HAND_L_GLTF)
wick_bone = GRIP_L.inverted() @ wick_gun
print(f"wick in hand.L bone space (Godot): ({wick_bone.x:.4f}, {wick_bone.y:.4f}, {wick_bone.z:.4f})")

wick_empty = bpy.data.objects.new("wick", None)
bpy.context.scene.collection.objects.link(wick_empty)
wick_empty.matrix_world = TO_HAND_L_GLTF @ Matrix.Translation(wick_gun)
wick_empty.parent = lighter_ob

bpy.ops.object.select_all(action="DESELECT")
lighter_ob.select_set(True)
wick_empty.select_set(True)
bpy.context.view_layer.objects.active = lighter_ob
bpy.ops.export_scene.gltf(
    filepath=os.path.join(args.out, "lighter.gltf"),
    export_format="GLTF_SEPARATE",
    use_selection=True,
    export_apply=True,
)
