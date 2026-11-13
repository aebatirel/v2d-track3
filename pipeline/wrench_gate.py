#!/usr/bin/env python3
"""Wrench-feasibility gate on one reference (2026-11-12, note 29 idea 1; rule pre-registered in docs/work-log.md,
"2026-11-12 ~22:20 UTC ... PRE-REGISTRATION for note 29 ideas 1 and 2").

Question per frame of a held window: can the grasp that the reference's contacts describe supply the wrench that the
object's reference motion needs?
  demand  W = [F ; tau / rc] in the world frame, about the object's centre of mass (COM):
          F = m (a - g), tau = I_w alpha + omega x I_w omega (pipeline/task_wrench.py, Savitzky-Golay derivatives of
          OUR object track, window 9, 20 fps).
  supply  every active contact slot on that object, from both hands (mkref.py writes 16 slots per hand in
          CONTACT_SLOT_NAMES order = PROBE_SITES + palm: world-frame point on the object surface, unit normal INTO the
          object, part id = object body index + 1; a slot is active when its part id matches and |normal| > 1e-3, as in
          hold_phases.py). Each contact gives a friction cone of 8 edge rays plus the normal, unit length, with the
          Frisvad tangent basis, exactly as NVIDIA's exercise-3 contacts.py and FlashCHORD objectives/wrench.py; each ray
          f at point p gives the generator [f ; ((p - c) x f) / rc], c = the COM at that frame.
  score   min over lambda >= 0 of |G lambda - W| / |W| (scipy nnls). 0 = the demand lies inside the contact wrench cone
          (feasible with some contact forces), 1 = no contact on the object. A point contact transmits no torsional
          friction (the simulator's condim-3 contacts have none either, note 24 section 1).
  frames  object-event windows (pipeline/object_events.hold_events, grasp_lock --events convention): for each hold of
          an object (pipeline/hold_phases.py, both hands merged per object), the window runs from the object's lift-off
          to the frame after its last movement inside the hold (hold_events' settle frame; used also when hold_events
          rejects it as a placement, so a still tail resting on a rack or pot is left out). The contact labels only
          say which hold the events belong to; the window edges come from the object's own track, because the MANO
          labels are mistimed by up to ~24 frames (object_events.py docstring). Objects never lifted get no window.
Parameters (defaults fixed with the pre-registered test, docs/research/work/wrench-gate-20261112/README.md):
  mu 1.0   FlashCHORD scene contact friction: configs/scene/{train,eval}.yaml contact_friction 1.0, which leaves every
           shape at Newton 1.2.0's ShapeConfig.mu = 1.0 (also measured, note 24 section 1).
  m        <mass> of the URDF the reference names (the kit and make_assets.py both write the 0.3 kg placeholder), else 0.3.
  COM, I   the URDF's <inertial> (what the simulator uses), else a uniform solid of the object's mesh with mass m
           (trimesh; the convex hull when the mesh is not watertight), else the body origin and a solid sphere of
           radius rc (crude; flagged in the output).
  rc       object_mesh_radius from the reference (max vertex distance from the vertex mean; FlashCHORD's torque scale).
Inference only, no ground truth: reads our reference parquet and the object assets it names (or --assets). Never the
episode parquet's observation.objects pose field, never mocap.
Usage: wrench_gate.py REF.parquet [--assets DIR] [--mu 1.0] [--mass M] [--json OUT] [--frames]
  --assets DIR: look for DIR/urdf/<obj>_rigid.urdf and DIR/mesh/<obj>/<obj>.glb (make_assets.py layout) when the paths
  stored in the reference do not exist on this machine. --frames: also write per-frame rows to the JSON.
"""
import argparse, json, os, sys
import xml.etree.ElementTree as ET

import numpy as np
import pyarrow.parquet as pq
from scipy.optimize import nnls
from scipy.spatial.transform import Rotation as Rot

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import object_events as oe  # noqa: E402
from hold_phases import hold_phases  # noqa: E402
from task_wrench import object_tracks, wrench as task_wrench  # noqa: E402

MU, MASS, FPS, N_EDGES, INFEASIBLE = 1.0, 0.3, 20.0, 8, 0.5
SIDES = ('right', 'left')


# ------------------------------------------------------------------ supply: contact wrench generators
def cone_rays(n, mu=MU, edges=N_EDGES):
    """(edges+1, 3) unit friction-cone rays around the inward unit normal n (exercise 3 contacts.py)."""
    n = np.asarray(n, float) / np.linalg.norm(n)
    sign = 1.0 if n[2] >= 0 else -1.0
    a = -1.0 / (sign + n[2]); b = n[0] * n[1] * a
    t1 = np.array([1 + sign * n[0] * n[0] * a, sign * b, -sign * n[0]]); t1 /= np.linalg.norm(t1)
    t2 = np.array([b, sign + n[1] * n[1] * a, -n[1]]); t2 /= np.linalg.norm(t2)
    th = np.arange(edges) * 2 * np.pi / edges
    rays = np.vstack([n + mu * (np.cos(th)[:, None] * t1 + np.sin(th)[:, None] * t2), n[None]])
    return rays / np.linalg.norm(rays, axis=1, keepdims=True)


