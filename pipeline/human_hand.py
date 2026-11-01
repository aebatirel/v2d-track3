"""Human capsule hand for the physics study (2026-10-30; docs/research/physics-2026-10-30/human-hand-models.md, option b).

A 22-DoF human hand with the Sharpa Wave's joint and link names (thumb CMC FE/AA, MCP FE/AA, IP; index-ring MCP FE/AA,
PIP, DIP; pinky CMC, MCP FE/AA, PIP, DIP), so FlashCHORD's SharpaHands class loads it unchanged through its
left/right_urdf_path config and every tool that reads `robot_<side>_finger_joints` by name keeps working. Geometry: one
capsule per phalanx, two pad spheres per fingertip, metacarpal capsules and a box for the palm (Newton reads URDF
<capsule>). The root link is the MediaPipe wrist keypoint with mkref.hand_rotations' wrist frame (x proximal, y dorsal,
z radial on the right hand, ulnar on the left), so the wrist pose is read straight off the perceived keypoints.
Zero pose: straight fingers along the template's proximal-phalanx directions. Flexion is positive: each chain's
flexion axis is +-z of its frame, the sign chosen so that a positive angle curls the bone toward the palm (-y root).

Size variants:
  A  mkref.TEMPLATE_RIGHT as is (an adult relaxed hand: wrist -> middle tip 18.4 cm, index 8.5 cm);
  P  the same directions with the bone lengths of the reference's perceived hand (episode median per side).

  human_hand.py urdf {A|P} OUT_DIR [--ref REF.parquet] [--name NAME] [--wrist_kp 400]
      writes OUT_DIR/{left,right}_human.urdf, OUT_DIR/hand.json (template, lengths, radii) and OUT_DIR/NAME.yaml, an
      embodiment config for FlashCHORD's configs/embodiment/ (absolute URDF paths).
  human_hand.py ref HAND_DIR IN.parquet OUT.parquet [--squeeze RAD --holds GRASP_LOCK.json]
      per frame: wrist pose from the perceived keypoints (mano_<side>_joints) and the 22 joint angles that best match
      the perceived bone directions (bounded least squares, warm-started); writes them as the robot_<side>_* columns.
      --squeeze (2026-10-30, [H-squeeze]): the grip force video cannot show. During each hold phase of a
      pipeline/grasp_lock.py *_grasp_lock.json (hand, start..end), the holding hand's flexion targets (finger MCP_FE,
      PIP, DIP; thumb MCP_FE, IP) get +RAD (toward the palm), ramped in and out over 5 frames, so the PD presses the
      fingers into the object instead of resting where the keypoints put them.
No ground truth is read.
"""
import argparse, json, os, sys
import numpy as np, pyarrow as pa, pyarrow.parquet as pq
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mkref  # noqa: E402  (numpy-only at import: TEMPLATE_RIGHT, PARENT, hand_rotations)

SIDES = ('right', 'left')
FINGERS = {'index': 5, 'middle': 9, 'ring': 13, 'pinky': 17}       # MCP keypoint; PIP, DIP, tip follow
# capsule radii (m) for variant A (review table 6.3: MyoHand / HOIC); variant P scales them with finger length
RADII = {'index': (0.009, 0.008, 0.0075), 'middle': (0.009, 0.008, 0.0075), 'ring': (0.0085, 0.0075, 0.007),
         'pinky': (0.008, 0.007, 0.006), 'thumb': (0.011, 0.0095, 0.0075)}          # thumb: MC, PP, DP
MASS = {'palm': 0.25, 'thumb_MC': 0.035, 'pinky_MC': 0.02, 'PP': 0.015, 'MP': 0.008, 'DP': 0.005}
PAD_R = 0.004
# thumb limits are symmetric: its anatomical axes are only approximated by the template frame (first pass)
LIM = {'MCP_FE': (-0.52, 1.57), 'MCP_AA': (-0.45, 0.45), 'PIP': (-0.10, 1.83), 'DIP': (-0.17, 1.40),
       'thumb_CMC_FE': (-1.0, 1.0), 'thumb_CMC_AA': (-1.0, 1.0), 'thumb_MCP_FE': (-1.0, 1.0),
       'thumb_MCP_AA': (-0.5, 0.5), 'thumb_IP': (-1.2, 1.2), 'pinky_CMC': (-0.10, 0.50)}
