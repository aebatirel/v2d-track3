"""Physics-aware grip forces for a locked grasp (2026-10-23, docs/research/notes/24; owner: "design the grasps physics
aware, research the physics and the anatomy of a grasp").
grasp_lock.py used one uniform squeeze (+0.4 rad on every flexion joint past contact). That is not a static
equilibrium (tau = kp * 0.4 is not in range(J^T)): the fingers keep curling and on eval ep35 they rolled the 1.3 cm
spoon handle up to 72 deg inside the hand (zero-action replay). Here the grip is designed from the task instead:
  1. contacts: per hand link (finger PP/MP/DP, thumb MC/PP/DP, palm C_MC) the collision-surface sample closest to the
     object's hulls, kept if within TOL; the object's outward normal there (hull SDF gradient);
  2. contact Jacobians d p_contact / d q_finger (22 finger joints, numerical, Newton FK), object frame;
  3. task wrench per frame (pipeline/task_wrench.py: m (a - g), I alpha + w x I w about the COM, from OUR object
     reference), expressed in the object frame (the grasp is locked to the object, so contacts are constant there);
  4. per frame an LP (8-edge friction pyramids with MU_D = mu / (sqrt(2) SF): MuJoCo's pyramidal condim-3 cone is a
     diamond, worst case mu / sqrt(2), plus a safety factor; Ferrari-Canny / Kerr-Roth style): contact forces f_i with
     sum G_i f_i = SF * W(t), every finger contact pressing >= F_MIN (preload: keeps contact, human safety margin
     30-50 %), finger joint torques J^T f within kp * (room to the joint limit), minimising the total normal force;
  5. squeeze targets dq(t) = J^T f(t) / kp per joint (grip force follows the load, Johansson-Westling / Flanagan-Wing),
     led by LEAD frames (anticipatory) and smoothed;
  6. release: a separating direction d (object frame) maximising min_i n_i . d over the near contacts of the opened
     hand (an LP; Ohwovoriole-Roth repelling screws), so withdrawing does not drag the object.
The palm's force comes from the wrist drive (no joint-torque limit here). Only our own reference is read.
"""
import numpy as np
from scipy.optimize import linprog
from scipy.spatial.transform import Rotation as Rot

MU_SIM, SF, F_MIN, TOL, EDGES = 1.0, 1.5, 1.5, 0.004, 8
LINKS = ([f'{f}_{s}' for f in ('index', 'middle', 'ring', 'pinky') for s in ('PP', 'MP', 'DP')]
         + ['thumb_MC', 'thumb_PP', 'thumb_DP', 'hand_C_MC'])


def world_points(bq, body_ids, local):
    return Rot.from_quat(bq[body_ids, 3:7]).apply(local) + bq[body_ids, :3]


def find_contacts(bq, side, bodies, pb, pl, sdf, R_o, p_o, tol=TOL):
    """Per link: closest collision sample to the object within TOL. Object frame point p (on the surface), outward n."""
    Xo = R_o.inv().apply(world_points(bq, pb, pl) - p_o); d = sdf(Xo); out = []
    for name in LINKS:
        b = bodies.get(f'{side}_{name}')
        sel = np.nonzero(pb == b)[0] if b is not None else []
        if not len(sel):
            continue
        i = sel[np.argmin(d[sel])]
        if d[i] > tol:
            continue
        n = sdf.grad(Xo[i:i + 1])[0]
        out.append(dict(link=name, body=int(b), local=pl[i], p=Xo[i] - d[i] * n, n=n, gap_mm=round(1000 * float(d[i]), 1)))
    return out


def contact_jacobians(fk, q, o, contacts, R_o, h=1e-4):
    """J[i] (3 x 22): object-frame velocity of contact i per unit finger joint velocity of the hand at joint offset o."""
    base = fk(q); J = np.zeros((len(contacts), 3, 22))
    b = np.array([c['body'] for c in contacts]); loc = np.array([c['local'] for c in contacts])
    x0 = world_points(base, b, loc)
    for k in range(22):
        qq = q.copy(); qq[o + 7 + k] += h
        J[:, :, k] = R_o.inv().apply(world_points(fk(qq), b, loc) - x0) / h
    return J


