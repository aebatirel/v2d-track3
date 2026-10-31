# gmg I: INTERLOCK stage (slot / seat / cavity geometry) — working notes

Started 2026-10-31 ~09:10 UTC. Owner (31 Oct ~09:00 UTC): "how do you expect the wooden blocks to interlock in a
physical simulation without the slot?" Deliverables: `INTERLOCK.md` (design, owner-readable first page) and a dated
PREREG section F entry; commit + push to `claude/bold-albattani-6qmxsv`. Design only in this step. Build 1 owns
B2-B7 files; the placement slot (P workflow, `PLACEMENT.md`) runs in parallel: coordinate, do not duplicate.

## Log
- 09:10 read STATUS head, SPEC 0-16, PREREG A, B.7-B.15, E, F; P.md (placement slot started 08:45). No I.md existed.

## ORCHESTRATOR NOTE (31 Oct 08:47 UTC): the Embodiment session replied; read `build/embodiment-reply-20261031.md`
Use their proposed intrusion export fields (or state ours), their sim-copy layout (`DIR/<obj>/<obj>.glb + piece_*.obj`
for `make_assets.py --pieces`), jittered-mean judging, and add a minimum frame count + relative-motion check to the
carve rule.
