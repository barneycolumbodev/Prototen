"""Owner likeness capture for the helmetless operative (owner, 2026-11-05: "I want the
operative to have my face").

Runs OUTSIDE Blender, in a venv with mediapipe and opencv (not part of the game):
    python3 -m venv /tmp/mpvenv && /tmp/mpvenv/bin/pip install mediapipe opencv-python-headless
    /tmp/mpvenv/bin/python capture.py --model face_landmarker.task --canon canonical_face_model.obj \
        --texture front.jpg --shape a.jpg b.jpg c.jpg --out raw_assets/characters/operative/likeness
Inputs (not committed; the owner's photos stay private):
  face_landmarker.task      MediaPipe Face Landmarker model (Apache-2.0)
  canonical_face_model.obj  MediaPipe canonical face mesh, 468 vertices with UVs (Apache-2.0)
  photos                    the owner's selfies
Outputs (committed, consumed by ../build.py):
  face_shape.npy   468 x 3 landmark positions in metres, Blender head frame (+X his left, -Y forward,
                   +Z up), origin between the eyes; Procrustes-aligned and averaged over --shape photos
  face_tris.npy    898 x 3 triangle indices (canonical topology)
  face_uv.npy      468 x 2 canonical UVs
  face_tex.png     the --texture photo unwrapped into canonical UV space (1024 px), shading flattened
                   (divided by a broad blur), RGBA, alpha = trust (fades out over the mesh's outer ring)
"""
import argparse
import os

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--canon", required=True)
ap.add_argument("--texture", required=True, help="main photo (front)")
ap.add_argument("--fix-right", action="store_true", help="re-tone his right half from the mirrored left")
ap.add_argument("--shape", nargs="+", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--size", type=int, default=1024)
ap.add_argument("--ipd", type=float, default=0.064, help="outer-canthus-based scale: eye-centre distance, metres")
args = ap.parse_args()

# ---------------------------------------------------------------- canonical mesh
C, VT, F = [], [], []
for line in open(args.canon):
    t = line.split()
    if not t:
        continue
    if t[0] == "v":
        C.append([float(x) for x in t[1:4]])
    elif t[0] == "vt":
        VT.append([float(x) for x in t[1:3]])
    elif t[0] == "f":
        F.append([tuple(int(i) - 1 for i in s.split("/")) for s in t[1:4]])
C = np.array(C)
UV = np.zeros((len(C), 2))
for f in F:
    for v, t in f:
        UV[v] = VT[t]
TRI = np.array([[v for v, _t in f] for f in F], dtype=np.int32)

det = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=mpt.BaseOptions(model_asset_path=args.model), num_faces=1))


def landmarks(path):
    img = mp.Image.create_from_file(path)
    r = det.detect(img)
    if not r.face_landmarks:
        raise SystemExit(f"no face in {path}")
    lm = np.array([[p.x, p.y, p.z] for p in r.face_landmarks[0]])[:468]
    w, h = img.width, img.height
    pix = lm[:, :2] * (w, h)
    Q = np.stack([lm[:, 0] * w, -lm[:, 1] * h, -lm[:, 2] * w], 1)   # canonical axes: x his left, y up, z out
    return pix, Q


def procrustes(Q, P):
    """Similarity transform taking Q onto P (rows are points)."""
    mq, mp_ = Q.mean(0), P.mean(0)
    q, p = Q - mq, P - mp_
    U, S, Vt = np.linalg.svd(q.T @ p)
    D = np.eye(3)
    D[2, 2] = np.sign(np.linalg.det(U @ Vt))
    R = (U @ D @ Vt).T
    s = (S * np.diag(D)).sum() / (q * q).sum()
    return lambda X: (s * (R @ (X - mq).T)).T + mp_


# ---------------------------------------------------------------- shape: average of the aligned photos
shapes = []
for p in args.shape:
    _pix, Q = landmarks(p)
    shapes.append(procrustes(Q, C)(Q))
    print(p, "residual (cm):", np.sqrt(((shapes[-1] - C) ** 2).sum(1)).mean().round(3))
S = np.median(np.stack(shapes), 0)
eye_l = S[[362, 263, 386, 374]].mean(0)
eye_r = S[[33, 133, 159, 145]].mean(0)
scale = args.ipd / np.linalg.norm(eye_l - eye_r)
mid = (eye_l + eye_r) / 2
S = (S - mid) * scale
shape = np.stack([S[:, 0], -S[:, 2], S[:, 1]], 1)   # -> Blender: +X left, -Y forward, +Z up
os.makedirs(args.out, exist_ok=True)
np.save(os.path.join(args.out, "face_shape.npy"), shape.astype(np.float32))
np.save(os.path.join(args.out, "face_tris.npy"), TRI)
np.save(os.path.join(args.out, "face_uv.npy"), UV.astype(np.float32))
print("face width (m):", np.ptp(shape[:, 0]).round(4), "height:", np.ptp(shape[:, 2]).round(4),
      "depth:", np.ptp(shape[:, 1]).round(4))

# ---------------------------------------------------------------- texture: piecewise-affine unwrap
N = args.size
dst_all = np.stack([UV[:, 0] * N, (1 - UV[:, 1]) * N], 1)