def pyramid(n, mu):
    """EDGES unit-normal-force edge vectors of the friction pyramid for a force pushing INTO the object (normal -n)."""
    t1 = np.cross(n, [1.0, 0, 0]) if abs(n[0]) < 0.9 else np.cross(n, [0, 1.0, 0]); t1 /= np.linalg.norm(t1); t2 = np.cross(n, t1)
    th = 2 * np.pi * np.arange(EDGES) / EDGES
    return np.stack([-n + mu * (np.cos(a) * t1 + np.sin(a) * t2) for a in th])          # (EDGES, 3)


class ForceDesign:
    """Precomputed LP pieces for one locked grasp; solve(W) gives contact forces and finger joint torques."""

    def __init__(self, contacts, J, com, kp, room_hi, room_lo, mu=MU_SIM, sf=SF, f_min=F_MIN):
        self.c, self.J, self.sf, self.f_min = contacts, J, sf, f_min
        mu_d = mu / (np.sqrt(2) * sf); nc = len(contacts); self.nv = nc * EDGES
        self.E = np.stack([pyramid(c['n'], mu_d) for c in contacts])                        # (nc, EDGES, 3)
        r = np.array([c['p'] for c in contacts]) - com
        Gf = self.E.reshape(-1, 3).T                                                          # (3, nv)
        Gt = np.cross(np.repeat(r, EDGES, 0), self.E.reshape(-1, 3)).T                        # (3, nv)
        self.G = np.vstack([Gf, Gt])                                                          # (6, nv)
        T = np.einsum('ixk,iex->kie', J, self.E).reshape(22, -1)                              # joint torque per edge weight
        self.finger = np.array([c['link'] != 'hand_C_MC' for c in contacts])
        self.A_ub = np.vstack([T, -T]); self.b_ub = np.concatenate([kp * room_hi, kp * room_lo])
        pre = np.zeros((nc, self.nv))                                                         # preload: -sum_e lam <= -F_MIN
        for i in range(nc):
            pre[i, i * EDGES:(i + 1) * EDGES] = -1.0
        self.A_pre = pre[self.finger]; self.T = T

    def solve(self, W):
        """W (6,) wrench the hand must apply about the COM (object frame). Returns (lam, tau) or (None, None)."""
        A_ub = np.vstack([self.A_ub, self.A_pre]); b_ub = np.concatenate([self.b_ub, -self.f_min * np.ones(len(self.A_pre))])
        r = linprog(np.ones(self.nv), A_ub=A_ub, b_ub=b_ub, A_eq=self.G, b_eq=self.sf * W, bounds=(0, None), method='highs')
        if r.status != 0:
            return None, None
        return r.x, self.T @ r.x

    def normal_forces(self, lam):
        return lam.reshape(len(self.c), EDGES).sum(1)


def separating_direction(normals):
    """Unit d maximising min_i n_i . d (object frame): moving the hand along d leaves every near contact. Returns (d, s)."""
    n = np.asarray(normals, float)
    if not len(n):
        return np.zeros(3), 1.0
    d0 = n.mean(0); d0 = d0 / max(np.linalg.norm(d0), 1e-9)          # straight away from the near surfaces, if it clears all
    if (n @ d0).min() > 0.05:
        return d0, float((n @ d0).min())
    # otherwise the LP over (d, s): max s  s.t.  n_i . d >= s,  -1 <= d <= 1
    r = linprog(np.r_[0, 0, 0, -1.0], A_ub=np.hstack([-n, np.ones((len(n), 1))]), b_ub=np.zeros(len(n)),
                bounds=[(-1, 1)] * 3 + [(None, None)], method='highs')
    d = r.x[:3]; s = -r.fun
    return d / max(np.linalg.norm(d), 1e-9), s / max(np.linalg.norm(d), 1e-9)
