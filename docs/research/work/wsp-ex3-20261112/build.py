"""Build each tested edit version deterministically from the original actor.npz.

Usage: python -I build.py ORIGINAL_ACTOR_NPZ VERSION OUT_NPZ
Versions are cumulative only where stated. Idle units were chosen from the census of rollout 1 (units whose
pre-activation stayed below -1 for every recorded frame); see README.md.
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net, edits

CH_J6 = 78          # private stream coordinate for the Joint6_R limit (least damage when cleared, census of rollout 1)
GATE_J6 = 887       # idle block-0 unit (max pre-activation -1.50 over rollout 1)


def v02(w):
    """Joint6_R virtual limit: gate = 10*relu((q - ref)_J6R - 0.42 rad) from input 47 (= ref - q of Joint6_R);
    head: Joint6_R pre-tanh -= 6 per unit gate at stream rms 1.2 (K = 60 per rad)."""
    w = edits.privatize_coordinate(w, CH_J6)
    w = edits.gate_unit_block0(w, GATE_J6, {47: -1.0}, 0.42, 10.0, CH_J6)
    return edits.head_row(w, CH_J6, {5: -6.0}, 1.2)


def v03(w):
    """As v02 with threshold 0.25 rad: keeps Joint6_R within ref + ~0.3, which keeps the simulator's wrist-pair
    coupling from clipping Joint7_R (|J7_R ref| ~1.23-1.25 during the handover needs |J6_R| <= 0.636, J6_R ref 0.24-0.38)
    and matches the upper 2-sd edge of the training distribution of this offset (+0.28, input batch-norm statistics)."""
    w = edits.privatize_coordinate(w, CH_J6)
    w = edits.gate_unit_block0(w, GATE_J6, {47: -1.0}, 0.25, 10.0, CH_J6)
    return edits.head_row(w, CH_J6, {5: -6.0}, 1.2)


def limit(w, ch, unit, arm_index, side, k_sd=1.5, kappa=10.0, per_unit=6.0):
    """One-sided virtual limit on an arm joint's offset from its reference (q - ref), on private coordinate ch
    (which must already be privatized, together with every other channel, so the readout sees the final embedding).
    arm_index 0..13 (R J1..J7, L J1..J7) -> input 42+arm_index (= ref - q), output joint id. side 'upper' or 'lower'.
    Threshold: training mean of the offset +/- k_sd training sd (input batch-norm statistics of the actor itself).
    Gain: per_unit pre-tanh per unit gate (gate = kappa * excess in rad) at stream rms 1.2, i.e. K = 60 per rad."""
    i = 42 + arm_index
    out = arm_index if arm_index < 7 else 29 + arm_index - 7
    mu = -float(w['batch_stats/input_norm/running_mean'][i]); sd = float(np.sqrt(w['batch_stats/input_norm/running_variance'][i]))
    if side == 'upper':   # gate on (q - ref) - (mu + k sd) = -x_i - th
        w = edits.gate_unit_block0(w, unit, {i: -1.0}, mu + k_sd * sd, kappa, ch)
        return edits.head_row(w, ch, {out: -per_unit}, 1.2)
    w = edits.gate_unit_block0(w, unit, {i: 1.0}, -(mu - k_sd * sd), kappa, ch)   # x_i - (-(mu - k sd))
    return edits.head_row(w, ch, {out: per_unit}, 1.2)


def limits(w, specs, **kw):
    """specs: list of (channel, gate unit, arm_index, side). Privatize all channels first, then build the gates."""
    for ch, *_ in specs:
        w = edits.privatize_coordinate(w, ch)
    for ch, unit, arm_index, side in specs:
        w = limit(w, ch, unit, arm_index, side, **kw)
    return w


def v04(w):
    """Virtual limits at the training mean +/- 1.5 sd of the joint offsets that drift in the failed rollouts 1 and 3
    but not in the successful rollout 2: Joint6_R upper (+0.222), Joint7_L upper (+0.275), Joint5_L lower (-0.079).
    (Joint4_L also drifts but its input cannot be read cleanly from h0: readout correlation 0.66.)"""
    return limits(w, [(78, 887, 5, 'upper'), (39, 777, 13, 'upper'), (159, 322, 11, 'lower')])


LW = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lwrist_controller.json')))


def lwrist(w, ch, unit, threshold=0.20, kappa=10.0, per_unit=6.0):
    """Left-wrist orientation controller on private coordinate ch (already privatized).
    Gate = kappa * relu(sum_k c_k (ref - q)_{left J_k} - threshold): the rotation the left wrist needs about body axis
    n = (0,1,1)/sqrt2, linearised with the angular Jacobian at reference frame 290 (lwrist_controller.json).
    Output: Joint5-7_L pre-tanh += per_unit * dq567 / dq567[0] per unit gate (dq567 = J567^-1 n), at stream rms 1.2."""
    terms = {49 + k: LW['c'][k] for k in range(7)}
    w = edits.gate_unit_block0(w, unit, terms, threshold, kappa, ch)
    d = np.array(LW['dq567_per_rad']); d = d / d[0]
    return edits.head_row(w, ch, {33: per_unit * d[0], 34: per_unit * d[1], 35: per_unit * d[2]}, 1.2)


def v05(w):
    """Joint6_R upper limit (training mean + 1.5 sd, coordinate 78) + left-wrist orientation controller
    (threshold 0.20 rad along n, the level of the only successful handover seen, rollout 2; coordinate 39)."""
    for ch in (78, 39):
        w = edits.privatize_coordinate(w, ch)
    w = limit(w, 78, 887, 5, 'upper')
    return lwrist(w, 39, 777)


def nuisance(w, seed, sd=0.01):
    """Robustness probe, not an edit: add N(0, sd^2) to the 58 output biases (seeded)."""
    w = edits.copy(w)
    w['params/mean_bias'] = (w['params/mean_bias'] + np.random.default_rng(seed).normal(0, sd, 58)).astype(np.float32)
    return w


VERSIONS = {'v02': v02, 'v03': v03, 'v04': v04, 'v05': v05}

LWP = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lwrist_pos_controller.json')))


def lwrist_pos(w, ch, unit, kappa=100.0, per_cm=1.0):
    """End-phase left-wrist position controller on private coordinate ch (already privatized).
    Gate = kappa * relu(m . e - threshold), e = left-wrist position error in its body frame (inputs 158:161),
    m and threshold from lwrist_pos_controller.json (gate 1 per cm of excess). Output: Joint1-7_L pre-tanh
    += per_cm * dq_k per unit gate, dq = pinv(Jp) m (rad per m), at stream rms 1.2."""
    m = LWP['m_body']
    w = edits.gate_unit_block0(w, unit, {158 + k: m[k] for k in range(3)}, LWP['threshold_m'], kappa, ch)
    return edits.head_row(w, ch, {29 + k: per_cm * LWP['dq_per_m'][k] for k in range(7)}, 1.2)


def v06(w):
    """v05 + end-phase left-wrist position controller (coordinate 159, gate unit 322)."""
    for ch in (78, 39, 159):
        w = edits.privatize_coordinate(w, ch)
    w = limit(w, 78, 887, 5, 'upper')
    w = lwrist(w, 39, 777)
    return lwrist_pos(w, 159, 322)


VERSIONS['v06'] = v06


def lrelease(w, ch, unit, k_sd=3.0, kappa=10.0, per_unit=-1.5):
    """Left-hand release primitive on private coordinate ch (already privatized).
    Gate = kappa * relu(-(mean of the 22 left finger commands, ref - q, inputs 187:209) - th), th = -(training mean
    - k_sd * sd of that mean), sd from the input batch-norm statistics assuming independent inputs (-0.144 for k_sd 3).
    Fires only when the reference opens the left hand ahead of the fingers (release after placing, ~frame 900; the
    mean never fell below -0.10 before frame 900 in rollouts 1-6). Output: all 22 left finger pre-tanh += per_unit per
    unit gate (opens the hand), at stream rms 1.2."""
    idx = list(range(187, 209))
    mu = w['batch_stats/input_norm/running_mean'][idx].astype(np.float64)
    var = w['batch_stats/input_norm/running_variance'][idx].astype(np.float64)
    m, sd = mu.mean(), np.sqrt(var.sum()) / len(idx)
    th = -(m - k_sd * sd)                       # gate on -mean - th > 0  <=>  mean < m - k sd
    w = edits.gate_unit_block0(w, unit, {i: -1.0 / len(idx) for i in idx}, th, kappa, ch)
    return edits.head_row(w, ch, {j: per_unit for j in range(36, 58)}, 1.2)


def v07(w):
    """v06 + left-hand release primitive (coordinate 161, gate unit 67)."""
    for ch in (78, 39, 159, 161):
        w = edits.privatize_coordinate(w, ch)
    w = limit(w, 78, 887, 5, 'upper')
    w = lwrist(w, 39, 777)
    w = lwrist_pos(w, 159, 322)
    return lrelease(w, 161, 67)


VERSIONS['v07'] = v07


if __name__ == '__main__':
    src, ver, out = sys.argv[1:4]
    w0 = net.load(src)
    w1 = VERSIONS[ver](w0)
    assert all(w1[k].shape == w0[k].shape and w1[k].dtype == w0[k].dtype for k in w0)
    edits.save(w1, out)
    d = edits.diff(w0, w1)
    print(json.dumps({'version': ver, 'out': out, 'changed': sum(v['changed'] for v in d.values()),
                      'zeroed': sum(v['zeroed'] for v in d.values())}))
