# Eval references and pack mesh set, from focused-pascal (31 Oct 10:48 UTC, data; at determined-wright's request)

Source: `docs/research/work/masses-eval-20261031/PLAN.md` section 1 and `packed_refs.json` on branch
`claude/focused-pascal-2nz9s1` (md5 = the reference parquet pack 6's box evaluated with).
- **eval 25:** run `20261026-c25s42-feb0407`, `refs/perc2mcks/ep25/processed/sequence_id=t3_ep025/robot_name=sharpa_wave/
  2057d9f1...-0.parquet` (md5 71ac95f3), standard learner; URDFs from `/content/assets` = make_assets(meshes/library_v3)
  + collision pieces `meshes/carve/ev25` (board slots).
- **eval 30:** run `20261025-std30-ee7ba8e` (also in `20261024-ev30rp-07eef1a`, md5-checked), `refs/perc2mcks/ep30/.../
  a2eb7d27...-0.parquet` (md5 dd464c96), standard learner; assets from library_v3, no pieces (the ev30 carve was dropped:
  the sweeper fell through).
- **eval 14:** run `20261025-evb1420-ee7ba8e`, `refs/glockt/ep14/.../ref_gl_ilc.parquet` (md5 10d5f3ba), grasp lock; its
  own asset copy `refs/sf/ep14/assets` (library_v3 geometry; the ev14 carve failed its rule and is not packed).
- **Pack mesh set** (pack 7 = current submission): library_v3 for all episodes except eval 8 (`meshes/library_v3x`, beige
  cup); eval 20's pitcher reverted to library_v3. Sim collision pieces in the pack environment: `meshes/carve/ev25` and
  `meshes/carve/ev10` (packs 6/7); the pack-8 candidate adds `meshes/carve/ev01` for eval 1 only. Submitted meshes are
  never the carves.
- All 20 eval rows (run, learner, reference path / md5 / fingerprint, asset source, pull list):
  `docs/research/work/masses-eval-20261031/packed_refs.json` on that branch.
Note for the gmg: these references were perceived with library_v3-templated tracks (tier P1); the section-11 validator
decides whether their provenance passes. Our carves start from our own gmg meshes, not from library_v3, and are compared
against the packed base (library_v3 + the listed carve pieces).
