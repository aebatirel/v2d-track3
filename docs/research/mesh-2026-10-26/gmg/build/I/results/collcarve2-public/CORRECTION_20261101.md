# Dated correction to this folder's README (1 Nov 2026, 03:10 UTC, collision-carve round-2 Eval-carves step)

These fix statements in `README.md` (written 1 Nov 01:53-02:05 UTC). The README is left as written; read it together
with this file. Source: verify_cc2_0 B1 and verify_cc2_1 B1 (`build/I/verify_cc2_0.md`, `verify_cc2_1.md`). [M] unless
marked.

1. **"T-I17 c1 (the ep24 v6 bundle is not on this machine)"** (section "What this means", last bullet) **is false.**
   - Both ep24 bundles are on this machine: v6 in `<scratch>/gmg/runs/20261031-b4ext6-90c8cce/bundle/public/ep24` and
     v4 in `<scratch>/gmg/runs/20261031-b4ext4-b61e8aa/bundle/public/ep24`. The fi4o r0 was built from v4.
   - c1 does not need a bundle anyway: its pieces are committed (`build/I/results/slot2-ep24/fi4o/r0`), and its poses
     are determined-wright's reference (HF store).
   - The same false premise appears in PREREG F-I5.17 (14), F-I5.18 ("Not run in this step") and
     `collcarve2-evalcheck/README.md` section 5. Those two files are corrected in their own folder and in the build log
     (`build/I.md`, Collision carve round 2, 1 Nov 03:06). PREREG needs a dated entry from the orchestrator (F-I5.19).
   - **c1 has now run, and it fails.** Plain MuJoCo flags the default ep24 pieces as overflowing in 16 of 16 copies,
     where MuJoCo-Warp shows none. The carved pieces overflow in 12 of 16, not >= 15. See
     `build/I/results/collcarve-r2/t_i17_c1/README.md`.
   - Consequence (F-I5.16 (1)(h)): G1 is weaker than MuJoCo-Warp. No F-I5 delivery may be called usable before G1 has
     run in MuJoCo-Warp. Every G1 number in this folder is plain MuJoCo only. Nothing here was delivered, so no verdict
     changes.
2. **"Two cheap, falsifiable changes are open: B4's robust ring profile ..."**: the B4 change is falsified.
   - Measured by verify_cc2_1 B1: three robust variants (median-wall interval, half-sector offset, fitted eccentric /
     oval circle) leave the 12-sector local wall of both blue cups below 0 (ep12 -1.14 to -2.08 mm, ep13 -1.09 to -4.86
     mm).
   - 121-154 of 168-172 rows have a sector under 1.5 mm. At 32 sectors it is still 75-111 rows.
   - Cause: SHELL roughness, about 1 mm per face within a sector. A never-intruding ring cannot keep 1.5 mm on these
     SHELLs.
   - What remains open is a rule change for the orchestrator, e.g. quantile faces with a measured intrusion allowance
     [H, verify_cc2_1]. H-d (one keep-out grid) is still open; verify_cc2_0 N2 classes it as a code defect against
     F-I5.4.
3. **Precision** (verify_cc2_0 N6, verify_cc2_1 N1 / N2 / N6; no verdict changes):
   - "0.05 mm wall left" is the floor of the measurement (the 0.05 mm ray offset), so read it as <= 0.05 mm. With a
     1e-6 m offset the minimum is 0.001 mm.
   - The route-4 boxes are not wholly inside the SHELL. They reach 1.3-2.3 mm outside it, at most 0.19 cm3 per box.
     So "keep-out 0 by construction" should read "measured 0; bounded by <= 0.19 cm3 per box".
   - `contact_gate.json` says `g1_pass: true` in all five folders, but G1 was vacuous: no frame was gated.