def generators(points, normals, com, rc, mu=MU):
    """(6, K*(edges+1)) contact wrench generators [f ; ((p - c) x f)/rc]; world frame."""
    cols = []
    for p, n in zip(points, normals):
        f = cone_rays(n, mu)
        cols.append(np.hstack([f, np.cross(np.asarray(p, float) - com, f) / rc]))
    return np.vstack(cols).T if cols else np.zeros((6, 0))


def feasibility(demand, G):
    """Relative NNLS residual of the demand wrench (6,) in the cone of the columns of G; 1.0 without contacts."""
    nw = float(np.linalg.norm(demand))
    if nw < 1e-12:
        return 0.0
    if G.shape[1] == 0:
        return 1.0
    lam, res = nnls(G, demand, maxiter=50 * G.shape[1])
    return float(res / nw)


# ------------------------------------------------------------------ object physics (mass, COM, inertia)
def _urdf_inertial(path):
    root = ET.parse(path).getroot(); el = root.find('.//inertial')
    if el is None:
        return None
    o = el.find('origin'); xyz = np.zeros(3); rpy = np.zeros(3)
    if o is not None:
        xyz = np.array([float(x) for x in o.get('xyz', '0 0 0').split()])
        rpy = np.array([float(x) for x in o.get('rpy', '0 0 0').split()])
    m = float(el.find('mass').get('value')); i = el.find('inertia')
    g = lambda k: float(i.get(k, 0.0))  # noqa: E731
    I = np.array([[g('ixx'), g('ixy'), g('ixz')], [g('ixy'), g('iyy'), g('iyz')], [g('ixz'), g('iyz'), g('izz')]])
    Rr = Rot.from_euler('xyz', rpy).as_matrix()
    return dict(mass=m, com=xyz, inertia=Rr @ I @ Rr.T, source=f'urdf:{path}')


def _mesh_solid(path, mass):
    import trimesh
    m = trimesh.load(path, force='mesh')
    note = 'mesh solid'
    if not m.is_watertight:
        m = m.convex_hull; note = 'mesh convex hull solid (mesh not watertight)'
    m.density = 1.0; vol = float(m.volume)
    return dict(mass=mass, com=np.asarray(m.center_mass, float), inertia=np.asarray(m.moment_inertia, float) * mass / vol,
                source=f'{note}:{path}')


def object_physics(name, urdf_path, mesh_path, rc, assets=None, mass=None):
    """Mass, COM (object frame) and inertia about the COM (object-frame axes) for one object, with its source."""
    cands = [(urdf_path, mesh_path)]
    if assets:
        cands.append((os.path.join(assets, 'urdf', f'{name}_rigid.urdf'), os.path.join(assets, 'mesh', name, f'{name}.glb')))
    for u, _ in cands:
        if u and os.path.exists(u):
            ph = _urdf_inertial(u)
            if ph is not None:
                if mass is not None:
                    ph['inertia'] = ph['inertia'] * mass / ph['mass']; ph['mass'] = mass
                return ph
    m = MASS if mass is None else mass
    for _, g in cands:
        if g and os.path.exists(g):
            return _mesh_solid(g, m)
    return dict(mass=m, com=np.zeros(3), inertia=np.eye(3) * 0.4 * m * rc ** 2,
                source='APPROX: body origin, solid sphere of radius rc (no URDF or mesh found)')


# ------------------------------------------------------------------ demand
def demand_wrench(P, Q, ph, fps=FPS):
    """Task wrench (T,6) [F ; tau] about the COM in the world frame and the COM track (T,3), via task_wrench.wrench.
    task_wrench takes a diagonal body inertia, so the object frame is turned onto the inertia's principal axes V
    (Q' = R V, com' = V^T com): this leaves the COM track, the angular velocity and R I R^T unchanged."""
    lam, V = np.linalg.eigh(ph['inertia'])
    if np.linalg.det(V) < 0:
        V[:, 2] *= -1
    R = Rot.from_quat(Q); Rp = R * Rot.from_matrix(V)
    o = task_wrench(P, Rp.as_quat(), ph['mass'], lam, fps, com=V.T @ ph['com'])
    return np.hstack([o['F'], o['tau']]), P + R.apply(ph['com'])


# ------------------------------------------------------------------ held windows
def held_windows(ref, names, OP, OR):
    """{object: [(start, end_exclusive, info)]}: object-event windows inside each hold (both hands merged)."""
    phases = hold_phases(ref)[0]['phases']; out = {}
    for j, n in enumerate(names):
        iv = sorted((p['start'], p['end']) for p in phases if p['object'] == n)
        merged = []
        for a, b in iv:
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        wins, prev_end, mv = [], 0, oe.moving(OP[:, j], OR[j])
        for s0, s1 in merged:
            lf, se = oe.hold_events(OP[:, j], OR[j], prev_end, s1)
            if lf is not None:
                # end = the frame after the object's last movement inside the hold: hold_events' settle candidate,
                # also when it rejects it as a placement (put on a rack / lid on the pot / held still): the still
                # tail is dropped (it is resting on something in nearly all cases; up to 78 frames on public refs)
                idx = np.nonzero(mv[lf:min(s1, len(mv))])[0]
                end = lf + int(idx[-1]) + 1 if len(idx) else lf + 1
                if end > lf:
                    wins.append((int(lf), int(end), dict(hold=[int(s0), int(s1)], rest_from=int(prev_end), liftoff=int(lf),
                                                         settle=None if se is None else int(se))))
            prev_end = s1
        out[n] = wins
    return out


