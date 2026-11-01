"""E0 report step: add ship gates and the pose-board note to MANIFEST.json (documents only; no mesh, pick or
frozen field changes). Fixes the documentation part of verify_0 B1 and verify_1 B1; the decisions stay open.

Usage: python -I e0_status.py <E0 dir>   (idempotent; prints old and new sha256)
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

E0 = Path(sys.argv[1])
P = E0 / "MANIFEST.json"
raw = P.read_bytes()
m = json.loads(raw)
frozen = copy.deepcopy(m)
old_sha = hashlib.sha256(raw).hexdigest()

G1 = {
    "id": "G1-marker-prior",
    "source": "verify_0 B1 (docs/research/mesh-2026-10-26/cdo-sprint/E0/verify_0.md, commit 42ab815)",
    "objects": ["white_pot", "white_pot_lid", "plastic_dish_rack"],
    "what": "The pot, lid and rack picks were built with the frozen prim_potlid.py marker-ball prior: MK_R0 = 7 mm and "
            "a 5-9.5 mm free-fit window, both measured on the public scans (C0b AUDIT ids 12 and 13). Kept balls [M]: "
            "pot 2 x 7 mm prior (free fits 7.34, 32.52 mm); lid 1 free 7.74 mm (accepted by the scan window) + 1 prior "
            "7 mm (cluster 12.07 mm); rack 2 x 7 mm prior (free fits 6.52, 6.24 mm). The owner's 'Ship 9a, flagged' "
            "covers the C0 meshes of pack 9a only.",
    "needs": "an explicit owner decision before E0's pot, lid or rack ships; otherwise use the scan-free E0b rebuild "
             "(C0b PREREG section 9). The blue cup (lathe, no marker balls) is not affected.",
    "state": "open",
}
G2 = {
    "id": "G2-pose-boards",
    "source": "verify_1 B1 (docs/research/mesh-2026-10-26/cdo-sprint/E0/verify_1.md, commit f302485)",
    "objects": ["white_pot", "white_pot_lid", "plastic_dish_rack", "blue_cup"],
    "what": "The packed mesh also drives all five pose boards: AUC, MPPE, RPE, SP-SR and MP-SR register the submitted "
            "mesh to the hidden reference and convert the submitted poses with that registration (kit "
            "metric_code/track_3/*.py lines 867-869); ops/jobs/submit_pack.sh puts LIB/<object>.glb into the pose "
            "submission. E0 has no public-twin AUC guard (C0 had one). GT-free kit-registration proxy with library_v3 "
            "as the reference stand-in [M]: pot, lid and rack move like the guarded C0 meshes; the blue cup's axis "
            "tilts 3.3-7.3 deg (C0 cup 0.9-2.3 deg).",
    "needs": "a choice: (a) use the E0 meshes for the CD-O (reconstruction) submission only and keep the current "
             "pack's meshes in the pose-board parquet; or (b) first run C0's AUC guard unchanged "
             "(C0/scripts/run_auc_guard.sh + guard_eval.py, 15 public twins, frozen thresholds) with the E0 meshes. "
             "(b) reads public scans and parquets for scoring, which E0's eval-only rules exclude, so it is a "
             "separate step for the owner or orchestrator to start.",
    "state": "open",
}

m["status"] = ("packaged and verified (verify_0, verify_1); not scored (no eval ground truth exists). PREREG section 6 "
               "rule result: white_pot E0, white_pot_lid E0, plastic_dish_rack E0, blue_cup E0, with no PREREG rule "
               "flags. That is the rule's output, not a ship decision: two ship gates are open (ship_gates G1, G2). "
               "Owner decides what ships.")
m["ship_gates"] = [G1, G2]
m["pose_boards"] = G2["what"]
m["verification"] = {
    "verify_0": {"path": "docs/research/mesh-2026-10-26/cdo-sprint/E0/verify_0.md", "commit": "42ab815",
                 "lens": "integrity", "blocking": ["B1 -> ship gate G1"], "nonblocking": "N1-N9", "confirmed": "C1-C9"},
    "verify_1": {"path": "docs/research/mesh-2026-10-26/cdo-sprint/E0/verify_1.md", "commit": "f302485",
                 "lens": "frame and kit", "blocking": ["B1 -> ship gate G2"], "nonblocking": "N1-N6",
                 "confirmed": "C1-C8"},
}
m["provenance_note"] = (
    "Tier P1: the eval tracks are store run 20261025-evperc-4f596df, templated on library_v3 (gmg SPEC section 3; "
    "owner decision O1). obs_points also read library_v3 for --roi and --others (library_v3 is on "
    "ops/provenance/denylist.json; verify_0 N2). Thickness 2.5 mm (lid, rack) = public clean-up grid midpoint, "
    "flagged. Object set and methods from C0 (chosen with public-scan scores).")
m["not_a_drop_in"] = (
    "library_e0 / library_e0x keep library_v3 for beige_cup and mini_dust_pan, whereas pack 9a+ ships the C1 beige-cup "
    "lathe (evals 8, 10) and the C1 dust pan (evals 19, 38). Merge E0's objects one by one into the current pack "
    "library; packing either folder whole reverts those 4 pairs (verify_1 N6). 'unchanged' in this MANIFEST means "
    "unchanged against C0 and pack 7, not against pack 9a+.")
hist = m.setdefault("status_history", [])
if not any(h.get("commit") == "3fbc1d1" for h in hist):
    hist.append({"commit": "3fbc1d1", "sha256": old_sha,
                 "note": "first packaged version (e0_package.py output); status said 'no flags' without ship gates"})

gate_of = {"white_pot": ["G1-marker-prior", "G2-pose-boards"], "white_pot_lid": ["G1-marker-prior", "G2-pose-boards"],
           "plastic_dish_rack": ["G1-marker-prior", "G2-pose-boards"], "blue_cup": ["G2-pose-boards"]}
for p in m["pairs"]:
    p["ship_gates"] = gate_of.get(p["object"], []) if p.get("e0_swapped") else []

# every field from e0_package.py must be unchanged, apart from the top-level status text
new_top = {"ship_gates", "pose_boards", "verification", "provenance_note", "not_a_drop_in", "status_history"}
for k, v in frozen.items():
    if k in ("status", "status_history"):
        continue
    if k == "pairs":
        for a, b in zip(v, m["pairs"]):
            strip = lambda d: {x: y for x, y in d.items() if x != "ship_gates"}
            assert strip(b) == strip(a), a["eval_episode"]
        assert len(v) == len(m["pairs"])
    else:
        assert m[k] == v, k
assert set(m) - set(frozen) <= new_top, set(m) - set(frozen)

out = json.dumps(m, indent=1) + "\n"
P.write_text(out)
print("old", old_sha)
print("new", hashlib.sha256(out.encode()).hexdigest())