# PD gains / effort (N m) per joint class (review 3.2 / 6.5: index MCP/PIP/DIP effort 2.5/1.5/0.6, graded kp, kd ~0.5 crit)
GAINS = {'MCP': (2.0, 0.14, 2.5), 'PIP': (1.2, 0.11, 1.5), 'DIP': (0.5, 0.07, 0.6), 'thumb_CMC': (2.0, 0.14, 2.5),
         'thumb_MCP': (1.2, 0.11, 1.5), 'thumb_IP': (0.5, 0.07, 0.8), 'pinky_CMC': (1.0, 0.10, 1.0)}


def unit(v):
    return v / max(np.linalg.norm(v), 1e-12)


def frame(x, zref):
    x = unit(x); z = unit(zref - x * (zref @ x)); return np.column_stack([x, np.cross(z, x), z])


def rot(axis, th):
    return Rot.from_rotvec(np.asarray(axis, float) * th).as_matrix()


# ---------------------------------------------------------------------------------------------------- template / model
def template(side, variant, J=None):
    """21 keypoints of the zero-pose hand in its root frame."""
    TA = mkref.TEMPLATE_RIGHT * (np.array([1, 1, -1.0]) if side == 'left' else 1.0)
    if variant == 'A':
        return TA.copy(), None
    L = np.median(np.linalg.norm(J[:, 1:] - J[:, mkref.PARENT[1:]], axis=-1), 0)       # (20,) perceived bone lengths
    T = np.zeros((21, 3))
    for k in range(1, 21):
        p = mkref.PARENT[k]; T[k] = T[p] + L[k - 1] * unit(TA[k] - TA[p])
    return T, L


def flex_sign(F):
    """+1 or -1: the sign of z for which a positive rotation turns the frame's x toward the palm (-y root)."""
    return 1.0 if (F @ rot([0, 0, 1], 0.1))[:, 0][1] < F[1, 0] else -1.0


def model(T, side):
    """Joint/link layout of the zero pose in the root frame (all frames 3x3 with columns x, y, z)."""
    zl = np.array([0, 0, 1.0])                                     # root z: radial (right) / ulnar (left)
    zthumb = np.array([0, -1.0, 0]) if side == 'right' else np.array([0, 1.0, 0])   # as mkref.hand_rotations
    m = {'fingers': {}}
    for f, k in FINGERS.items():
        F = frame(T[k + 1] - T[k], zl)
        L = [np.linalg.norm(T[k + 1] - T[k]), np.linalg.norm(T[k + 2] - T[k + 1]), np.linalg.norm(T[k + 3] - T[k + 2])]
        m['fingers'][f] = dict(base=T[k].copy(), F=F, L=L, s=flex_sign(F))
    B = T[0] + 0.35 * (T[17] - T[0])                                  # 5th CMC (palm cupping)
    a = unit(T[13] - T[0])
    if np.cross(a, T[17] - B) @ np.array([0, 1.0, 0]) > 0:           # positive angle moves the pinky MCP palmar (-y)
        a = -a
    m['pinky_cmc'] = dict(base=B, axis=a)
    Ft = frame(T[2] - T[1], zthumb)
    m['thumb'] = dict(base=T[1].copy(), F=Ft, s=flex_sign(Ft), L=[np.linalg.norm(T[2] - T[1]), np.linalg.norm(T[3] - T[2]),
                                                  np.linalg.norm(T[4] - T[3])])
    return m


