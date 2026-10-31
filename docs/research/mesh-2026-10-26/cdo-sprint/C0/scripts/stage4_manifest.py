"""C0 stage 4: update MANIFEST.json status and flags after the AUC guard and the two verifiers (verify_0 B1, B2).

Changes ONLY documentation fields; no mesh, pair mapping, hash, score or rule changes:
  - status (old value kept in status_history with the frozen file's sha256 at 081b37e);
  - c0_final: the guard verdict (all 4 ADOPTED, guard_result.json) and the packing set (pot, lid, rack; blue cup held
    back, a deviation from PREREG section 5 recorded here);
  - pack_9a: which pairs the shipped pack swaps;
  - flags: the scan-derived marker-ball prior (verify_0 B1) on pot, lid, rack; selection and frame qualifiers;
  - provenance_note: library_v3 itself was fused along scan-templated tracks (open organiser question).
Idempotent: re-running leaves the file unchanged. Reads no ground truth.

Usage: python -I stage4_manifest.py MANIFEST.json
"""
import json
import sys

P = sys.argv[1]
d = json.load(open(P))

FROZEN = dict(commit='081b37e460d28fa3540bb1a77fad9934208ef58e',
              sha256='22209582f5698543a9220ff1dcdaeeb3e4605dcef30bea56761d9596950c55b5',
              status='assembled, AUC guard pre-registered (PREREG.md), not adopted')
PACK = ['white_pot', 'white_pot_lid', 'plastic_dish_rack']

MK = ("MARKER BALLS (verify_0 B1): prim_potlid.py markers_from (also used by prim_rack.py) falls back to a fixed ball "
      "radius MK_R0 = 7 mm and accepts a free sphere fit only inside 5-9.5 mm. Both values are SCAN-DERIVED (spoon "
      "template note 17 = marker catalogue fitted on the public scans; stage-1 audit, work log entry 2026-10-27 ~17:20 "
      "UTC, blocker 1; code comment corrected on 29 Oct in 14eaf37). The audit made this object's 27 Oct scan pass provisional until "
      "rebuilt with a generic ball rule; stage 1b closed on 30 Oct without that rebuild, so this mesh carries the prior. ")
MKO = {
    'white_pot': MK + "In this mesh [M, verify_0]: 4 exact spheres, 3 at 7.00 mm (prior) and 1 at 6.94 mm (free fit "
                      "inside the window); the build record shows free fits of 11.96, 27.88 and 3.67 mm replaced by "
                      "the 7 mm prior.",
    'white_pot_lid': MK + "In this mesh [M, verify_0]: 1 floating ball at 7.00 mm; build record: 1 free fit at 7.35 mm "
                          "(inside the window) and 2 balls at the 7 mm prior.",
    'plastic_dish_rack': MK + "In this mesh [M, verify_0]: balls at 7.00 mm (prior; free fit was 9.51 mm, just outside "
                              "the window) and 5.22 mm (free, inside the window).",
}
SEL = ("SELECTION QUALIFIER: the C0 object set was chosen with [D] public-scan scores. Pot, lid and rack passed a scan "
       "pass-rule pre-registered on 27 Oct; the blue cup had no such rule. Do not call C0 'chosen GT-free' without this "
       "qualifier and the marker-ball flag.")
BC_HOLD = ("HELD BACK from packing (pack 9a): the AUC guard ADOPTED the blue cup, but its obs_fidelity selector was "
           "written after its lathes were scored against the scan and picks the lowest-CD-O of the 12 blue-cup lathe "
           "records, so it does not meet 'picked GT-free under pre-registered rules'. Decision by the score session and "
           "focused-pascal, 31 Oct ~16:20 UTC; included only if the owner says so. Deviation from PREREG section 5.")
BC_FRAME = ("FRAME: rigid ICP C0 -> library_v3 moves 6.67 mm / 2.6 deg, about 6.45 mm of it along the cup axis "
            "(verify_handoff B1, verify_0 N5); 'same object frame as library_v3' is not confirmed for this mesh.")
BC_SEED = ("REGISTRATION: on twin ep21 the kit registration lands at 146.9 deg (1 of 5 seeds for this mesh, 0 of 5 for "
           "library_v3; verify_1 N4). [H] spin about the cup axis; the test reads the scan and was not run.")

new_flags = {o: [] for o in d['swaps']}
for o in PACK:
    new_flags[o] = [MKO[o], SEL]
new_flags['blue_cup'] = [BC_HOLD, SEL, BC_FRAME, BC_SEED]


def add(lst, items):
    for it in items:
        if it not in lst:
            lst.append(it)


for o, s in d['swaps'].items():
    add(s['flags'], new_flags[o])
    s['in_pack_9a'] = o in PACK
for p in d['pairs']:
    if p.get('swapped'):
        add(p['flags'], new_flags[p['object']])
        p['in_pack_9a'] = p['object'] in PACK
    else:
        p['in_pack_9a'] = False

d['status'] = ("AUC guard done (guard_result.json: all 4 ADOPTED under the frozen rule). C0-final FOR PACKING = "
               "white_pot, white_pot_lid, plastic_dish_rack (pack 9a, 12 pairs); blue_cup held back unless the owner "
               "includes it (deviation from PREREG section 5, see c0_final). Pot, lid and rack carry the scan-derived "
               "marker-ball prior (flags). See README.md.")
hist = d.setdefault('status_history', [])
if not any(h.get('commit') == FROZEN['commit'] for h in hist):
    hist.append(FROZEN)
d['c0_final'] = dict(
    auc_guard_verdict=['white_pot', 'white_pot_lid', 'plastic_dish_rack', 'blue_cup'],
    auc_guard_source='guard_result.json (scripts/guard_eval.py, PREREG.md 081b37e)',
    for_packing=PACK,
    held_back={'blue_cup': BC_HOLD},
    deviation_from_prereg=("PREREG section 5 says 'C0-final = the adopted objects. There is no other selection.' The "
                           "packing set drops the adopted blue cup for an integrity reason (selector not pre-registered), "
                           "not for a score reason. Nothing was added, and no mesh was re-selected."),
)
pk = [dict(eval_episode=p['eval_episode'], slot=p['slot'], object=p['object']) for p in d['pairs'] if p['in_pack_9a']]
d['pack_9a'] = dict(n_swapped=len(pk), swapped_pairs=pk,
                    built_by='focused-pascal, commit 50004a7 (2026-10-31 16:20 UTC): pack 8 plus byte copies of the '
                             'C0 pot, lid and rack; blue cup and all other pairs unchanged')
d['provenance_note'] = ("'tier P1, same tier as library_v3' means: fitted to our stereo points along library_v3-anchored "
                        "tracks. library_v3 itself was fused along scan-templated tracks, which is an open organiser / "
                        "owner question (verify_handoff N4). The 22 Oct owner decision says eval meshes are re-fused per "
                        "eval episode; these are public-built meshes reused for eval, as library_v3 is.")
order = ['candidate', 'status', 'status_history', 'c0_final', 'pack_9a', 'provenance_note', 'rule', 'n_pairs',
         'n_swapped', 'swaps', 'pairs']
d = {k: d[k] for k in order + [k for k in d if k not in order]}
json.dump(d, open(P, 'w'), indent=1)
print('pack_9a swapped pairs:', len(pk), '; flags per swap:', {o: len(s['flags']) for o, s in d['swaps'].items()})
