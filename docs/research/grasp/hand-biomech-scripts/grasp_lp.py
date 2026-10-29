"""Required contact normal forces for idealised human-like grasp layouts on OUR meshes, along OUR reference motion.

For each frame of a human hold (from human_grasp_census.py's frames, our perceived object track, no ground truth):
  required wrench on the object (object PCA frame, COM origin): F = R^T m (a - g), tau = 0 (inertial torque is small)
  times a safety factor SF on the load.
Contacts: point contacts with Coulomb friction in a 4-edge pyramid (MuJoCo pyramidal cone, condim 3: NO torsional
friction), evaluated with the pyramid's tangent axes at 0 and 45 deg to be conservative (worst case is diagonal, mu/sqrt2).
LP (scipy HiGHS): minimise s subject to sum_i G_i f_i = SF * W(t), f_i in cone_i, normal_i <= s.
Reports, per layout and mu, the worst-case (over the hold) minimal max-normal force s* (N), the total normal force at
that frame, and which frames are infeasible (no force distribution exists: the layout cannot resist the load).
Usage: grasp_lp.py PARQUET LIBRARY_DIR OBJECT F0 F1 LAYOUT_SET [SF]
"""
import sys, json
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.optimize import linprog
from scipy.signal import savgol_filter
from scipy.spatial.transform import Rotation as Rot

G = np.array([0.0, 0.0, -9.81]); MASS = 0.3; FPS = 20.0


def unit(v): v = np.asarray(v, float); return v / np.linalg.norm(v)


def C(name, p_cm, n):                      # contact: position (cm, PCA frame) and the direction of the force ON the object
    return (name, np.asarray(p_cm, float) / 100.0, unit(n))


def wrap(prefix, centre_cm, axis, radius_cm, stations_cm, angles_deg, ref=(0, 0, 1)):
    """contacts around a handle: at each station along `axis`, at the given angles around it, force pointing inward."""
    a = unit(axis); e1 = unit(np.cross(a, ref)) if abs(np.dot(a, unit(ref))) < 0.95 else unit(np.cross(a, (1, 0, 0)))
    e2 = np.cross(a, e1); out = []
    for s in stations_cm:
        for ang in angles_deg:
            r = np.cos(np.radians(ang)) * e1 + np.sin(np.radians(ang)) * e2
            p = np.asarray(centre_cm, float) + s * a + radius_cm * r
            out.append(C(f'{prefix}{s:+.0f}@{ang}', p, -r))
    return out


