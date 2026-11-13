# T-I12 (PREREG F-I5.9 / F-I5.12) and diagnostic D2 (F-I5.13): synthetic results, 31 Oct 2026

Copied from the scratchpad (`<scratch>/fi5/`). Command per batch:
`CC_OUT=<scratch>/fi5/<name>.json GMG_MODE=dev nice -n 5 <venv>/python docs/research/mesh-2026-10-26/gmg/tests/test_collcarve.py <tests>`
on the shared 4-core container (loaded). Code versions: t_x1 / t_x11 / t_ctl* / t_oth = fae78de and earlier WIP (the
previous build instance; t_oth's sweeper used an older reach measure); t_cups / t_diag = WIP snapshots after fae78de
(18:11-18:41); t_oth2 = 72cfef3 (CoACD in a forked child); d2a / d2b = 3484d8d; d2c = cbed3cb; d2a_aborted = 5569b42
(stopped before any result, see build/I.md 18:39-18:41). diag/d2_topo.py: the x1-D2 carve rebuilt with physics off,
topology on 2 / 1 mm grids and the thinnest wall. Synthetic fixtures only (GT-free by construction). Outcomes and
mechanisms: PREREG F-I5.12, F-I5.13 outcomes; INTERLOCK 21.10; build/I.md "Collision carve" entries.
