# Priority input from keen-heisenberg (professor-feedback analysis), 31 Oct 09:58 UTC (data, sent at the owner's request)

INTERLOCK v2 already covers their section 7 points (collider overlap along the reference = E13; board 2 HULL = F-I1).
Ordering by measured score at risk: H5 10-draw spread on eval, sim_vs_ref (`docs/analysis/h5-20261029/h5_summary.json`
on branch claude/keen-heisenberg-engcwz):
- eval 30, sweeper <-> rack: sd 0.255, min 0.26; the sweeper starts inside our rack mesh (public twin ep31);
- eval 14, cup <-> rack: sd 0.199; our reference pushes the cup into the rack mesh (public twin ep13);
- eval 25, boards: sd 0.099, already slot-carved on library_v3;
- eval 1, lid <-> pot: sd 0.239, already fixed by a carve (0.924 +- 0.017 over 20 official draws).
So the rack seat / cavity cases carry more spread than the board slot. Caveats: eval 14's twin also fails at the
hand-over even with true motion (0.544 both), so a rack seat alone may not lift eval 14; eval 30's twin was inconclusive
(+0.086 at one seed). The free-travel test answers October's v2 rack carve, which dropped the sweeper 2.5-3.5 cm.
Analysis: `docs/analysis/arda-feedback-20261031.md` sections 2 and 7 on that branch.

## Follow-up 10:11 UTC: evidence for the seat priority (branch claude/keen-heisenberg-engcwz, docs/analysis/drawdiv-20261031/README.md)
- 10 official draws of one checkpoint on public ep31 (eval 30 twin: sweeper + rack), run 20261030-orcB-38234d1,
  grasp-lock learner; arm P = our reference + library_v3 meshes.
- Draws stay within 5 mm until f~48-53, then split by 2 cm: the sweeper's fast lift-off from the rack (reference 9 ->
  30 cm/s at f45-50). In the bad P draws the rack is knocked at that moment (3.7-5.6 cm off; good draws 0.5 cm); in the
  mocap-motion arm the rack is not knocked (worst draw 1.6-2.9 cm, otherwise 0.1-0.4 cm).
- Reading: the sweeper-rack contact at lift-off decides eval 30's spread; a sweeper-rack seat in the simulator copy that
  passes the free-travel test is the most direct fix for the largest spread (eval 30 sd 0.255).
- Caveats: one low-spread twin (sd 0.019 for P), a grasp-lock policy (eval 30's packed policy is the standard learner),
  and the P vs O rack-knock difference may come from the reference itself, not only the mesh.