def layouts(set_name):
    L = {}
    if set_name == 'pan':        # mini_dust_pan, ours: ring end band pca1 -10.6..-8.2, hole -8.2..-5.4 (x 4.2 wide), plate normal pca3
        L['P1 single pinch at ring end (thumb top / index under, one point)'] = [
            C('thumb', (-9.5, 0, 0.8), (0, 0, -1)), C('index', (-9.5, 0, -0.4), (0, 0, 1))]
        L['P2 key pinch across end band, spread 3 cm along band'] = [
            C('thumbDP', (-9.5, 1.5, 0.8), (0, 0, -1)), C('thumbPP', (-9.5, -1.5, 0.8), (0, 0, -1)),
            C('indexMP', (-9.5, -1.5, -0.4), (0, 0, 1)), C('indexDP', (-9.5, 1.5, -0.4), (0, 0, 1))]
        L['P3 hook through hole + thumb on end band + middle under end band'] = [
            C('thumb', (-9.5, 0, 0.8), (0, 0, -1)), C('middle_under_end', (-9.5, -1.0, -0.4), (0, 0, 1)),
            C('index_under_inner_band', (-5.0, 0, -0.2), (0, 0, 1)), C('index_in_hole_far_edge', (-5.4, 0, 0.6), (1, 0, 0)),
            C('index_in_hole_near_edge', (-8.2, 0, 0.2), (-1, 0, 0))]
        L['P4 P3 + thumb spread (thumb DP + PP on band top, 3 cm apart)'] = L['P3 hook through hole + thumb on end band + middle under end band'] + [
            C('thumbPP', (-9.5, 2.0, 0.8), (0, 0, -1)), C('ring_under_end', (-9.5, 1.5, -0.4), (0, 0, 1))]
    elif set_name == 'sweeper':  # mini_sweeper, ours: ring end -7.2, hole ~2 cm, plate half thickness ~1 cm
        L['S1 band clamp (thumb DP+PP on +face, 3 fingers on -face, 2 cm spread)'] = [
            C('thumbDP', (-5.0, -2.0, 0.8), (0, 0, -1)), C('thumbPP', (-6.5, -1.5, 0.9), (0, 0, -1)),
            C('indexMP', (-5.5, -2.5, -1.1), (0, 0, 1)), C('middleMP', (-4.5, -2.0, -1.1), (0, 0, 1)),
            C('ringMP', (-6.5, -2.0, -1.1), (0, 0, 1))]
        L['S2 neck/head clamp (RL-found: thumb column one face, 4 fingers flat on other, 6 x 5 cm spread)'] = [
            C('thumbMC', (-2.0, -2.5, 1.0), (0, 0, -1)), C('thumbPP', (-1.0, -1.0, 1.0), (0, 0, -1)), C('thumbDP', (0.0, 0.5, 1.2), (0, 0, -1)),
            C('index', (-3.0, -2.0, -1.0), (0, 0, 1)), C('middle', (-1.0, 0.0, -1.0), (0, 0, 1)), C('ring', (1.0, 2.0, -1.0), (0, 0, 1)),
            C('pinky', (2.0, 4.0, -1.0), (0, 0, 1)), C('palm_edge', (-2.0, -3.4, 0.0), (0, 1, 0))]
        L['S3 single pinch on the ring end (one point)'] = [
            C('thumb', (-6.8, 0, 1.0), (0, 0, -1)), C('index', (-6.8, 0, -1.1), (0, 0, 1))]
    elif set_name == 'board':    # wooden boards, ours: 22.9 x 13.3, half thickness ~0.45 cm; long edge at pca2 = -6.6
        L['B1 edge pinch, one point (thumb top / index under)'] = [
            C('thumb', (0, -6.0, 0.45), (0, 0, -1)), C('index', (0, -6.0, -0.45), (0, 0, 1))]
        L['B2 parallel extension at long edge: thumb DP+PP on top, 3 fingertips under 4 cm in, PPs under at edge'] = [
            C('thumbDP', (0, -6.0, 0.45), (0, 0, -1)), C('thumbPP', (2.0, -6.2, 0.45), (0, 0, -1)),
            C('indexDP', (-2.0, -2.5, -0.45), (0, 0, 1)), C('middleDP', (0, -2.0, -0.45), (0, 0, 1)), C('ringDP', (2.0, -2.5, -0.45), (0, 0, 1)),
            C('indexPP', (-2.0, -5.5, -0.45), (0, 0, 1)), C('middlePP', (0, -5.5, -0.45), (0, 0, 1))]
        L['B3 short-edge grip (grip 10 cm from COM): thumb top at edge, fingers under 3.5 cm in, spread 4 cm'] = [
            C('thumbDP', (-10.5, 0.0, 0.45), (0, 0, -1)), C('thumbPP', (-10.5, 2.0, 0.45), (0, 0, -1)),
            C('indexDP', (-7.0, -2.0, -0.45), (0, 0, 1)), C('middleDP', (-7.0, 0.0, -0.45), (0, 0, 1)), C('ringDP', (-7.0, 2.0, -0.45), (0, 0, 1)),
            C('indexPP', (-10.0, -1.5, -0.45), (0, 0, 1)), C('middlePP', (-10.0, 0.5, -0.45), (0, 0, 1))]
        L['B4 pad opposition: thumb DP opposite index/middle DPs 3 cm in, thumb PP at edge, fingers spread 4 cm'] = [
            C('thumbDP', (-1.0, -3.0, 0.45), (0, 0, -1)), C('thumbPP', (1.5, -5.8, 0.45), (0, 0, -1)),
            C('indexDP', (-2.0, -3.0, -0.45), (0, 0, 1)), C('middleDP', (0.0, -3.0, -0.45), (0, 0, 1)), C('ringDP', (2.0, -3.0, -0.45), (0, 0, 1)),
            C('indexPP', (-2.0, -5.8, -0.45), (0, 0, 1)), C('ringPP', (2.0, -5.8, -0.45), (0, 0, 1))]
        L['B5 two pad pairs 6 cm apart along the edge (thumb vs index, palm-heel/thumbPP vs ring), 3 cm in'] = [
            C('thumbDP', (-3.0, -3.0, 0.45), (0, 0, -1)), C('indexDP', (-3.0, -3.0, -0.45), (0, 0, 1)),
            C('thumbPP', (3.0, -4.0, 0.45), (0, 0, -1)), C('ringDP', (3.0, -4.0, -0.45), (0, 0, 1)),
            C('middleDP', (0.0, -3.0, -0.45), (0, 0, 1)), C('palm', (0.0, -5.0, 0.45), (0, 0, -1))]
    elif set_name == 'pot':      # white_pot, ours: stick handle along pca1 -9..-25.5, section pca2 -1.0..2.2, pca3 1.1..3.6
        c = (0, 0.6, 2.35)
        L['T1 handle-end pinch (thumb top / index under at -22 cm)'] = [
            C('thumb', (-22, 0.6, 3.6), (0, 0, -1)), C('index', (-22, 0.6, 1.1), (0, 0, 1))]
        L['T2 medium wrap: 4 fingers under+side at -13..-19, palm side, thumb + palm heel on top'] = (
            [C(f'f{x}', (x, 0.6, 1.1), (0, 0, 1)) for x in (-13, -15, -17, -19)] +
            [C(f'f{x}side', (x, 2.2, 2.35), (0, -1, 0)) for x in (-13, -15, -17, -19)] +
            [C('palm_a', (-14, -1.0, 2.35), (0, 1, 0)), C('palm_b', (-18, -1.0, 2.35), (0, 1, 0)),
             C('thumb', (-15, 0.6, 3.6), (0, 0, -1)), C('palm_heel_top', (-21, 0.6, 3.6), (0, 0, -1))])
        L['T3 wrap far out (-19..-25 only, the human thumb zone)'] = (
            [C(f'f{x}', (x, 0.6, 1.1), (0, 0, 1)) for x in (-19, -21, -23)] +
            [C(f'f{x}side', (x, 2.2, 2.35), (0, -1, 0)) for x in (-19, -21, -23)] +
            [C('palm', (-21, -1.0, 2.35), (0, 1, 0)), C('thumb', (-20, 0.6, 3.6), (0, 0, -1)), C('heel', (-24.5, 0.6, 3.4), (0, 0, -1))])
    elif set_name == 'lid':      # white_pot_lid, ours: strap centre (0.4, 0, 3.2), along u, cross-section 1.4 x 1.4, gap under it 1.5 cm
        u = unit((-0.48, 0.88, 0)); v = unit((0.88, 0.48, 0)); c = np.array((0.4, 0, 3.2))
        L['L1 strap side pinch: thumb one side, index + middle other side, 2.4 cm apart'] = [
            C('thumb', c + 0.7 * v, -v), C('index', c - 0.7 * v - 1.2 * u, v), C('middle', c - 0.7 * v + 1.2 * u, v)]
        L['L2 hook under strap (index+middle) + thumb on top'] = [
            C('index_under', c + np.array((0, 0, -0.7)) - 1.0 * u, (0, 0, 1)), C('middle_under', c + np.array((0, 0, -0.7)) + 1.0 * u, (0, 0, 1)),
            C('thumb_top', c + np.array((0, 0, 0.7)), (0, 0, -1)),
            C('index_side', c - 0.7 * v - 1.0 * u, v), C('thumb_side', c + 0.7 * v, -v)]
        L['L3 rim pinch at one side (thumb top / two fingers under rim, 8 cm from COM)'] = [
            C('thumb', (7.5, 3.0, 1.0), (0, 0, -1)), C('index', (7.8, 1.5, -0.8), (0, 0, 1)), C('middle', (7.0, 4.5, -0.8), (0, 0, 1))]
    elif set_name == 'pitcher':  # water_pitcher, ours: handle around (-11, 6.5, 1.5) cm, roughly along (-1, -0.9, -0.3)
        a = unit((-1, -0.9, -0.3))
        L['W1 handle wrap (power, 3 stations x 4 sides, radius 2 cm)'] = wrap('w', (-11, 6.5, 1.5), a, 2.0, (-2.5, 0, 2.5), (0, 90, 180, 270))
        L['W2 handle hook (fingers on one inner side only, no thumb)'] = wrap('h', (-11, 6.5, 1.5), a, 2.0, (-2.5, 0, 2.5), (90,))
        L['W3 handle pinch, one station (thumb vs index)'] = wrap('p', (-11, 6.5, 1.5), a, 2.0, (0,), (90, 270))
    return L