def finger_dirs(fm, th, pre=np.eye(3)):
    """Bone directions (PP, MP, DP) in the root frame for angles (MCP_FE, MCP_AA, PIP, DIP)."""
    z = [0, 0, fm['s']]
    R1 = pre @ fm['F'] @ rot(z, th[0]) @ rot([0, 1, 0], th[1])
    R2 = R1 @ rot(z, th[2]); R3 = R2 @ rot(z, th[3])
    return np.stack([R1[:, 0], R2[:, 0], R3[:, 0]])


def thumb_dirs(tm, th):
    """Bone directions (MC, PP, DP) for (CMC_FE, CMC_AA, MCP_FE, MCP_AA, IP)."""
    z = [0, 0, tm['s']]
    R1 = tm['F'] @ rot(z, th[0]) @ rot([0, 1, 0], th[1])
    R2 = R1 @ rot(z, th[2]) @ rot([0, 1, 0], th[3]); R3 = R2 @ rot(z, th[4])
    return np.stack([R1[:, 0], R2[:, 0], R3[:, 0]])


# ---------------------------------------------------------------------------------------------------------------- URDF
def rpy(R):
    return Rot.from_matrix(R).as_euler('xyz')        # URDF fixed-axis roll, pitch, yaw


def inertial(mass, c, L, r):
    ixx = mass * r * r / 2; iyy = mass * (3 * r * r + L * L) / 12
    return (f'<inertial><origin xyz="{c[0]:.5f} {c[1]:.5f} {c[2]:.5f}" rpy="0 0 0"/><mass value="{mass}"/>'
            f'<inertia ixx="{ixx:.3e}" ixy="0" ixz="0" iyy="{iyy:.3e}" iyz="0" izz="{iyy:.3e}"/></inertial>')


def capsule_x(x0, x1, r, origin=(0, 0, 0)):
    """Capsule along the link x axis from x0 to x1 (Newton's URDF capsule is along z: rotate z -> x)."""
    h = max(x1 - x0, 1e-3)
    return (f'<collision><origin xyz="{origin[0] + (x0 + x1) / 2:.5f} {origin[1]:.5f} {origin[2]:.5f}" '
            f'rpy="0 1.5707963 0"/><geometry><capsule radius="{r:.4f}" height="{h:.4f}"/></geometry></collision>')


def capsule_between(p0, p1, r):
    """Capsule between two points given in the link frame."""
    d = p1 - p0; c = (p0 + p1) / 2; R = frame(d, np.array([0, 1.0, 0]) if abs(unit(d)[1]) < 0.9 else np.array([1.0, 0, 0]))
    Rz = R @ np.array([[0, 0, 1.0], [0, 1.0, 0], [-1.0, 0, 0]])     # capsule z axis along d
    e = rpy(Rz)
    return (f'<collision><origin xyz="{c[0]:.5f} {c[1]:.5f} {c[2]:.5f}" rpy="{e[0]:.5f} {e[1]:.5f} {e[2]:.5f}"/>'
            f'<geometry><capsule radius="{r:.4f}" height="{np.linalg.norm(d):.4f}"/></geometry></collision>')


def link(name, inert='', geoms=''):
    return f'  <link name="{name}">{inert}{geoms}</link>\n'


def tiny(mass=2e-3):
    return f'<inertial><origin xyz="0 0 0" rpy="0 0 0"/><mass value="{mass}"/><inertia ixx="2e-7" ixy="0" ixz="0" iyy="2e-7" iyz="0" izz="2e-7"/></inertial>'


def joint(name, parent, child, xyz=(0, 0, 0), R=np.eye(3), axis=(0, 0, 1), lim=None, jtype='revolute'):
    e = rpy(R)
    s = (f'  <joint name="{name}" type="{jtype}"><origin xyz="{xyz[0]:.6f} {xyz[1]:.6f} {xyz[2]:.6f}" '
         f'rpy="{e[0]:.6f} {e[1]:.6f} {e[2]:.6f}"/><parent link="{parent}"/><child link="{child}"/>')
    if jtype == 'revolute':
        s += f'<axis xyz="{axis[0]:.6f} {axis[1]:.6f} {axis[2]:.6f}"/><limit lower="{lim[0]}" upper="{lim[1]}" effort="10" velocity="20"/>'
    return s + '</joint>\n'


