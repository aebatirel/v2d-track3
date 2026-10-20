"""Policy-side error models applied to public GT and scored with the official Track 3 metric
functions (mesh-sampled AUC vertices). Answers: how much score does a given tracking error cost,
and how do perception and policy errors compose. Research only; GT used for analysis."""
import sys
import numpy as np
from common14 import *

R = 4
EPS = [dict(e, p=fill_gaps(e["pose"], e["vis"])) for e in all_episodes()]
dt = 1 / FPS


def rand_axis(rng, n=None):
    v = rng.normal(size=(3,) if n is None else (n, 3))
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def qrot(q, v):
    qv = np.concatenate([v, np.zeros(v.shape[:-1] + (1,))], -1)
    return qmul(qmul(q, qv), qconj(q))[..., :3]


def motion_mask(p, j):
    x = p[:, j, :3]; q = p[:, j, 3:]
    v = np.r_[0, np.linalg.norm(np.diff(x, axis=0), axis=1)] / dt
    w = np.r_[0, qangle(q[1:], q[:-1])] / dt
    k = np.ones(5) / 5
    return (np.convolve(v, k, "same") > 0.03) | (np.convolve(w, k, "same") > np.radians(15))


def most_moving(p):
    return int(np.argmax([np.sum(np.linalg.norm(np.diff(p[:, j, :3], axis=0), axis=1)) for j in range(p.shape[1])]))


# ---------------- perception-side (reference) models, as in note 02 ----------------
def anchor(cm=0.0, deg=0.0):
    def f(p, rng, e):
        o = p.copy()
        if cm:
            o[0, 0, :3] += rand_axis(rng) * cm / 100
        if deg:
            o[0, 0, 3:] = qmul(qaxang(rand_axis(rng), np.radians(deg)), p[0, 0, 3:])
        return o
    return f


def jitter(cm=0.0, deg=0.0, keep0=True):
    def f(p, rng, e):
        o = p.copy()
        o[..., :3] += rng.normal(size=p[..., :3].shape) * cm / 100
        if deg:
            rv = rng.normal(size=p[..., :3].shape) * np.radians(deg)
            o[..., 3:] = qmul(qaxang(rv + 1e-12, np.linalg.norm(rv, axis=-1)), p[..., 3:])
        if keep0:
            o[0, 0] = p[0, 0]
        return o
    return f


def drift(cm):
    def f(p, rng, e):
        o = p.copy(); T, N, _ = p.shape; u = rand_axis(rng)
        o[..., :3] += np.linspace(0, 1, T)[:, None, None] * u * cm / 100
        return o
    return f


def scale(s):
    def f(p, rng, e):
        o = p.copy(); c = p[0, 0, :3]; o[..., :3] = c + (1 + s) * (p[..., :3] - c); return o
    return f


# ---------------- policy-side (tracking) models ----------------
def lowpass(tau):
    """First-order lag of every object toward its reference (pos lerp, rot slerp)."""
    a = dt / (tau + dt)

    def f(p, rng, e):
        o = p.copy()
        for t in range(1, len(p)):
            o[t, :, :3] = o[t-1, :, :3] + a * (p[t, :, :3] - o[t-1, :, :3])
            o[t, :, 3:] = slerp(o[t-1, :, 3:], p[t, :, 3:], a)
        return o
    return f


def settle0(cm=0.0, deg=0.0, persist=False):
    """Sim settle of slot 0 at reset (row 0 differs from reference). The scorer anchors on achieved
    slot-0 row 0, so this acts like an anchor error. persist=True: the settled offset also stays
    while the object is static (more physical); tracked poses while moving are unaffected."""
    def f(p, rng, e):
        o = p.copy()
        ax = rand_axis(rng); ax[2] = 0; ax /= np.linalg.norm(ax) + 1e-12  # tipping about horizontal axis
        dq = qaxang(ax, np.radians(deg)); dz = np.array([0, 0, -cm / 100])
        rows = [0]
        if persist:
            mv = motion_mask(p, 0)
            first = int(np.argmax(mv)) if mv.any() else len(p)
            rows = range(first)
        for t in rows:
            o[t, 0, :3] = p[t, 0, :3] + dz
            o[t, 0, 3:] = qmul(dq, p[t, 0, 3:])
        return o
    return f


def place_offset(cm, deg):
    """After each object's last motion, it rests at a constant offset (imperfect placement)."""
    def f(p, rng, e):
        o = p.copy()
        for j in range(p.shape[1]):
            mv = motion_mask(p, j)
            if not mv.any():
                continue
            last = len(mv) - int(np.argmax(mv[::-1]))
            if last >= len(p):
                continue
            d = rand_axis(rng); d[2] = 0; d /= np.linalg.norm(d) + 1e-12
            ax = rand_axis(rng)
            o[last:, j, :3] += d * cm / 100
            o[last:, j, 3:] = qmul(qaxang(ax, np.radians(deg)), p[last:, j, 3:])
        return o
    return f


def never_moves(which="most"):
    def f(p, rng, e):
        o = p.copy(); js = [most_moving(p)] if which == "most" else range(p.shape[1])
        for j in js:
            o[:, j] = p[0, j]
        return o
    return f