def unwrap(path):
    pix, _Q = landmarks(path)
    img = cv2.imread(path, cv2.IMREAD_COLOR).astype(np.float32) / 255.0
    tex = np.zeros((N, N, 3), np.float32)
    cov = np.zeros((N, N), np.float32)
    for tri in TRI:
        src = pix[tri].astype(np.float32)
        dst = dst_all[tri].astype(np.float32)
        x0, y0 = np.floor(dst.min(0)).astype(int)
        x1, y1 = np.ceil(dst.max(0)).astype(int) + 1
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, N), min(y1, N)
        if x1 <= x0 or y1 <= y0:
            continue
        M = cv2.getAffineTransform(dst.astype(np.float32), src)          # uv pixel -> photo pixel
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        sx = M[0, 0] * gx + M[0, 1] * gy + M[0, 2]
        sy = M[1, 0] * gx + M[1, 1] * gy + M[1, 2]
        mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
        cv2.fillConvexPoly(mask, np.round((dst - (x0, y0)) * 16).astype(np.int32), 1, shift=4)
        samp = cv2.remap(img, sx.astype(np.float32), sy.astype(np.float32), cv2.INTER_LINEAR)
        m = mask.astype(bool)
        tex[y0:y1, x0:x1][m] = samp[m]
        cov[y0:y1, x0:x1][m] = 1.0
    return tex, cov


def flatten(tex, cov):
    """Divide out broad shading (luminance only) and restore the mean tone."""
    lum = tex @ np.array([0.114, 0.587, 0.299], np.float32)    # BGR
    sig = N / 14
    wsum = cv2.GaussianBlur(cov, (0, 0), sig) + 1e-4
    broad = cv2.GaussianBlur(lum * cov, (0, 0), sig) / wsum
    mean = float((lum * cov).sum() / cov.sum())
    return np.clip(tex * (mean / np.maximum(broad, 0.05))[..., None], 0, 1)


def match(src, ref, mask):
    """Per-channel mean/std transfer in Lab, statistics taken inside `mask`."""
    a = cv2.cvtColor(src, cv2.COLOR_BGR2LAB)
    b = cv2.cvtColor(ref, cv2.COLOR_BGR2LAB)
    m = mask > 0.5
    for c in range(3):
        sa, sb = a[..., c][m], b[..., c][m]
        a[..., c] = (a[..., c] - sa.mean()) / (sa.std() + 1e-4) * sb.std() + sb.mean()
    return np.clip(cv2.cvtColor(a, cv2.COLOR_LAB2BGR), 0, 1)


tex, cov = unwrap(args.texture)
tex = flatten(tex, cov)
gx = (np.arange(N) + 0.5) / N
if args.fix_right:
    # The main photo's warm side light leaves his right half (u < 0.5) red and shadowed. Local colour
    # transfer onto the mirrored good half: keeps his own features and detail, takes tone and shading
    # from the other side. Far out (cheek edge) it fades to the mirrored half itself.
    lab = cv2.cvtColor(tex, cv2.COLOR_BGR2LAB)
    ref = lab[:, ::-1].copy()
    out = lab.copy()
    sig = N / 40
    for c in range(3):
        ms, mr = cv2.GaussianBlur(lab[..., c], (0, 0), sig), cv2.GaussianBlur(ref[..., c], (0, 0), sig)
        vs = cv2.GaussianBlur((lab[..., c] - ms) ** 2, (0, 0), sig)
        vr = cv2.GaussianBlur((ref[..., c] - mr) ** 2, (0, 0), sig)
        out[..., c] = (lab[..., c] - ms) / np.sqrt(vs + 1e-3) * np.sqrt(vr + 1e-3) + mr
    fixed = np.clip(cv2.cvtColor(out, cv2.COLOR_LAB2BGR), 0, 1)
    edge = np.clip((0.3 - gx) / 0.1, 0, 1)[None, :]
    fixed = fixed * (1 - edge[..., None]) + tex[:, ::-1] * edge[..., None]
    w = np.clip((0.5 - gx) / 0.05, 0, 1)[None, :] * np.ones((N, 1))
    w = cv2.GaussianBlur(w.astype(np.float32), (0, 0), 4)
    tex = tex * (1 - w[..., None]) + fixed * w[..., None]
flat = tex
# Fill outside the coverage by dilation so later bilinear lookups never pick up black.
out = flat.copy()
c = cov.copy()
for _ in range(24):
    blur = cv2.blur(out * c[..., None], (5, 5))
    cb = cv2.blur(c, (5, 5))
    grow = (c == 0) & (cb > 0)
    out[grow] = blur[grow] / cb[grow][:, None]
    c[grow] = 1
# Alpha: trust falls off over the outer ring of the mesh (ears, hairline and background smear there).
solid = (cov > 0).astype(np.uint8)
fill = solid.copy()
cv2.floodFill(fill, np.zeros((N + 2, N + 2), np.uint8), (0, 0), 2)
solid[fill == 0] = 1                     # eye and mouth holes count as covered (only the outer rim fades)
dist = cv2.distanceTransform(solid, cv2.DIST_L2, 5)
alpha = np.clip((dist - N * 0.03) / (N * 0.09), 0, 1)
rgba = np.dstack([out, alpha]) * 255
cv2.imwrite(os.path.join(args.out, "face_tex.png"), rgba.astype(np.uint8))
print("texture coverage:", cov.mean().round(3))
