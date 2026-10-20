"""Dig 14 Stage C re-run: eval-set e_track prior with per-episode failure classes from note 15.
Inputs: per-episode kit-scored policy-outcome rows on the 20 PUBLIC GT episodes (work/14/e_mix.csv,
work/14-verify/c2_kit_surf.csv), averaged by object count. Eval episodes enter only through their object
count (kit evaluation-objects list) and note 15's grasp-synthesis class. Research only, no inference path.
p_N = s + (1-s) * r**N : s = structural (seed-independent) failure prob, r = random per-seed failure prob."""
import itertools, json
import pandas as pd

W = "/Users/aebatirel/Documents/Code/v2d-research/work"
EV = json.load(open("/Users/aebatirel/Documents/Code/v2d-research/kit/v2d_submission_kit/data/track_3_evaluation_objects.json"))["episodes"]
NOBJ = {int(k): len(v) for k, v in EV.items()}
CLS = {e: "F" for e in (1, 8, 37, 38)}
CLS.update({e: "P" for e in (3, 5, 6, 10, 19, 30, 32, 33)})
CLS.update({e: "L" for e in (14, 15, 16, 20, 25, 28, 35, 36)})
assert sorted(CLS) == sorted(NOBJ)

v = pd.read_csv(f"{W}/14-verify/c2_kit_surf.csv").rename(columns={"SP-SR": "SPSR", "MP-SR": "MPSR"})
gt = v.groupby(["model", "nobj"])[["AUC", "SPSR", "MPSR"]].mean()
m = pd.read_csv(f"{W}/14/e_mix.csv")
pm = m[m.ref == "PERC_M"].groupby(["pol", "nobj"])[["AUC", "SPSR", "MPSR"]].mean()

def row(tab, key, n):
    return tab.loc[(key, n)].values

def outcome(ref, cont, failmode, n):
    if ref == "GT":
        ok = row(gt, cont, n)
        fails = {"soft": ["never+good", "freeze50+good"], "hard": ["never+good", "fall50_tipped+good"]}[failmode]
        bad = sum(row(gt, f, n) for f in fails) / 2
    else:  # PERC_M reference; no physical-fall rows exist for it -> freeze model only (optimistic SP-SR)
        ok = row(pm, cont, n)
        bad = (row(pm, "never", n) + row(pm, "drop50", n)) / 2
    return ok, bad

def evalset(ref, cont, failmode, s, r, N):
    tot = 0
    for e, n in NOBJ.items():
        p = s[CLS[e]] + (1 - s[CLS[e]]) * r ** N
        ok, bad = outcome(ref, cont, failmode, n)
        tot = tot + (1 - p) * ok + p * bad
    return tot / len(NOBJ)

S_LO = {"F": 0.0, "P": 0.25, "L": 0.6}
S_HI = {"F": 0.05, "P": 0.5, "L": 0.9}
S_FIX = {k: v / 2 for k, v in S_LO.items()}          # structural fixes halve s (low end) [H]
S0 = {"F": 0.0, "P": 0.0, "L": 0.0}                  # class-blind (old Stage C)
REG = [  # name, cont models, r range, N, s variants
    ("real speed, soft wrist, 1 seed", ["lag30"], (0.20, 0.45), 1),
    ("real speed, soft wrist, best-of-3", ["lag30"], (0.20, 0.45), 3),
    ("headroom fixed, 1 seed", ["good"], (0.11, 0.25), 1),
    ("headroom fixed, best-of-3", ["good"], (0.11, 0.25), 3),
]
out = []
for ref in ("GT", "PERC_M"):
    for name, conts, rr, N in REG:
        for sname, (sa, sb) in {"class-blind s=0": (S0, S0), "note-15 s (lo..hi)": (S_LO, S_HI), "s halved by fixes": (S_FIX, S_LO)}.items():
            vals = [evalset(ref, c, fm, s, r, N) for c in conts for fm in (("soft", "hard") if ref == "GT" else ("soft",))
                    for s in (sa, sb) for r in rr]
            lo = pd.DataFrame(vals).min().values; hi = pd.DataFrame(vals).max().values
            out.append(f"{ref:6s} | {name:34s} | {sname:20s} | AUC {lo[0]:.3f}-{hi[0]:.3f} | SP-SR {lo[1]:.2f}-{hi[1]:.2f} | MP-SR {lo[2]:.2f}-{hi[2]:.2f}")
# worst case: every eval episode fails (p=1), and 5/20 perfect + 15 fail
for ref in ("GT", "PERC_M"):
    for fm in (("soft", "hard") if ref == "GT" else ("soft",)):
        allf = sum(outcome(ref, "good", fm, n)[1] for n in NOBJ.values()) / 20
        out.append(f"{ref} all-fail ({fm}): AUC {allf[0]:.3f} SP-SR {allf[1]:.2f} MP-SR {allf[2]:.2f}")
txt = "\n".join(out)
print(txt)
open(f"{W}/14/c2/eval_prior.txt", "w").write(txt + "\n")
