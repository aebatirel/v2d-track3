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


def nuisance(w, seed, sd=0.01):
    """Robustness probe, not an edit: add N(0, sd^2) to the 58 output biases (seeded)."""
    w = edits.copy(w)
    w['params/mean_bias'] = (w['params/mean_bias'] + np.random.default_rng(seed).normal(0, sd, 58)).astype(np.float32)
    return w


VERSIONS = {'v02': v02, 'v03': v03}

if __name__ == '__main__':
    src, ver, out = sys.argv[1:4]
    w0 = net.load(src)
    w1 = VERSIONS[ver](w0)
    assert all(w1[k].shape == w0[k].shape and w1[k].dtype == w0[k].dtype for k in w0)
    edits.save(w1, out)
    d = edits.diff(w0, w1)
    print(json.dumps({'version': ver, 'out': out, 'changed': sum(v['changed'] for v in d.values()),
                      'zeroed': sum(v['zeroed'] for v in d.values())}))
