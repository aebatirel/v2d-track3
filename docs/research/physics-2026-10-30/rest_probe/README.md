# Do the robot hands disturb objects "at rest" in the zero-action replay? (1 Nov 2026, CPU) [M]

**Asked by** keen-heisenberg (06:57 UTC), from bold-albattani's f0 survey (a6923c5).
- In the pack's FlashCHORD zero-action rest checks, pots on evals 3 / 5 / 6 / 8 move 17.5–65 mm and spoons on
  16 / 33 move ~24 mm / 24°. Hands-free they move only 0.2–1.8 mm.
- [H]: the robot hands touch them during the replayed approach.
- Falsifier: with the hands parked, the objects stay within 5 mm / 2°.

**Method** (`scripts/rest_probe.py`):
- Packed eval references and assets: `refs/sf/ep<N>/assets`, md5s = packed_refs.json. FlashCHORD at the pin, 1 world,
  CPU, EMB=sharpa_hands_mid.
- **hands:** as `tools/trace_rollout.py zero` (explicit reset at frame 0, VOC 0, zero action: the hands follow the
  reference). This is the pack's rest check.
- **parked:** the same reset, actuator gains zeroed and wrists parked 3 m away, no drive.
- Window per object as `tools/rest_check.py`: frames 0 … its first hold start − 6.
- Reported per object: the largest displacement / rotation from its simulated frame-0 pose, and in the hands run
  every robot-body contact inside that window (first frame, body).
- (A first run had a parsing bug: object bodies are named `track3_<obj>_object`. Fixed; numbers below are from the
  fixed run. The box patch set changes nothing at zero action, checked on all 6.)

| eval | object | window | hands: max mm / deg | parked: max mm / deg | first robot touch in the window (frame, body) | pack's GPU rest check |
|---|---|---|---|---|---|---|
| 3 | white_pot | f0–51 | 4.9 / 2.7 | 6.0 / 6.8 | f37, left ring DP (+ pinky, index DP) | 65.1 / 11.4 |
| 3 | wooden_spoon | f0–29 | 2.9 / 0.9 | 3.3 / 13.8 | none | 2.4 / 1.6 |
| 5 | white_pot | f0–21 | **25.7 / 9.0** | 3.3 / 1.7 | **f3, left index DP** (20 steps) | — |
| 5 | wooden_spoon | f0–26 | 5.4 / 11.7 | 4.4 / 4.7 | f20, right middle DP | — |
| 6 | white_pot | f0–26 | 5.3 / 3.1 | 11.6 / 11.8 | f4, left middle DP (+ pinky, thumb DP) | — |
| 6 | wooden_spoon | f0–21 | 7.4 / 3.8 | **198 / 176** (falls) | f9, right thumb PP | — |
| 8 | white_pot | f0–83 | **41.7 / 15.4** | 8.9 / 8.2 | **f13, left pinky DP** (+ index DP ×8) | — |
| 8 | beige_cup | f0–33 | 2.5 / 1.5 | 26.6 / 15.4 | none | — |
| 16 | wooden_spoon | f0–24 | 4.5 / 17.8 | 8.3 / **29.1** | f20, right thumb PP | 4.9 / 24.2 |
| 33 | wooden_spoon | f0–42 | **87.0 / 31.5** | 10.6 / 19.5 | **f24, right hand C_MC (palm) + pinky MC** | 24.5 / 21.7 |

**Reading:**
- **[H] holds for evals 5, 8 and 33.** The robot touches the object inside its "rest" window, and with the hands
  parked the motion is far smaller:
  - eval 5 pot: fingertip from f3;
  - eval 8 pot: fingertips from f13;
  - eval 33 spoon: palm at f24.
  - The touching bodies are mostly distal phalanges (DP) of the approaching hand, so the robot's fingers reach the
    object before our MANO hold phase starts.
- **Eval 16:** the spoon's rotation is not the hands. It rotates more with them parked (29° vs 18°): an unstable rest
  pose or support.
- **Eval 6:** mixed. The hands touch the pot at f4 but it moves only 5 mm. Parked, the spoon falls off (198 mm): it
  needs the hand, or a pot that does not move, to stay put.
- **Eval 3:** the pack's 65 mm pot motion does not reproduce on this CPU run (4.9 mm), although a fingertip touches
  it at f37. The replay is chaotic; the pack ran on GPU.
- **Hands-free instability also exists,** beyond the 5 mm / 2° rest bound when parked: eval 3 spoon 14°, eval 6
  spoon, eval 8 cup 27 mm, eval 16 spoon 29°, eval 33 spoon 20°. So the support or pose problem bold-albattani
  found is real alongside the hand contact.
