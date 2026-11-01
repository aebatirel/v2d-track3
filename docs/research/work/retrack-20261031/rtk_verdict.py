"""Verdict of the re-track test P_o' vs P_o (PREREG.md in this folder; written 31 Oct 2026 before any P_o' result).
ORACLE READING, after inference: the scores read public mocap (tools/leak_p1.py score); this script reads only their
JSON, the bundles, the tracks' cameras and the delivery's VALIDATION.json.

usage: rtk_verdict.py --po R_Po.json --pop R_Pop.json --po-bundles DIR --pop-bundles DIR --po-poses DIR --pop-poses DIR
                      --delivery DIR --commit SHA [--po-commit 87fc869] [--repo REPO] [--out JSON]
  R_*.json       tools/leak_p1.py score outputs (R = registered AUC, lib convention; RPE cm). P_o: --lib-ep-dir unset.
  *-bundles      folders searched recursively for ep<N>/bundle.json (one per episode and arm).
  *-poses        folders searched recursively for ep<N>/perc2/poses.npz (world_T_cam: the camera check).
  --delivery     the delivered folder (VALIDATION.json: status, md5 per mesh, provenance tier).
  --commit       the commit P_o' ran on (its bundles must carry it); --po-commit the Phase-1 commit (87fc869).
Verdict order (PREREG §4-§5): INVALID (the arms differ in anything but the templates) > INCOMPLETE (an episode
missing, failed or not ok: rerun those only) > PASS / FAIL by the rule:
  PASS iff mean dR >= +0.01 AND #(dR_e > 0) >= 12 of 20 AND min dR_e >= -0.03 AND mean dRPE <= 0,
  dR_e = R(P_o')_e - R(P_o)_e from the 4-decimal scores; an episode whose templates are all byte-identical to P_o's
  (nothing delivered for it) enters the rule with dR_e = dRPE_e = 0 (its measured values are the cross-box control).
Exit 0 PASS, 1 FAIL, 2 INCOMPLETE, 3 INVALID.
"""
import argparse, glob, hashlib, json, math, os, subprocess, sys
import numpy as np

PUBLIC = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
CAM_CM, CAM_DEG = 0.5, 0.25          # INVALID above this (review 31 Oct, amendment 2): camera P_o' vs P_o [H]
CAM_NOTE_CM, CAM_NOTE_DEG = 0.1, 0.05   # NOTE above this: Phase 1 cross-box/commit max 0.077 cm, 0.03 deg
NOISE = dict(R_mean_abs=0.0017, R_max_abs=0.0136, RPE_mean_abs_cm=0.0019, RPE_max_abs_cm=0.0077)   # o vs o2, lib [M]
CODE = ['pipeline/perc2.py', 'pipeline/det_rules.py', 'ops/box/']                     # what perc2 / the box run


def find(root, pat):
    out = {}
    for p in glob.glob(f'{root}/**/{pat}', recursive=True):
        parts = p.split(os.sep)
        ep = [x for x in parts if x.startswith('ep') and x[2:].isdigit()]
        if ep:
            out.setdefault(int(ep[-1][2:]), []).append(p)
    return out


