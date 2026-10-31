# Track 3 pack-9a candidate, 31 Oct 2026: pack 8 with the mesh session's C0 pot, lid and rack

**NOT UPLOADED YET.** Owner: "I want a pack today" (31 Oct ~15:40 UTC, via the score-status session); planned upload
~20:00–20:30 UTC to all six boards unless the owner stops it. Fallback: pot + rack only (`build_2obj/`), or pack 8.

**Chosen build: `build_3obj/`** — `track3_submission.parquet` sha256 `9c19bb0c85901de46113483c9df5a2927ae626f1094a87ad3f77725aa22ea662`,
1,335,354 bytes, 9,120 rows, 0 MESH WARNINGs, uploader offline validation PASS, code commit
https://github.com/aebatirel/v2d-track3/commit/50004a7575b4ecf4f31058434b56589cca0f64dd (holds `meshes/c0_pack9a/`, the
exact packed C0 files: white_pot 0264da83…, white_pot_lid 35727a10…, plastic_dish_rack bbca8ec0…, from bold-albattani
5cce3d2). Differs from pack 8 only in `object_mesh_b64` (12 payloads) and `code_commit_url` (all rows). CD-O file
`track3_submission.cd-o.parquet` (294,912 rows) derived offline by the uploader's own code.

**Mesh choice and checks.**
- Blue cup held back (its selector was written after scoring; CLAUDE.md). Pot, lid, rack as fitted (C0, not the
  aligned C0a): rule `docs/research/work/pack9a-20261031/MESH_RULE.md`, fixed before reading the mesh session's AUC guard
  (public twins, registered scoring, single swaps vs library_v3, 51 runs, 0 failures: pot mean dAUC +0.0030 (n 9),
  lid +0.0055 (n 2), rack +0.0158 (n 5)).
- Swap tool frame check exit 2 (needs review) → mesh-session sign-off per the tool's procedure: **pot YES, lid YES, rack
  YES** (bold-albattani, ~16:30 UTC). Flags were: centroid shifts 5.4 / 7.3 / 11.5 mm (shape: pot handle, lid underside,
  rack ribs/stems; ICP 2.9 / 2.6 / 1.9 mm); lid extent ratio 0.87 along its normal (C0 42.4 mm vs library_v3 52.4 mm;
  the cameras' points of the lid span 43.2 mm: library_v3's underside is inflated); and the offline proxy (library_v3 as
  the stand-in scan) flipping the lid 162°. Under the kit's real registration onto the public lid scan the C0 lid lands
  1.45–1.81° from identity (library_v3 1.05–1.74°) with a smaller anchor shift (0.40–0.47 vs 0.71–0.79 cm); the kit
  declares the lid half-turn symmetric.
- Expected effect [E, mesh session]: CD-O ≈ 0.367 (from 0.402) with these three; pose boards about unchanged (public
  guard mean dAUC ≥ 0 per object). Each board keeps its best submission.

## Content

| Item | Source |
|---|---|
| Rollouts, all 20 evals | pack 8's, byte for byte: pack 7's 19 rollouts plus eval 1 from `runs/20261030-e1conf2-d41382e/results/submission/results/episode_000001.{json,parquet}` |
| Meshes, 24 of 36 (episode, object) pairs | pack 6/7/8's `meshes/`, unchanged: library_v3, plus v3x for eval 8's beige_cup |
| Meshes, 12 pairs: white_pot (evals 1, 3, 5, 6, 8, 28), white_pot_lid (1), plastic_dish_rack (14, 15, 16, 28, 30) | the mesh session's C0 files (all 12 replaced files are library_v3 in pack 8) |
| Simulator assets, policies | unchanged: no rollout was re-run |

- The C0 mesh is what gets packed and scored. The rollouts' poses are body frames of the library_v3 bodies the
  simulator built. Every pose board registers the submitted mesh to the scan and moves the body poses with that
  registration (kit `metric_code/track_3/AUC.py`, `_register_object_body` / `_convert_object_body`).
- So C0 must be in the library_v3 body frame, or come with a C0 → library_v3 4x4. Otherwise a frame offset of d mm
  moves every scored pose of that object by about d mm. `tools/pack_swap_meshes.py` measures this before packing (frame
  report).
- Boards affected: CD-O (12 of its 36 pairs change), and the five pose boards through the mesh registration.

## Build (CPU, scratch `S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad`)

**Inputs, all measured on 31 Oct**
- `$S/pack9a/build8/results`: pack 7's build results (`$S/pack7/build/results`) with eval 1 replaced by e1conf2's two
  files. Single-file `hf_hub_download`: json md5 642ee590…, parquet md5 d185451b….
- `$S/pack9a/build8/meshes`: copy of pack 6's `meshes/` (`diff -r` clean).