def build_urdf(side, T, m, rs):
    # robot name = the Sharpa's: our tools find hand bodies by the "<side>_sharpa_wave/" label prefix
    # (contact_retarget.hand_geometry; the first grasp-lock run on this hand found no geometry under "<side>_human")
    s = side; out = [f'<?xml version="1.0"?>\n<robot name="{s}_sharpa_wave">\n']
    # palm: metacarpal capsules (index, middle, ring) + a box closing the volar surface
    geoms = ''
    for f in ('index', 'middle', 'ring'):
        k = FINGERS[f]; u = unit(T[k] - T[0]); b = T[k] - min(0.045, 0.8 * np.linalg.norm(T[k] - T[0])) * u
        geoms += capsule_between(b, T[k], 0.010 * rs)
    xm = np.mean([T[k][0] for k in (5, 9, 13, 17)]); zs = [T[5][2], T[17][2]]
    x0, x1 = xm + 0.005, -0.02; z0, z1 = min(zs) - 0.006, max(zs) + 0.006
    geoms += (f'<collision><origin xyz="{(x0 + x1) / 2:.5f} -0.003 {(z0 + z1) / 2:.5f}" rpy="0 0 0"/><geometry>'
              f'<box size="{abs(x1 - x0):.4f} {0.024 * rs:.4f} {abs(z1 - z0):.4f}"/></geometry></collision>')
    out.append(link(f'{s}_hand_C_MC', inertial(MASS['palm'], ((x0 + x1) / 2, 0, (z0 + z1) / 2), abs(x1 - x0), 0.03), geoms))
    # thumb
    tm = m['thumb']; Lt = tm['L']; rt = [r * rs for r in RADII['thumb']]; zt = (0, 0, tm['s'])
    out.append(joint(f'{s}_thumb_CMC_FE', f'{s}_hand_C_MC', f'{s}_thumb_CMC_VL', tm['base'], tm['F'], zt, LIM['thumb_CMC_FE']))
    out.append(link(f'{s}_thumb_CMC_VL', tiny()))
    out.append(joint(f'{s}_thumb_CMC_AA', f'{s}_thumb_CMC_VL', f'{s}_thumb_MC', axis=(0, 1, 0), lim=LIM['thumb_CMC_AA']))
    out.append(link(f'{s}_thumb_MC', inertial(MASS['thumb_MC'], (Lt[0] / 2, 0, 0), Lt[0], rt[0]), capsule_x(0, Lt[0], rt[0])))
    out.append(joint(f'{s}_thumb_MCP_FE', f'{s}_thumb_MC', f'{s}_thumb_MCP_VL', (Lt[0], 0, 0), axis=zt, lim=LIM['thumb_MCP_FE']))
    out.append(link(f'{s}_thumb_MCP_VL', tiny()))
    out.append(joint(f'{s}_thumb_MCP_AA', f'{s}_thumb_MCP_VL', f'{s}_thumb_PP', axis=(0, 1, 0), lim=LIM['thumb_MCP_AA']))
    out.append(link(f'{s}_thumb_PP', inertial(MASS['PP'], (Lt[1] / 2, 0, 0), Lt[1], rt[1]), capsule_x(0, Lt[1], rt[1])))
    out.append(joint(f'{s}_thumb_IP', f'{s}_thumb_PP', f'{s}_thumb_DP', (Lt[1], 0, 0), axis=zt, lim=LIM['thumb_IP']))
    out += dp_links(s, 'thumb', Lt[2], rt[2], palmar=np.array([0, -1.0, 0]))
    # fingers
    for f, k in FINGERS.items():
        fm = m['fingers'][f]; L = fm['L']; r = [x * rs for x in RADII[f]]; zf = (0, 0, fm['s'])
        parent, base = f'{s}_hand_C_MC', fm['base']
        if f == 'pinky':
            pc = m['pinky_cmc']
            out.append(joint(f'{s}_pinky_CMC', parent, f'{s}_pinky_MC', pc['base'], np.eye(3), pc['axis'], LIM['pinky_CMC']))
            mc = capsule_between(np.zeros(3), T[17] - pc['base'], 0.009 * rs)
            out.append(link(f'{s}_pinky_MC', inertial(MASS['pinky_MC'], (T[17] - pc['base']) / 2, np.linalg.norm(T[17] - pc['base']), 0.009), mc))
            parent, base = f'{s}_pinky_MC', T[17] - pc['base']
        out.append(joint(f'{s}_{f}_MCP_FE', parent, f'{s}_{f}_MCP_VL', base, fm['F'], zf, LIM['MCP_FE']))
        out.append(link(f'{s}_{f}_MCP_VL', tiny()))
        out.append(joint(f'{s}_{f}_MCP_AA', f'{s}_{f}_MCP_VL', f'{s}_{f}_PP', axis=(0, 1, 0), lim=LIM['MCP_AA']))
        out.append(link(f'{s}_{f}_PP', inertial(MASS['PP'], (L[0] / 2, 0, 0), L[0], r[0]), capsule_x(0, L[0], r[0])))
        out.append(joint(f'{s}_{f}_PIP', f'{s}_{f}_PP', f'{s}_{f}_MP', (L[0], 0, 0), axis=zf, lim=LIM['PIP']))
        out.append(link(f'{s}_{f}_MP', inertial(MASS['MP'], (L[1] / 2, 0, 0), L[1], r[1]), capsule_x(0, L[1], r[1])))
        out.append(joint(f'{s}_{f}_DIP', f'{s}_{f}_MP', f'{s}_{f}_DP', (L[1], 0, 0), axis=zf, lim=LIM['DIP']))
        out += dp_links(s, f, L[2], r[2], palmar=np.array([0, -1.0, 0]))
    out.append('</robot>\n')
    return ''.join(out)


