#!/usr/bin/env python3
"""CPU pose refinement between perception (perc2) and the reference builder (mkref): ground-truth-free (2026-10-29).

Reads ONE episode's perception directory and writes a refined perception directory with the same files and keys, so
that pipeline/mkref.py (and pipeline/score_registered.py on public episodes) consume it unchanged:
  poses.npz           world_T_cam   copied byte-identically from the input (hands depend on it and need no rerun);
                      cam_T_<name>  float32 (T,4,4) for the roster objects only (the input's cam_T_ keys, same order).
                                    No other key starts with cam_T_ (identity_fix.py:53 and tools/manip_segments.py:16
                                    take the object names from that prefix). A frame no step changed keeps its input
                                    bytes; a changed frame is inv(world_T_cam[t]) @ O(t), O = refined world pose.
  poses_world_vo.npz  <name> -> world_T_cam @ cam_T_<name> (float64), input bytes on unchanged frames.
  pose_opt.json       what each step did, per object, plus the labels, plane, inputs (sha256), code version, checks.
  pose_opt_aux.npz    per-frame diagnostics (labels, hand distances, change magnitudes). Never read by mkref.
  vo.json             copied; the depth file is symlinked (pipeline_ep.sh resolves it with readlink -f).

Inputs (inference only; nothing derived from mocap): poses.npz, poses_world_vo.npz (optional), vo.json (optional),
the hands file (hands_refined.npz, else hands.npz: joints_<side> in the same world frame, measured_<side>), frame-0
depth (depth0.npy, or frame 0 of depths_fs0.5.npy), our mesh library (default meshes/library_v3; the mesh frame of the
tracking templates), optional collision pieces (make_assets.py --pieces layout, for COM and hulls), the rectified K
(KR in the hands file, or the calibration json), and for S0 the ego_cam_c video. Object names and slot order are the
cam_T_ keys of poses.npz (the kit roster on eval). assert_inference_input() refuses any path that contains
'observation', '.parquet', 'score_registered', 'per_frame', 'quarantine_gt', a 'baseline' directory, or is named
result.json / summary.json / log.txt (on public episodes perc2 writes mocap AUCs into those, perc2.py:502-542).

Table plane: mkref's own fit_table() with mkref's defaults (ring 10-90 px, 6 mm, 1000 iterations, support_tol 3 cm,
mkref.py:797-804) on the input frame-0 poses and our meshes (loaded as make_assets.py does), so refine and mkref see the
same plane (mkref refits it on the refined frame 0; pose_opt.json reports that refit as checks.mkref_refit). --table
overrides it with a mkref table_frame.npz (plane_n, plane_d) or 'nx,ny,nz,d' (world frame, n toward the camera).

Shared labels, from our own track (after S0) and our hands only, never ground truth:
  moving[t]     centroid speed >= 0.5 cm/frame (3-frame mean position) or turn >= 2 deg/frame (3-frame mean), plus a
                3-frame closing: object_events.py thresholds, as in map_semantic §2 (recall 0.966 / precision 0.817 of
                mocap motion on the public sweep tracks, measured there).
  first_move    first frame of the first run of >= 3 moving frames (T if none).
  rest segments runs of >= 5 non-moving frames.
  liftoff       object_events.hold_events rule: centroid > 1.5 cm above its frame-0 height (along the plane normal)
                for 3 consecutive frames.
  hand_cm[t]    nearest MEASURED hand joint to the object surface (600 samples) at the tracked pose; inf when no hand
                is measured. hand_held_cm[t]: the same against the frame-0 pose (where S4 holds the object).
  support       at frame 0: bottom h = min over mesh vertices of n.x + d (mkref's bottoms()). For another object k
                with a bottom at least 2 mm lower: on_other = >= 20 % of the object's low surface samples (within 5 mm
                of its lowest) lie within 1 cm of k's surface (lid on pot, cup on a rack grid); over_other = its centre
                of mass projects inside k's footprint (convex hull of k's vertices projected on the plane: cup in a
                rack or pot, pot in a rack). table_supported = plane ok and |h| <= snap_max (2 cm) and
                h - min_k h_k <= 0.5 cm and not on_other and not over_other.

Steps (each switchable with --steps; always applied in the order S0, S1, S3, S4, S5, S2):
  S0 identity fix hook: pipeline/identity_fix.py (board knob darkness) on a copy, when the roster is the board pair
     and the video, calibration and both board meshes exist; otherwise skipped and logged. Its output is the input of
     every later step and of the labels.
  S1 support-gated snap (R1): a table_supported object's whole trajectory moves by -h along the plane normal (as
     mkref's per-object snap, but gated). Objects over or on another object, or more than 0.5 cm above the lowest
     bottom, are left alone. Later rest segments (>= 10 frames, after first_move, hand-free on >= 50 % of the frames,
     |h| <= snap_max, not on/over another object at the segment's middle frame, bottom within 0.5 cm of the lowest
     object there) get their median bottom put on the plane; the offset ramps in and out over 10 frames (linear
     between two segments closer than 20 frames), so the carry is otherwise unchanged.
     WHEN S1 IS ON THE REFERENCE MUST BE BUILT WITH mkref --snap none: mkref's default per_object snap would re-snap
     the objects S1 deliberately left alone (the R1 defect). pose_opt.json carries "mkref_args": "--snap none".
  S3 tilt-to-plane anchor (R2) [H]: for a table_supported object with a static prefix [0, first_move) of >= 5 frames,
     the prefix's mean orientation (chordal L2 mean, frames > 3 deg off dropped) is turned by the minimal swing (no
     twist about the plane normal: yaw kept) that puts the nearest stable resting up of our mesh (convex hull face
     clusters within 2 deg that contain the projected COM with 2 mm margin, area >= 1 cm2; COM as make_assets.py)
     onto the plane normal; skipped when that tilt exceeds 10 deg. ONE rigid body-frame correction C is applied to
     every frame, prefix and moving part: R'(t) = R(t) C about the COM, then one constant translation along the
     normal that keeps the frame-0 bottom height (S1's snap survives). Why body frame over the whole track: the
     tilt is a register() bias at frame 0 that FoundationPose's track_one carries forward (it refines from the
     previous pose), so it is a constant offset of the object's body frame; correcting the body frame keeps every
     tracked increment and cannot introduce a jump at motion onset, while a world-frame correction faded out after
     onset would inject a rotation the object never made during the lift. The R2 oracle that measured +0.023
     perception / +0.029 refs (refcheck verify_systematics/v7_tilt_anchor.py) used the same whole-track body-frame
     form. --s3_carry fade keeps the world-frame correction on the prefix and fades it out over --s3_fade frames
     after first_move instead (alternative for an A/B).
  S4 pre-contact drift hold (R5) [H]: an object with no measured hand within 5 cm at frame 0 is held at its frame-0
     pose (after S1/S3) until the first of: its own motion onset (first_move: >= 3 moving frames), its lift-off, or
     a measured hand within 5 cm (of the tracked or the held pose). It is released as soon as the object moves even
     if no hand is seen (ep2 lid: MediaPipe missed the grasp). At release the body-frame offset between the held
     pose and the track decays linearly to zero over 10 frames (SE(3) screw interpolation), so there is no jump.
     Frame 0 is never changed by S4. Opt-in variants [H], all off by default (= the rule above): --s4_owner 1 (a hand
     counts only when this object is its nearest roster object; on public ep24 a hand handling board 1 comes within
     5 cm of board 2's frame-0 pose at frame 30), --s4_lift_moving 1 (lift-off needs a moving frame; ep24 board 2's
     track creeps 1.5 cm upward by frame 40 with no motion label), --s4_deadband CM,DEG (own motion releases only
     once the track has left the held pose by more than CM or DEG, as the hand-gated lock of map_semantic §2).
  S5 rest smoothing (off by default): each rest segment of >= 10 frames is held at one robust constant pose (median
     COM position, trimmed mean rotation); the segment containing frame 0 is held at the frame-0 pose (frame 0 kept);
     the offset ramps out over 5 frames on both sides.
  S2 constant time advance (R6): O'(t) = O(t + 0.545) by SE(3) screw interpolation between neighbouring frames
     (bi-invariant, so independent of the mesh-frame origin; --s2_interp decoupled = linear position + slerp as in
     refcheck systematics/fixed_shift.py); T frames kept; the last frame is held. --s2_hold_f0 1 keeps frame 0.
     Hands are not shifted [H: the lag is tracker latency, not a sync offset; untested].

Usage:
  python pipeline/refine.py --in PERC_DIR --out OUT_DIR [--steps S1,S2,S3,S4] [--hands H.npz] [--depth D.npy]
      [--meshes meshes/library_v3] [--table table_frame.npz | --table nx,ny,nz,d] [--video ep_c.mp4 --calib calib.json]
Then (S1 on): mkref.py ... --poses OUT_DIR/poses.npz --depth $(readlink -f OUT_DIR/depths_fs0.5.npy) ... --snap none
Public scoring: score_registered.py EP OUT_DIR/poses_world_vo.npz --meshes meshes/library_v3 ...
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STEP_ORDER = ['S0', 'S1', 'S3', 'S4', 'S5', 'S2']
DEFAULT_STEPS = 'S0,S1,S2,S3,S4'
FORBIDDEN_SUBSTR = ('observation', '.parquet', 'score_registered', 'per_frame', 'quarantine_gt')
FORBIDDEN_BASENAMES = ('result.json', 'summary.json', 'log.txt')
BOARDS = ['wooden_piece_1', 'wooden_piece_2']
T0 = time.time()
LOG = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    LOG.append(s)
    print(f'[refine {time.time() - T0:6.1f}s] {s}', flush=True)


# ======================================================================== integrity
def assert_inference_input(path):
    """Refuse anything that is, or may hold, ground truth (raises AssertionError; not stripped by python -O)."""
    if path is None:
        return
    for p in {str(path), os.path.realpath(str(path))}:
        low = p.lower()
        bad = [s for s in FORBIDDEN_SUBSTR if s in low]
        if os.path.basename(low) in FORBIDDEN_BASENAMES:
            bad.append(os.path.basename(low))
        if 'baseline' in low.replace('\\', '/').split('/'):
            bad.append('baseline/')
        if bad:
            raise AssertionError(f'refine is inference: refusing input {path!r} (resolves to {p!r}; matches {bad}). '
                                 f'Ground truth (mocap poses, scores, per-frame errors, dataset parquets) is read only '
                                 f'by the scorer, after refine has written its outputs.')


def checked(path):
    assert_inference_input(path)
    return path


def sha256(path, cap=None):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        n = 0
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
            n += len(b)
            if cap and n >= cap:
                return h.hexdigest() + f'(first {cap} B)'
    return h.hexdigest()


def code_version():
    """Commit read from .git files (no git command is run) plus this file's sha256."""
    out = dict(refine_sha256=sha256(os.path.abspath(__file__)))
    try:
        g = os.path.join(REPO, '.git')
        if os.path.isfile(g):                                    # worktree: "gitdir: ..."
            g = open(g).read().split(':', 1)[1].strip()
        head = open(os.path.join(g, 'HEAD')).read().strip()
        if head.startswith('ref:'):
            ref = head.split(None, 1)[1]
            out['branch'] = ref
            rp = os.path.join(g, ref)
            if os.path.exists(rp):
                out['commit'] = open(rp).read().strip()
            else:
                for line in open(os.path.join(g, 'packed-refs')):
                    if line.strip().endswith(ref):
                        out['commit'] = line.split()[0]
        else:
            out['commit'] = head
    except Exception as e:  # noqa: BLE001
        out['commit_error'] = str(e)
    return out