def freeze_mid(frac=0.5):
    """Object follows until frac of its moving frames, then stays where it was (drop/stall)."""
    def f(p, rng, e):
        o = p.copy(); j = most_moving(p); mv = np.where(motion_mask(p, j))[0]
        if len(mv):
            t0 = mv[int(frac * (len(mv) - 1))]
            o[t0:, j] = p[t0, j]
        return o
    return f


def halfspeed_bug(ratio=0.508):
    """Default motion_speed 0.5 export packed by the kit: row f holds source frame ~0.508 f (note 06)."""
    def f(p, rng, e):
        T = len(p); src = np.clip(np.arange(T) * ratio, 0, T - 1)
        lo = np.floor(src).astype(int); hi = np.minimum(lo + 1, T - 1); w = src - lo
        o = p.copy()
        o[..., :3] = p[lo, :, :3] * (1 - w)[:, None, None] + p[hi, :, :3] * w[:, None, None]
        for j in range(p.shape[1]):
            o[:, j, 3:] = slerp(p[lo, j, 3:], p[hi, j, 3:], w)
        return o
    return f


def compose(*fs):
    def f(p, rng, e):
        for g in fs:
            p = g(p, rng, e)
        return p
    return f


def run(fn, reps=R):
    vals = []
    for e in EPS:
        for r in range(reps):
            rng = np.random.default_rng(1000 * e["ep"] + r)
            vals.append(metrics(fn(e["p"], rng, e), e["p"], e["names"]))
    keys = vals[0].keys()
    return {k: float(np.mean([v[k] for v in vals])) for k in keys}


PERC_A = compose(anchor(0.5, 2), jitter(0.5, 2), drift(2), scale(0.01))     # careful stereo (02 "A"-like)
PERC_M = compose(anchor(1.0, 3), jitter(0.8, 3), drift(3), scale(0.03))     # middle
PERC_B = compose(anchor(1.5, 5), jitter(1.0, 3), drift(5), scale(0.10))     # rough mono (02 "B"-like)
POL_GOOD = compose(lowpass(0.10), jitter(0.3, 1), place_offset(1.0, 3), settle0(0.2, 1.5, persist=True))
POL_MID = compose(lowpass(0.20), jitter(0.5, 2), place_offset(2.0, 5), settle0(0.3, 3, persist=True))

CASES = [
    ("GT (no error)", lambda p, r, e: p.copy()),
    ("lowpass tau 0.05 s", lowpass(0.05)),
    ("lowpass tau 0.10 s", lowpass(0.10)),
    ("lowpass tau 0.20 s", lowpass(0.20)),
    ("lowpass tau 0.30 s", lowpass(0.30)),
    ("settle0 slot0 2deg+2mm (row0 only)", settle0(0.2, 2)),
    ("settle0 slot0 5deg+3mm (row0 only)", settle0(0.3, 5)),
    ("settle0 slot0 5deg+3mm persist", settle0(0.3, 5, persist=True)),
    ("settle0 slot0 10deg+5mm persist", settle0(0.5, 10, persist=True)),
    ("place offset 1cm 3deg", place_offset(1.0, 3)),
    ("place offset 2cm 5deg", place_offset(2.0, 5)),
    ("place offset 4cm 10deg", place_offset(4.0, 10)),
    ("contact jitter 3mm 1deg", jitter(0.3, 1)),
    ("most-moving never moves", never_moves()),
    ("most-moving freezes at 50% of motion", freeze_mid(0.5)),
    ("most-moving freezes at 80% of motion", freeze_mid(0.8)),
    ("half-speed export bug (row f = src 0.508f)", halfspeed_bug()),
    ("POL_GOOD (tau .1, 3mm, place 1cm/3d, settle 1.5d)", POL_GOOD),
    ("POL_MID (tau .2, 5mm/2d, place 2cm/5d, settle 3d)", POL_MID),
    ("PERC_A careful stereo", PERC_A),
    ("PERC_A + POL_GOOD", compose(PERC_A, POL_GOOD)),
    ("PERC_A + POL_MID", compose(PERC_A, POL_MID)),
    ("PERC_M middle", PERC_M),
    ("PERC_M + POL_GOOD", compose(PERC_M, POL_GOOD)),
    ("PERC_M + POL_MID", compose(PERC_M, POL_MID)),
    ("PERC_B rough mono", PERC_B),
    ("PERC_B + POL_GOOD", compose(PERC_B, POL_GOOD)),
    ("PERC_B + POL_MID", compose(PERC_B, POL_MID)),
]

if __name__ == "__main__":
    sel = sys.argv[1:] or None
    print(f"{'case':52s} {'AUC':>6} {'SP-SR':>6} {'MP-SR':>6} {'RPE':>6} {'MPPE':>6}", flush=True)
    for name, fn in CASES:
        if sel and not any(s in name for s in sel):
            continue
        m = run(fn, 1 if name.startswith(("GT", "lowpass", "most-moving", "half")) else R)
        print(f"{name:52s} {m['AUC']:6.3f} {m['SPSR']:6.2f} {m['MPSR']:6.2f} {m['RPE']:6.2f} {m['MPPE']:6.2f}", flush=True)
