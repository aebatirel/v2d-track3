#!/usr/bin/env python3
"""Build a FlashCHORD ManoSharpa reference for one Track 3 episode (objects + MediaPipe hands -> Sharpa IK).

Stages
  a  table/gravity frame: RANSAC plane on the frame-0 stereo depth in a ring around the objects' projected
     footprints; z = plane normal toward the camera, table top at z = TABLE_Z, xy origin under the objects'
     centroid, x = camera forward projected on the table. Object poses (world_T_cam @ cam_T_obj) and hand
     joints are expressed in this frame; optional per-object snap of resting objects onto the table.
  b  hands: park a side with too few valid frames; fill invalid runs (hold, or ride along with an object the
     hand touches at the run boundary, blended across the run); joint quaternions (MANO anatomical frames:
     x proximal, y dorsal, z = x cross y; see hand_rotations); write the "loaded" ManoSharpaData parquet that
     ego_recon_to_sharpa.py (E2S) reads, with WARMUP copies of frame 0 prepended.
  c  support USDA (one Cylinder 'table', top at TABLE_Z) at OUT/reconstructed_stage/<seq>_support.usda, which
     is where flash_chord.assets.registry.support_usda_for_parquet looks for OUT/processed/sequence_id=<seq>/...
  d  run E2S unchanged in a subprocess (this file with argument _e2s installs compatibility shims first:
     hppfcl alias, kinematics-only RobotWrapper.BuildFromMJCF so no robot meshes are needed, and a ManoSharpaData
     schema patch if this pinocchio build reports a different frame/joint count than the 67/22 in data_logger.py)
  e  drop the warm-up frames, recompute hand-object contacts from the retargeted robot frames vs the object
     meshes (16 probes per hand, part id = body index + 1, normals into the object), write OUT/processed
  f  print IK frame-task errors; validate with flash_chord's own loader (and scene build) in the FlashCHORD venv

Run in /content/rtvenv:
  PYTHONPATH=/content/v2d/robotic_grounding/source/robotic_grounding /content/rtvenv/bin/python mkref.py --ep 12
Inference only: object names come from the episode parquet's first row; its 'pose' field is never used.
"""
import argparse
import json
import os
import runpy
import shlex
import subprocess
import sys
import time
import types
import xml.etree.ElementTree as ET

import numpy as np

SIDES = ('right', 'left')
ROBOT = 'sharpa_wave'
TIPS = [4, 8, 12, 16, 20]
PALM = [0, 5, 9, 13, 17]
PROBE_SITES = ['thumb_tip_site', 'index_tip_site', 'middle_tip_site', 'ring_tip_site', 'pinky_tip_site',
               'thumb_DP_site', 'index_DP_site', 'middle_DP_site', 'ring_DP_site', 'pinky_DP_site',
               'thumb_MCP_VL_site', 'index_MP_site', 'middle_MP_site', 'ring_MP_site', 'pinky_MP_site']
PALM_FRAMES = ['hand_C_MC', 'index_MCP_VL_site', 'middle_MCP_VL_site', 'ring_MCP_VL_site', 'pinky_MC_site']
# Slot k of mano_<side>_object_contact_* belongs to CONTACT_SLOT_NAMES[k] ('palm' = mean of PALM_FRAMES); written as the
# contact_slot_names column. mano_link_names keeps the kit's MANO link list, which does NOT describe these slots.
CONTACT_SLOT_NAMES = PROBE_SITES + ['palm']
N_SLOTS = len(CONTACT_SLOT_NAMES)                               # 15 site probes + 1 palm probe
# Relaxed right hand in the MANO anatomical wrist frame (x proximal, y dorsal, z radial), metres, MediaPipe order.
TEMPLATE_RIGHT = np.array([
    [0, 0, 0],
    [-0.030, -0.012, 0.020], [-0.055, -0.020, 0.040], [-0.080, -0.025, 0.050], [-0.100, -0.028, 0.055],
    [-0.090, 0.000, 0.025], [-0.130, -0.005, 0.027], [-0.153, -0.012, 0.028], [-0.172, -0.020, 0.028],
    [-0.093, 0.000, 0.003], [-0.137, -0.006, 0.003], [-0.163, -0.013, 0.003], [-0.184, -0.022, 0.003],
    [-0.088, 0.000, -0.016], [-0.128, -0.006, -0.018], [-0.152, -0.013, -0.019], [-0.172, -0.021, -0.019],
    [-0.080, -0.002, -0.033], [-0.110, -0.008, -0.037], [-0.128, -0.014, -0.039], [-0.145, -0.021, -0.040]])
T_START = time.time()


def log(*a):
    print(f'[{time.time() - T_START:7.1f}s]', *a, flush=True)


# ======================================================================== robotic_grounding compatibility
def rg_src(v2d):
    return os.path.join(v2d, 'robotic_grounding', 'source', 'robotic_grounding')


def install_compat(v2d):
    """Make robotic_grounding's retargeter importable in a plain pip venv (pin >= 3, no robot meshes)."""
    src = rg_src(v2d)
    if src not in sys.path:
        sys.path.insert(0, src)
    try:
        import hppfcl  # noqa: F401  (pinocchio_viser_visualizer imports it at module level)
    except ImportError:
        try:
            import coal as shim
        except ImportError:
            shim = types.ModuleType('hppfcl')
        for n in ('BVHModelBase', 'HeightFieldOBBRSS', 'HeightFieldAABB'):
            if not hasattr(shim, n):
                setattr(shim, n, type(n, (), {}))
        sys.modules['hppfcl'] = shim
    import pinocchio as pin
    try:
        import pinocchio.visualize.base_visualizer  # noqa: F401  (imported by the unused viser visualizer)
    except ImportError:
        bv = types.ModuleType('pinocchio.visualize.base_visualizer')
        bv.BaseVisualizer = type('BaseVisualizer', (), {'__init__': lambda self, *a, **k: None})
        sys.modules['pinocchio.visualize.base_visualizer'] = bv

    def build_from_mjcf(filename, root_joint=None, *args, **kwargs):
        # Kinematic model only: the IK never touches geometry, and the robot STL meshes may be LFS pointers.
        if root_joint is None:
            model = pin.buildModelFromMJCF(filename)
        else:
            try:
                model = pin.buildModelFromMJCF(filename, root_joint)
            except TypeError:  # pin 4.1 (box 1, 2026-10-20) also wants the root joint's name
                model = pin.buildModelFromMJCF(filename, root_joint, 'root_joint')
        if isinstance(model, tuple):
            model = model[0]
        try:
            rw = pin.RobotWrapper(model)
        except Exception:
            rw = object.__new__(pin.RobotWrapper)
            rw.model, rw.data = model, model.createData()
            rw.collision_model = rw.visual_model = rw.collision_data = rw.visual_data = None
        if getattr(rw, 'q0', None) is None:
            rw.q0 = pin.neutral(model)
        return rw

    pin.RobotWrapper.BuildFromMJCF = staticmethod(build_from_mjcf)
    return pin


def sharpa_layout(pin, v2d):
    from robotic_grounding.retarget.params import SHARPA_TO_MANO_MAPPING
    xml_dir = os.path.join(rg_src(v2d), 'robotic_grounding', 'assets', 'xmls', 'sharpawave')
    per = {}
    for s in SIDES:
        rw = pin.RobotWrapper.BuildFromMJCF(filename=os.path.join(xml_dir, f'{s}_sharpawave.xml'),
                                            root_joint=pin.JointModelFreeFlyer())
        m = rw.model
        frames = [f.name for f in m.frames]
        tasks = [k.replace('.*', s) for k in SHARPA_TO_MANO_MAPPING]
        need = tasks + [f'{s}_{x}' for x in PROBE_SITES + PALM_FRAMES]
        missing = sorted({n for n in need if n not in frames})
        if missing:
            raise SystemExit(f'pinocchio MJCF model ({s}) lacks frames {missing}; check the pin version')
        per[s] = dict(n_frames=len(frames), n_fingers=m.nq - 7, n_tasks=len(tasks),
                      fingers=[m.names[i] for i in range(2, m.nq - 7 + 2)])
    keys = ('n_frames', 'n_fingers', 'n_tasks')
    if any(per['right'][k] != per['left'][k] for k in keys):
        raise SystemExit(f'left/right Sharpa layouts differ: {[(k, per["right"][k], per["left"][k]) for k in keys]}')
    return dict(per_side=per, **{k: per['right'][k] for k in keys})


def patch_logger(lay, slot_names=False):
    """Return ManoSharpaData; rebuild it if this pinocchio reports another frame / finger / task count. slot_names=True
    returns a subclass schema with the extra contact_slot_names column (main process only: E2S keeps the kit class,
    whose from_parquet drops the column, and stage (e) writes it again)."""
    import pyarrow as pa
    import robotic_grounding.retarget.data_logger as dl
    F, NF, NT = lay['n_frames'], lay['n_fingers'], lay['n_tasks']
    if (F, NF, NT) != (dl.SHARPA_NUM_FRAMES, 22, 11):
        specs = []
        for name, typ, py, ts in dl.BASE_FIELDS + dl.MANO_FIELDS + dl.SHARPA_FIELDS + dl.OBJECT_FIELDS:
            if name in ('robot_right_frames', 'robot_left_frames'):
                typ = pa.list_(pa.list_(pa.list_(pa.float32(), 7), F))
            elif name in ('robot_right_finger_joints', 'robot_left_finger_joints'):
                typ = pa.list_(pa.list_(pa.float32(), NF))
            elif name in ('robot_right_frame_task_errors', 'robot_left_frame_task_errors'):
                typ = pa.list_(pa.list_(pa.float32(), NT))
            specs.append((name, typ, py, ts))
        dl.ManoSharpaData = dl.create_data_logger_class('ManoSharpaData', specs)
        dl.SHARPA_NUM_FRAMES = F
        print(f'[compat] ManoSharpaData schema patched: frames {F} (repo 67), finger joints {NF} (22), tasks {NT} (11)',
              flush=True)
    if slot_names:
        return dl.create_data_logger_class('ManoSharpaData', list(dl.ManoSharpaData._field_specs)
                                           + [('contact_slot_names', pa.list_(pa.string()), list[str], False)])
    return dl.ManoSharpaData


