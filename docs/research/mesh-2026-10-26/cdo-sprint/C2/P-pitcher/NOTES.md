# C2 / Track P (water_pitcher) — working notes (append-only, UTC timestamps)

Resume rule: read this file first, continue from the last line.

- 2026-10-31 ~date-start: track started. Dir created. Next: read C0b AUDIT/PREREG/REPLACEMENTS, C1 T1 beige-lathe (lathe_obs usage), C0 AUC guard runner; GT-free diagnosis of ep21/ep22 pitcher obs points.
- 2026-10-31T18:23:56Z read C0b AUDIT/REPLACEMENTS/PREREG s1-3, C1 README + T1 PREREG, lathe_obs/hybrid/obs_fidelity, C0 guard runner. Baseline library_v3 pitcher [D, results/baseline_library.jsonl]: eval 20 slot 1 seed 20000161 cdo 0.8942, add_med (6 seeds: eval+11,22,33,44,55) 7.97 mm, 0 flips. Prior GT-free notes: pitcher 'not a lathe' (rot. consistency 8.85 mm, gmg evidence.md); observed rest up 38 deg from library base axis.
- 2026-10-31T18:23:56Z inputs [M]: sweep tracks ep21/22 sha 7e4dae9c / 50acd616 = store 20261025-sweep-a894083; hands 8143230b / 77b56f43 = store g1-022fece; depth ep21 sha f2aa07b7 = LFS. Local disk only 3.7 GB free -> one episode's depth (1.2 GB) at a time, deleted after its obs points. No Vast box needed so far.
- 2026-10-31T18:23:56Z launched scripts/obs_c0b.sh 21 (C0b pass A pitcher + blue cup, pass B pitcher with own-point cup carving; --roi_cube 0.30 + cube guard), bulk SCR/cdo_c2/P/pts.