def cam_diff(a, b):
    A, B = np.load(a)['world_T_cam'].astype(float), np.load(b)['world_T_cam'].astype(float)
    if A.shape != B.shape:
        return math.inf, math.inf
    dt = np.linalg.norm(A[:, :3, 3] - B[:, :3, 3], axis=1).max() * 100
    R = np.einsum('tji,tjk->tik', A[:, :3, :3], B[:, :3, :3])
    ang = np.degrees(np.arccos(np.clip((np.trace(R, axis1=1, axis2=2) - 1) / 2, -1, 1))).max()
    return float(dt), float(ang)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ('po', 'pop', 'po-bundles', 'pop-bundles', 'po-poses', 'pop-poses', 'delivery', 'commit'):
        p.add_argument(f'--{k}', required=True)
    p.add_argument('--po-commit', default='87fc869'); p.add_argument('--repo', default=os.getcwd()); p.add_argument('--out')
    a = p.parse_args()
    SPo, SPop = json.load(open(a.po))['episodes'], json.load(open(a.pop))['episodes']
    Bpo, Bpop = find(a.po_bundles, 'bundle.json'), find(a.pop_bundles, 'bundle.json')
    Ppo, Ppop = find(a.po_poses, 'perc2/poses.npz'), find(a.pop_poses, 'perc2/poses.npz')
    inval, incomp, rows, notes = [], [], {}, []
    for nm, D in (('P_o bundles', Bpo), ("P_o' bundles", Bpop), ('P_o poses', Ppo), ("P_o' poses", Ppop)):
        for e, ps in D.items():                                        # a rerun next to its failed original: ambiguous
            if len(ps) > 1:
                inval.append(f'ep{e}: {len(ps)} {nm} under the root (keep only the run that is scored): {ps}')
    Bpo, Bpop, Ppo, Ppop = ({e: ps[-1] for e, ps in D.items()} for D in (Bpo, Bpop, Ppo, Ppop))
    try:
        V = json.load(open(f'{a.delivery}/VALIDATION.json'))
    except Exception as x:
        V = {}; inval.append(f'delivery: VALIDATION.json unreadable ({x!r})')
    vfiles = V.get('files') or {}
    if V and V.get('status') not in ('pass', 'flagged'):
        inval.append(f'delivery: VALIDATION status {V.get("status")}')
    tiers = sorted({str(f.get('provenance_tier')) for f in vfiles.values()})
    if any(f.get('provenance_tier') in (None, '') for f in vfiles.values()):
        inval.append('delivery: a mesh without a provenance tier (integrity: GT-freeness must be stated)')
    # code: perc2 and the box setup byte-identical between the Phase-1 commit and P_o''s commit
    if a.commit.startswith(a.po_commit) or a.po_commit.startswith(a.commit):
        code = 'same commit'
    else:
        g = subprocess.run(['git', '-C', a.repo, 'diff', '--stat', a.po_commit, a.commit, '--', *CODE], capture_output=True, text=True)
        code = 'identical' if g.returncode == 0 and not g.stdout.strip() else f'DIFFERS or unknown (rc {g.returncode}): {(g.stdout or g.stderr).strip()[:200]}'
        if code != 'identical':
            inval.append(f'code: {", ".join(CODE)} between {a.po_commit} and {a.commit}: {code}')
    for e in PUBLIC:
        k = str(e); r = rows[e] = dict(episode=e)
        if k not in SPo:
            inval.append(f'ep{e}: no P_o score (control)'); continue
        if k not in SPop or e not in Bpop or e not in Ppop:
            incomp.append(f'ep{e}: P_o\' {"score" if k not in SPop else "bundle" if e not in Bpop else "poses"} missing'); continue
        bo, bp = json.load(open(Bpo[e])) if e in Bpo else None, json.load(open(Bpop[e]))
        if bo is None:
            inval.append(f'ep{e}: no P_o bundle'); continue
        ao, ap = bo['arms'].get('perc2'), bp['arms'].get('perc2')
        if not ap or not bp.get('ok') or ap.get('rc') != 0 or not ap.get('poses_ok'):
            incomp.append(f'ep{e}: P_o\' arm failed or bundle not ok (rc {ap and ap.get("rc")}, ok {bp.get("ok")})'); continue
        bad = []
        if not str(bo.get('commit', '')).startswith(a.po_commit):
            bad.append(f'P_o commit {str(bo.get("commit"))[:7]}')
        if not (str(bp.get('commit', '')).startswith(a.commit) or a.commit.startswith(str(bp.get('commit', '-')))):
            bad.append(f'P_o\' commit {str(bp.get("commit"))[:7]} != {a.commit[:7]}')
        if bo['objects'] != bp['objects'] or bo['T'] != bp['T']:
            bad.append('objects / frames differ')
        do, dp = bo['inputs']['depth'], bp['inputs']['depth']
        for f in ('store', 'bytes', 'shape', 'frame0_sha256'):
            if do.get(f) != dp.get(f):
                bad.append(f'depth {f} differs')
        for f in ('hands.npz', 'hands_refined.npz'):
            if bo['inputs']['hands'][f].get('md5') != bp['inputs']['hands'][f].get('md5'):
                bad.append(f'{f} md5 differs')
        for nm, arm in (('P_o', ao), ('P_o\'', ap)):
            if not (arm and arm.get('gdino') and arm.get('depth_reused') and arm.get('template_kind') == 'library'):
                bad.append(f'{nm} arm: gdino / depth reuse / template kind')
        if not ap.get('lib_ep_dir') or ap.get('templates_as_delivered') is not True:
            bad.append('P_o\' arm: no LIB_EP_DIR record or templates not as delivered')
        changed = []
        for n in bp['objects']:
            to, tp = ao['templates'][n], ap['templates'][n]
            rel = f'ep{e}/{n}.glb'
            want = vfiles[rel]['md5'] if rel in vfiles else to['md5']
            if tp.get('source') != ('episode' if rel in vfiles else 'library') or tp['md5'] != want:
                bad.append(f'{n}: template {tp.get("source")} {tp["md5"][:8]} != {"delivered" if rel in vfiles else "library_v3"} {want[:8]}')
            if tp['md5'] != to['md5']:
                changed.append(n)
        own = os.path.join(os.path.dirname(Bpop[e]), 'perc2')
        wvo = f'{own}/poses_world_vo.npz'
        if os.path.isfile(wvo) and hashlib.md5(open(wvo, 'rb').read()).hexdigest() != SPop[k].get('track_md5'):
            bad.append(f"P_o' scored track {str(SPop[k].get('track_md5'))[:8]} is not this bundle's poses_world_vo.npz")
        ct, cr = cam_diff(Ppo[e], f'{own}/poses.npz' if os.path.isfile(f'{own}/poses.npz') else Ppop[e])
        if not (ct <= CAM_CM and cr <= CAM_DEG):
            bad.append(f'camera differs {ct:.3f} cm / {cr:.3f} deg (> {CAM_CM} cm / {CAM_DEG} deg)')
        elif ct > CAM_NOTE_CM or cr > CAM_NOTE_DEG:
            notes.append(f'ep{e}: camera differs {ct:.3f} cm / {cr:.3f} deg (above the {CAM_NOTE_CM} cm / {CAM_NOTE_DEG} deg note level)')
        if bad:
            inval.append(f'ep{e}: ' + '; '.join(bad))
        so, sp = SPo[k], SPop[k]
        for nm, s, src in (('P_o', so, 'library'), ('P_o\'', sp, None)):
            for n, m in s['meshes'].items():                                  # scoring registered the tracked mesh
                want = (ao if nm == 'P_o' else ap)['templates'][n]['md5']
                if m['md5'] != want:
                    inval.append(f'ep{e}: {nm} scored with {n} {m["md5"][:8]} but tracked with {want[:8]}')
        dR, dP = round(sp['AUC'] - so['AUC'], 4), round(sp['RPE_cm'] - so['RPE_cm'], 4)
        r.update(R_Po=so['AUC'], R_Pop=sp['AUC'], dR=dR, RPE_Po=so['RPE_cm'], RPE_Pop=sp['RPE_cm'], dRPE=dP,
                 changed=changed, rule_dR=dR if changed else 0.0, rule_dRPE=dP if changed else 0.0,
                 camera_cm=round(ct, 5), camera_deg=round(cr, 5),
                 per_obj=dict(Po=so['per_obj_AUC'], Pop=sp['per_obj_AUC']))
    ok = [r for r in rows.values() if 'dR' in r]
    res = dict(prereg='docs/research/work/retrack-20261031/PREREG.md', invalid=inval, incomplete=incomp, code_check=code,
               delivery=dict(status=V.get('status'), meshes=len(vfiles), provenance_tiers=tiers, validated=V.get('time'),
                             commit=V.get('commit')), noise_floor_within_box=NOISE, episodes=rows)
    if len(ok) == 20:
        dr = np.array([r['rule_dR'] for r in ok]); dp = np.array([r['rule_dRPE'] for r in ok])
        mr = np.array([r['dR'] for r in ok]); mp = np.array([r['dRPE'] for r in ok])     # measured (the agreed rule)
        unch = [r for r in ok if not r['changed']]
        crit = dict(mean_dR=round(float(dr.mean()), 5), n_dR_pos=int((dr > 0).sum()), min_dR=round(float(dr.min()), 4),
                    mean_dRPE=round(float(dp.mean()), 5), n_changed=len(ok) - len(unch),
                    measured=dict(mean_dR=round(float(mr.mean()), 5), n_dR_pos=int((mr > 0).sum()),
                                  min_dR=round(float(mr.min()), 4), mean_dRPE=round(float(mp.mean()), 5)),
                    raw_mean_dR=round(float(np.mean([r['dR'] for r in ok])), 5),
                    control_unchanged=dict(n=len(unch), max_abs_dR=max([abs(r['dR']) for r in unch], default=None),
                                           max_abs_dRPE=max([abs(r['dRPE']) for r in unch], default=None)))
        ok4 = lambda c: dict(mean_dR=c['mean_dR'] >= 0.01, n_pos=c['n_dR_pos'] >= 12, floor=c['min_dR'] >= -0.03, rpe=c['mean_dRPE'] <= 0)
        z, m = ok4(crit), ok4(crit['measured'])                          # PASS only if both hold: never easier than agreed
        crit['pass'] = {c: z[c] and m[c] for c in z}; crit['pass_zeroed'], crit['pass_measured'] = z, m
        res['criteria'] = crit
        if unch and crit['control_unchanged']['max_abs_dR'] > NOISE['R_max_abs']:
            notes.append(f'cross-box control: an unchanged episode moved |dR| {crit["control_unchanged"]["max_abs_dR"]} > the '
                         f'within-box max {NOISE["R_max_abs"]}: read margins with that noise')
    verdict = 'INVALID' if inval else 'INCOMPLETE' if incomp else ('PASS' if all(res['criteria']['pass'].values()) else 'FAIL')
    res.update(verdict=verdict, notes=notes, rerun=[int(x.split(':')[0][2:]) for x in incomp])
    print(f'VERDICT {verdict}')
    for x in inval:
        print('  INVALID', x)
    for x in incomp:
        print('  INCOMPLETE', x)
    if 'criteria' in res:
        c = res['criteria']
        print(f'  mean dR {c["mean_dR"]:+.5f} (>= +0.01: {c["pass"]["mean_dR"]}); dR > 0 on {c["n_dR_pos"]}/20 (>= 12: '
              f'{c["pass"]["n_pos"]}); min dR {c["min_dR"]:+.4f} (>= -0.03: {c["pass"]["floor"]}); mean dRPE {c["mean_dRPE"]:+.5f} cm '
              f'(<= 0: {c["pass"]["rpe"]}); changed episodes {c["n_changed"]}/20; raw mean dR {c["raw_mean_dR"]:+.5f}; '
              f'control (unchanged) {c["control_unchanged"]}')
    print(f'  code {code}; delivery {res["delivery"]}')
    for e in PUBLIC:
        r = rows.get(e, {})
        if 'dR' in r:
            print(f'  ep{e:<3d} R {r["R_Po"]:.4f} -> {r["R_Pop"]:.4f} dR {r["dR"]:+.4f}  RPE {r["RPE_Po"]:.3f} -> {r["RPE_Pop"]:.3f} '
                  f'dRPE {r["dRPE"]:+.4f}  changed {",".join(r["changed"]) or "- (enters as 0)"}  cam {r["camera_cm"]:.4f} cm')
    for x in notes:
        print('  NOTE', x)
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1)
    sys.exit({'PASS': 0, 'FAIL': 1, 'INCOMPLETE': 2, 'INVALID': 3}[verdict])


if __name__ == '__main__':
    main()