def e2s_entry(argv):
    """argv = ['_e2s', V2D, '--', <ego_recon_to_sharpa.py args>]: run E2S unchanged after the shims."""
    v2d = argv[1]
    rest = argv[3:] if len(argv) > 2 and argv[2] == '--' else argv[2:]
    pin = install_compat(v2d)
    if os.environ.get('E2S_WRIST_COST'):
        # Retargeting weights are ours to choose (only the evaluator is fixed). NVIDIA's mapping weights the wrist
        # (hand_C_MC) position at 0.2 vs 1.0 per fingertip, and the warm-started IK then drifts the wrist up to 33 cm
        # to reach fingertips (2026-10-20, ep44). Patched in place, so E2S's own import sees it; E2S itself unchanged.
        from robotic_grounding.retarget import params as rgp
        k = '.*_hand_C_MC'
        src, pos, ori = rgp.SHARPA_TO_MANO_MAPPING[k]
        rgp.SHARPA_TO_MANO_MAPPING[k] = (src, float(os.environ['E2S_WRIST_COST']), float(os.environ.get('E2S_WRIST_ORI_COST', ori)))
        print(f'E2S mapping patched: {k} {(src, pos, ori)} -> {rgp.SHARPA_TO_MANO_MAPPING[k]}', flush=True)
    patch_logger(sharpa_layout(pin, v2d))
    e2s = os.path.join(v2d, 'robotic_grounding', 'scripts', 'retarget', 'ego_recon_to_sharpa.py')
    sys.argv = [e2s] + rest
    runpy.run_path(e2s, run_name='__main__')


# ======================================================================== small math helpers
def rot():
    from scipy.spatial.transform import Rotation
    return Rotation


def wxyz_from_R(R):
    q = rot().from_matrix(R.reshape(-1, 3, 3)).as_quat()                  # xyzw
    return np.concatenate([q[:, 3:4], q[:, :3]], 1).reshape(R.shape[:-2] + (4,))


def rotvec_from_wxyz(q):
    q = np.asarray(q, float).reshape(-1, 4)
    return rot().from_quat(q[:, [1, 2, 3, 0]]).as_rotvec()


def continuous(q):
    q = q.copy()
    for t in range(1, len(q)):
        flip = (q[t] * q[t - 1]).sum(-1) < 0
        q[t][flip] *= -1.0
    return q


def runs(mask):
    m = np.r_[False, np.asarray(mask, bool), False].astype(np.int8)
    d = np.diff(m)
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


def orthoframe(x, zref):
    """Columns [x, y, z] with x along `x`, z = `zref` orthogonalised against x, y = z cross x."""
    xn = np.linalg.norm(x, axis=-1, keepdims=True)
    xh = x / np.maximum(xn, 1e-12)
    z = zref - (zref * xh).sum(-1, keepdims=True) * xh
    zn = np.linalg.norm(z, axis=-1, keepdims=True)
    zh = z / np.maximum(zn, 1e-12)
    R = np.stack([xh, np.cross(zh, xh), zh], -1)
    bad = (xn[..., 0] < 1e-6) | (zn[..., 0] < 1e-3 * np.maximum(np.linalg.norm(zref, axis=-1), 1e-9))
    return R, bad


def hand_rotations(J, side):
    """MANO-anatomical joint frames from 21 MediaPipe-order joints, (T,21,3) -> (T,21,3,3).

    Matches manotorch AxisLayerFK as consumed by E2S: frame x = proximal along the bone the joint drives,
    y = dorsal, z = x cross y (radial on the right hand, ulnar on the left; the Sharpa wrist site has the same
    convention). Tips reuse their distal joint's frame. Only joint 0 (cost 0.2) and the tips (0.05-0.1) carry
    orientation cost in the Sharpa IK; the thumb twist reference (palmar for right, dorsal for left) is an
    approximation of manotorch's skewed thumb up-axis.
    """
    zr = (J[:, 5] - J[:, 17]) if side == 'right' else (J[:, 17] - J[:, 5])
    Rw, bad = orthoframe(J[:, 0] - J[:, 9], zr)
    good = np.flatnonzero(~bad)
    if len(good) == 0:
        Rw[:] = np.eye(3)
    else:
        for t in np.flatnonzero(bad):                      # nearest good frame
            Rw[t] = Rw[good[np.argmin(np.abs(good - t))]]
    yw, zw = Rw[:, :, 1], Rw[:, :, 2]
    zthumb = -yw if side == 'right' else yw
    R = np.repeat(Rw[:, None], 21, 1)
    for k in range(1, 21):
        x = (J[:, k - 1] - J[:, k]) if k in TIPS else (J[:, k] - J[:, k + 1])
        Rk, badk = orthoframe(x, zthumb if k <= 4 else zw)
        Rk[badk] = Rw[badk]
        R[:, k] = Rk
    return R


PARENT = [-1, 0, 1, 2, 3, 0, 5, 6, 7, 0, 9, 10, 11, 0, 13, 14, 15, 0, 17, 18, 19]   # MediaPipe order


def normalize_bones(J, valid, scale=1.0):
    """Rebuild the 21-joint skeleton with every bone at its median length over the valid frames (x scale), keeping
    each bone's direction (2026-10-20: ep44's wrist->middle-MCP varied 5.6-9.0 cm within 20 frames, and the E2S IK
    drifted up to 33 cm from the wrist and snapped back). Parents precede children in MediaPipe order."""
    L = np.zeros(21)
    for k in range(1, 21):
        L[k] = np.median(np.linalg.norm(J[valid, k] - J[valid, PARENT[k]], axis=-1)) * scale
    out = J.copy()
    for k in range(1, 21):
        d = J[:, k] - J[:, PARENT[k]]
        out[:, k] = out[:, PARENT[k]] + d / np.maximum(np.linalg.norm(d, axis=-1, keepdims=True), 1e-9) * L[k]
    return out, L


def palmar_score(J, R):
    """Mean (MCPs -> tips) . palmar; > 0 means flexion goes palmar, i.e. the side label fits the chirality."""
    y = R[:, 0, :, 1]
    return -((J[:, TIPS].mean(1) - J[:, [5, 9, 13, 17]].mean(1)) * y).sum(-1)


# ======================================================================== geometry / objects / table
def rectified_K(calib_path):
    import cv2
    C = json.load(open(calib_path))
    cam = C['cameras']
    sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)  # noqa: E731
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)  # noqa: E731
    E = np.array(sp['left_to_right'], float)
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b'),
                                                (1280, 800), E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(),
                                                alpha=0, newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
    return P1[:3, :3].copy()


def load_names(t3, ep, split='public', roster='/content/kit/v2d_submission_kit/data/track_3_evaluation_objects.json'):
    if split == 'eval':                                                  # eval: the kit roster (no episode parquet)
        return [str(n) for n in json.load(open(roster))['episodes'][str(ep)]]
    import pyarrow.parquet as pq
    tab = pq.read_table(f'{t3}/ep{ep}.parquet', columns=['observation.objects'])
    return [str(o['name']) for o in tab.column('observation.objects')[0].as_py()]   # slot order only


def visual_mesh_path(t3, n):
    p = f'{t3}/mesh/{n}/{n}.glb'
    return p if os.path.exists(p) else f'{t3}/mesh/{n}/{n}_visual.glb'


def contact_mesh_path(t3, n):
    p = f'{t3}/mesh/{n}/{n}_collision.glb'
    return p if os.path.exists(p) else visual_mesh_path(t3, n)


def check_urdf(path, vis, con):
    msgs = []
    try:
        root = ET.parse(path).getroot()
    except Exception as e:  # noqa: BLE001
        return [f'cannot parse {path}: {e}']
    base = os.path.dirname(path)
    for tag in ('visual', 'collision'):
        for el in root.iter(tag):
            o = el.find('origin')
            if o is not None:
                xyz = np.array([float(v) for v in o.get('xyz', '0 0 0').split()])
                rpy = np.array([float(v) for v in o.get('rpy', '0 0 0').split()])
                if np.abs(xyz).max() > 1e-6 or np.abs(rpy).max() > 1e-6:
                    msgs.append(f'{tag} origin xyz={xyz.tolist()} rpy={rpy.tolist()} (mesh frame != link frame!)')
            m = el.find('geometry/mesh')
            if m is not None:
                f = os.path.normpath(os.path.join(base, m.get('filename', '')))
                sc = m.get('scale')
                if not os.path.exists(f):
                    msgs.append(f'{tag} mesh missing: {f}')
                elif os.path.realpath(f) not in (os.path.realpath(vis), os.path.realpath(con)):
                    msgs.append(f'{tag} mesh {f} differs from the pose mesh {vis}')
                if sc and any(abs(float(v) - 1) > 1e-6 for v in sc.split()):
                    msgs.append(f'{tag} mesh scale {sc}')
    return msgs