def cone_edges(n, mu, rot45):
    t1 = unit(np.cross(n, (0, 0, 1)) if abs(n[2]) < 0.9 else np.cross(n, (1, 0, 0))); t2 = np.cross(n, t1)
    if rot45: t1, t2 = (t1 + t2) / np.sqrt(2), (t2 - t1) / np.sqrt(2)
    return [n + mu * t1, n - mu * t1, n + mu * t2, n - mu * t2]


def solve(contacts, W, mu, rot45):
    cols = []; owner = []
    for i, (_, p, n) in enumerate(contacts):
        for d in cone_edges(n, mu, rot45):
            cols.append(np.concatenate([d, np.cross(p, d)])); owner.append(i)
    A = np.array(cols).T                                  # 6 x K
    K = A.shape[1]; nC = len(contacts)
    # variables: lambda (K) , s ; minimise s
    c = np.zeros(K + 1); c[-1] = 1.0
    Aeq = np.hstack([A, np.zeros((6, 1))])
    Aub = np.zeros((nC, K + 1))
    for k, i in enumerate(owner): Aub[i, k] = 1.0         # normal_i = sum of its edge weights (edges have unit normal part)
    Aub[:, -1] = -1.0
    r = linprog(c, A_ub=Aub, b_ub=np.zeros(nC), A_eq=Aeq, b_eq=W, bounds=[(0, None)] * (K + 1), method='highs')
    if r.status != 0: return None, None
    lam = r.x[:K]; N = np.zeros(nC)
    for k, i in enumerate(owner): N[i] += lam[k]
    return r.x[-1], N