# ======================================================================== SE(3) helpers
def hat(w):
    return np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0.0]])


def rot_from_rotvec(w):
    from scipy.spatial.transform import Rotation
    return Rotation.from_rotvec(w).as_matrix()


def rotvec_from_rot(R):
    from scipy.spatial.transform import Rotation
    return Rotation.from_matrix(R).as_rotvec()


def inv_rigid(T):
    Ti = np.eye(4)
    Ti[:3, :3] = T[:3, :3].T
    Ti[:3, 3] = -T[:3, :3].T @ T[:3, 3]
    return Ti


def se3_log(T):
    w = rotvec_from_rot(T[:3, :3])
    th = float(np.linalg.norm(w))
    W = hat(w)
    if th < 1e-8:
        Vi = np.eye(3) - 0.5 * W + W @ W / 12.0
    else:
        Vi = np.eye(3) - 0.5 * W + (1.0 / th ** 2) * (1 - th * np.sin(th) / (2 * (1 - np.cos(th)))) * (W @ W)
    return w, Vi @ T[:3, 3]


def se3_exp(w, v):
    th = float(np.linalg.norm(w))
    W = hat(w)
    if th < 1e-8:
        R = np.eye(3) + W + W @ W / 2.0
        V = np.eye(3) + W / 2.0 + W @ W / 6.0
    else:
        R = rot_from_rotvec(w)
        V = np.eye(3) + (1 - np.cos(th)) / th ** 2 * W + (th - np.sin(th)) / th ** 3 * (W @ W)
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = V @ v
    return T


def se3_pow(T, s):
    """T^s by screw interpolation (s in [0, 1])."""
    if s == 1.0:
        return T.copy()
    if s == 0.0:
        return np.eye(4)
    w, v = se3_log(T)
    return se3_exp(s * w, s * v)


def interp_pose(A, B, alpha, mode='se3'):
    """Pose between A (alpha 0) and B (alpha 1)."""
    if alpha <= 0 or np.array_equal(A, B):
        return A.copy()
    if alpha >= 1:
        return B.copy()
    if mode == 'se3':
        return A @ se3_pow(inv_rigid(A) @ B, alpha)
    from scipy.spatial.transform import Rotation, Slerp
    out = np.eye(4)
    out[:3, :3] = Slerp([0.0, 1.0], Rotation.from_matrix(np.stack([A[:3, :3], B[:3, :3]])))([alpha]).as_matrix()[0]
    out[:3, 3] = (1 - alpha) * A[:3, 3] + alpha * B[:3, 3]
    return out


def swing(u, v):
    """Minimal rotation matrix taking unit vector u onto unit vector v."""
    u = u / np.linalg.norm(u)
    v = v / np.linalg.norm(v)
    ax = np.cross(u, v)
    s = np.linalg.norm(ax)
    c = float(np.clip(u @ v, -1, 1))
    if s < 1e-12:
        return np.eye(3)
    return rot_from_rotvec(ax / s * np.arctan2(s, c))


def ang_deg(R):
    return float(np.degrees(np.linalg.norm(rotvec_from_rot(R))))