def fit_table(depth0, KR, W0, cam_T0, meshes, a):
    import cv2
    H, W = depth0.shape
    U = np.zeros((H, W), np.uint8)
    rng = np.random.default_rng(0)
    for n, m in meshes.items():
        v = np.asarray(m.vertices)
        v = v[rng.choice(len(v), min(len(v), 8000), replace=False)]
        X = v @ cam_T0[n][:3, :3].T + cam_T0[n][:3, 3]
        X = X[X[:, 2] > 0.05]
        if len(X) < 3:
            continue
        uv = np.stack([KR[0, 0] * X[:, 0] / X[:, 2] + KR[0, 2], KR[1, 1] * X[:, 1] / X[:, 2] + KR[1, 2]], 1)
        uv = np.clip(uv, -4 * W, 5 * W)
        cv2.fillConvexPoly(U, cv2.convexHull(uv.astype(np.float32)).astype(np.int32), 1)
    k = lambda r: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))  # noqa: E731
    D = np.asarray(depth0, np.float32)
    ring = (cv2.dilate(U, k(a.ring_out)) > 0) & ~(cv2.dilate(U, k(a.ring_in)) > 0) & (D > 0)
    vv, uu = np.nonzero(ring)
    if len(vv) < 500:
        raise SystemExit(f'only {len(vv)} valid depth pixels in the ring around the objects; widen --ring_out')
    z = D[vv, uu].astype(np.float64)
    P = np.stack([(uu - KR[0, 2]) * z / KR[0, 0], (vv - KR[1, 2]) * z / KR[1, 1], z], 1)
    P = P @ W0[:3, :3].T + W0[:3, 3]
    if len(P) > 30000:
        P = P[rng.choice(len(P), 30000, replace=False)]
    # Object vertices in world, to pick the plane the objects stand on. The ring can also hold the floor past the
    # table edge, and the floor can win a plain RANSAC (box 1, ep12: the floor 60 cm under the objects won).
    Vw = [np.asarray(m.vertices) @ (W0 @ cam_T0[n_])[:3, :3].T + (W0 @ cam_T0[n_])[:3, 3] for n_, m in meshes.items()]

    def ransac(Q):
        best, best_cnt = None, -1
        for _ in range(a.plane_iters):
            p0, p1, p2 = Q[rng.choice(len(Q), 3, replace=False)]
            n = np.cross(p1 - p0, p2 - p0)
            nn = np.linalg.norm(n)
            if nn < 1e-9:
                continue
            n = n / nn
            cnt = int((np.abs(Q @ n - n @ p0) < a.plane_thr).sum())
            if cnt > best_cnt:
                best, best_cnt = (n, -n @ p0), cnt
        n, d = best
        inl = np.abs(Q @ n + d) < a.plane_thr
        for _ in range(3):
            c = Q[inl].mean(0)
            n = np.linalg.svd(Q[inl] - c, full_matrices=False)[2][2]
            d = -n @ c
            inl = np.abs(Q @ n + d) < a.plane_thr
        if n @ W0[:3, 3] + d < 0:                  # camera on the positive side: n points up, toward the camera
            n, d = -n, -d
        return n, d

    # Sequential RANSAC: up to 4 planes holding >= 3 % of the ring points each.
    cands, rest = [], np.ones(len(P), bool)
    for _ in range(4):
        if rest.sum() < max(500, 0.03 * len(P)):
            break
        n, d = ransac(P[rest])
        inl = np.abs(P @ n + d) < a.plane_thr
        if (inl & rest).sum() < 0.03 * len(P):
            break
        lowest = min(float((V @ n).min() + d) for V in Vw)          # lowest object point above this plane (m)
        cands.append(dict(n=n, d=d, frac=float(inl.mean()), lowest=lowest,
                          tilt=float(np.degrees(np.arccos(np.clip(abs(n @ cands[0]['n']), -1, 1)))) if cands else 0.0,
                          rms=float(np.sqrt(np.mean((P[inl] @ n + d) ** 2)))))
        rest &= ~inl
    # The support plane: parallel to the dominant plane (within 25 deg) and closest under the lowest object point.
    ok = [c for c in cands if c['tilt'] <= 25 and c['lowest'] > -a.support_tol]
    pick = min(ok or cands, key=lambda c: abs(c['lowest']))
    a._plane_cands = [{k: (round(v, 4) if isinstance(v, float) else None) for k, v in c.items() if k not in ('n', 'd')}
                      for c in cands]
    a._plane_full = cands
    return pick['n'], pick['d'], pick['frac'], len(P), pick['rms']


def table_frame(n, d, W0, centroid_w, table_z):
    """4x4 mapping world (rectified-left camera 0) -> table frame."""
    z = n / np.linalg.norm(n)
    f = W0[:3, :3] @ np.array([0.0, -1.0, 1.0])     # camera forward + image-up, projected on the table
    x = f - (f @ z) * z
    if np.linalg.norm(x) < 1e-6:
        x = W0[:3, :3] @ np.array([1.0, 0.0, 0.0])
        x = x - (x @ z) * z
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    o = centroid_w - (n @ centroid_w + d) * n       # under the objects' centroid, on the plane
    Rt = np.stack([x, y, z])                         # rows: table axes in world
    M = np.eye(4)
    M[:3, :3] = Rt
    M[:3, 3] = -Rt @ o + np.array([0.0, 0.0, table_z])
    return M


# ======================================================================== contacts
class BodyQuery:
    def __init__(self, mesh):
        import trimesh
        self.mesh = mesh
        self.q = trimesh.proximity.ProximityQuery(mesh)
        self.watertight = bool(mesh.is_watertight)
        self.fn = np.asarray(mesh.face_normals)

    def closest(self, pts):
        c, d, tri = self.q.on_surface(pts)
        inside = self.mesh.contains(pts) if self.watertight else np.zeros(len(pts), bool)
        return c, np.where(inside, 0.0, d), tri, inside


def table_disc(depth0, KR, T_tab, table_z, band=0.008, cell=0.01):
    """The real table's footprint in the table frame (2026-10-21: the simulated cylinder had radius 0.45 m around the
    objects' centroid while the real round table measures ~0.22-0.25 m, so table edges that the person uses -- a board
    slid until it overhangs, a dustpan held at the edge -- did not exist in sim). Frame-0 depth points within BAND of
    the plane, a 1 cm occupancy grid, the connected region nearest the objects (origin), its minimum enclosing circle."""
    import cv2
    from scipy import ndimage
    H, W = depth0.shape
    v, u = np.mgrid[0:H:2, 0:W:2]; z = np.asarray(depth0)[v, u]
    ok = np.isfinite(z) & (z > 0.2) & (z < 1.5)
    X = np.stack([(u[ok] - KR[0, 2]) * z[ok] / KR[0, 0], (v[ok] - KR[1, 2]) * z[ok] / KR[1, 1], z[ok]], 1)
    P = X @ T_tab[:3, :3].T + T_tab[:3, 3]
    Q = P[np.abs(P[:, 2] - table_z) < band, :2]
    Q = Q[np.abs(Q).max(1) < 1.0]
    if len(Q) < 1000:
        return None
    n = int(2.0 / cell); ij = np.clip(((Q + 1.0) / cell).astype(int), 0, n - 1)
    G = np.zeros((n, n), bool); G[ij[:, 0], ij[:, 1]] = True
    G = ndimage.binary_closing(G, iterations=3)                    # holes under objects / sparse depth
    lab, nl = ndimage.label(G)
    if nl == 0:
        return None
    c0 = int(1.0 / cell); cand = np.argwhere(lab > 0)
    k = lab[tuple(cand[np.argmin(np.linalg.norm(cand - c0, axis=1))])]
    pts = (np.argwhere(lab == k) * cell - 1.0 + cell / 2).astype(np.float32)
    (cx, cy), r = cv2.minEnclosingCircle(pts)
    return float(cx), float(cy), float(r)


def start_overlap_lift(OBJ, names, vis, con, cap, table_z, n_samp=3000, min_in=5, margin=0.0005, on_table=0.02):
    """Objects that start inside one another (2026-10-24, eval 1: 243 of 3000 lid surface samples 7.6 mm inside the pot
    solid at frame 0; the simulated lid was wedged and never lifted; public twin ep2 has the same failure). For each
    frame-0 pair, surface samples of the object with the higher bottom (the one resting on the other: lid on pot, cup
    in pot) are tested against the other's watertight solid; when >= MIN_IN are inside, the upper object is lifted along
    the table normal, whole trajectory, as the table snap. The lift is the largest upward exit distance of the inside
    samples (vertical rays) + MARGIN, checked by a containment test (< MIN_IN inside), then raised by half steps.
    An upper object whose bottom is within ON_TABLE of the table stands on the table and is never lifted (eval 8: the
    pot beside the beige cup). Not resolved within CAP: left unchanged and reported. Returns the per-object lifts (m)
    and a log record."""
    import trimesh
    B = len(names); lift = np.zeros(B); rec = []
    pts = [np.asarray(trimesh.sample.sample_surface(vis[nm], n_samp, seed=0)[0]) for nm in names]

    def in_c(b, c, dz):                                                 # b's samples in c's mesh frame, inside mask
        Rb, tb = OBJ[0, b, :3, :3], OBJ[0, b, :3, 3] + np.array([0.0, 0.0, lift[b] + dz])
        Rc, tc = OBJ[0, c, :3, :3], OBJ[0, c, :3, 3] + np.array([0.0, 0.0, lift[c]])
        P = (pts[b] @ Rb.T + tb - tc) @ Rc
        return P, con[names[c]].contains(P)

    bot = np.array([(np.asarray(vis[nm].vertices) @ OBJ[0, b, :3, :3].T + OBJ[0, b, :3, 3])[:, 2].min()
                    for b, nm in enumerate(names)])
    for b in range(B):
        for c in range(B):
            if b == c or bot[b] < bot[c] or not con[names[c]].is_watertight:   # b is the upper object of the pair
                continue
            if bot[b] - table_z < on_table:                             # b stands on the table, not on c
                continue
            P, ins = in_c(b, c, 0.0); n0 = int(ins.sum())
            if n0 < min_in:
                continue
            up = OBJ[0, c, :3, :3].T @ np.array([0.0, 0.0, 1.0])            # table normal in c's mesh frame
            loc, ri, _ = con[names[c]].ray.intersects_location(P[ins], np.repeat(up[None], n0, 0), multiple_hits=True)
            ex = np.full(n0, np.inf)
            if len(ri):
                np.minimum.at(ex, ri, (loc - P[ins][ri]) @ up)               # first exit above each inside sample
            dz = float(np.max(ex[np.isfinite(ex)], initial=0.0)) + margin
            while dz <= cap and int(in_c(b, c, dz)[1].sum()) >= min_in:
                dz += max(0.5 * dz, 0.001)
            dz = None if dz > cap else dz
            r = dict(upper=names[b], lower=names[c], samples_inside=n0, of=n_samp)
            if dz is None:
                r['lift_cm'] = None; r['note'] = f'not resolved within {cap * 100:.1f} cm: unchanged'
            else:
                lift[b] += dz; r['lift_cm'] = round(dz * 100, 2)
            rec.append(r)
    for b in range(B):
        OBJ[:, b, 2, 3] += lift[b]
    return lift, rec


