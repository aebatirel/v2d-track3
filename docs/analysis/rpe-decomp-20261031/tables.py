"""Tables for README.md from decomp_Po.json (and roll_rollouts.json if present). Usage: python -I tables.py DIR > tables.md"""
import json, os, sys
import numpy as np

D = sys.argv[1]
R = json.load(open(f'{D}/decomp_Po.json'))['episodes']
eps = sorted(R, key=int)
multi = [e for e in eps if len(R[e]['names']) > 1]
V = ['a0', 'a', 'a_rot', 'b', 'c', 'c_rest', 'd', 'cd', 'c_k', 'c_rest_k', 'd_k', 'cd_k']
f = lambda x: f'{x:.3f}'


def mean(key, var, sel):
    return float(np.mean([R[e]['variants'][var][key] for e in sel]))


print('## Per episode, base (P_o, lib convention) [M]\n')
print('| ep | objects | frames | AUC | MPPE cm | RPE cm | RPE/MPPE | obj MPPE cm | obj rot err deg (mean / f0) | obj pos err cm (mean / f0) | untouched |')
print('|---|---|---|---|---|---|---|---|---|---|---|')
for e in eps:
    r = R[e]; b = r['variants']['base']; o = r['objects']
    print(f'| {e} | {", ".join(r["names"])} | {r["frames"]} | {b["AUC"]:.3f} | {b["MPPE"]:.2f} | {b["RPE"]:.2f} | '
          f'{(b["RPE"] / b["MPPE"]) if len(o) > 1 else float("nan"):.2f} | {" / ".join(f"{x:.2f}" for x in b["obj_MPPE"])} | '
          f'{" ; ".join(f"{x["rot_err_deg_mean"]:.1f}/{x["rot_err_deg_f0"]:.1f}" for x in o)} | '
          f'{" ; ".join(f"{x["pos_err_cm_mean"]:.2f}/{x["pos_err_cm_f0"]:.2f}" for x in o)} | '
          f'{",".join(x["name"] for x in o if x["untouched"]) or "-"} |')
for lab, sel in (('mean, 20 eps (RPE: single-object eps count 0, as the kit)', eps), ('mean, 13 multi-object eps', multi)):
    print(f'| **{lab}** | | | {mean("AUC", "base", sel):.4f} | {mean("MPPE", "base", sel):.3f} | {mean("RPE", "base", sel):.3f} | '
          f'{mean("RPE", "base", sel) / mean("MPPE", "base", sel):.2f} | | | | |')

print('\n## Worst-3 share [M]\n')
for key, worse in (('RPE', 1), ('MPPE', 1), ('AUC', -1)):
    vals = {e: R[e]['variants']['base'][key] for e in eps}
    loss = {e: (v if worse > 0 else 1 - v) for e, v in vals.items()}
    top = sorted(loss, key=lambda e: -loss[e])[:3]
    tot = sum(loss.values())
    rest = [e for e in eps if e not in top]
    print(f'- {key}: worst 3 = {", ".join("ep" + e + f" {vals[e]:.3f}" for e in top)}; they carry {sum(loss[e] for e in top) / tot:.0%} '
          f'of the summed {"value" if worse > 0 else "AUC loss"}; mean without them {np.mean([vals[e] for e in rest]):.3f} '
          f'(all {np.mean(list(vals.values())):.3f})')

print('\n## Ablations by GT substitution: mean over 20 episodes (RPE: 13 multi-object eps in brackets) [M, oracle]\n')
print('| variant | RPE | ΔRPE | MPPE | ΔMPPE | AUC | ΔAUC | eps RPE better / worse | eps AUC better / worse |')
print('|---|---|---|---|---|---|---|---|---|')
b0 = {k: mean(k, 'base', eps) for k in ('RPE', 'MPPE', 'AUC')}
b0m = mean('RPE', 'base', multi)
print(f'| base | {b0["RPE"]:.3f} [{b0m:.3f}] | – | {b0["MPPE"]:.3f} | – | {b0["AUC"]:.4f} | – | – | – |')
for v in V:
    m = {k: mean(k, v, eps) for k in ('RPE', 'MPPE', 'AUC')}; mm = mean('RPE', v, multi)
    dr = [R[e]['variants'][v]['RPE'] - R[e]['variants']['base']['RPE'] for e in multi]
    da = [R[e]['variants'][v]['AUC'] - R[e]['variants']['base']['AUC'] for e in eps]
    print(f'| {v} | {m["RPE"]:.3f} [{mm:.3f}] | {m["RPE"] - b0["RPE"]:+.3f} [{mm - b0m:+.3f}] | {m["MPPE"]:.3f} | {m["MPPE"] - b0["MPPE"]:+.3f} | '
          f'{m["AUC"]:.4f} | {m["AUC"] - b0["AUC"]:+.4f} | {sum(x < -0.01 for x in dr)} / {sum(x > 0.01 for x in dr)} (of 13) | '
          f'{sum(x > 0.001 for x in da)} / {sum(x < -0.001 for x in da)} |')