def mean_rotation(Rs, trim_deg=3.0):
    """Chordal L2 mean; members more than TRIM_DEG from the first mean are dropped and the mean recomputed."""
    from scipy.spatial.transform import Rotation
    R = Rotation.from_matrix(Rs)
    m = R.mean()
    d = np.degrees((R * m.inv()).magnitude())
    keep = d <= max(trim_deg, 1e-9)
    if keep.sum() >= max(2, len(Rs) // 2) and not keep.all():
        m = R[keep].mean()
    return m.as_matrix(), int(keep.sum())


# ======================================================================== labels
def runs(mask):
    """[(start, end_exclusive)] of True runs."""
    m = np.r_[False, np.asarray(mask, bool), False].astype(np.int8)
    d = np.diff(m)
    return list(zip(np.nonzero(d == 1)[0].tolist(), np.nonzero(d == -1)[0].tolist()))


def moving_labels(O, com, still_cm=0.5, still_deg=2.0):
    from scipy.ndimage import binary_closing, uniform_filter1d
    from scipy.spatial.transform import Rotation
    T = len(O)
    if T < 2:
        return np.zeros(T, bool)
    c = O[:, :3, :3] @ com + O[:, :3, 3]
    Ps = uniform_filter1d(c, 3, axis=0)
    v = np.r_[0.0, np.linalg.norm(np.diff(Ps, axis=0), axis=1) * 100]
    Q = Rotation.from_matrix(O[:, :3, :3])
    w = uniform_filter1d(np.r_[0.0, np.degrees((Q[1:] * Q[:-1].inv()).magnitude())], 3)
    m = (v >= still_cm) | (w >= still_deg)
    return binary_closing(m, np.ones(3, bool)) | m


def liftoff_frame(O, com, n, lift_cm=1.5):
    c = O[:, :3, :3] @ com + O[:, :3, 3]
    zr = (c @ n - c[0] @ n) * 100
    T = len(O)
    for t in range(T - 2):
        if (zr[t:t + 3] > lift_cm).all():
            return t
    return None


def hand_distances(O, S, J, M):
    """(T,) cm: nearest measured hand joint to the surface samples S (body frame) posed by O (T,4,4) or one 4x4."""
    T = len(next(iter(J.values()))) if J else 0
    out = np.full(T, np.inf)
    for t in range(T):
        Ot = O if O.ndim == 2 else O[t]
        X = S @ Ot[:3, :3].T + Ot[:3, 3]
        for s in J:
            if M[s][t]:
                d = np.linalg.norm(J[s][t][:, None, :] - X[None], axis=2).min() * 100
                out[t] = min(out[t], d)
    return out


# ======================================================================== object geometry
class Obj:
    def __init__(self, name, path, pieces_dir=None):
        import trimesh
        m = trimesh.load(checked(path), force='mesh')
        self.mesh = trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)   # as make_assets.py
        self.name, self.path = name, path
        self.V = np.asarray(self.mesh.vertices, float)
        self.com, self.com_src = self._com(pieces_dir)
        self.S = np.asarray(trimesh.sample.sample_surface(self.mesh, 600, seed=0)[0], float)       # hand distance
        self.D = np.asarray(trimesh.sample.sample_surface(self.mesh, 4000, seed=1)[0], float)      # support tests
        self._ups = None
        self.hull_V = None
        if pieces_dir and os.path.isdir(os.path.join(pieces_dir, name)):
            import glob
            pcs = sorted(glob.glob(os.path.join(pieces_dir, name, 'piece_*.obj')))
            if pcs:
                self.hull_V = np.concatenate([np.asarray(trimesh.load(checked(p), force='mesh').vertices) for p in pcs])

    def _com(self, pieces_dir):
        import trimesh
        if pieces_dir:
            js = os.path.join(pieces_dir, self.name, 'inertia.json')
            if os.path.exists(js):
                return np.array(json.load(open(checked(js)))['com'], float), 'pieces inertia.json'
        f = getattr(trimesh.sample, 'sample_surface_even', None)
        pts = f(self.mesh, 20000, seed=0)[0] if f else trimesh.sample.sample_surface(self.mesh, 20000, seed=0)[0]
        return np.asarray(pts, float).mean(0), 'surface estimate (make_assets.py)'

    def stable_ups(self, cluster_deg=2.0, margin=0.002, min_area=1e-4):
        """Body-frame 'up' vectors of stable rests on a plane: clusters of convex-hull faces whose normals agree within
        CLUSTER_DEG, whose support polygon contains the COM projection with MARGIN, area >= MIN_AREA (m2)."""
        if self._ups is not None:
            return self._ups
        import trimesh
        from scipy.spatial import ConvexHull
        hull = (trimesh.Trimesh(self.hull_V).convex_hull if self.hull_V is not None else self.mesh.convex_hull)
        N = np.asarray(hull.face_normals)
        A = np.asarray(hull.area_faces)
        F = np.asarray(hull.faces)
        HV = np.asarray(hull.vertices)
        order = np.argsort(-A)
        free = np.ones(len(F), bool)
        cos_c = np.cos(np.radians(cluster_deg))
        ups = []
        for i in order:
            if not free[i]:
                continue
            g = free & (N @ N[i] >= cos_c)
            free &= ~g
            area = float(A[g].sum())
            if area < min_area:
                continue
            nf = (N[g] * A[g, None]).sum(0)
            nf /= np.linalg.norm(nf)
            Vf = HV[np.unique(F[g])]
            e1 = np.cross(nf, [1.0, 0, 0] if abs(nf[0]) < 0.9 else [0, 1.0, 0])
            e1 /= np.linalg.norm(e1)
            e2 = np.cross(nf, e1)
            S2 = np.c_[Vf @ e1, Vf @ e2]
            c2 = np.array([self.com @ e1, self.com @ e2])
            try:
                ch = ConvexHull(S2)
            except Exception:  # noqa: BLE001
                continue
            mg = float(np.min(-(ch.equations[:, :2] @ c2 + ch.equations[:, 2])))
            if mg >= margin:
                ups.append(dict(up=-nf, margin_mm=round(mg * 1000, 2), area_cm2=round(area * 1e4, 2)))
        self._ups = ups
        return ups

    def world(self, Ot, X=None):
        X = self.V if X is None else X
        return X @ Ot[:3, :3].T + Ot[:3, 3]