def dp_links(s, f, L, r, palmar):
    """Distal phalanx: capsule whose cap ends at the tip, two pad spheres flush on the volar side, then the Sharpa-style
    fixed elastomer and fingertip frames."""
    xc = max(L - r, 0.004)
    g = capsule_x(0, xc, r)
    for dz in (-0.003, 0.003):
        p = np.array([xc - 0.002, 0, dz]) + palmar * (r - PAD_R)
        g += (f'<collision><origin xyz="{p[0]:.5f} {p[1]:.5f} {p[2]:.5f}" rpy="0 0 0"/><geometry>'
              f'<sphere radius="{PAD_R}"/></geometry></collision>')
    return [link(f'{s}_{f}_DP', inertial(MASS['DP'], (L / 2, 0, 0), L, r), g),
            joint(f'{s}_{f}_elastomer_fix_joint', f'{s}_{f}_DP', f'{s}_{f}_elastomer', jtype='fixed'),
            link(f'{s}_{f}_elastomer', tiny(1e-5)),
            joint(f'{s}_{f}_fingertip_fix_joint', f'{s}_{f}_elastomer', f'{s}_{f}_fingertip', (L, 0, 0), jtype='fixed'),
            link(f'{s}_{f}_fingertip', tiny(1e-6))]


SHAPED = ['hand_C_MC', 'thumb_MC', 'thumb_PP', 'thumb_DP', 'pinky_MC'] + [f'{f}_{p}' for f in FINGERS for p in ('PP', 'MP', 'DP')]


