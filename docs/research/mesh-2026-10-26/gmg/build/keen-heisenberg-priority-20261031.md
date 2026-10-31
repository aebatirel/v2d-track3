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
