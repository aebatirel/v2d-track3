# Guard-bridge reference repair + eval 15 two-hand (perfect-following lane), pre-registered 1 Nov 2026 ~20:45 UTC,
# before any GPU result of this batch (batch 1, pf-hands, still training; none of its results seen)

Session: perfect-following (session_01D9UJC8Nz9EEFNmz2yzimzN). Job: `ops/jobs/pf_arms.sh` with `BRIDGE=1`; repair
`tools/guard_bridge.py`; events `events.json` (here); verdicts `tools/pf_verdict.py`.

## 1. Evidence [M] (GT-free; docs/analysis/perfect-following-20261101/README.md)
- The packed eval perceptions re-acquire the blue cup through TRACK_GUARD at eval 14 f46, eval 32 f21 and f34, eval 33
  f91 (and nowhere else in the 20 eval logs). Each leaves a one-frame jump of 11–20 cm in the reference (eval 32: the
  cup's axis flips by ~150° at f21 and back at f34). H5p7 error onsets: 14 f42–46 (9 / 10 draws), 32 f19 (10 / 10),
  33 f91–93 (6 / 10).
- Distance of the cup to the nearest perceived fingertip: eval 14 f37–45 3.1–13.9 cm, f46 0.3 cm (the tracker drifted out
  of the hand before the re-acquisition); eval 32 f24–33 3.2–9.7 cm, f34 0.1 cm; eval 33 f79–90 1.7–4.1 cm, f91 0.3 cm.
- No public episode run with TRACK_GUARD re-acquired an object during tracking (checked: orcB ep11 / 13 / 31, twin21
  base, twin11v3; public sweep tracks of the mesh lane have no jump > 7.2 cm), so **no public twin test exists for
  this repair** [M]. The case rests on physics (no hand, no robot, can move a held cup 19 cm in 50 ms) and on the
  two-reference eval rule below.
- CPU zero-action replays (one each): eval 14 single-hand 0.293 → bridged 0.558; two-hand 0.586 → bridged 0.573.

## 2. Repair rule (tools/guard_bridge.py, frozen at this commit)
Per object with events: two events < 20 frames apart bound a span (r1 .. r2−1); otherwise the span is the run of frames
before the event with fingertip distance > 3 cm (≤ 30 frames; nothing if the re-acquired pose itself is ≥ 3 cm from
every fingertip). The span is replaced by interpolation between its boundary frames (linear / slerp); a remaining jump
> 4 cm or 30° is spread over a 6-frame ramp ending at the event. Only the object pose columns change.
Result on the packed bases [M]: eval 14 f37–45 (max shift 18.8 cm); eval 32 f21–33 (15.9 cm); eval 33 f90 + ramp f86–90.

## 3. Boxes and arms (recipe = pf-hands PREREG §2; the packed episode's env, e.g. eval 33 CURR_SCALE 0.4)
- pfC: BRIDGE=1, eval 14, arms s and 2h, seeds 42 / 43.
- pfD: BRIDGE=1, evals 32 and 33 arm s, eval 15 arm 2h (no events: not bridged), seeds 42 / 43.

## 4. Rule per (episode, arm)
- Seed choice as pf-hands §4.1. Bridged cells skip the training-box gate (its yardsticks differ) and always get the
  10 fresh official draws; eval 15 keeps the gate (> 0.9057, its H5p7 mean).
- Bridged cells are scored by tools/dr_score.py against BOTH P (the packed reference) and B (the candidate's own bridged
  reference; own-reference check on B). **PASS** = the full pack-9b swap rule (a, b, c, s) on B **and** clause (a) on P
  (mean sim_vs_ref vs the packed reference not below the packed policy's). Inclusion bar (binding): gain on B ≥ +0.02.
- Eval 15 (2h, unbridged): pf-hands §4 verbatim, and, like 14 / 16, it needs the pf-hands public PASS (pfA) to enter
  a pack.
- If both a bridged and an unbridged candidate of eval 14 pass, the one with the larger gain on its own reference is
  taken, reported with both yardsticks.

## 5. Cost [E]
pfC ≈ 3.5 h ≈ $5; pfD ≈ 5 h (3 pairs per seed: waves of 2 + 1) ≈ $7. Batch ≈ $12; with batch 1 ≈ $23 of $110.