**Pack 8 reproduces byte for byte**
- With these inputs, the kit's `tools/pack_submission.py` (as in pack 7's README) and pack 8's own commit URL (read from
  its parquet: …/commit/d41382e8b5fe8982ba06173231ddee29ae7059ba), the output is **sha256 `f2bf0441…` = pack 8's file**.
- This needs the venv `$S/pack9a_venv306`: Python 3.13.17, pandas 3.0.6 (as on the e1conf2 box), pyarrow 26.0.0,
  numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0, fast_simplification 0.2.0.
- Pack 7's venv (pandas 3.1.0) gives sha 6075d64d…, with every cell identical; only the `pandas_version` string in the
  schema metadata differs.
- A placeholder commit URL changes only `code_commit_url`, on all 9,120 rows (sha f378c72e…).

**Swap, one command once C0 is in a new folder `$S/pack9a/c0_in/<object>.glb`**
- First commit and push the code: `tools/pack_swap_meshes.py`, and the C0 meshes (or their store path and md5s).
- `<SHA>` below is that commit's full 40-hex sha.

```
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; $S/pack9a_venv306/bin/python -I /home/user/v2d-track3/tools/pack_swap_meshes.py --kit $S/map/scoring/kit/v2d_submission_kit --results $S/pack9a/build8/results --meshes $S/pack9a/build8/meshes --replace $S/pack9a/c0_in --objects white_pot,white_pot_lid,plastic_dish_rack,blue_cup --base /home/user/v2d-track3/results/submissions/20261030-track3h-candidate/track3_submission.parquet --code-commit https://github.com/aebatirel/v2d-track3/commit/<SHA> -o $S/pack9a/pack9a_C0 > $S/pack9a/pack9a_C0.out 2>&1; echo exit=$?; cat $S/pack9a/pack9a_C0.out
```

- Add `--transform <json {object: 4x4}>` only if the mesh session gives a C0 → library_v3 transform.

**What the command does**
1. Runs `tools/no_oracle.py` on its inputs.
2. Copies the results and meshes and swaps the 17 files. md5 before and after for every (episode, object) goes to
   `swap_manifest.json`.
3. Writes a frame report per object: AABB centre and extent, surface-centroid offset, symmetric surface distance, ICP
   correction, and a kit-registration proxy.
4. Packs with the kit's packer.
5. Checks against pack 8. Row count and order must match. Only `code_commit_url` and the swapped objects' payload rows
   of `object_mesh_b64` may differ. Each payload must equal the kit's `budget_mesh` of the written file.
6. Runs the uploader's offline `validate_submission` and derives the CD-O file, with no Kaggle call.
7. Counts the MESH WARNINGs in `pack.log`.

**Exit status**
- 0: go.
- 2: flags. Do not upload. Send the frame report to the mesh session.
- 1: hard failure.

**Then copy into this folder:** `track3_submission.parquet`, `pack.log`, `summary.txt`, `swap_manifest.json`. Fill in
the checks below.

**Tool tests** (31 Oct, measured, dummy replacements from `meshes/library_v3`; details in `$S/pack9a/README.md`)
- Identity bytes with pack 8's URL: byte-identical to pack 8 (f2bf0441…).
- Identity with a placeholder URL: only the commit column differs.
- Trimesh re-export: geometry identical, only the commit column differs.
- white_pot +20 mm: FLAG (centroid 20.0 mm, ICP 19.99 mm, kit proxy 20.0 mm).
- blue_cup 90° about x: FLAG (ICP 87°, extents permuted).
- white_pot rotated 10° about its centroid: FLAG (ICP 9.9°, kit proxy 10.0°).
- Shift plus its inverse `--transform`: clean.
- Wrong base parquet (pack 7): hard fail.
- Wrong base mesh for eval 8: hard fail.

## Checks (fill in)
- Frame report per object: `<TBD>`. Flags: `<TBD>`.
- Parquet vs pack 8:
  - columns differing: `<TBD>`, expected `code_commit_url` (9,120) and `object_mesh_b64` (≤ 17 payload rows);
  - payloads changed: `<TBD>`;
  - CD-O pairs changed: `<TBD>`.
