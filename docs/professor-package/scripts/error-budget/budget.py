"""Task 2: error budget. Perturb public GT and score with the official Track 3 metric functions."""
import json, sys
import numpy as np
from common import *
from verts import vertex_table

MODS = {m: load_metric(m) for m in ["AUC", "SP-SR", "MP-SR", "RPE", "MPPE"]}
A = MODS["AUC"]
EPS = all_episodes()
VMODE = sys.argv[1] if len(sys.argv) > 1 else "box"
VERTS = vertex_table(sorted({n for e in EPS for n in e["names"]}), VMODE)
R = 8  # random repeats


def metrics(ach, ref, names):
    """ach/ref: [T,N,7] xyz+qxyzw. Mirrors score(): normalise, warp to reference start, metric."""
    a = A._normalise_quaternions(ach[:, None], "submission", ValueError)
    r = A._normalise_quaternions(ref[:, None], "solution", ValueError)
    a = MODS["AUC"]._warp_to_reference_start(a, r)
    ids = np.arange(ach.shape[1])
    v = np.stack([VERTS[n] for n in names])
    return dict(AUC=MODS["AUC"]._add_auc(MODS["AUC"]._object_add(a, r, v)),
                SPSR=float(np.mean(MODS["SP-SR"]._spider_success(a, r))),
                MPSR=float(np.mean(MODS["MP-SR"]._maniptrans_success(a, r, ids))),
                RPE=MODS["RPE"]._relative_position_error_cm(a, r),
                MPPE=MODS["MPPE"]._mean_per_point_error_cm(a, r))


def rand_axis(rng, n=None):
    v = rng.normal(size=(3,) if n is None else (n, 3))
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def onset(p, j, dmin=0.03, rmin=10):
    x, q = p[:, j, :3], p[:, j, 3:]
    m = (np.linalg.norm(x - x[0], axis=1) > dmin) | (np.degrees(qangle(q, q[0])) > rmin)
    return int(np.argmax(m)) if m.any() else None


def first_motion_end(p, j, dt):
    x, q = p[:, j, :3], p[:, j, 3:]
    v = np.r_[0, np.linalg.norm(np.diff(x, axis=0), axis=1)] / dt
    w = np.r_[0, qangle(q[1:], q[:-1])] / dt
    k = np.ones(5) / 5
    mv = (np.convolve(v, k, "same") > 0.03) | (np.convolve(w, k, "same") > np.radians(15))
    o = onset(p, j)
    if o is None:
        return None
    i, still = o, 0
    while i < len(mv) and still < 10:  # segment ends after 10 still frames (~0.5 s)
        still = still + 1 if not mv[i] else 0
        i += 1
    return min(i - still, len(mv) - 1)


def most_moving(p):
    return int(np.argmax([np.sum(np.linalg.norm(np.diff(p[:, j, :3], axis=0), axis=1)) for j in range(p.shape[1])]))


# ---------- perturbations: f(p, rng, e) -> perturbed copy (p is [T,N,7]) ----------
def scale(s):
    def f(p, rng, e):
        o = p.copy(); c = p[0, 0, :3]
        o[..., :3] = c + (1 + s) * (p[..., :3] - c); return o
    return f


def anchor_rot(deg, axis=None):
    def f(p, rng, e):
        o = p.copy(); ax = rand_axis(rng) if axis is None else axis
        o[0, 0, 3:] = qmul(qaxang(ax, np.radians(deg)), p[0, 0, 3:]); return o
    return f


def anchor_trans(cm):
    def f(p, rng, e):
        o = p.copy(); o[0, 0, :3] += rand_axis(rng) * cm / 100; return o
    return f


def lag(k):
    def f(p, rng, e):
        idx = np.clip(np.arange(len(p)) - k, 0, None); return p[idx].copy()
    return f


def jitter(cm, anchor=True, rot_deg=0.0):
    def f(p, rng, e):
        o = p.copy()
        o[..., :3] += rng.normal(size=p[..., :3].shape) * cm / 100
        if rot_deg:
            rv = rng.normal(size=p[..., :3].shape) * np.radians(rot_deg)
            ang = np.linalg.norm(rv, axis=-1)
            o[..., 3:] = qmul(qaxang(rv + 1e-12, ang), p[..., 3:])
        if not anchor:
            o[0, 0] = p[0, 0]
        return o
    return f


def drift(cm, common=True, rot_deg=0.0):
    def f(p, rng, e):
        o = p.copy(); T, N, _ = p.shape; ramp = np.linspace(0, 1, T)[:, None]
        u = np.repeat(rand_axis(rng)[None], N, 0) if common else rand_axis(rng, N)
        for j in range(N):
            o[:, j, :3] += ramp * u[j] * cm / 100
        if rot_deg:  # common world-frame rotational drift about slot-0 start, random axis
            ax = rand_axis(rng); c = p[0, 0, :3]
            qd = qaxang(np.repeat(ax[None], T, 0), np.radians(rot_deg) * ramp[:, 0])
            for j in range(N):
                o[:, j, :3] = c + qrot(qd, o[:, j, :3] - c)
                o[:, j, 3:] = qmul(qd, o[:, j, 3:])
        return o
    return f