def separate_hands(J, valid, meas, gap, lead_in, lead_in_step=0.01):
    """Rigid per-frame shifts that keep the two hands apart (table frame, z up). Returns ({side: (T, 3)}, stats).

    1) lead-in: a hand first valid at t1 > 0 was held at its first pose from frame 0 (fill_invalid); it now starts
       15 cm out (horizontally away from the other hand) and 10 cm up and arrives over the LEAD_IN frames before t1.
       The approach moves at most LEAD_IN_STEP per frame (m): with few frames before t1 the start is nearer.
       Evidence (2026-10-23, eval ep35): the right hand was first valid at t1 = 6, so 18 cm came in over 6 frames
       (3 cm per frame = 60 cm/s); with zero policy action the simulated wrist fell 16 cm behind by step 10 (the
       wrist termination is 15 cm) and the trained policy never moved its hands. 1 cm per frame = 20 cm/s at 20 fps.
    2) separation: where the closest left/right joint pair is nearer than GAP, the hand that is not measured in that
       frame moves (both half-way if both or neither are measured), away from the other hand and upward (free space).
       Each round adds the needed shifts box-smoothed over 5 frames, up to 5 rounds (the last unsmoothed), so no
       overlap is left and the shifts do not jump. Evidence: ep24 the right hand, unseen for frames 0-16, was held where it first appeared, 1-6 cm from the
       left hand; the two robot hands overlapped by up to 14 mm at reset and the near board popped 15 deg.
    """
    from scipy.ndimage import uniform_filter1d
    T = len(J['left']); z = np.array([0, 0, 1.0]); off = {s: np.zeros((T, 3)) for s in SIDES}; st = {}
    other = {'left': 'right', 'right': 'left'}
    for s in SIDES:                                              # 1) lead-in
        v = np.nonzero(valid[s][:T])[0]; t1 = int(v[0]) if len(v) else 0; st[s] = dict(first_valid=t1, lead_in=0)
        if t1 <= 0 or lead_in <= 0:
            continue
        u = (J[s][t1, 0] - J[other[s]][t1, 0]) * np.array([1, 1, 0.0])
        u = u / np.linalg.norm(u) if np.linalg.norm(u) > 0.01 else np.array([0, -1.0 if s == 'right' else 1.0, 0])
        n = min(lead_in, t1); o = 0.15 * u + 0.10 * z
        if lead_in_step > 0 and np.linalg.norm(o) / n > lead_in_step:
            o = o * (lead_in_step * n / np.linalg.norm(o))
        w = np.clip((t1 - np.arange(T)) / n, 0, 1)
        off[s] += w[:, None] * o[None]; st[s]['lead_in'] = t1; st[s]['lead_in_cm'] = round(float(np.linalg.norm(o)) * 100, 1)
    def needs():                                                 # per-frame shifts that would clear every overlap
        raw = {s: np.zeros((T, 3)) for s in SIDES}; n = 0; w = 0.0
        for t in range(T):
            A = J['left'][t] + off['left'][t]; B = J['right'][t] + off['right'][t]
            for _ in range(6):
                d = np.linalg.norm((A + raw['left'][t])[:, None] - (B + raw['right'][t])[None], axis=2).min()
                if d >= gap:
                    break
                w = max(w, gap - d)
                u = (B.mean(0) - A.mean(0)) * np.array([1, 1, 0.0]); u = u / max(np.linalg.norm(u), 1e-6)
                share = ({'left': 0.0, 'right': 1.0} if meas['left'][t] and not meas['right'][t] else
                         {'left': 1.0, 'right': 0.0} if meas['right'][t] and not meas['left'][t] else {'left': 0.5, 'right': 0.5})
                for s, sgn in (('left', -1.0), ('right', 1.0)):
                    dv = sgn * u + 0.7 * z; raw[s][t] += share[s] * (gap - d + 0.005) * dv / np.linalg.norm(dv)
            n += bool(np.abs(raw['left'][t]).sum() + np.abs(raw['right'][t]).sum() > 0)
        return raw, n, w
    nfix = worst = None; moved = {s: np.zeros(T) for s in SIDES}
    for rnd in range(5):                                         # correct, smooth (5 frames), repeat on what is left
        raw, n, w = needs()
        if nfix is None:
            nfix, worst = n, w
        if n == 0:
            break
        for s in SIDES:
            sm = uniform_filter1d(raw[s], 5, axis=0, mode='nearest') if rnd < 4 else raw[s]
            off[s] += sm; moved[s] = np.maximum(moved[s], np.linalg.norm(raw[s], axis=1))
    for s in SIDES:
        st[s].update(sep_frames=int((moved[s] > 0).sum()), sep_max_cm=round(float(moved[s].max() * 100), 1))
    st['rounds'] = rnd + 1; st['left_overlap_frames'] = n
    st['overlap_frames'] = nfix; st['worst_overlap_cm'] = round(worst * 100, 1)
    return off, st


def depenetrate(J, OBJ, queries, table_z, clear, disc=None):
    """Physics-aware hand targets (2026-10-21; cf. ContactOpt, Grady et al. CVPR 2021, which tolerates ~2 mm of
    interpenetration): every joint centre is kept at least CLEAR outside every object surface and above the table
    (joint centres sit ~8 mm inside the skin, so CLEAR = 6 mm leaves ~2 mm of squeeze). A joint inside an object, or
    closer than CLEAR, moves along the surface normal of its closest point; under the table it moves up. Inside
    tests: mesh.contains for watertight meshes (our reconstructions), else the side of the closest face. The table
    rule applies only over the measured table DISC (cx, cy, r): fingers under a board that overhangs the real edge stay.
    A joint pinned between the table and an object goes to the object's top above it (highest surface sample within 1.5 cm in
    x-y + CLEAR) instead of oscillating between the two rules."""
    out = J.copy(); T = len(J); moved = 0; depth_max = 0.0
    for t in range(T):
        P = out[t].reshape(-1, 3)
        for b, q in enumerate(queries):
            M = OBJ[t, b]; Pl = (P - M[:3, 3]) @ M[:3, :3]
            c, d, tri = q.q.on_surface(Pl)
            n = q.fn[tri]
            inside = q.mesh.contains(Pl) if q.watertight else (np.einsum('ij,ij->i', Pl - c, n) < 0) & (d < 0.03)
            sd = np.where(inside, -d, d)                               # signed distance, negative inside
            k = sd < clear
            if k.any():
                Pl[k] = c[k] + n[k] * clear
                moved += int(k.sum()); depth_max = max(depth_max, float(-sd[k].min()))
                P = Pl @ M[:3, :3].T + M[:3, 3]
        low = P[:, 2] < table_z + clear
        if disc is not None:
            low &= np.linalg.norm(P[:, :2] - np.array(disc[:2]), axis=1) < disc[2]
        if low.any():
            depth_max = max(depth_max, float(table_z + clear - P[low, 2].min())); moved += int(low.sum())
            P[low, 2] = table_z + clear
            for b, q in enumerate(queries):                        # pinned between table and object -> object top
                M = OBJ[t, b]; Pl = (P[low] - M[:3, 3]) @ M[:3, :3]
                inside = q.mesh.contains(Pl) if q.watertight else np.zeros(len(Pl), bool)
                if inside.any():
                    if not hasattr(q, 'dense'):                    # surface samples (vertices are too sparse on flat faces)
                        import trimesh
                        q.dense = np.asarray(trimesh.sample.sample_surface(q.mesh, 20000, seed=0)[0])
                    Vw = q.dense @ M[:3, :3].T + M[:3, 3]
                    idx = np.nonzero(low)[0][inside]
                    for i in idx:
                        near = np.linalg.norm(Vw[:, :2] - P[i, :2], axis=1) < 0.015
                        if near.any():
                            P[i, 2] = Vw[near, 2].max() + clear
        out[t] = P.reshape(out[t].shape)
    return out, dict(joints_moved=moved, joint_frames=int(T * J.shape[1]), max_push_cm=round(depth_max * 100, 2))


def anchor_body(Jt, t, OBJ, queries, a):
    pts = Jt[TIPS + PALM]
    best, bd = None, a.attach_dist
    for b, q in enumerate(queries):
        M = OBJ[t, b]
        _, d, _, _ = q.closest((pts - M[:3, 3]) @ M[:3, :3])
        if d.min() < bd:
            best, bd = b, float(d.min())
    return best