- Kit `tools/preflight.py --track track_3 --results $S/pack9a/build8/results --skip-kaggle` (31 Oct, measured):
  - with the upload venv `$S/pack7_venv` (kaggle 2.2.5): all ok, "Ready to submit.";
  - with the packing venv: one FAIL, "kaggle missing" (deliberate, as in pack 7's preflight.log).
  - Pack 9a's results folder is a byte copy of these inputs (md5 in `swap_manifest.json`).
- Ground truth: none read. The packer reads only `row_id` from the kit's sample submission, plus the object roster.

## Expected effect [estimate, to fill in]
- CD-O: the mesh session's C0 proxy numbers vs library_v3 on these 4 objects, weighted by 17 of 36 pairs: `<TBD>`.
- Pose boards: the frame report's kit-proxy pose shift is a stand-in for the change in registration. The true change
  depends on the scan and cannot be measured before upload.

## Upload (NOT run; needs the owner's go)

**How pack 7 was uploaded.** Reconstructed from the work log of 30 Oct ~06:35 UTC and its receipt
`20261030-track3g-candidate/track3_submission.parquet.kaggle-receipt.json`. The literal command line was not recorded.
- Tool: the kit's `submit/v2d_submit.py`, run through `tools/kaggle_upload.py`. The proxy injects the Kaggle token;
  `KAGGLE_API_TOKEN=placeholder` only satisfies the client's pre-check.
- Venv `$S/pack7_venv` (kaggle 2.2.5), cwd = kit root.
- A dry run first, then five boards: AUC, SP-SR, MP-SR, RPE, MPPE. CD-O was left out because the meshes were unchanged.
- An explicit `--receipt`. Scores came back COMPLETE.
- Kaggle allows 5 uploads per board per day, reset 00:00 UTC. Today's remaining quota is unverified (no Kaggle call
  made).

**Pack 9a: all six boards** (the meshes changed, so CD-O too). Set
`K=$S/map/scoring/kit/v2d_submission_kit` and `R=/home/user/v2d-track3/results/submissions/20261031-track3i-candidate`.

```
# 1. dry run: validates, writes $R/track3_submission.cd-o.parquet, prints the quota (read-only Kaggle calls)
cd $K && KAGGLE_API_TOKEN=placeholder $S/pack7_venv/bin/python -I /home/user/v2d-track3/tools/kaggle_upload.py submit/v2d_submit.py $R/track3_submission.parquet --track track_3 --only add_auc spider_sr maniptrans_sr rpe_cm mppe_cm cd_o_cm -m "dry run" --dry-run
# 2. upload and wait for the scores
cd $K && KAGGLE_API_TOKEN=placeholder $S/pack7_venv/bin/python -I /home/user/v2d-track3/tools/kaggle_upload.py submit/v2d_submit.py $R/track3_submission.parquet --track track_3 --only add_auc spider_sr maniptrans_sr rpe_cm mppe_cm cd_o_cm -m "pack 9a 31 Oct 2026 (pack 8 + C0 meshes for white_pot, white_pot_lid, plastic_dish_rack, blue_cup), code commit <sha7>" --receipt $R/track3_submission.parquet.kaggle-receipt.json --wait
```

**Fallback, pack 8 alone: the five pose boards** (meshes identical to pack 7, so no CD-O). The receipt is a new file in
pack 8's folder. With `--only` leaving out `cd_o_cm`, the uploader writes no CD-O file there.

```
R8=/home/user/v2d-track3/results/submissions/20261030-track3h-candidate
cd $K && KAGGLE_API_TOKEN=placeholder $S/pack7_venv/bin/python -I /home/user/v2d-track3/tools/kaggle_upload.py submit/v2d_submit.py $R8/track3_submission.parquet --track track_3 --only add_auc spider_sr maniptrans_sr rpe_cm mppe_cm -m "dry run" --dry-run
cd $K && KAGGLE_API_TOKEN=placeholder $S/pack7_venv/bin/python -I /home/user/v2d-track3/tools/kaggle_upload.py submit/v2d_submit.py $R8/track3_submission.parquet --track track_3 --only add_auc spider_sr maniptrans_sr rpe_cm mppe_cm -m "eighth pack 31 Oct 2026 (pack 7 + fresh official eval-1 rollout of the carved s43 policy, 20-draw confirmed), code commit d41382e" --receipt $R8/track3_submission.parquet.kaggle-receipt.json --wait
```

**Reading the boards afterwards (read-only)**

```
# our six scores, from the receipt's submission IDs (v2d_submit.py's read-only mode; resumes polling)
cd $K && KAGGLE_API_TOKEN=placeholder $S/pack7_venv/bin/python -I /home/user/v2d-track3/tools/kaggle_upload.py submit/v2d_submit.py --track track_3 --poll-receipt $R/track3_submission.parquet.kaggle-receipt.json
# the six leaderboards: top 8 and our row ("Ahmet Ercan Batirel"), saved as JSON
KAGGLE_API_TOKEN=placeholder $S/pack7_venv/bin/python -I $S/pack9a/scripts/boards.py $R/boards-<UTC>.json
```

- `boards.py` uses the same client stub as `tools/kaggle_upload.py` and as `$S/lbcheck/lb.py`, which read the board on
  30 Oct. For each slug it calls `api.competition_leaderboard_view(slug)`.
- The slugs are `v2d-challenge-track3-{auc,sp-sr,mp-sr,rpe,mppe,cd-o}`.
- Reading rule, as for pack 7: a board result is a transfer measurement only. No mesh or rollout is chosen or reverted
  by its board score, because that would tune on eval ground truth.