print('\n## Per-episode ablations: RPE / MPPE / AUC [M, oracle]\n')
print('| ep | base | ' + ' | '.join(V) + ' |')
print('|---|' + '---|' * (len(V) + 1))
for e in eps:
    row = [R[e]['variants'][v] for v in ['base'] + V]
    print(f'| {e} | ' + ' | '.join(f'{x["RPE"]:.2f} / {x["MPPE"]:.2f} / {x["AUC"]:.3f}' for x in row) + ' |')

print('\n## RPE anatomy, multi-object episodes (base) [M]\n')
print('| ep | RPE kit | slot 0 (axis) | true separation cm | RPE both still / any moving | share of RPE in both-still frames | split in W* world: rel. translation / slot-0 rotation × lever (cm) | same split, kit world | W* vs kit world: rot °, shift cm |')
print('|---|---|---|---|---|---|---|---|---|')
for e in multi:
    r = R[e]; q = r['rpe']; o0 = r['objects'][0]
    print(f'| {e} | {q["kit"]:.2f} | {o0["name"]} | {q["true_sep_cm_mean"]:.1f} | '
          f'{q["rpe_both_still"] if q["rpe_both_still"] is None else round(q["rpe_both_still"], 2)} / {q["rpe_any_moving"] if q["rpe_any_moving"] is None else round(q["rpe_any_moving"], 2)} | '
          f'{q["share_of_sum_both_still"]:.0%} | {q["split_Wstar"]["rel_translation_cm"]:.2f} / {q["split_Wstar"]["slot0_rotation_x_lever_cm"]:.2f} | '
          f'{q["split_kit"]["rel_translation_cm"]:.2f} / {q["split_kit"]["slot0_rotation_x_lever_cm"]:.2f} | '
          f'{r["W_star_vs_kit"]["rot_deg"]:.2f}, {r["W_star_vs_kit"]["shift_at_slot0_cm"]:.2f} |')

print('\n## Per object, base (P_o, lib) [M]\n')
print('| ep | object | true travel cm / rot ° | still frac | AUC | MPPE cm | MPPE still / moving | pos err cm mean (f0) | rot err ° mean (f0) |')
print('|---|---|---|---|---|---|---|---|---|')
for e in eps:
    for o in R[e]['objects']:
        print(f'| {e} | {o["name"]} | {o["true_travel_cm"]:.1f} / {o["true_rot_deg"]:.0f} | {o["still_frac"]:.2f} | {o["auc"]:.3f} | {o["mppe_cm"]:.2f} | '
              f'{o["mppe_still_cm"]} / {o["mppe_moving_cm"]} | {o["pos_err_cm_mean"]:.2f} ({o["pos_err_cm_f0"]:.2f}) | {o["rot_err_deg_mean"]:.1f} ({o["rot_err_deg_f0"]:.1f}) |')

rf = f'{D}/roll_rollouts.json'
if os.path.exists(rf):
    C = json.load(open(rf))['cells']
    print('\n## Rollout level: reference vs policy error (10 official draws per cell) [M]\n')
    print('| cell | ep | draws | reference vs mocap RPE / MPPE / AUC | sim vs mocap (total), mean | sim vs reference (policy), mean | total − ref RPE / MPPE / AUC | total RPE range over draws |')
    print('|---|---|---|---|---|---|---|---|')
    for k, c in C.items():
        rr, t, p = c['reference'], c['total_mean'], c['policy_mean']
        tr = [d['total']['RPE'] for d in c['draws']]
        print(f'| {c["arm"]} | {c["ep"]} | {c["n_draws"]} | {rr["RPE"]:.2f} / {rr["MPPE"]:.2f} / {rr["AUC"]:.3f} | {t["RPE"]:.2f} / {t["MPPE"]:.2f} / {t["AUC"]:.3f} | '
              f'{p["RPE"]:.2f} / {p["MPPE"]:.2f} / {p["AUC"]:.3f} | {t["RPE"] - rr["RPE"]:+.2f} / {t["MPPE"] - rr["MPPE"]:+.2f} / {t["AUC"] - rr["AUC"]:+.3f} | '
              f'{min(tr):.2f}–{max(tr):.2f} |')