def fill_invalid(J, valid, OBJ, queries, a):
    T = len(J)
    out = J.copy()
    notes = []
    for s, e in runs(~valid):
        t0 = s - 1 if s > 0 else None
        t1 = e if e < T else None
        trajs = []
        for tk in (t0, t1):
            if tk is None:
                trajs.append(None)
                continue
            b = anchor_body(J[tk], tk, OBJ, queries, a) if a.gap_fill == 'attach' else None
            if b is None:
                tr = np.repeat(J[tk][None], e - s, 0)
            else:
                Mi = np.linalg.inv(OBJ[tk, b])
                loc = J[tk] @ Mi[:3, :3].T + Mi[:3, 3]
                tr = np.einsum('tij,kj->tki', OBJ[s:e, b, :3, :3], loc) + OBJ[s:e, b, None, :3, 3]
            trajs.append(tr)
            notes.append((int(s), int(e), int(tk), None if b is None else int(b)))
        A, B_ = trajs
        if A is not None and B_ is not None:
            w = ((np.arange(s, e) - t0) / (t1 - t0))[:, None, None]
            out[s:e] = (1 - w) * A + w * B_
        else:
            out[s:e] = A if A is not None else B_
    return out, notes


def motion_gate(Mb, a):
    T, w = len(Mb), a.gate_win
    gate = np.zeros(T, bool)
    if T <= w:
        return gate, None
    dp = np.linalg.norm(Mb[w:, :3, 3] - Mb[:-w, :3, 3], axis=1)
    Rr = np.einsum('tji,tjk->tik', Mb[:-w, :3, :3], Mb[w:, :3, :3])
    ang = np.degrees(np.arccos(np.clip((np.trace(Rr, axis1=1, axis2=2) - 1) / 2, -1, 1)))
    idx = np.flatnonzero((dp > a.gate_disp) | (ang > a.gate_rot_deg))
    if not len(idx):
        return gate, None
    lo, hi = max(0, int(idx[0]) - a.gate_pad), min(T - 1, int(idx[-1]) + w + a.gate_pad)
    gate[lo:hi + 1] = True
    return gate, (lo, hi)


def deflicker(x, n):
    out = np.zeros_like(x)
    for s, e in runs(x):
        if e - s >= n:
            out[s:e] = True
    return out


def compute_contacts(frames, fnames, side, OBJ, queries, gates, a):
    ix = {n: i for i, n in enumerate(fnames)}
    probes = [frames[:, ix[f'{side}_{s}'], :3] for s in PROBE_SITES]
    probes.append(np.mean([frames[:, ix[f'{side}_{s}'], :3] for s in PALM_FRAMES], 0))
    Pw = np.stack(probes, 1)                                           # (T,16,3)
    T, K, B = Pw.shape[0], Pw.shape[1], OBJ.shape[1]
    thr = np.full(K, a.contact_thr)
    thr[-1] += a.palm_extra
    best_d = np.full((T, K), np.inf)
    best_b = np.full((T, K), -1)
    best_c = np.zeros((T, K, 3))
    best_n = np.zeros((T, K, 3))
    flips = []
    for b, q in enumerate(queries):
        R, t = OBJ[:, b, :3, :3], OBJ[:, b, :3, 3]
        Po = np.einsum('tji,tkj->tki', R, Pw - t[:, None])           # R^T (p - t)
        c, d, tri, inside = q.closest(Po.reshape(-1, 3))
        c, d, tri, inside = c.reshape(T, K, 3), d.reshape(T, K), tri.reshape(T, K), inside.reshape(T, K)
        n_in = -q.fn[tri]                                               # inward
        flip = (~inside) & (d > 0.002) & ((n_in * (c - Po)).sum(-1) < 0)
        n_in[flip] *= -1.0
        flips.append(float(flip[d < a.contact_thr].mean()) if (d < a.contact_thr).any() else 0.0)
        cw = np.einsum('tij,tkj->tki', R, c) + t[:, None]
        nw = np.einsum('tij,tkj->tki', R, n_in)
        upd = d < best_d
        best_d[upd], best_b[upd], best_c[upd], best_n[upd] = d[upd], b, cw[upd], nw[upd]
    active = (best_d < thr[None]) & (best_b >= 0)
    if gates is not None:
        active &= gates[np.clip(best_b, 0, B - 1), np.arange(T)[:, None]]
    for k in range(K):
        active[:, k] = deflicker(active[:, k], a.min_run)
    nrm = best_n / np.maximum(np.linalg.norm(best_n, axis=-1, keepdims=True), 1e-12)
    pos = np.where(active[..., None], best_c, 0.0)
    nrm = np.where(active[..., None], nrm, 0.0)
    pid = np.where(active, best_b + 1, 0).astype(np.int32)
    return pos, nrm, pid, active, best_d, flips


# ======================================================================== validation (FlashCHORD venv)
VALIDATE = r'''
import json, sys
import numpy as np
p, do_scene, fps = sys.argv[1], sys.argv[2] == "1", float(sys.argv[3])
from flash_chord.data.loader import load_reference
from flash_chord.assets.registry import support_usda_for_reference
r = load_reference(p, control_fps=fps, motion_speed=1.0)
out = dict(num_frames=int(r.num_frames), fps=float(r.fps), source_fps=float(r.metadata.source_fps),
           resampled=bool(r.metadata.is_resampled), sequence_id=r.metadata.sequence_id, robot_name=r.metadata.robot_name,
           support=str(support_usda_for_reference(r)), objects=list(r.object_body_names()),
           urdfs=[str(x.urdf_path) for x in r.object_assets()],
           object_z_range=[float(r.object_body_pos_w()[..., 2].min()), float(r.object_body_pos_w()[..., 2].max())])
for s in r.sides:
    out[s] = dict(contact_active_frac=float(np.mean(r.contact_active(s))), n_fingers=len(r.finger_joint_names(s)),
                  wrist_min=np.min(r.wrist_pos_w(s), 0).round(3).tolist(), wrist_max=np.max(r.wrist_pos_w(s), 0).round(3).tolist())
if do_scene:
    import warp as wp
    from flash_chord.scene.setup import setup_scene
    from flash_chord.embodiments.sharpa_hands import SharpaHands
    from flash_chord.scene.collision import CollisionPolicy
    with wp.ScopedDevice("cuda:0"):
        st = setup_scene(parquet=p, control_fps=fps, motion_speed=1.0, embodiment=SharpaHands(),
                         collision=CollisionPolicy(robot_scope="all", hand_self_collision=True, robot_object_collision=True,
                                                   robot_support_collision=False, ground=True),
                         world_count=1, include_support=True, decompose_objects=True)
    out["scene"] = dict(ok=True, support_usda=str(st.support_usda), num_frames=int(st.reference.num_frames))
print("VALIDATION " + json.dumps(out))
'''