def main(parquet, lib, obj, f0, f1, set_name, SF=1.5):
    f0, f1, SF = int(f0), int(f1), float(SF)
    t = pq.read_table(parquet); names = t.column('object_body_names')[0].as_py(); k = names.index(obj)
    P = np.array(t.column('object_body_position')[0].as_py(), float)[:, k]
    Q = np.array(t.column('object_body_wxyz')[0].as_py(), float)[:, k][:, [1, 2, 3, 0]]
    m = trimesh.load(f'{lib}/{obj}.glb', force='mesh'); com = m.center_mass if m.is_watertight else m.vertices.mean(0)
    _, _, Vt = np.linalg.svd(m.vertices - m.vertices.mean(0), full_matrices=False)
    R = Rot.from_quat(Q); Pc = P + R.apply(com)
    acc = savgol_filter(Pc, 9, 3, deriv=2, delta=1 / FPS, axis=0, mode='interp')
    Fw = MASS * (acc - G)                                   # force the hand must apply (world)
    frames = range(f0, f1 + 1)
    Wl = [np.concatenate([Vt @ R[f].inv().apply(Fw[f]), np.zeros(3)]) * SF for f in frames]
    out = {}
    for name, cs in layouts(set_name).items():
        row = {}
        for mu in (0.5, 0.71, 1.0):
            worst = 0.0; worstN = None; infeas = 0
            for W in Wl:
                best = None
                for rot45 in (False, True):
                    s, N = solve(cs, W, mu, rot45)
                    if s is None: best = None; break
                    if best is None or s > best[0]: best = (s, N)
                if best is None: infeas += 1; continue
                if best[0] > worst: worst, worstN = best
            row[str(mu)] = dict(max_normal_N=round(worst, 2), total_normal_N=round(float(worstN.sum()), 2) if worstN is not None else None,
                                infeasible_frames=infeas, of=len(Wl))
        out[name] = row
        print(f'{name}')
        for mu, r in row.items():
            print(f'    mu {mu}: max normal per contact {r["max_normal_N"]:6.2f} N, total {r["total_normal_N"]} N, '
                  f'infeasible {r["infeasible_frames"]}/{r["of"]} frames')
    return out


if __name__ == '__main__':
    res = main(*sys.argv[1:8])
    if len(sys.argv) > 8: json.dump(res, open(sys.argv[8], 'w'), indent=1)
