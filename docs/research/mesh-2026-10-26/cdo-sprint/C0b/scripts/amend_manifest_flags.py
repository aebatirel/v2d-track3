#!/usr/bin/env python3
"""Add the verify_1 B1 / B2 disclosure flags and the verify_0 N1 / verify_1 N1 caveats to MANIFEST_E0b.json.

Disclosure only: no mesh, path, hash or choice changes. The prior manifest (commit 94742e4, sha256 4ebbe5bc...) is
recorded in `amendments`. Idempotent: refuses if the amendment is already present.
Usage: python amend_manifest_flags.py <MANIFEST_E0b.json>
"""
import hashlib
import json
import sys

PRIOR_SHA = "4ebbe5bc61e7c8100afb81bee80a8277f2a2810f8d3f6bd0dec7d74e06a845b3"
AMEND_ID = "2026-10-31-verify-flags"

POT_FLAG = (
    "B1 (verify_1; disclosure added after verification, mesh unchanged) [M]: 17 of the 32 marker balls lie below the "
    "pot's own base. On the build axis the lowest point is -60.2 mm, against -43.3 mm for the same ep3 build without "
    "balls (nomk) and -39.3 mm for library_v3; 7.2 % of the surface lies below -44 mm; the balls add about 192 cm3 to "
    "a 207 cm3 body (nomk 206.6, fit 398.7, shipped thick 563.7 cm3). [H] fingers or table clutter, not markers. "
    "NOT FOR CONTACT / SIMULATOR USE (SR, contact_retarget, collision carve) until the owner decides: ship flagged, "
    "ship the same build's nomk (fidelity 3.377 vs 3.275 mm), or keep C0 / library_v3 (every option post hoc)."
)
BEIGE_FLAG = (
    "B2 (verify_1; disclosure added after verification, mesh unchanged) [M]: three inside-out appendage shells "
    "(signed volumes -30.5, -29.3, -15.9 cm3; main body +99.1 cm3), net signed volume 23.5 cm3 (library_v3 157.8, "
    "T1 66.4); after the kit budget 16 bodies, not watertight (library_v3 / v3x: 2 bodies, watertight). Known for the "
    "whole lathe g1 family. NOT FOR MASS / INERTIA / INSIDE-OUTSIDE OR SIMULATOR USE until the owner decides: "
    "re-orient the three shells (surface unchanged) or ship the same build's g0 (one body, 99.1 cm3, watertight after "
    "the budget; fidelity 4.343 vs 3.322 mm), both post hoc."
)
CAVEATS = [
    "CONSTANT ORIGINS (verify_0 N1): no scan-derived (S) value reaches the shipped meshes, but the frozen gmg ball "
    "detector carries one gmg-informed setting (seed count raised from 5,000 to 15,000 after a first run, by agents who "
    "knew the scan marker catalogue; gmg PREREG A.6 origin column, SPEC section 10), and 40 KEEP constants of unknown "
    "origin remain (one U-suspect: obs_points table_band 8 mm). Describe the pack as 'no scan-derived value; the ball "
    "detector carries one gmg-informed setting', not 'no scan-derived or unknown constant'.",
    "KIT BUDGET 'OK' (verify_1 N1) covers face and vertex counts only: after budget_mesh the shipped pot is 6 bodies "
    "(as library_v3) and the shipped beige 16 bodies, neither watertight.",
]


def main(path):
    raw = open(path, "rb").read()
    m = json.loads(raw)
    if any(a.get("id") == AMEND_ID for a in m.get("amendments", [])):
        sys.exit("already amended")
    sha = hashlib.sha256(raw).hexdigest()
    if sha != PRIOR_SHA:
        sys.exit(f"unexpected prior sha256 {sha}")
    n = {"white_pot": 0, "beige_cup": 0}
    for p in m["pairs"]:
        if p["object"] == "white_pot" and p.get("e0b_swapped"):
            assert p["md5"] == "073872f4d0bdd0935a27fa985ae0063d"
            p["flags"].append(POT_FLAG)
            n["white_pot"] += 1
        elif p["object"] == "beige_cup" and p.get("e0b_swapped"):
            assert p["md5"] == "0d926da1b444f4982de50ceb0e90ade7"
            p["flags"].append(BEIGE_FLAG)
            n["beige_cup"] += 1
    assert n == {"white_pot": 6, "beige_cup": 2}, n
    m["objects"]["white_pot"].setdefault("flags", []).append(POT_FLAG)
    m["objects"]["beige_cup"].setdefault("flags", []).append(BEIGE_FLAG)
    m["caveats"].extend(CAVEATS)
    m.setdefault("amendments", []).append({
        "id": AMEND_ID,
        "what": "added verify_1 B1 (pot) and B2 (beige) flags to the 8 swapped pairs and to objects.<o>.flags; added "
                "two caveats (verify_0 N1 constant origins, verify_1 N1 kit budget). Disclosure only: no mesh, path, "
                "hash, pick or library file changed.",
        "prior_sha256": PRIOR_SHA,
        "prior_commit": "94742e4",
        "evidence": ["docs/research/mesh-2026-10-26/cdo-sprint/C0b/verify_0.md",
                     "docs/research/mesh-2026-10-26/cdo-sprint/C0b/verify_1.md"],
        "meshes_changed": False,
    })
    out = json.dumps(m, indent=1).encode()
    open(path, "wb").write(out)
    print("amended", n, "new sha256", hashlib.sha256(out).hexdigest())


if __name__ == "__main__":
    main(sys.argv[1])