def embodiment_yaml(name, left, right, wrist_kp):
    kd = 20.0 if wrist_kp >= 400 else 6.0
    ov = {r'wrist_[xyz]$': dict(kp=wrist_kp, kd=kd, effort_limit=150.0 if wrist_kp >= 400 else 45.0),
          r'right_wrist_y': dict(default_pos=0.25), r'left_wrist_y': dict(default_pos=-0.25),
          r'wrist_z$': dict(default_pos=0.5),
          r'wrist_rotvec$': dict(mode='effort', kp=25.0, kd=6.0, effort_limit=45.0),
          r'(index|middle|ring|pinky)_MCP_(FE|AA)$': GAINS['MCP'], r'(index|middle|ring|pinky)_PIP$': GAINS['PIP'],
          r'(index|middle|ring|pinky)_DIP$': GAINS['DIP'], r'thumb_CMC_(FE|AA)$': GAINS['thumb_CMC'],
          r'thumb_MCP_(FE|AA)$': GAINS['thumb_MCP'], r'thumb_IP$': GAINS['thumb_IP'], r'pinky_CMC$': GAINS['pinky_CMC']}
    lines = ['# Human capsule hand (pipeline/human_hand.py; physics study 2026-10-30). Not a submission embodiment.',
             '_target_: flash_chord.embodiments.sharpa_hands.SharpaHands', 'config:',
             '  _target_: flash_chord.embodiments.sharpa_hands.SharpaHandsConfig',
             f'  left_urdf_path: {left}', f'  right_urdf_path: {right}', '  joint_overrides:']
    for k, v in ov.items():
        if isinstance(v, tuple):
            v = dict(kp=v[0], kd=v[1], effort_limit=v[2])
        lines.append(f'    "{k}": {{' + ', '.join(f'{a}: {json.dumps(b)}' for a, b in v.items()) + '}')
    # first pass: no contacts inside a hand (perceived poses interpenetrate); the two hands still collide
    lines.append('  exclude_contacts:')
    for i, a in enumerate(SHAPED):
        for b in SHAPED[i + 1:]:
            lines.append(f'    - [{a}, {b}]')
    return '\n'.join(lines) + '\n'


# ------------------------------------------------------------------------------------------------------------------ IK
def fit_side(J, m, T):
    """(T,21,3) perceived keypoints in the world -> wrist position, wrist wxyz, 22 angles in the Sharpa joint order."""
    n = len(J)
    Rw = mkref.hand_rotations(J, 'right' if m['side'] == 'right' else 'left')[:, 0]      # (n,3,3) root frames
    pos = J[:, 0].copy(); wxyz = Rot.from_matrix(Rw).as_quat()[:, [3, 0, 1, 2]]
    wxyz *= np.sign(wxyz[:, :1] + 1e-12)
    q = np.zeros((n, 22)); err = np.zeros((n, 5))
    lo = {f: [LIM['MCP_FE'][0], LIM['MCP_AA'][0], LIM['PIP'][0], LIM['DIP'][0]] for f in FINGERS}
    hi = {f: [LIM['MCP_FE'][1], LIM['MCP_AA'][1], LIM['PIP'][1], LIM['DIP'][1]] for f in FINGERS}
    tlo = [LIM[k][0] for k in ('thumb_CMC_FE', 'thumb_CMC_AA', 'thumb_MCP_FE', 'thumb_MCP_AA', 'thumb_IP')]
    thi = [LIM[k][1] for k in ('thumb_CMC_FE', 'thumb_CMC_AA', 'thumb_MCP_FE', 'thumb_MCP_AA', 'thumb_IP')]
    prev = {f: np.zeros(4) for f in FINGERS}; prev['thumb'] = np.zeros(5); prev['cmc'] = np.zeros(1)
    pc = m['pinky_cmc']
    for t in range(n):
        Jl = (J[t] - J[t, 0]) @ Rw[t]                                  # keypoints in the root frame
        d = lambda a, b: unit(Jl[b] - Jl[a])
        # thumb
        obs = np.stack([d(1, 2), d(2, 3), d(3, 4)])
        r = least_squares(lambda th: (thumb_dirs(m['thumb'], th) - obs).ravel(), np.clip(prev['thumb'], tlo, thi),
                          bounds=(tlo, thi), xtol=1e-6, ftol=1e-6)
        q[t, 0:5] = prev['thumb'] = r.x; err[t, 0] = np.degrees(np.arccos(np.clip((thumb_dirs(m['thumb'], r.x) * obs).sum(1), -1, 1)).max())
        # pinky CMC from the wrist -> pinky MCP direction (cupping), then the four fingers
        o17 = unit(Jl[17])

        def cmc_res(th):              # cupping moves the pinky MCP out of the palm plane: fit the palm-normal part only
            return [(unit(rot(pc['axis'], th[0]) @ (T[17] - pc['base']) + pc['base']) - o17)[1]]
        r = least_squares(cmc_res, np.clip(prev['cmc'], LIM['pinky_CMC'][0], LIM['pinky_CMC'][1]),
                          bounds=([LIM['pinky_CMC'][0]], [LIM['pinky_CMC'][1]]))
        prev['cmc'] = r.x; Rc = rot(pc['axis'], r.x[0])
        col = {'index': 5, 'middle': 9, 'ring': 13, 'pinky': 18}
        for i, (f, k) in enumerate(FINGERS.items()):
            obs = np.stack([d(k, k + 1), d(k + 1, k + 2), d(k + 2, k + 3)]); pre = Rc if f == 'pinky' else np.eye(3)
            fm = m['fingers'][f]
            r = least_squares(lambda th: np.concatenate([(finger_dirs(fm, th, pre) - obs).ravel(), [0.05 * th[1]]]),
                              np.clip(prev[f], lo[f], hi[f]), bounds=(lo[f], hi[f]), xtol=1e-6, ftol=1e-6)
            prev[f] = r.x; q[t, col[f]:col[f] + 4] = r.x
            err[t, i + 1] = np.degrees(np.arccos(np.clip((finger_dirs(fm, r.x, pre) * obs).sum(1), -1, 1)).max())
        q[t, 17] = prev['cmc'][0]
    return pos, wxyz, q, err