def support_relation(objs, Os, n, d, low_band=0.005, near=0.01, frac=0.2, above=0.002):
    """Per object j at one frame (Os: list of 4x4 world poses): bottom height h_j (m, min over mesh vertices of n.x + d,
    as mkref's bottoms()) and whether it rests on / over another object k. Both need j to be the upper one
    (h_j > h_k + ABOVE: a pot is not 'over' the lid resting on it).
      on   share of j's low surface samples (within LOW_BAND of its lowest sample) within NEAR of k's surface (>= FRAC)
      over j's centre of mass projects (along n) inside the convex hull of k's projected footprint (margin in cm)."""
    from scipy.spatial import ConvexHull, cKDTree
    B = len(objs)
    W = [o.world(Os[j]) for j, o in enumerate(objs)]
    h = np.array([float((Wj @ n).min() + d) for Wj in W])
    e1 = np.cross(n, [1.0, 0, 0] if abs(n[0]) < 0.9 else [0, 1.0, 0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    Dw = [o.world(Os[j], o.D) for j, o in enumerate(objs)]
    rel = []
    for j in range(B):
        hd = Dw[j] @ n + d
        low = Dw[j][hd < hd.min() + low_band]
        cw = Os[j][:3, :3] @ objs[j].com + Os[j][:3, 3]
        c2 = np.array([cw @ e1, cw @ e2])
        on, over = {}, {}
        for k in range(B):
            if k == j:
                continue
            upper = bool(h[j] > h[k] + above)
            on[objs[k].name] = float((cKDTree(Dw[k]).query(low, k=1)[0] < near).mean()) if upper else 0.0
            mg = None
            try:
                ch = ConvexHull(np.c_[W[k] @ e1, W[k] @ e2])
                mg = float(np.min(-(ch.equations[:, :2] @ c2 + ch.equations[:, 2])))
            except Exception:  # noqa: BLE001
                pass
            over[objs[k].name] = dict(upper=upper, com_in_footprint_margin_cm=None if mg is None else round(mg * 100, 2),
                                      over=bool(upper and mg is not None and mg >= 0))
        rel.append(dict(h=float(h[j]), on=on, over=over,
                        on_other=any(v >= frac for v in on.values()), over_other=any(v['over'] for v in over.values())))
    return h, rel


# ======================================================================== table plane
def fit_plane(a, depth0, KR, W0, camT0, objs):
    sys.path.insert(0, HERE)
    import mkref
    ns = argparse.Namespace(ring_in=a.ring_in, ring_out=a.ring_out, plane_thr=a.plane_thr, plane_iters=a.plane_iters,
                            support_tol=a.support_tol)
    n, d, frac, npts, rms = mkref.fit_table(depth0, KR, W0, camT0, {o.name: o.mesh for o in objs}, ns)
    return np.asarray(n, float), float(d), dict(source='mkref.fit_table on frame-0 depth', inlier_frac=round(float(frac), 4),
                                               ring_points=int(npts), rms_mm=round(float(rms) * 1000, 2),
                                               candidates=ns._plane_cands)


def plane_from_arg(s, W0):
    if os.path.exists(s):
        tf = np.load(checked(s))
        n, d = np.asarray(tf['plane_n'], float), float(tf['plane_d'])
        src = f'--table {s}'
    else:
        v = [float(x) for x in s.split(',')]
        n, d = np.array(v[:3]), v[3]
        nn = np.linalg.norm(n)
        n, d = n / nn, d / nn
        src = f'--table {s}'
    if n @ W0[:3, 3] + d < 0:
        n, d = -n, -d
    return n, d, dict(source=src)


# ======================================================================== steps
def step_S0(a, names, W_C, camT, out_dir):
    rec = dict(applied=False)
    script = os.path.join(HERE, 'identity_fix.py')
    if sorted(names) != BOARDS:
        rec['skipped'] = 'not the board pair'
        return camT, rec
    miss = []
    if not os.path.exists(script):
        miss.append('pipeline/identity_fix.py')
    if not a.video or not os.path.exists(a.video):
        miss.append(f'video ({a.video or "no --video"})')
    if not a.calib or not os.path.exists(a.calib):
        miss.append(f'calibration ({a.calib or "no --calib"})')
    meshes = [os.path.join(a.meshes, f'{n}.glb') for n in BOARDS]
    miss += [m for m in meshes if not os.path.exists(m)]
    try:
        import cv2  # noqa: F401
    except ImportError:
        miss.append('cv2')
    if miss:
        rec['skipped'] = 'cannot run on available inputs: missing ' + ', '.join(miss)
        log('S0 skipped:', rec['skipped'])
        return camT, rec
    for p in (a.video, a.calib, *meshes):
        assert_inference_input(p)
    wd = os.path.join(out_dir, 's0_identity_fix')
    os.makedirs(wd, exist_ok=True)
    np.savez(os.path.join(wd, 'poses.npz'), world_T_cam=W_C, **{f'cam_T_{n}': camT[n] for n in names})
    np.savez(os.path.join(wd, 'poses_world_vo.npz'), **{n: W_C @ camT[n].astype(np.float64) for n in names})
    cmd = [sys.executable, script, a.video, a.calib, wd, *meshes] + (['--frames', a.s0_frames] if a.s0_frames else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    rec.update(cmd=' '.join(cmd), returncode=r.returncode, stdout=r.stdout[-2000:], stderr=r.stderr[-2000:])
    if r.returncode != 0:
        rec['skipped'] = 'identity_fix.py failed; input kept'
        log('S0 identity_fix FAILED (input kept):', r.stderr[-300:])
        return camT, rec
    js = os.path.join(wd, 'identity_fix.json')
    if os.path.exists(js):
        rec['identity_fix'] = json.load(open(js))
    P = np.load(os.path.join(wd, 'poses.npz'))
    new = {n: P[f'cam_T_{n}'] for n in names}
    rec['applied'] = bool(rec.get('identity_fix', {}).get('applied', False))
    log('S0 identity_fix:', json.dumps(rec.get('identity_fix', {}))[:300])
    return new, rec


def step_S1(a, objs, O, lab, n, d, plane_ok):
    rec = {}
    B = len(objs)
    for j, o in enumerate(objs):
        L = lab[j]
        r = dict(h0_cm=round(L['h0'] * 100, 3), table_supported=L['table_supported'], reason=L['support_reason'])
        if L['table_supported']:
            O[j][:, :3, 3] -= L['h0'] * n
            r['f0_shift_cm'] = round(-L['h0'] * 100, 3)
        else:
            r['f0_shift_cm'] = 0.0
        rec[o.name] = r
    if not a.s1_rest or not plane_ok:
        return rec
    T = len(O[0])
    for j, o in enumerate(objs):
        L = lab[j]
        segs = [(s, e) for s, e in L['rest_segments'] if s >= L['first_move'] and e - s >= a.s1_rest_min]
        anchors, srec = [], []
        for s, e in segs:
            mid = (s + e) // 2
            h, rel = support_relation(objs, [O[k][mid] for k in range(B)], n, d)
            hs = np.array([float((o.world(O[j][t]) @ n).min() + d) for t in range(s, e)])
            hmed = float(np.median(hs))
            free = float(np.mean(~(L['hand_cm'][s:e] < a.hand_cm)))
            why = []
            if abs(hmed) > a.snap_max:
                why.append(f'|h| {hmed * 100:.2f} cm > snap_max')
            if hmed - h.min() > a.lowest_tol:
                why.append(f'{(hmed - h.min()) * 100:.2f} cm above the lowest object')
            if rel[j]['on_other'] or rel[j]['over_other']:
                why.append('on/over another object')
            if free < a.s1_rest_hand_free:
                why.append(f'hand-free {free:.2f} < {a.s1_rest_hand_free}')
            ok = not why
            srec.append(dict(frames=[s, e], h_med_cm=round(hmed * 100, 3), hand_free=round(free, 2), snapped=ok,
                             shift_cm=round(-hmed * 100, 3) if ok else 0.0, reason='; '.join(why) or 'table-supported'))
            if ok:
                anchors.append((s, e, -hmed))
        if not anchors:
            rec[o.name]['rest_segments'] = srec
            continue
        off = np.zeros(T)
        bl = a.s1_blend
        for i, (s, e, v) in enumerate(anchors):
            off[s:e] = v
        # transitions: ramp from/to 0 over BL frames, or linear between two anchors closer than 2*BL
        for i, (s, e, v) in enumerate(anchors):
            prev = anchors[i - 1] if i > 0 else None
            if prev is not None and s - prev[1] <= 2 * bl:
                g0, g1 = prev[1], s
                for t in range(g0, g1):
                    off[t] = prev[2] + (v - prev[2]) * (t - g0 + 1) / (g1 - g0 + 1)
            else:
                for t in range(max(0, s - bl), s):
                    off[t] = v * (t - (s - bl) + 1) / (bl + 1)
            nxt = anchors[i + 1] if i + 1 < len(anchors) else None
            if nxt is None or nxt[0] - e > 2 * bl:
                for t in range(e, min(T, e + bl)):
                    off[t] = v * (1 - (t - e + 1) / (bl + 1))
        O[j][:, :3, 3] += off[:, None] * n[None]
        rec[o.name]['rest_segments'] = srec
        rec[o.name]['rest_offset_max_cm'] = round(float(np.abs(off).max() * 100), 3)
    return rec


def step_S3(a, objs, O, lab, n, d):
    rec = {}
    T = len(O[0])
    for j, o in enumerate(objs):
        L = lab[j]
        r = {}
        rec[o.name] = r
        p_end = int(L['first_move'])
        if not L['table_supported']:
            r['skipped'] = 'not table-supported: ' + L['support_reason']
            continue
        if p_end < a.s3_min_prefix:
            r['skipped'] = f'static prefix {p_end} frames < {a.s3_min_prefix}'
            continue
        Rm, kept = mean_rotation(O[j][:p_end, :3, :3])
        u_now = Rm.T @ n                                          # plane normal in the body frame (prefix mean)
        ups = o.stable_ups()
        if not ups:
            r['skipped'] = 'no stable resting face on our mesh hull'
            continue
        angs = [float(np.degrees(np.arccos(np.clip(u['up'] @ u_now, -1, 1)))) for u in ups]
        k = int(np.argmin(angs))
        r.update(prefix=[0, p_end], prefix_frames_used=kept, tilt_deg=round(angs[k], 3), stable_up_body=np.round(ups[k]['up'], 5).tolist(),
                 stable_margin_mm=ups[k]['margin_mm'], stable_area_cm2=ups[k]['area_cm2'], n_stable_rests=len(ups))
        if angs[k] > a.s3_max_tilt:
            r['skipped'] = f'nearest stable rest {angs[k]:.2f} deg > {a.s3_max_tilt}'
            continue
        C = swing(ups[k]['up'], u_now)                            # body frame: R C up = n  (R = prefix mean)
        S_w = Rm @ C @ Rm.T                                       # the same as a world swing about an axis _|_ n
        r['world_swing_axis_dot_n'] = round(float(abs(rotvec_from_rot(S_w) @ n) / max(np.linalg.norm(rotvec_from_rot(S_w)), 1e-12)), 6)
        c = o.com
        h_before = float((o.world(O[j][0]) @ n).min() + d)
        new = O[j].copy()
        if a.s3_carry == 'body':
            new[:, :3, :3] = O[j][:, :3, :3] @ C
            new[:, :3, 3] = O[j][:, :3, 3] + O[j][:, :3, :3] @ c - new[:, :3, :3] @ c
            frames = T
        else:                                                     # fade: world-frame swing about the COM, faded after
            fade = a.s3_fade
            for t in range(T):
                s = 1.0 if t < p_end else max(0.0, 1 - (t - p_end + 1) / (fade + 1))
                if s <= 0:
                    break
                Sw = se3_pow(np.block([[S_w, np.zeros((3, 1))], [np.zeros((1, 3)), np.ones((1, 1))]]), s)[:3, :3]
                cw = O[j][t, :3, :3] @ c + O[j][t, :3, 3]
                new[t, :3, :3] = Sw @ O[j][t, :3, :3]
                new[t, :3, 3] = cw - new[t, :3, :3] @ c
            frames = int(min(T, p_end + a.s3_fade))
        h_after = float((o.world(new[0]) @ n).min() + d)
        dz = h_before - h_after
        new[:frames, :3, 3] += dz * n
        O[j] = new
        r.update(applied=True, carry=a.s3_carry, frames_changed=frames, height_keep_shift_mm=round(dz * 1000, 3),
                 f0_bottom_cm=round(h_before * 100, 3))
    return rec


def body_blend(Ot, Otarget_rel, s):
    """Ot @ Otarget_rel^s (body-frame correction scaled by s in [0, 1])."""
    return Ot @ se3_pow(Otarget_rel, s)


def step_S4(a, objs, O, lab, have_hands, n):
    rec = {}
    T = len(O[0])
    for j, o in enumerate(objs):
        L = lab[j]
        r = {}
        rec[o.name] = r
        if not have_hands:
            r['skipped'] = 'no hands file'
            continue
        h0 = float(L['hand_cm'][0])
        if h0 < a.hand_cm:
            r['skipped'] = f'touched at frame 0 (hand {h0:.1f} cm)'
            continue
        held = O[j][0].copy()
        if a.s4_owner and len(objs) > 1:                          # variant: the hand must be nearest to THIS object
            near = np.zeros(T, bool)
            for s in L['_J']:
                Js, Ms = {s: L['_J'][s]}, {s: L['_M'][s]}
                dj = np.minimum(hand_distances(O[j], o.S, Js, Ms), hand_distances(held, o.S, Js, Ms))
                dk = np.min([hand_distances(O[k], objs[k].S, Js, Ms) for k in range(len(objs)) if k != j], axis=0)
                near |= (dj < a.hand_cm) & (dj <= dk)
        else:
            hh = hand_distances(held, o.S, L['_J'], L['_M'])
            near = np.minimum(L['hand_cm'], hh) < a.hand_cm
        t_hand = int(np.argmax(near)) if near.any() else T
        t_move = int(L['first_move'])
        if a.s4_deadband:                                         # variant: own motion counts only past a deadband
            dcm, ddeg = (float(x) for x in a.s4_deadband.split(','))
            c0 = held[:3, :3] @ o.com + held[:3, 3]
            dev = np.linalg.norm(O[j][:, :3, :3] @ o.com + O[j][:, :3, 3] - c0, axis=1) * 100
            turn = np.array([ang_deg(O[j][t, :3, :3] @ held[:3, :3].T) for t in range(T)])
            past = (dev > dcm) | (turn > ddeg)
            t_move = max(t_move, int(np.argmax(past)) if past.any() else T)
        t_lift = int(L['liftoff']) if L['liftoff'] is not None else T
        if a.s4_lift_moving and t_lift < T:                       # variant: a lift-off needs the object to be moving
            mv = L['moving']
            ok = [t for t in range(t_lift, T) if mv[t] and (O[j][t, :3, :3] @ o.com + O[j][t, :3, 3]) @ n
                  - (O[j][0, :3, :3] @ o.com + O[j][0, :3, 3]) @ n > 0.015]
            t_lift = ok[0] if ok else T
        t_r, reason = min([(t_move, 'own motion'), (t_lift, 'lift-off'), (t_hand, f'hand within {a.hand_cm:.0f} cm')],
                          key=lambda x: x[0])
        if t_r >= T:
            t_r, reason = T, 'never released'
        if t_r <= 1:
            r.update(skipped=f'released at frame {t_r} ({reason})')
            continue
        Ot = O[j]
        drift = np.array([np.linalg.norm((Ot[t, :3, :3] @ o.com + Ot[t, :3, 3]) - (held[:3, :3] @ o.com + held[:3, 3])) * 100
                          for t in range(t_r)])
        turn = np.array([ang_deg(Ot[t, :3, :3] @ held[:3, :3].T) for t in range(t_r)])
        new = Ot.copy()
        new[1:t_r] = held
        blend = 0
        if t_r < T:
            rel = inv_rigid(Ot[t_r]) @ held                       # body-frame offset at release
            bl = a.s4_blend
            for t in range(t_r, min(T, t_r + bl)):
                s = 1 - (t - t_r) / bl
                new[t] = body_blend(Ot[t], rel, s)
                blend += 1
        O[j] = new
        r.update(applied=True, hold=[1, t_r], released_at=t_r if t_r < T else None, reason=reason,
                 variants=dict(owner=bool(a.s4_owner), lift_moving=bool(a.s4_lift_moving), deadband=a.s4_deadband),
                 first_hand_near=t_hand if t_hand < T else None, first_move=t_move if t_move < T else None,
                 liftoff=t_lift if t_lift < T else None, blend_frames=blend,
                 drift_suppressed_max_cm=round(float(drift.max()), 3), drift_at_release_cm=round(float(drift[-1]), 3),
                 turn_suppressed_max_deg=round(float(turn.max()), 3))
    return rec


def step_S5(a, objs, O, lab):
    rec = {}
    T = len(O[0])
    for j, o in enumerate(objs):
        L = lab[j]
        segs = [(s, e) for s, e in L['rest_segments'] if e - s >= a.s5_min]
        Ot = O[j]
        new = Ot.copy()
        srec = []
        bl = a.s5_blend
        for i, (s, e) in enumerate(segs):
            if s == 0:
                C = Ot[0].copy()
                kept = e
            else:
                Rm, kept = mean_rotation(Ot[s:e, :3, :3])
                cm = np.median(Ot[s:e, :3, :3] @ o.com + Ot[s:e, :3, 3], axis=0)
                C = np.eye(4)
                C[:3, :3] = Rm
                C[:3, 3] = cm - Rm @ o.com
            dev = [np.linalg.norm((Ot[t, :3, :3] @ o.com + Ot[t, :3, 3]) - (C[:3, :3] @ o.com + C[:3, 3])) * 100 for t in range(s, e)]
            new[s:e] = C
            m_in = (segs[i - 1][1] + s) // 2 if i > 0 else 0      # gaps are split at their middle frame
            m_out = (e + segs[i + 1][0]) // 2 if i + 1 < len(segs) else T
            if s > 0:                                              # ramp in (before the segment)
                rel = inv_rigid(Ot[s]) @ C
                a0 = max(m_in, s - bl)
                for t in range(a0, s):
                    new[t] = body_blend(Ot[t], rel, (t - a0 + 1) / (s - a0 + 1))
            if e < T:                                              # ramp out (after the segment)
                rel = inv_rigid(Ot[e - 1]) @ C
                b1 = min(m_out, e + bl)
                for t in range(e, b1):
                    new[t] = body_blend(Ot[t], rel, 1 - (t - e + 1) / (b1 - e + 1))
            srec.append(dict(frames=[s, e], frames_used=kept, max_dev_cm=round(float(np.max(dev)), 3)))
        O[j] = new
        rec[o.name] = dict(segments=srec)
    return rec


def step_S2(a, O):
    T = len(O[0])
    L = a.s2_advance
    out = []
    for Ot in O:
        new = Ot.copy()
        for t in range(T):
            if t == 0 and a.s2_hold_f0:
                continue
            tq = min(t + L, T - 1)
            i = int(np.floor(tq))
            al = tq - i
            new[t] = Ot[i].copy() if (i >= T - 1 or al == 0) else interp_pose(Ot[i], Ot[i + 1], al, a.s2_interp)
        out.append(new)
    return out, dict(advance_frames=L, interp=a.s2_interp, hold_f0=bool(a.s2_hold_f0), last_frame='held')


# ======================================================================== main
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--in', dest='inp', required=True, help='perception dir (poses.npz, poses_world_vo.npz, vo.json, ...)')
    p.add_argument('--out', required=True, help='refined perception dir (new; never the input dir)')
    p.add_argument('--steps', default=DEFAULT_STEPS, help=f'comma list of S0..S5 (default {DEFAULT_STEPS}; applied in '
                                                           f'the order {",".join(STEP_ORDER)}); "none" = copy only')
    p.add_argument('--hands', default=None, help='default IN/hands_refined.npz, else IN/hands.npz')
    p.add_argument('--depth', default=None, help='frame-0 depth: default IN/depth0.npy, else frame 0 of IN/depths_fs0.5.npy')
    p.add_argument('--meshes', default=os.path.join(REPO, 'meshes', 'library_v3'), help='our mesh library (tracking frame)')
    p.add_argument('--pieces', default=None, help='collision pieces DIR/<obj>/piece_*.obj (+inertia.json), make_assets layout')
    p.add_argument('--calib', default=None, help='camera calibration json (KR when the hands file has none; S0)')
    p.add_argument('--table', default=None, help='table plane: mkref table_frame.npz or "nx,ny,nz,d"; default: fit')
    p.add_argument('--video', default=None, help='S0: ego_cam_c video of the episode')
    p.add_argument('--s0_frames', default=None, help='S0: identity_fix --frames (default its own 0,2,4,6)')
    p.add_argument('--force', action='store_true', help='write into an existing OUT')
    # mkref table-fit defaults (mkref.py:797-804)
    p.add_argument('--ring_in', type=int, default=10)
    p.add_argument('--ring_out', type=int, default=90)
    p.add_argument('--plane_thr', type=float, default=0.006)
    p.add_argument('--plane_iters', type=int, default=1000)
    p.add_argument('--support_tol', type=float, default=0.03)
    p.add_argument('--support_max', type=float, default=0.05)
    # labels
    p.add_argument('--still_cm', type=float, default=0.5)
    p.add_argument('--still_deg', type=float, default=2.0)
    p.add_argument('--move_run', type=int, default=3)
    p.add_argument('--rest_min', type=int, default=5)
    p.add_argument('--hand_cm', type=float, default=5.0)
    # S1
    p.add_argument('--snap_max', type=float, default=0.02)
    p.add_argument('--lowest_tol', type=float, default=0.005)
    p.add_argument('--s1_rest', type=int, default=1, help='1: also snap later table-supported rest segments')
    p.add_argument('--s1_rest_min', type=int, default=10)
    p.add_argument('--s1_rest_hand_free', type=float, default=0.5)
    p.add_argument('--s1_blend', type=int, default=10)
    # S3
    p.add_argument('--s3_min_prefix', type=int, default=5)
    p.add_argument('--s3_max_tilt', type=float, default=10.0)
    p.add_argument('--s3_carry', choices=['body', 'fade'], default='body')
    p.add_argument('--s3_fade', type=int, default=10)
    # S4
    p.add_argument('--s4_blend', type=int, default=10)
    p.add_argument('--s4_owner', type=int, default=0, help='[H] variant: a hand releases the hold only when this object '
                   'is its nearest roster object (default 0 = any hand within --hand_cm)')
    p.add_argument('--s4_lift_moving', type=int, default=0, help='[H] variant: lift-off counts only on a moving frame '
                   '(vertical creep alone does not release; default 0 = object_events rule)')
    p.add_argument('--s4_deadband', default=None, help='[H] variant "CM,DEG": own motion releases only once the track '
                   'has left the held pose by more than CM or DEG (default off)')
    # S5
    p.add_argument('--s5_min', type=int, default=10)
    p.add_argument('--s5_blend', type=int, default=5)
    # S2
    p.add_argument('--s2_advance', type=float, default=0.545)
    p.add_argument('--s2_interp', choices=['se3', 'decoupled'], default='se3')
    p.add_argument('--s2_hold_f0', type=int, default=0)
    a = p.parse_args(argv)
    st = [s.strip().upper() for s in a.steps.split(',') if s.strip() and s.strip().lower() != 'none']
    bad = [s for s in st if s not in STEP_ORDER]
    if bad:
        p.error(f'unknown steps {bad}')
    a.step_set = set(st)
    return a


def main(argv=None):
    a = parse_args(argv)
    inp = os.path.abspath(a.inp)
    out = os.path.abspath(a.out)
    for pth in (inp, a.hands, a.depth, a.meshes, a.pieces, a.calib, a.video,
                a.table if a.table and os.path.exists(a.table) else None):
        assert_inference_input(pth)                               # before anything is created
    if os.path.realpath(inp) == os.path.realpath(out):
        raise SystemExit('refine: --out must differ from --in (existing runs are preserved)')
    if os.path.exists(os.path.join(out, 'poses.npz')) and not a.force:
        raise SystemExit(f'refine: {out}/poses.npz exists (use --force or a new --out)')
    os.makedirs(out, exist_ok=True)
    rec = dict(tool='pipeline/refine.py', argv=sys.argv if argv is None else ['refine.py'] + list(argv),
               time_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), code=code_version(),
               steps_requested=sorted(a.step_set, key=STEP_ORDER.index),
               steps_order=[s for s in STEP_ORDER if s in a.step_set], params={k: v for k, v in vars(a).items() if k != 'step_set'})

    # ---------------- inputs
    pp = checked(os.path.join(inp, 'poses.npz'))
    P = np.load(pp)
    W_C = P['world_T_cam']
    names = [k[6:] for k in P.files if k.startswith('cam_T_')]
    camT_in = {n: P[f'cam_T_{n}'] for n in names}
    T = len(W_C)
    for n in names:
        if len(camT_in[n]) != T:
            raise SystemExit(f'cam_T_{n} has {len(camT_in[n])} frames, world_T_cam {T}')
    inputs = {'poses.npz': pp}
    vop = os.path.join(inp, 'poses_world_vo.npz')
    VO_in = None
    if os.path.exists(vop):
        VO_in = {n: np.load(checked(vop))[n] for n in names}
        inputs['poses_world_vo.npz'] = vop
    voj = os.path.join(inp, 'vo.json')
    vo_info = None
    if os.path.exists(voj):
        J_ = json.load(open(checked(voj)))
        vo_info = dict(keyframes=len(J_.get('keyframes', [])), fails=J_.get('fails'))
        inputs['vo.json'] = voj
    hp = a.hands or next((q for q in (os.path.join(inp, 'hands_refined.npz'), os.path.join(inp, 'hands.npz'))
                          if os.path.exists(q)), None)
    H = np.load(checked(hp)) if hp and os.path.exists(hp) else None
    if H is not None:
        inputs['hands'] = hp
    dp = a.depth or next((q for q in (os.path.join(inp, 'depth0.npy'), os.path.join(inp, 'depths_fs0.5.npy'))
                          if os.path.exists(q)), None)
    if dp:
        inputs['depth'] = checked(dp)
    for n in names:
        inputs[f'mesh {n}'] = checked(os.path.join(a.meshes, f'{n}.glb'))
    if 'hfds' in os.path.realpath(a.meshes) or os.path.join('track_3', 'public', 'mesh') in os.path.realpath(a.meshes):
        log('WARNING: --meshes points at the public scans; refine should use our own meshes (eval has no scans)')
    rec['inputs'] = {k: dict(path=v, sha256=sha256(v, cap=None if os.path.getsize(v) < 50e6 else 8 << 20)) for k, v in inputs.items()}
    rec.update(T=T, names=names, vo=vo_info)
    log(f'{inp}: T={T}, objects {names}, steps {rec["steps_order"]}, hands {"yes" if H is not None else "NO"}')

    # ---------------- S0 (changes the input of everything after it)
    if 'S0' in a.step_set:
        camT_in, rec_s0 = step_S0(a, names, W_C, camT_in, out)
        rec.setdefault('steps', {})['S0'] = rec_s0
        if rec_s0.get('applied'):
            VO_in = None                                          # identities changed: rebuild the world file
    objs = [Obj(n, os.path.join(a.meshes, f'{n}.glb'), a.pieces) for n in names]
    O_in = [np.einsum('tij,tjk->tik', W_C.astype(np.float64), camT_in[n].astype(np.float64)) for n in names]
    O = [x.copy() for x in O_in]

    # ---------------- plane
    need_plane = bool(a.step_set & {'S1', 'S3', 'S4'})
    n_ = d_ = None
    plane_ok = False
    KR = None
    if H is not None and 'KR' in H.files:
        KR = np.asarray(H['KR'], float)
    elif a.calib:
        sys.path.insert(0, HERE)
        import mkref
        KR = mkref.rectified_K(checked(a.calib))
    depth0 = None
    if dp:
        depth0 = np.load(dp, mmap_mode='r')
        depth0 = np.asarray(depth0[0] if depth0.ndim == 3 else depth0, np.float32)
    if a.table:
        n_, d_, prec = plane_from_arg(a.table, W_C[0])
    elif need_plane and depth0 is not None and KR is not None:
        try:
            n_, d_, prec = fit_plane(a, depth0, KR, W_C[0], {n: camT_in[n][0].astype(np.float64) for n in names}, objs)
        except BaseException as e:  # noqa: BLE001  (mkref.fit_table raises SystemExit when the ring is too small)
            prec = dict(source=None, note=f'mkref.fit_table failed: {e}')
    else:
        prec = dict(source=None, note='no plane: ' + ('not needed' if not need_plane else 'missing depth or KR'))
    if n_ is not None:
        h0 = np.array([float((o.world(O[j][0]) @ n_).min() + d_) for j, o in enumerate(objs)])
        plane_ok = bool(-a.support_tol <= h0.min() <= a.support_max)
        prec.update(n=np.round(n_, 6).tolist(), d=round(d_, 6), ok=plane_ok,
                    f0_bottoms_cm={o.name: round(h0[j] * 100, 3) for j, o in enumerate(objs)},
                    camera_height_m=round(float(n_ @ W_C[0][:3, 3] + d_), 4))
        if not plane_ok:
            prec['note'] = (f'lowest frame-0 bottom {h0.min() * 100:.1f} cm outside [{-a.support_tol * 100:.0f}, '
                            f'{a.support_max * 100:.0f}] cm: no support plane, S1/S3 skip (mkref would use its fallback)')
    rec['plane'] = prec
    log('plane:', json.dumps({k: v for k, v in prec.items() if k != 'candidates'}))

    # ---------------- shared labels (our track after S0, our hands)
    Jh = Mh = None
    if H is not None:
        Jh = {s: H[f'joints_{s}'].astype(np.float64) for s in ('left', 'right') if f'joints_{s}' in H.files}
        Mh = {s: (H[f'measured_{s}'] if f'measured_{s}' in H.files else H[f'valid_{s}']).astype(bool) for s in Jh}
        for s in Jh:
            if len(Jh[s]) != T:
                raise SystemExit(f'hands joints_{s} has {len(Jh[s])} frames, poses {T}')
    lab = []
    rel0 = None
    if n_ is not None:
        _, rel0 = support_relation(objs, [O[j][0] for j in range(len(objs))], n_, d_)
    for j, o in enumerate(objs):
        mv = moving_labels(O[j], o.com, a.still_cm, a.still_deg)
        mr = [(s, e) for s, e in runs(mv) if e - s >= a.move_run]
        first_move = mr[0][0] if mr else T
        rest = [(s, e) for s, e in runs(~mv) if e - s >= a.rest_min]
        hand = hand_distances(O[j], o.S, Jh, Mh) if Jh else np.full(T, np.inf)
        L = dict(moving=mv, first_move=int(first_move), rest_segments=rest, hand_cm=hand, _J=Jh, _M=Mh,
                 liftoff=liftoff_frame(O[j], o.com, n_) if n_ is not None else None,
                 h0=None, table_supported=False, support_reason='no plane')
        if n_ is not None:
            r0 = rel0[j]
            L['h0'] = r0['h']
            hmin = min(x['h'] for x in rel0)
            why = []
            if not plane_ok:
                why.append('no support plane')
            if abs(r0['h']) > a.snap_max:
                why.append(f'|h| {r0["h"] * 100:.2f} cm > snap_max {a.snap_max * 100:.1f}')
            if r0['h'] - hmin > a.lowest_tol:
                why.append(f'{(r0["h"] - hmin) * 100:.2f} cm above the lowest object bottom')
            if r0['on_other']:
                why.append(f'on another object {r0["on"]}')
            if r0['over_other']:
                why.append(f'over another object {r0["over"]}')
            L['table_supported'] = not why
            L['support_reason'] = '; '.join(why) or 'on the table'
            L['support_f0'] = r0
        lab.append(L)
        hn = np.nonzero(hand < a.hand_cm)[0]
        log(f'labels {o.name}: first_move {first_move}, liftoff {L["liftoff"]}, first hand<{a.hand_cm:.0f}cm '
            f'{int(hn[0]) if len(hn) else None}, rest segs {rest}, h0 {None if L["h0"] is None else round(L["h0"] * 100, 2)} cm, '
            f'support: {L["support_reason"]}')
    rec['labels'] = {o.name: dict(first_move=L['first_move'], liftoff=L['liftoff'], rest_segments=L['rest_segments'],
                                  moving_frames=int(L['moving'].sum()),
                                  first_hand_near=(int(np.argmax(L['hand_cm'] < a.hand_cm)) if (L['hand_cm'] < a.hand_cm).any() else None),
                                  hand_f0_cm=(None if not np.isfinite(L['hand_cm'][0]) else round(float(L['hand_cm'][0]), 2)),
                                  h0_cm=None if L['h0'] is None else round(L['h0'] * 100, 3),
                                  table_supported=L['table_supported'], support_reason=L['support_reason'],
                                  support_f0=L.get('support_f0'), com_body=np.round(objs[j].com, 5).tolist(),
                                  com_source=objs[j].com_src)
                     for j, (o, L) in enumerate(zip(objs, lab))}

    # ---------------- steps in the fixed order
    steps = rec.setdefault('steps', {})
    snap = [O[j].copy() for j in range(len(O))]
    deltas = {}

    def note_delta(step):
        dc = {}
        for j, o in enumerate(objs):
            c0 = snap[j][:, :3, :3] @ o.com + snap[j][:, :3, 3]
            c1 = O[j][:, :3, :3] @ o.com + O[j][:, :3, 3]
            dp_ = np.linalg.norm(c1 - c0, axis=1) * 100
            dr = np.array([ang_deg(O[j][t, :3, :3] @ snap[j][t, :3, :3].T) for t in range(T)])
            deltas[f'{step}_{o.name}_cm'] = dp_
            deltas[f'{step}_{o.name}_deg'] = dr
            nch = int(sum(not np.array_equal(O[j][t], snap[j][t]) for t in range(T)))
            dc[o.name] = dict(frames_changed=nch, max_cm=round(float(dp_.max()), 3),
                              max_deg=round(float(dr.max()), 3), f0_cm=round(float(dp_[0]), 4), f0_deg=round(float(dr[0]), 4))
            snap[j] = O[j].copy()
        steps[step]['delta'] = dc

    for step in STEP_ORDER:
        if step not in a.step_set or step == 'S0':
            continue
        if step == 'S1':
            if n_ is None:
                steps['S1'] = dict(skipped='no table plane')
            else:
                steps['S1'] = step_S1(a, objs, O, lab, n_, d_, plane_ok)
        elif step == 'S3':
            steps['S3'] = dict(skipped='no table plane') if n_ is None else step_S3(a, objs, O, lab, n_, d_)
        elif step == 'S4':
            steps['S4'] = step_S4(a, objs, O, lab, Jh is not None, n_)
        elif step == 'S5':
            steps['S5'] = step_S5(a, objs, O, lab)
        elif step == 'S2':
            O, steps['S2'] = step_S2(a, O)
        note_delta(step)
        log(f'{step}:', json.dumps({k: v for k, v in steps[step].items() if k != 'delta'}, default=str)[:600])
    if 'S1' in a.step_set:
        rec['mkref_args'] = '--snap none'
        log('S1 is on: build the reference with mkref --snap none (mkref would otherwise re-snap the gated objects)')

    # ---------------- write
    camT_out, vo_out, changed = {}, {}, {}
    for j, n in enumerate(names):
        ch = np.array([not np.array_equal(O[j][t], O_in[j][t]) for t in range(T)])
        Ct = camT_in[n].copy()
        Vw = (VO_in[n].copy() if VO_in is not None else np.einsum('tij,tjk->tik', W_C.astype(np.float64), camT_in[n].astype(np.float64)))
        for t in np.nonzero(ch)[0]:
            M = O[j][t].copy()
            U, _, Vt = np.linalg.svd(M[:3, :3])
            M[:3, :3] = U @ np.diag([1, 1, np.linalg.det(U @ Vt)]) @ Vt
            Ct[t] = (inv_rigid(W_C[t].astype(np.float64)) @ M).astype(camT_in[n].dtype)
            Vw[t] = W_C[t].astype(np.float64) @ Ct[t].astype(np.float64)
        camT_out[n], vo_out[n], changed[n] = Ct, Vw, ch
    np.savez(os.path.join(out, 'poses.npz'), world_T_cam=W_C, **{f'cam_T_{n}': camT_out[n] for n in names})
    np.savez(os.path.join(out, 'poses_world_vo.npz'), **{n: vo_out[n] for n in names})
    if 'vo.json' in inputs:
        shutil.copyfile(inputs['vo.json'], os.path.join(out, 'vo.json'))
    if dp:
        link = os.path.join(out, os.path.basename(dp))
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(os.path.realpath(dp), link)

    # ---------------- checks
    Q = np.load(os.path.join(out, 'poses.npz'))
    chk = dict(world_T_cam_byte_identical=bool(Q['world_T_cam'].tobytes() == W_C.tobytes() and Q['world_T_cam'].dtype == W_C.dtype),
               keys=list(Q.files), keys_ok=Q.files == ['world_T_cam'] + [f'cam_T_{n}' for n in names],
               frames_ok=all(len(Q[f'cam_T_{n}']) == T for n in names),
               finite=all(bool(np.isfinite(Q[f'cam_T_{n}']).all()) for n in names),
               frame0_byte_identical={n: bool(camT_out[n][0].tobytes() == camT_in[n][0].tobytes()) for n in names},
               frames_changed={n: int(changed[n].sum()) for n in names})
    if n_ is not None and depth0 is not None and KR is not None and not a.table:
        try:
            n2, d2, p2 = fit_plane(a, depth0, KR, W_C[0], {n: camT_out[n][0].astype(np.float64) for n in names}, objs)
            O0 = [W_C[0].astype(np.float64) @ camT_out[n][0].astype(np.float64) for n in names]
            chk['mkref_refit'] = dict(normal_change_deg=round(float(np.degrees(np.arccos(np.clip(n2 @ n_, -1, 1)))), 4),
                                      offset_change_mm=round(float((d2 - d_) * 1000), 3),
                                      f0_bottoms_cm={o.name: round(float((o.world(O0[j]) @ n2).min() + d2) * 100, 3)
                                                     for j, o in enumerate(objs)})
        except BaseException as e:  # noqa: BLE001  (fit_table raises SystemExit on too few ring pixels)
            chk['mkref_refit'] = dict(error=str(e))
    rec['checks'] = chk
    rec['log'] = LOG
    json.dump(rec, open(os.path.join(out, 'pose_opt.json'), 'w'), indent=1, default=lambda x: x.tolist() if hasattr(x, 'tolist') else str(x))
    aux = {}
    for j, (o, L) in enumerate(zip(objs, lab)):
        aux[f'{o.name}_moving'] = L['moving']
        aux[f'{o.name}_hand_cm'] = L['hand_cm']
        aux[f'{o.name}_changed'] = changed[o.name]
    aux.update(deltas)
    np.savez(os.path.join(out, 'pose_opt_aux.npz'), **aux)
    log(f'wrote {out}: checks {json.dumps({k: v for k, v in chk.items() if k != "keys"})}')
    if not (chk['world_T_cam_byte_identical'] and chk['keys_ok'] and chk['frames_ok'] and chk['finite']):
        raise SystemExit('refine: output check failed (see pose_opt.json checks)')
    return rec


if __name__ == '__main__':
    main()
