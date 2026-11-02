# Pre-registration: complete-base pitcher as the TRACKING template (2 Nov 2026, tracking-perception session)

Written before any run of this test. [H]: our library_v3 pitcher lacks half its base, so FoundationPose fits the
visible body with a ≈ 6° systematic tilt (physperc O1 / D3: 70 % of the exact-tilt oracle's +0.016 is the pitcher,
ep21 / ep22). Tracking with a template whose base is complete removes part of that tilt.

- Template: `meshes/library_v3p/water_pitcher.glb` (our lathe-completed pitcher, built GT-free on 26 Oct, same body frame
  as library_v3; never used as a tracking template so far). All other objects: library_v3.
- Run: `ops/jobs/perc_vos.sh` with LIB = a copy of library_v3 whose water_pitcher.glb is the v3p one; variants
  C (control, library_v3) and P (v3p pitcher), episodes 21 and 22 (the only public pitcher episodes), same box.
- Scoring: `pipeline/score_registered.py`, pack 9a+ meshes (the submitted pitcher stays library_v3, so only the track
  changes), per frame; plus the physperc D1-style frame-0 tilt error of the pitcher vs mocap (diagnostic).
- **Gate:** mean ΔAUC (P − C) over ep21 / 22 ≥ +0.010, neither episode < −0.005, pitcher frame-0 tilt error lower on
  both. Because only 2 episodes exist, a pass is "promising", handed over as a candidate for eval 20 (pitcher episode)
  with the run-to-run noise from the main batch's C vs C2 stated next to it.
- Cost: added to an existing or one small RTX 5090 box, ≈ $0.3–0.6 [E].
