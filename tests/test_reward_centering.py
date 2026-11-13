"""CPU test of FC_RC reward centring in ops/box/fc_v2d_fdr.py: b tracks the mean raw reward of non-terminal
transitions (running average, then EMA), every reward is shifted by the b in force before the update, and terminating
worlds get the absorbing-state correction -gamma b / (1 - gamma). Also checks the incentive claim: with the correction,
a terminating transition's centred return equals the uncentred one shifted by the same constant as continuing.
Needs warp-lang 1.14 and FlashCHORD's src on PYTHONPATH:
  PYTHONPATH=<video_to_data>/robotic_grounding/flash_chord/src python tests/test_reward_centering.py"""
import importlib.util, os, sys
from types import SimpleNamespace as NS
import numpy as np
import warp as wp

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fc_v2d_fdr", os.path.join(HERE, "..", "ops", "box", "fc_v2d_fdr.py"))
fdr = importlib.util.module_from_spec(spec); sys.modules["fc_v2d_fdr"] = fdr; spec.loader.exec_module(fdr)


def main():
    wp.init()
    os.environ.update(FC_RC="1", FC_RC_GAMMA="0.99", FC_RC_BETA="0.01")
    rng = np.random.default_rng(0)
    W, gamma, beta = 64, 0.99, 0.01
    obj = NS(world_count=W, buffers=NS(score=wp.zeros(W, dtype=wp.float32, device="cpu")))
    b, n = 0.0, 0
    for step in range(300):
        raw = rng.normal(1.0 + 0.2 * np.sin(step / 50), 0.3, W).astype(np.float32)
        term = (rng.random(W) < 0.05).astype(np.int32)
        raw[term == 1] -= 5.0                                   # the stock termination penalty x frame_dt
        obj.buffers.score.assign(raw)
        fdr.center_reward(obj, wp.array(term, dtype=wp.int32, device="cpu"))
        got = obj.buffers.score.numpy()
        want = raw - b - term * gamma * b / (1 - gamma)
        assert np.allclose(got, want, atol=1e-4), (step, np.abs(got - want).max())
        m = float(raw[term == 0].mean())                        # reference update, as the kernel
        rate = max(beta, 1.0 / (n + 1)); b = b + rate * (m - b); n += 1
        st = obj.v2d_rc_state.numpy()
        assert abs(st[0] - b) < 1e-3 and st[1] == n, (step, st, b, n)
    print(f"b after 300 steps: kernel {obj.v2d_rc_state.numpy()[0]:.4f}, reference {b:.4f}")
    # incentive: from any state, (continue forever at reward r) minus (terminate now with penalty p) is the same with and
    # without centring, i.e. sum_k gamma^k (r - b) - (p - b - gamma b/(1-gamma)) = sum_k gamma^k r - p
    for r, p_ in ((0.3, -5.0), (1.2, -5.0)):
        cont_c, term_c = (r - b) / (1 - gamma), p_ - b - gamma * b / (1 - gamma)
        cont_u, term_u = r / (1 - gamma), p_
        assert abs((cont_c - term_c) - (cont_u - term_u)) < 1e-6
    print("reward centring checks passed (shift, terminal correction, running mean, incentive invariance)")


if __name__ == "__main__":
    main()