def body_offset(rot_deg=0.0, trans_cm=0.0, slot=1):
    def f(p, rng, e):
        o = p.copy()
        if p.shape[1] <= slot:
            return o
        if rot_deg:
            o[:, slot, 3:] = qmul(p[:, slot, 3:], qaxang(rand_axis(rng), np.radians(rot_deg))[None])
        if trans_cm:
            d = rand_axis(rng) * trans_cm / 100
            o[:, slot, :3] = p[:, slot, :3] + qrot(p[:, slot, 3:], np.repeat(d[None], len(p), 0))
        return o
    return f


def drop(which="most", mode="onset"):
    def f(p, rng, e):
        o = p.copy(); dt = np.median(np.diff(e["ts"]))
        js = [most_moving(p)] if which == "most" else ([1] if which == "slot1" else range(p.shape[1]))
        for j in js:
            if j >= p.shape[1]:
                continue
            t0 = 0 if mode == "start" else (onset(p, j) if mode == "onset" else first_motion_end(p, j, dt))
            if t0 is not None:
                o[t0:, j] = p[t0, j]
        return o
    return f


def run(f, repeats=1, multi_only=False):
    per = []
    for e in EPS:
        if multi_only and len(e["names"]) < 2:
            continue
        acc = []
        for r in range(repeats):
            rng = np.random.default_rng(1000 * e["ep"] + r)
            acc.append(metrics(f(e["pose"], rng, e), e["pose"], e["names"]))
        per.append({k: float(np.mean([a[k] for a in acc])) for k in acc[0]} | {"ep": e["ep"]})
    mean = {k: float(np.mean([x[k] for x in per])) for k in ["AUC", "SPSR", "MPSR", "RPE", "MPPE"]}
    return mean, per


Z = np.array([0, 0, 1.0]); X = np.array([1.0, 0, 0])
CASES = [("GT (no error)", lag(0), 1, False)]
CASES += [(f"scale +{int(s*100)}%", scale(s), 1, False) for s in [0.01, 0.03, 0.05, 0.10]]
CASES += [("scale -10%", scale(-0.10), 1, False)]
CASES += [(f"slot0 init rot {d} deg (random axis)", anchor_rot(d), R, False) for d in [2, 5, 10]]
CASES += [(f"slot0 init rot {d} deg (yaw, world z)", anchor_rot(d, Z), 1, False) for d in [2, 5, 10]]
CASES += [(f"slot0 init trans {c} cm", anchor_trans(c), R, False) for c in [1, 3]]
CASES += [(f"lag {k} fr", lag(k), 1, False) for k in [1, 3, 5]]
CASES += [(f"jitter {c} cm/axis", jitter(c), R, False) for c in [0.5, 1, 2]]
CASES += [(f"jitter {c} cm/axis, anchor exact", jitter(c, anchor=False), R, False) for c in [0.5, 1, 2]]
CASES += [(f"rot jitter {d} deg/axis", jitter(0, rot_deg=d), R, False) for d in [1, 3, 5]]
CASES += [(f"drift {c} cm common", drift(c), R, False) for c in [1, 3, 5]]
CASES += [(f"drift {c} cm per-object", drift(c, common=False), R, False) for c in [1, 3, 5]]
CASES += [(f"rot drift {d} deg common", drift(0, rot_deg=d), R, False) for d in [1, 3, 5]]
for mo in [False, True]:
    CASES += [(f"slot1 body rot {d} deg" + (" [multi]" if mo else ""), body_offset(rot_deg=d), R, mo) for d in [5, 15]]
    CASES += [(f"slot1 body trans {c} cm" + (" [multi]" if mo else ""), body_offset(trans_cm=c), R, mo) for c in [1, 3]]
CASES += [(f"slot0 body rot {d} deg (all frames)", body_offset(rot_deg=d, slot=0), R, False) for d in [5, 15]]
CASES += [("drop most-moving @onset", drop("most", "onset"), 1, False),
          ("drop most-moving after 1st motion", drop("most", "after"), 1, False),
          ("drop slot1 @onset [multi]", drop("slot1", "onset"), 1, True),
          ("drop all @onset", drop("all", "onset"), 1, False),
          ("all frozen at frame 0", drop("all", "start"), 1, False)]

if __name__ == "__main__":
    out = {}
    print(f"vertices: {VMODE}")
    print(f"{'perturbation':42s} {'AUC':>6} {'SP-SR':>6} {'MP-SR':>6} {'RPE cm':>7} {'MPPE cm':>7}")
    for name, f, rep, mo in CASES:
        m, per = run(f, rep, mo)
        out[name] = dict(mean=m, per=per)
        print(f"{name:42s} {m['AUC']:6.3f} {m['SPSR']:6.2f} {m['MPSR']:6.2f} {m['RPE']:7.2f} {m['MPPE']:7.2f}", flush=True)
    json.dump(out, open(f"budget_{VMODE}.json", "w"), indent=1)