# ======================================================================== main
def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--ep', type=int, required=True)
    p.add_argument('--t3', default='/content/t3')
    p.add_argument('--poses', default=None, help='default /content/perc2/epN/poses.npz')
    p.add_argument('--depth', default=None, help='default /content/perc/epN/depths_fs0.5.npy')
    p.add_argument('--hands', default=None, help='default OUT/hands.npz')
    p.add_argument('--out', default=None, help='default /content/refs/epN')
    p.add_argument('--seq', default=None, help='sequence_id (default t3_epNNN)')
    p.add_argument('--assets', default=os.environ.get('ASSETS') or None,
                   help='object assets root (mesh/<obj>/<obj>.glb, urdf/<obj>_rigid.urdf); default --t3 = the public '
                        'scans; route A uses our own (pipeline/make_assets.py; default from env ASSETS)')
    p.add_argument('--split', choices=['public', 'eval'], default=os.environ.get('SPLIT', 'public'),
                   help='eval: object names from the kit roster (default from env SPLIT)')
    p.add_argument('--v2d', default='/content/v2d')
    p.add_argument('--fc_python', default='/content/v2d/robotic_grounding/flash_chord/.venv/bin/python')
    p.add_argument('--fps', type=float, default=20.0)
    # table
    p.add_argument('--table_z', type=float, default=0.60)
    p.add_argument('--table_radius', type=float, default=0.45, help='support disc radius when --table_fit fails or is off')
    p.add_argument('--table_fit', type=int, default=1, help='1: support disc (centre, radius) measured from frame-0 depth')
    p.add_argument('--table_height', type=float, default=0.02)
    p.add_argument('--ring_in', type=int, default=10)
    p.add_argument('--ring_out', type=int, default=90)
    p.add_argument('--plane_thr', type=float, default=0.006)
    p.add_argument('--plane_iters', type=int, default=1000)
    p.add_argument('--support_max', type=float, default=0.05,
                   help='abort if the lowest frame-0 object bottom is more than this above the table (m)')
    p.add_argument('--support_tol', type=float, default=0.03,
                   help='abort if it is more than this below the table (m); also the plane-pick tolerance')
    p.add_argument('--support_fallback', type=int, default=1,
                   help='when no plane passes the support check: the candidate supporting most objects, objects that '
                        'start inside the table lifted onto it (2026-10-24, eval 30)')
    p.add_argument('--snap', choices=['none', 'lowest', 'per_object'], default='per_object',
                   help='lowest: move the plane to the lowest object bottom at frame 0; per_object: lift/lower each '
                        'object whose frame-0 bottom is within SNAP_MAX of the plane onto it (whole trajectory)')
    p.add_argument('--snap_max', type=float, default=0.02)
    p.add_argument('--start_overlap', type=float, default=0.0,
                   help='lift an object that starts inside another (higher bottom = upper) by the least that clears it, '
                        'at most this (m; 2026-10-24, eval 1 lid 7.6 mm inside the pot); 0 = off')
    # hands
    p.add_argument('--min_valid_frac', type=float, default=0.10, help='park a side with fewer valid frames')
    p.add_argument('--gap_fill', choices=['attach', 'hold'], default='attach')
    p.add_argument('--hand_sep', type=float, default=0.04,
                   help='minimum gap between any left and any right hand joint (m); the robot hands are larger than '
                        'human hands and overlapped at reset in ep24 (2026-10-21); <= 0: off')
    p.add_argument('--lead_in', type=int, default=10,
                   help='a hand first seen at frame t1 > 0 comes in from 15 cm out and 10 cm up over the LEAD_IN frames '
                        'before t1 instead of holding its first pose from frame 0')
    p.add_argument('--lead_in_speed', type=float, default=0.2,
                   help='largest lead-in approach speed (m/s); a hand first seen early starts nearer (2026-10-23, '
                        'ep35: 18 cm in 6 frames left the simulated wrist 16 cm behind); <= 0: no limit')
    p.add_argument('--attach_dist', type=float, default=0.03)
    # retarget
    p.add_argument('--mano_to_robot_scale', type=float, default=1.2)
    p.add_argument('--wrist_cost', type=float, default=None,
                   help='E2S IK position cost of the wrist (hand_C_MC); NVIDIA default 0.2 (fingertips 1.0)')
    p.add_argument('--wrist_ori_cost', type=float, default=None, help='E2S IK orientation cost of the wrist (default 0.2)')
    p.add_argument('--depenetrate', type=float, default=0.006,
                   help='keep hand joint centres this far outside objects and above the table (m; 0 = off)')
    p.add_argument('--bone_norm', action='store_true', help='fix bone lengths to the episode median (normalize_bones)')
    p.add_argument('--hand_scale', type=float, default=1.0, help='with --bone_norm: multiply the median bone lengths')
    p.add_argument('--warmup', type=int, default=10, help='copies of frame 0 prepended for the IK, dropped after')
    p.add_argument('--e2s_args', default='', help='extra ego_recon_to_sharpa.py flags, e.g. "--smooth_reference"')
    p.add_argument('--skip_e2s', action='store_true', help='reuse OUT/e2s_raw (redo contacts + validation only)')
    # contacts
    p.add_argument('--contact_thr', type=float, default=0.018)
    p.add_argument('--palm_extra', type=float, default=0.010)
    p.add_argument('--min_run', type=int, default=2)
    p.add_argument('--no_motion_gate', action='store_true')
    p.add_argument('--gate_win', type=int, default=7)
    p.add_argument('--gate_disp', type=float, default=0.01)
    p.add_argument('--gate_rot_deg', type=float, default=5.0)
    p.add_argument('--gate_pad', type=int, default=20)
    # validation
    p.add_argument('--no_validate', action='store_true')
    p.add_argument('--no_scene_check', action='store_true')
    a = p.parse_args()
    n = a.ep
    a.poses = a.poses or f'/content/perc2/ep{n}/poses.npz'
    a.depth = a.depth or f'/content/perc/ep{n}/depths_fs0.5.npy'
    a.out = a.out or f'/content/refs/ep{n}'
    a.hands = a.hands or f'{a.out}/hands.npz'
    a.seq = a.seq or f't3_ep{n:03d}'
    return a


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '_e2s':
        return e2s_entry(sys.argv[1:])
    a = parse_args()
    import trimesh
    os.makedirs(a.out, exist_ok=True)
    pin = install_compat(a.v2d)
    lay = sharpa_layout(pin, a.v2d)
    MSD = patch_logger(lay, slot_names=True)
    from robotic_grounding.retarget.naming import make_usd_safe
    from robotic_grounding.retarget.params import MANO_HAND_LINKS
    log(f'Sharpa layout via pinocchio {pin.__version__}: frames {lay["n_frames"]}, fingers {lay["n_fingers"]}, tasks {lay["n_tasks"]}')
    summary = dict(ep=a.ep, seq=a.seq, fps=a.fps)

    # ---------------- objects
    names = load_names(a.t3, a.ep, a.split)
    B = len(names)
    P = np.load(a.poses)
    W_C = P['world_T_cam'].astype(np.float64)
    T = len(W_C)
    cam_T = {}
    for nm in names:
        if f'cam_T_{nm}' not in P.files:
            raise SystemExit(f'poses.npz lacks cam_T_{nm}')
        cam_T[nm] = P[f'cam_T_{nm}'].astype(np.float64)
        if len(cam_T[nm]) != T:
            raise SystemExit(f'cam_T_{nm} has {len(cam_T[nm])} frames, world_T_cam has {T}')
    A = a.assets or a.t3                     # route A: our own meshes and URDFs (make_assets.py), same layout
    vis_p = {nm: visual_mesh_path(A, nm) for nm in names}
    con_p = {nm: contact_mesh_path(A, nm) for nm in names}
    urdf_p = {nm: f'{A}/urdf/{nm}_rigid.urdf' for nm in names}
    for nm in names:
        for pth in (vis_p[nm], con_p[nm], urdf_p[nm]):
            if not os.path.exists(pth):
                raise SystemExit(f'missing asset {pth}')
        for msg in check_urdf(urdf_p[nm], vis_p[nm], con_p[nm]):
            log(f'WARNING urdf {nm}: {msg}')
    vis = {nm: trimesh.load(vis_p[nm], force='mesh') for nm in names}
    con = {nm: trimesh.load(con_p[nm], force='mesh') for nm in names}
    radius = [float(np.linalg.norm(np.asarray(vis[nm].vertices) - np.asarray(vis[nm].vertices).mean(0), axis=1).max())
              for nm in names]
    log(f'ep{a.ep}: T={T}, objects {names}, radii {np.round(radius, 3).tolist()}, '
        f'watertight(contact mesh) {[bool(con[nm].is_watertight) for nm in names]}')

    # ---------------- (a) table frame
    KR = rectified_K(f'{a.t3}/calib.json')
    depth0 = np.load(a.depth, mmap_mode='r')[0]
    n, d, inl_frac, npts, rms = fit_table(depth0, KR, W_C[0], {nm: cam_T[nm][0] for nm in names}, vis, a)
    cam_up = -W_C[0][:3, 1]                                                  # image-up direction in world
    log(f'table plane: {npts} ring points, inliers {inl_frac:.2f}, rms {rms * 1000:.1f} mm, '
        f'angle(normal, camera image-up) {np.degrees(np.arccos(np.clip(n @ cam_up, -1, 1))):.1f} deg, '
        f'camera height above table {(n @ W_C[0][:3, 3] + d):.3f} m')
    OBJw = np.stack([np.stack([W_C[t] @ cam_T[nm][t] for nm in names]) for t in range(T)])   # (T,B,4,4) world
    centroid = np.mean([OBJw[0, b, :3, :3] @ np.asarray(vis[nm].vertices).mean(0) + OBJw[0, b, :3, 3]
                        for b, nm in enumerate(names)], 0)
    T_tab = table_frame(n, d, W_C[0], centroid, a.table_z)

    def obj_in_table(Tt):
        return np.einsum('ij,tbjk->tbik', Tt, OBJw)

    def bottoms(O):
        return np.array([(np.asarray(vis[nm].vertices) @ O[0, b, :3, :3].T + O[0, b, :3, 3])[:, 2].min() - a.table_z
                         for b, nm in enumerate(names)])

    OBJ = obj_in_table(T_tab)
    h = bottoms(OBJ)
    log(f'table plane candidates (fraction of ring points, lowest object point above it in m, tilt vs the first): '
        f'{a._plane_cands}')
    log(f'frame-0 object bottoms above the fitted table (cm): {dict(zip(names, np.round(h * 100, 2).tolist()))}')
    lifted = np.zeros(B)
    if not -a.support_tol <= h.min() <= a.support_max and a.support_fallback:
        # Only on this failure path (eval 30, 2026-10-24: the dominant plane was the floor, 54 cm under the objects; the
        # table candidate had the rack 1.7 cm and the sweeper 7.1 cm inside it): take the near-parallel candidate under
        # which most objects start within the allowed band, then lift objects that start inside the table onto it
        # (a body cannot start inside the table; whole trajectory shifted). Episodes that pass the check are unchanged.
        alt = []
        for c in a._plane_full:
            if c['tilt'] > 25:
                continue
            Tt = table_frame(c['n'], c['d'], W_C[0], centroid, a.table_z); hh = bottoms(obj_in_table(Tt))
            nin = int(((hh >= -a.support_tol) & (hh <= a.support_max)).sum())
            alt.append((nin, -float(np.abs(hh).sum()), c, Tt, hh))
        alt.sort(key=lambda x: x[:2], reverse=True)
        if alt and alt[0][0] > 0:
            _, _, c, T_tab, hh = alt[0]; n, d = c['n'], c['d']; OBJ = obj_in_table(T_tab)
            for b in range(B):
                if hh[b] < -a.support_tol:
                    lifted[b] = -hh[b]; OBJ[:, b, 2, 3] += lifted[b]
            h = bottoms(OBJ)
            log(f'support fallback: plane {dict(frac=round(c["frac"], 4), tilt=round(c["tilt"], 2))} supports {alt[0][0]} of {B} '
                f'objects; lifted onto the table (cm) {dict(zip(names, np.round(lifted * 100, 2).tolist()))}; bottoms now (cm) '
                f'{dict(zip(names, np.round(h * 100, 2).tolist()))}')
    if not -a.support_tol <= h.min() <= a.support_max:
        raise SystemExit(f'no support plane under the objects: the lowest object bottom is {h.min() * 100:.1f} cm above '
                         f'the fitted table (allowed {-a.support_tol * 100:.0f} to {a.support_max * 100:.0f} cm); '
                         f'the simulated objects would fall or start inside the table')
    shifts = np.zeros(B)
    if a.snap == 'lowest' and abs(h.min()) <= a.snap_max:
        T_tab[2, 3] -= h.min()
        OBJ = obj_in_table(T_tab)
        log(f'snap=lowest: table frame shifted by {-h.min() * 100:.2f} cm')
    elif a.snap == 'per_object':
        for b in range(B):
            if abs(h[b]) <= a.snap_max:
                shifts[b] = -h[b]
                OBJ[:, b, 2, 3] += shifts[b]
        log(f'snap=per_object: z shifts (cm) {dict(zip(names, np.round(shifts * 100, 2).tolist()))}')
    elif a.snap != 'none':
        log(f'WARNING: snap={a.snap} skipped, bottom offset {h.min() * 100:.1f} cm > snap_max')
    overlap = []
    if a.start_overlap > 0 and B > 1:
        olift, overlap = start_overlap_lift(OBJ, names, vis, con, a.start_overlap, a.table_z)
        shifts = shifts + olift
        log(f'start overlap (cap {a.start_overlap * 100:.0f} cm): {overlap if overlap else "none"}')
    h2 = bottoms(OBJ)
    obj_pos = OBJ[:, :, :3, 3]
    obj_wxyz = continuous(wxyz_from_R(OBJ[:, :, :3, :3]))
    log(f'object travel (cm): {dict(zip(names, np.round(np.linalg.norm(obj_pos - obj_pos[:1], axis=-1).max(0) * 100, 1).tolist()))}')
    disc = (0.0, 0.0, a.table_radius)
    if a.table_fit:
        dm = table_disc(depth0, KR, T_tab, a.table_z)
        if dm is not None:
            reach = float((np.linalg.norm(obj_pos[0, :, :2] - dm[:2], axis=-1) + np.array(radius) * 0.5).max())
            disc = (dm[0], dm[1], float(np.clip(max(dm[2], reach), 0.15, 0.6)))
        log(f'table disc measured from frame-0 depth: centre ({disc[0]:.3f}, {disc[1]:.3f}) m, radius {disc[2]:.3f} m '
            f'(was a {a.table_radius} m disc at the object centroid)')
    np.savez(f'{a.out}/table_frame.npz', T_table_from_world=T_tab, plane_n=n, plane_d=d, names=np.array(names),
             object_z_shift=shifts + lifted, table_z=a.table_z, table_disc=np.array(disc))
    summary['table'] = dict(inlier_frac=inl_frac, rms_mm=rms * 1000, bottoms_cm=(h * 100).tolist(),
                            bottoms_after_cm=(h2 * 100).tolist(), snap=a.snap, shifts_cm=(shifts * 100).tolist(), support_fallback_lift_cm=(lifted * 100).tolist(),
                            start_overlap=overlap)

    # ---------------- (b) hands
    Hn = np.load(a.hands)
    queries = [BodyQuery(con[nm]) for nm in names]
    J, Q, ferr, hinfo = {}, {}, {}, {}
    for s in SIDES:
        Jw = Hn[f'joints_{s}'].astype(np.float64)
        valid = Hn[f'valid_{s}'].astype(bool)
        if len(Jw) != T:
            raise SystemExit(f'hands.npz joints_{s} has {len(Jw)} frames, poses have {T}')
        Js = Jw @ T_tab[:3, :3].T + T_tab[:3, 3]
        if a.bone_norm and valid.sum() >= 5:
            Js, Lb = normalize_bones(Js, valid, a.hand_scale)
            log(f'{s}: bone lengths fixed to the episode median x {a.hand_scale} (wrist->middle MCP {Lb[9] * 100:.1f} cm, '
                f'middle finger {Lb[10:13].sum() * 100:.1f} cm)')
        n_valid = int(valid.sum())
        if n_valid < max(10, a.min_valid_frac * T):
            c = obj_pos.reshape(-1, 3).mean(0)
            sgn = -1.0 if s == 'right' else 1.0
            for extra in np.arange(0.0, 0.61, 0.1):
                pw = np.array([c[0] - 0.30, c[1] + sgn * (0.35 + extra), a.table_z + 0.25])
                if np.linalg.norm(obj_pos - pw, axis=-1).min() > 0.30:
                    break
            Rpark = np.column_stack([[-1.0, 0, 0], [0, 0, 1.0], [0, 1.0, 0]])   # fingers +x, dorsal up
            tmpl = TEMPLATE_RIGHT * (np.array([1, 1, -1.0]) if s == 'left' else 1.0)
            Js = np.repeat((pw + tmpl @ Rpark.T)[None], T, 0)
            hinfo[s] = dict(mode='parked', valid_frames=n_valid, park_pos=pw.tolist())
            log(f'{s}: only {n_valid} valid frames -> parked at {np.round(pw, 3).tolist()}')
        else:
            Js, notes = fill_invalid(Js, valid, OBJ, queries, a)
            hinfo[s] = dict(mode='tracked', valid_frames=n_valid, fills=notes)
            log(f'{s}: {n_valid}/{T} valid frames; invalid runs (start, end, from, anchor body): {notes}')
        if not np.isfinite(Js).all():
            raise SystemExit(f'non-finite {s} joints')
        if a.depenetrate > 0 and hinfo[s]['mode'] == 'tracked':
            Js, pen = depenetrate(Js, OBJ, queries, a.table_z, a.depenetrate, disc)
            hinfo[s]['depenetrate'] = pen
            log(f'{s}: depenetrate (clearance {a.depenetrate * 1000:.0f} mm): {pen}')
        R = hand_rotations(Js, s)
        J[s] = Js
        Q[s] = continuous(wxyz_from_R(R))
        e = Hn[f'rms_px_{s}'] if f'rms_px_{s}' in Hn.files else np.zeros(T)
        ferr[s] = np.nan_to_num(np.asarray(e, float), nan=0.0)
        ps = palmar_score(Js, R)
        below = float((Js[..., 2] < a.table_z - 0.02).mean())
        hl = np.linalg.norm(Js[:, 12] - Js[:, 0], axis=1)
        hinfo[s].update(palmar_score_median=float(np.median(ps)), palmar_negative_frac=float((ps < -0.005).mean()),
                        below_table_frac=below, wrist_to_middle_tip_cm=float(np.median(hl) * 100))
        log(f'{s}: palmar-flexion score median {np.median(ps) * 1000:+.1f} mm (negative => chirality/handedness '
            f'suspect; neg. frac {(ps < -0.005).mean():.2f}), joints below table {below:.2f}, '
            f'wrist->middle tip {np.median(hl) * 100:.1f} cm')
    if a.hand_sep > 0 and all(hinfo[s]['mode'] == 'tracked' for s in SIDES):
        off, sep = separate_hands(J, {s: Hn[f'valid_{s}'].astype(bool) for s in SIDES},
                                  {s: Hn[f'measured_{s}'].astype(bool) for s in SIDES}, a.hand_sep, a.lead_in,
                                  a.lead_in_speed / a.fps)
        for s in SIDES:
            J[s] = J[s] + off[s][:, None, :]                       # rigid shifts: the rotations Q are unchanged
            if a.depenetrate > 0:
                J[s], _ = depenetrate(J[s], OBJ, queries, a.table_z, a.depenetrate, disc)
            hinfo[s]['separation'] = sep[s]
        log(f'hand separation (min joint gap {a.hand_sep * 100:.1f} cm, lead-in {a.lead_in} frames): {sep}')
    summary['hands'] = hinfo

    # ---------------- write the loaded ManoSharpaData
    loaded_root = os.path.join(a.out, 'loaded')
    raw_root = os.path.join(a.out, 'e2s_raw')
    final_root = os.path.join(a.out, 'processed')
    W = a.warmup
    obj_name = '__'.join(names)
    if not a.skip_e2s:
        data = MSD(sequence_id=a.seq, raw_motion_file=f'{a.poses}|{a.hands}', robot_name=ROBOT, fps=float(a.fps),
                   mano_flat_hand_mean=True, mano_center_idx=None, mano_to_robot_scale=float(a.mano_to_robot_scale),
                   mano_right_betas=[0.0] * 10, mano_left_betas=[0.0] * 10, mano_link_names=list(MANO_HAND_LINKS.keys()),
                   right_robot_finger_joint_names=[], right_robot_frame_names=[], right_robot_frame_task_names=[],
                   left_robot_finger_joint_names=[], left_robot_frame_names=[], left_robot_frame_task_names=[],
                   object_name=obj_name, safe_object_name=make_usd_safe(obj_name), object_body_names=list(names),
                   safe_object_body_names=[make_usd_safe(nm) for nm in names],
                   object_mesh_paths=[vis_p[nm] for nm in names], object_urdf_paths=[urdf_p[nm] for nm in names],
                   object_mesh_radius=radius, contact_slot_names=list(CONTACT_SLOT_NAMES))
        z16 = np.zeros((N_SLOTS, 3)).tolist()
        i16 = [0] * N_SLOTS
        z45 = [0.0] * 45
        obj_rv = rotvec_from_wxyz(obj_wxyz[:, 0]).reshape(T, 3)
        gorient = {s: rotvec_from_wxyz(Q[s][:, 0]).reshape(T, 3) for s in SIDES}
        for t in [0] * W + list(range(T)):
            kw = {}
            for s in SIDES:
                kw[f'mano_{s}_trans'] = J[s][t, 0].tolist()
                kw[f'mano_{s}_global_orient'] = gorient[s][t].tolist()   # wrist anatomical frame (not MANO's)
                kw[f'mano_{s}_finger_pose'] = z45
                kw[f'mano_{s}_joints'] = J[s][t].tolist()
                kw[f'mano_{s}_joints_wxyz'] = Q[s][t].tolist()
                kw[f'mano_{s}_fitting_err'] = float(ferr[s][t])
                for f in ('link_contact_positions', 'link_contact_normals', 'object_contact_positions',
                          'object_contact_normals'):
                    kw[f'mano_{s}_{f}'] = z16
                kw[f'mano_{s}_object_contact_part_ids'] = i16
            kw['object_root_position'] = obj_pos[t, 0].tolist()
            kw['object_root_axis_angle'] = obj_rv[t].tolist()
            kw['object_body_position'] = obj_pos[t].tolist()
            kw['object_body_wxyz'] = obj_wxyz[t].tolist()
            data.log_timestep(**kw)
        data.save_to_parquet(loaded_root, partition_cols=['sequence_id', 'robot_name'])
        log(f'loaded ManoSharpaData written: {loaded_root} ({T} + {W} warm-up frames)')

    # ---------------- (c) support USDA
    stage = os.path.join(a.out, 'reconstructed_stage')
    os.makedirs(stage, exist_ok=True)
    usda = os.path.join(stage, f'{a.seq}_support.usda')
    hgt, zc = a.table_height, a.table_z - a.table_height / 2
    with open(usda, 'w') as f:
        f.write(f'''#usda 1.0
(
    defaultPrim = "support_surfaces"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "support_surfaces"
{{
    def Cylinder "table" (
        prepend apiSchemas = ["PhysicsCollisionAPI"]
    )
    {{
        uniform token axis = "Z"
        double height = {hgt:.6f}
        color3f[] primvars:displayColor = [(0.6, 0.6, 0.6)]
        double radius = {disc[2]:.6f}
        double3 xformOp:translate = ({disc[0]:.6f}, {disc[1]:.6f}, {zc:.6f})
        uniform token[] xformOpOrder = ["xformOp:translate"]
    }}
}}
''')
    far = float(np.linalg.norm(obj_pos[..., :2] - np.array(disc[:2]), axis=-1).max())
    log(f'support USDA {usda} (objects reach {far:.3f} m from the table centre, radius {disc[2]:.3f})')
    summary['table']['disc'] = list(disc)
    if far > a.table_radius - 0.05:
        log('WARNING: an object comes within 5 cm of the table edge; raise --table_radius')

    # ---------------- (d) E2S
    if not a.skip_e2s:
        cmd = [sys.executable, os.path.abspath(__file__), '_e2s', a.v2d, '--',
               '--input_dir', loaded_root, '--output_dir', raw_root, '--device', 'cpu', '--save',
               '--mano_to_robot_scale', str(a.mano_to_robot_scale), '--sequence_id', a.seq] + shlex.split(a.e2s_args)
        env = dict(os.environ)
        env['PYTHONPATH'] = rg_src(a.v2d) + (':' + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
        if a.wrist_cost is not None:
            env['E2S_WRIST_COST'] = str(a.wrist_cost)
        if a.wrist_ori_cost is not None:
            env['E2S_WRIST_ORI_COST'] = str(a.wrist_ori_cost)
        log('running E2S:', ' '.join(cmd))
        subprocess.run(cmd, check=True, env=env, cwd=os.path.join(a.v2d, 'robotic_grounding'))

    # ---------------- (e) post-process: drop warm-up, contacts, write final
    data = MSD.from_parquet(raw_root, filters=[('sequence_id', '=', a.seq)])
    nt = len(data.mano_right_trans)
    Wd = nt - T
    if Wd < 0:
        raise SystemExit(f'E2S output has {nt} frames < T={T}')
    for name, _typ, _py, ts in MSD._field_specs:
        v = getattr(data, name)
        if ts and v is not None and len(v):
            if len(v) != nt:
                raise SystemExit(f'time-series {name} has {len(v)} frames, expected {nt}')
            setattr(data, name, v[Wd:])
    log(f'E2S output: {nt} frames, dropped {Wd} warm-up frames')
    gates = None
    gate_info = {}
    if not a.no_motion_gate:
        gl = []
        for b, nm in enumerate(names):
            g, win = motion_gate(OBJ[:, b], a)
            gl.append(g)
            gate_info[nm] = win
        gates = np.stack(gl)
        log(f'contact motion gate windows (frames): {gate_info}')
    cstats = {}
    for s in SIDES:
        frames = np.asarray(getattr(data, f'robot_{s}_frames'), np.float64)
        fn = list(getattr(data, f'{s}_robot_frame_names'))
        pos, nrm, pid, act, dist, flips = compute_contacts(frames, fn, s, OBJ, queries, gates, a)
        setattr(data, f'mano_{s}_object_contact_positions', pos.astype(np.float32).tolist())
        setattr(data, f'mano_{s}_object_contact_normals', nrm.astype(np.float32).tolist())
        setattr(data, f'mano_{s}_object_contact_part_ids', pid.tolist())
        per_body = {nm: float((pid == b + 1).any(1).mean()) for b, nm in enumerate(names)}
        cstats[s] = dict(frames_with_contact=float(act.any(1).mean()), slots_active_mean=float(act.sum(1).mean()),
                         per_body_frame_frac=per_body, normal_flip_frac=flips,
                         min_probe_dist_median_cm=float(np.median(dist.min(1)) * 100))
        log(f'{s} contacts: frames with contact {act.any(1).mean():.2f}, mean active slots {act.sum(1).mean():.2f}, '
            f'per body {per_body}, local normal flips {np.round(flips, 3).tolist()}')
    summary['contacts'] = cstats
    data.contact_slot_names = list(CONTACT_SLOT_NAMES)              # E2S's kit class dropped it from e2s_raw
    data.fps = float(a.fps)
    data.mano_to_robot_scale = float(a.mano_to_robot_scale)
    data.save_to_parquet(final_root, partition_cols=['sequence_id', 'robot_name'])
    task_dir = os.path.join(final_root, f'sequence_id={a.seq}', f'robot_name={ROBOT}')
    pq_files = [f for f in os.listdir(task_dir) if f.endswith('.parquet')]
    if len(pq_files) != 1:
        raise SystemExit(f'{task_dir} must contain exactly one parquet, found {pq_files}')
    log(f'final reference: {task_dir}/{pq_files[0]}')

    # ---------------- (f) IK report
    ik = {}
    for s in SIDES:
        E = np.asarray(getattr(data, f'robot_{s}_frame_task_errors'), float) * 1000
        tn = list(getattr(data, f'{s}_robot_frame_task_names'))
        it = np.asarray(getattr(data, f'robot_{s}_num_optimization_iterations'))
        ik[s] = {t_: dict(median_mm=float(np.median(E[:, i])), p95_mm=float(np.percentile(E[:, i], 95)),
                          max_mm=float(E[:, i].max()), frame0_mm=float(E[0, i])) for i, t_ in enumerate(tn)}
        log(f'{s} IK frame-task position error (mm) median / p95 / max / frame0; iterations median {np.median(it):.0f} max {it.max()}')
        for i, t_ in enumerate(tn):
            log(f'    {t_:28s} {np.median(E[:, i]):7.1f} {np.percentile(E[:, i], 95):7.1f} {E[:, i].max():7.1f} {E[0, i]:7.1f}')
        wr = np.asarray(getattr(data, f'robot_{s}_wrist_position'), float)
        steps = np.linalg.norm(np.diff(wr, axis=0), axis=1) * 100
        log(f'    robot wrist travel {np.linalg.norm(wr - wr[0], axis=1).max():.3f} m, '
            f'max step {steps.max():.1f} cm/frame')
        summary.setdefault('wrist', {})[s] = dict(travel_m=float(np.linalg.norm(wr - wr[0], axis=1).max()),
                                                  max_step_cm=float(steps.max()), p99_step_cm=float(np.percentile(steps, 99)),
                                                  steps_over_5cm=int((steps > 5).sum()))
    summary['ik'] = ik

    # ---------------- (f) FlashCHORD validation
    if not a.no_validate:
        fc_dir = os.path.join(a.v2d, 'robotic_grounding', 'flash_chord')
        env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
        env.update(MUJOCO_GL='egl', XLA_PYTHON_CLIENT_PREALLOCATE='false')
        r = subprocess.run([a.fc_python, '-c', VALIDATE, task_dir, '0' if a.no_scene_check else '1', str(a.fps)],
                           cwd=fc_dir, env=env, capture_output=True, text=True)
        line = [ln for ln in r.stdout.splitlines() if ln.startswith('VALIDATION ')]
        if r.returncode != 0 or not line:
            print(r.stdout[-4000:], r.stderr[-6000:], flush=True)
            summary['validation'] = dict(ok=False, returncode=r.returncode)
            log('VALIDATION FAILED (see above)')
        else:
            v = json.loads(line[-1][len('VALIDATION '):])
            summary['validation'] = dict(ok=True, **v)
            log('VALIDATION OK:', json.dumps(v))
            if v['num_frames'] != T or abs(v['fps'] - a.fps) > 1e-6:
                log(f'WARNING: FlashCHORD sees {v["num_frames"]} frames at {v["fps"]} fps (expected {T} at {a.fps})')
    summary['task_parquet'] = task_dir
    summary['support_usda'] = usda
    json.dump(summary, open(os.path.join(a.out, 'ref_summary.json'), 'w'), indent=1, default=str)
    if not summary.get('validation', {}).get('ok', True):
        raise SystemExit('FlashCHORD validation failed: do not train on this reference')
    log(f'DONE. Train with task.parquet={task_dir} task.motion_speed=1.0')


if __name__ == '__main__':
    main()
