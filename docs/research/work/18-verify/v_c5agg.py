"""Verifier: re-aggregate c5_auc.json under alternative weightings; public episode lengths vs profile lengths."""
import json, numpy as np, pandas as pd
W = "/Users/aebatirel/Documents/Code/v2d-research/work/18"; ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
df = pd.read_json(f"{W}/c5_auc.json")
PUB = sorted(df.ep.unique()); PL = {}
for ep in PUB:
    PL[ep] = len(pd.read_parquet(f"{ROOT}/data/track_3/public/data/chunk-000/episode_{ep:06d}.parquet", columns=["frame_index"]))
prof_len = {1: 331, 3: 311, 5: 286, 6: 241, 8: 216, 10: 161, 14: 156, 15: 166, 16: 171, 19: 231, 20: 201, 25: 356, 28: 216, 30: 261, 32: 256, 33: 346, 35: 421, 36: 406, 37: 151, 38: 261}
print("public lengths", PL)
cnt = df[(df.arm == "map") & (df.ctx == "iso") & (df.seed == 0)].groupby("ep").prof.apply(list)
for ep in PUB: print(f"p{ep}: T={PL[ep]} n_profiles={len(cnt[ep])}", sorted(cnt[ep]) if len(cnt[ep]) < 20 else "all")
for ctx in ("iso", "stackA"):
    piv = df[df.ctx == ctx].pivot_table(index=["ep", "prof", "seed"], columns="arm", values="auc")
    for a in ("VOd3", "VO", "VOx3", "lin5"):
        g = piv["map"] - piv[a]
        board_pub = g.groupby(level="ep").mean().mean()
        per_prof = g.groupby(level="prof").mean()
        # near-full-length use: public T >= 0.75 x profile length (profile not heavily truncated)
        gi = g.reset_index(); gi["frac"] = [PL[e] / prof_len[p] for e, p in zip(gi.ep, gi.prof)]
        full = gi[gi.frac >= 0.75].groupby("prof")[0].mean()
        print(f"{ctx} map-{a}: public-ep-weighted {board_pub:+.4f} | eval-profile-weighted {per_prof.mean():+.4f} (n {len(per_prof)}) | profile-weighted using only T>=0.75*len {full.mean():+.4f} (n {len(full)})")
    g = piv["map"] - piv["VO"]; gi = g.reset_index(); gi["frac"] = [PL[e] / prof_len[p] for e, p in zip(gi.ep, gi.prof)]
    print(ctx, "VO gain by profile (all / T>=0.75 len):", " ".join(f"e{p}:{gi[gi.prof==p][0].mean():+.3f}/{gi[(gi.prof==p)&(gi.frac>=0.75)][0].mean():+.3f}" for p in sorted(prof_len)))