def cmd_urdf(a):
    os.makedirs(a.out, exist_ok=True); info = {'variant': a.variant}
    paths = {}
    t = pq.read_table(a.ref) if a.ref else None
    for s in SIDES:
        J = np.array(t.column(f'mano_{s}_joints')[0].as_py(), float).reshape(-1, 21, 3) if t is not None else None
        T, L = template(s, a.variant, J)
        rs = 1.0 if a.variant == 'A' else float(np.clip(np.linalg.norm(T[8] - T[5]) / np.linalg.norm(mkref.TEMPLATE_RIGHT[8] - mkref.TEMPLATE_RIGHT[5]), 0.7, 1.1))
        m = model(T, s)
        p = os.path.abspath(f'{a.out}/{s}_human.urdf'); open(p, 'w').write(build_urdf(s, T, m, rs)); paths[s] = p
        idx = sum(np.linalg.norm(T[k + 1] - T[k]) for k in (5, 6, 7))
        info[s] = dict(template=T.round(5).tolist(), radius_scale=round(rs, 3), index_mcp_tip_cm=round(100 * idx, 2),
                       wrist_midtip_cm=round(100 * np.linalg.norm(T[12]), 2),
                       palm_cm=round(100 * np.linalg.norm(T[5] - T[17]), 2),
                       perceived_bone_lengths_m=None if L is None else L.round(5).tolist())
        print(f'{s}: variant {a.variant}, index MCP->tip {100 * idx:.1f} cm, wrist->middle tip '
              f'{100 * np.linalg.norm(T[12]):.1f} cm, palm {100 * np.linalg.norm(T[5] - T[17]):.1f} cm, radius scale {rs:.2f}')
    json.dump(info, open(f'{a.out}/hand.json', 'w'), indent=1)
    open(f'{a.out}/{a.name}.yaml', 'w').write(embodiment_yaml(a.name, paths['left'], paths['right'], a.wrist_kp))
    print('wrote', a.out, f'{a.name}.yaml')