# ------------------------------------------------------------------ main entry
def gate(ref, assets=None, mu=MU, mass=None, fps=FPS):
    """Per-frame scores for every held window of every object. Returns a dict (JSON-ready except numpy rows)."""
    t = pq.read_table(ref)
    names, P, Q = object_tracks(ref)                                  # Q: xyzw
    T = P.shape[0]; OR = [Rot.from_quat(Q[:, j]) for j in range(len(names))]
    col = lambda c: t.column(c)[0].as_py() if c in t.column_names else None  # noqa: E731
    rc_all = np.asarray(col('object_mesh_radius') or [0.1] * len(names), float)
    urdfs = col('object_urdf_paths') or [None] * len(names); meshes = col('object_mesh_paths') or [None] * len(names)
    C = {}
    for s in SIDES:
        C[s] = (np.array(col(f'mano_{s}_object_contact_positions'), float).reshape(T, -1, 3),
                np.array(col(f'mano_{s}_object_contact_normals'), float).reshape(T, -1, 3),
                np.array(col(f'mano_{s}_object_contact_part_ids')).reshape(T, -1))
    wins = held_windows(ref, names, P, OR)
    res = dict(reference=os.path.abspath(ref), frames=int(T), mu=mu, edges=N_EDGES, infeasible_threshold=INFEASIBLE,
               objects={}, rows=[])
    for j, n in enumerate(names):
        rc = float(rc_all[j]); ph = object_physics(n, urdfs[j], meshes[j], rc, assets, mass)
        W, com_w = demand_wrench(P[:, j], Q[:, j], ph, fps)
        Wn = np.hstack([W[:, :3], W[:, 3:] / rc])
        scores, ncon = [], []
        for (a, b, info) in wins[n]:
            for f in range(a, b):
                pts, nrm = [], []
                for s in SIDES:
                    cp, cn, pid = C[s]
                    act = (pid[f] == j + 1) & (np.linalg.norm(cn[f], axis=1) > 1e-3)
                    pts.append(cp[f][act]); nrm.append(cn[f][act])
                pts, nrm = np.vstack(pts), np.vstack(nrm)
                sc = feasibility(Wn[f], generators(pts, nrm, com_w[f], rc, mu))
                scores.append(sc); ncon.append(len(pts))
                res['rows'].append(dict(object=n, frame=int(f), score=round(sc, 5), contacts=int(len(pts)),
                                        F_N=round(float(np.linalg.norm(W[f, :3])), 4),
                                        tau_Nm=round(float(np.linalg.norm(W[f, 3:])), 5)))
        sc, ncon = np.asarray(scores), np.asarray(ncon)
        res['objects'][n] = dict(rc_m=round(rc, 4), mass_kg=ph['mass'], com_obj_m=np.round(ph['com'], 4).tolist(),
                                 inertia_diag=np.round(np.diag(ph['inertia']), 7).tolist(), physics_source=ph['source'],
                                 windows=[dict(start=a, end=b, **info) for a, b, info in wins[n]], held_frames=int(len(sc)),
                                 share_infeasible=round(float((sc > INFEASIBLE).mean()), 4) if len(sc) else None,
                                 share_no_contact=round(float((ncon == 0).mean()), 4) if len(sc) else None,
                                 score_median=round(float(np.median(sc)), 4) if len(sc) else None)
    sc = np.array([r['score'] for r in res['rows']])
    res['held_frames'] = int(len(sc))
    res['share_infeasible'] = round(float((sc > INFEASIBLE).mean()), 4) if len(sc) else None
    return res


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('ref'); p.add_argument('--assets'); p.add_argument('--mu', type=float, default=MU)
    p.add_argument('--mass', type=float, default=None, help='override the URDF mass (default: URDF, else 0.3 kg)')
    p.add_argument('--fps', type=float, default=FPS); p.add_argument('--json'); p.add_argument('--frames', action='store_true')
    a = p.parse_args()
    r = gate(a.ref, a.assets, a.mu, a.mass, a.fps)
    for n, o in r['objects'].items():
        print(f"{n:22s} held {o['held_frames']:4d} frames, infeasible (> {INFEASIBLE}) {o['share_infeasible']}, "
              f"no contact {o['share_no_contact']}, median score {o['score_median']}; {o['physics_source']}")
        for w in o['windows']:
            print(f"    window {w['start']}-{w['end']} (hold {w['hold']}, settle {w['settle']})")
    if a.json:
        if not a.frames:
            r = {k: v for k, v in r.items() if k != 'rows'}
        json.dump(r, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
