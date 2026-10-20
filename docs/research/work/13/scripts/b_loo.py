"""Leave-one-out for the roll-rule families (and the z sign as a positive control)."""
import sys; sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
import numpy as np, b_search as B
D, NO, S = B.D, B.NO, B.S
fams = {"F1": B.fam_F1, "F2": B.fam_F2, "F2b": B.fam_F2b, "F4": B.fam_F4}
OK = {k: f(D)[0] for k, f in fams.items()}
allpf = np.concatenate(list(OK.values()))
print("LOO, parameter-free families: rules fitting the other 9 -> share predicting the held-out roll correctly")
for name, ok in list(OK.items()) + [("F1|F2|F2b|F4", allpf)]:
    row = []
    for o in range(NO):
        m = np.delete(ok, o, 1).all(1)
        row.append((m.sum(), ok[m, o].mean() if m.any() else np.nan))
    acc = np.nanmean([r[1] for r in row])
    print(f"  {name:13s} mean share correct {acc:.2f} | per held-out (n_rules, share): " +
          " ".join(f"{B.OBJ[o][:8]}:{r[0]},{r[1]:.2f}" for o, r in enumerate(row)))

# hybrids: refit tau on 9 (geometric mean of the feasible interval), predict the held-out object
sig = np.concatenate([D[:, :, :2], -D[:, :, :2]], 0) > 0                 # (2S, 10, 2)
P1 = sig.transpose(0, 2, 1).reshape(-1, NO)                              # (4S, 10)
VV = np.abs(np.concatenate([D[:, :, :2], D[:, :, :2]], 0)).transpose(0, 2, 1).reshape(-1, NO)
print("LOO, F3 hybrids (tau refitted on 9):")
shares = []
for o in range(NO):
    idx = np.delete(np.arange(NO), o)
    good = cnt = 0
    for i in range(P1.shape[0]):
        v = VV[i, idx]; order = np.argsort(v); vs = v[order]
        c1 = P1[i, idx][order]; suf = np.flip(np.cumprod(np.flip(c1)))
        c2 = P1[:, idx][:, order]; pre = np.cumprod(c2, 1)
        g = pre[:, :-1] & suf[1:][None, :]                                # k = 1..8 below tau
        for j in np.nonzero(g.any(1))[0]:
            ks = np.nonzero(g[j])[0] + 1
            k = ks[len(ks) // 2]
            tau = np.sqrt(max(vs[k - 1], 1e-12) * vs[k])
            pred = P1[i, o] if VV[i, o] >= tau else P1[j, o]
            good += pred; cnt += 1
    shares.append(good / max(cnt, 1))
    print(f"  held-out {B.OBJ[o]:18s}: {cnt:4d} hybrids fit the other 9; share predicting it correctly {good/max(cnt,1):.2f}")
print(f"  mean share {np.mean(shares):.2f}")

# z-sign positive control: single statistics on z
iz = [i for i, s in enumerate(B.ODD) if s not in B.ZBAD]
Z = np.concatenate([D[iz, :, 2], -D[iz, :, 2]]) > 0
fit = Z.all(1)
print("z control: single-stat rules fitting 10/10:", [(B.ODD[iz[i % len(iz)]], 1 if i < len(iz) else -1) for i in np.nonzero(fit)[0]])
rng = np.random.default_rng(3); hits = 0
for t in range(4000):
    f = rng.random(NO) < 0.5
    if not f.any(): f[rng.integers(NO)] = True
    Zn = D[iz, :, 2] * np.where(f, -1, 1)
    hits += ((np.concatenate([Zn, -Zn]) > 0).all(1)).any()
print(f"z control null: P(>=1 single-stat z rule fits 10/10 | random z bits) = {hits/4000:.3f}")
row = []
for o in range(NO):
    m = np.delete(Z, o, 1).all(1); row.append(Z[m, o].mean())
print("z control LOO share correct:", np.round(row, 2), "mean", np.round(np.mean(row), 2))