def cmd_ref(a):
    info = json.load(open(f'{a.hand}/hand.json'))
    t = pq.read_table(a.inp); cols = {}; rep = {}
    for s in SIDES:
        J = np.array(t.column(f'mano_{s}_joints')[0].as_py(), float).reshape(-1, 21, 3)
        T = np.array(info[s]['template']); m = model(T, s); m['side'] = s
        names = t.column(f'{s}_robot_finger_joint_names')[0].as_py()
        order = ['thumb_CMC_FE', 'thumb_CMC_AA', 'thumb_MCP_FE', 'thumb_MCP_AA', 'thumb_IP'] + \
                [f'{f}_{j}' for f in ('index', 'middle', 'ring') for j in ('MCP_FE', 'MCP_AA', 'PIP', 'DIP')] + \
                ['pinky_CMC'] + [f'pinky_{j}' for j in ('MCP_FE', 'MCP_AA', 'PIP', 'DIP')]
        assert [f'{s}_{o}' for o in order] == names, names
        pos, wxyz, q, err = fit_side(J, m, T)
        if a.squeeze:
            flex = [i for i, o in enumerate(order) if o.endswith(('MCP_FE', 'PIP', 'DIP')) or o == 'thumb_IP']
            w = np.zeros(len(q))
            for p in json.load(open(a.holds))['phases']:
                if p['hand'] != s:
                    continue
                a0, b0 = p.get('hold_from') or p['start'], min(p['end'], len(q) - 1)
                for f in range(max(a0 - 5, 0), min(b0 + 6, len(q))):
                    w[f] = max(w[f], min(1.0, (f - (a0 - 5)) / 5.0, (b0 + 5 - f) / 5.0))
            for i in flex:
                lo, hi = LIM[order[i] if order[i] in LIM else order[i].split('_', 1)[1]]
                q[:, i] = np.clip(q[:, i] + a.squeeze * w, lo, hi)
            rep.setdefault('squeeze', {})[s] = dict(rad=a.squeeze, frames=int((w > 0).sum()))
            print(f'{s}: squeeze +{a.squeeze} rad on {len(flex)} flexion joints over {(w > 0).sum()} frames')
        cols[f'robot_{s}_wrist_position'] = pos; cols[f'robot_{s}_wrist_wxyz'] = wxyz; cols[f'robot_{s}_finger_joints'] = q
        at_lim = float(np.mean([(np.isclose(q[:, i], lo) | np.isclose(q[:, i], hi)).mean() for i, (lo, hi) in
                                enumerate([LIM[k if k in LIM else k.split('_', 1)[1]] for k in order])]))
        rep[s] = dict(dir_err_deg_median=np.median(err, 0).round(1).tolist(), dir_err_deg_p90=np.percentile(err, 90, 0).round(1).tolist(),
                      share_at_limit=round(at_lim, 3))
        print(f'{s}: max bone-direction error per digit (thumb, index, middle, ring, pinky) median '
              f'{np.median(err, 0).round(1).tolist()} deg, p90 {np.percentile(err, 90, 0).round(1).tolist()}; '
              f'share of joint-frames at a limit {at_lim:.3f}')
    for k, v in cols.items():
        t = t.set_column(t.column_names.index(k), k, pa.array([v.astype(np.float32).tolist()], type=t.schema.field(k).type))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    pq.write_table(t, a.out)
    json.dump(dict(hand=a.hand, variant=info['variant'], **rep), open(a.out.replace('.parquet', '_human_ik.json'), 'w'), indent=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    u = sp.add_parser('urdf'); u.add_argument('variant', choices=['A', 'P']); u.add_argument('out')
    u.add_argument('--ref'); u.add_argument('--name', default='human_hands'); u.add_argument('--wrist_kp', type=float, default=400.0)
    r = sp.add_parser('ref'); r.add_argument('hand'); r.add_argument('inp'); r.add_argument('out')
    r.add_argument('--squeeze', type=float, default=0.0); r.add_argument('--holds')
    a = ap.parse_args()
    if a.cmd == 'urdf':
        if a.variant == 'P' and not a.ref:
            sys.exit('variant P needs --ref (the perceived hand)')
        cmd_urdf(a)
    else:
        cmd_ref(a)


if __name__ == '__main__':
    main()
