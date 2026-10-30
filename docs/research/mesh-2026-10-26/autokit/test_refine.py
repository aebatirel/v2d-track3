"""Tests and measurements of io_gt.py and refine.py on real observed points (stage 1, builder io-refine). GT-free.

Stages (each writes JSON lines under OUT = scratchpad/auto/stage1/io-refine/):
  unit       io_gt refusals (scan / loc / align / parquet / mocap paths, keys outside ALLOWED_KEYS) and an
             injection-recovery test: known, temporally correlated per-frame rigid errors are added to a real
             observation file and refine_frames must recover them (correlation and residual error of the corrections).
  falsifier  the pre-registered handle test (prereg.json, written before the first refinement of the pot): the
             critic's handle-wedge measure (critic/handle_smear.py, re-implemented here unchanged; its axis constants
             are our own GT-free lathe axis fit of ep41, prim/potlid/axis/ep41_white_pot.json) before / after
             refinement on white_pot ep41 and ep42, plus a held-out control: the handle wedge excluded from the fit
             and from the consensus (fit_mask), so any sharpening of the handle comes from corrections estimated
             elsewhere on the object.
  all        refine every single-episode observation file present (obs_all/ preferred over obs/), write
             refined/ep<N>_<obj>.npz (+ .refine.json, .corr.npz), and the object-agnostic statistics: median
             per-frame residual to the consensus before/after, spread of the corrections, patch_spread before/after.
             --shard i/n splits the list between processes.
  balls      marker-ball radius from PUBLIC refined observations: refine.ball_scan on every refined file, balls
             grouped per object across episodes (same object frame), median and spread.
Only object names used: the white-pot falsifier inputs and file names (driver input lists). No scan, no mocap,
no *_align file is opened (all loads go through io_gt.load_obs).
Usage: python test_refine.py {unit|falsifier|all|balls} [--shard 0/2] [--force]
"""
import argparse, glob, json, math, os, re, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from autokit import io_gt  # noqa: E402
from autokit.refine import refine_frames, save_refined, patch_spread, ball_scan, prepare_frames  # noqa: E402

OUT = f'{io_gt.SCRATCH}/auto/stage1/io-refine'
EXPECTED_LATE = ['ep11_beige_cup', 'ep11_blue_cup', 'ep12_blue_cup', 'ep13_blue_cup', 'ep21_blue_cup', 'ep22_blue_cup',
                 'ep21_water_pitcher', 'ep22_water_pitcher', 'ep18_mini_dust_pan', 'ep39_mini_dust_pan',
                 'ep40_mini_dust_pan', 'ep18_mini_sweeper', 'ep31_mini_sweeper', 'ep0_white_pot']


def jl(path, d):
    with open(path, 'a') as f:
        f.write(json.dumps(d) + '\n')


# ---------------------------------------------------------------------------------------------- handle measure
# critic/handle_smear.py, unchanged in substance; the constants are our GT-free lathe axis of white_pot ep41
HANDLE_C = np.array([0.0027, -0.0013, -0.0208]); HANDLE_D = np.array([0.9684, 0.0406, 0.2462])
BANDS = [(0.106, 0.14), (0.14, 0.18), (0.18, 0.22), (0.22, 0.25)]
FALSIFIER_BANDS = [(0.14, 0.18), (0.18, 0.22), (0.22, 0.25)]


def handle_wedge(P):
    """Boolean mask of the critic's handle wedge (radial band 106-250 mm, +-25 deg around the dominant azimuth)."""
    d = HANDLE_D / np.linalg.norm(HANDLE_D)
    X = P - HANDLE_C; h = X @ d; R = X - h[:, None] * d; r = np.linalg.norm(R, axis=1)
    sel = (r > 0.106) & (r < 0.25)
    e1 = np.cross(d, [0, 0, 1.0]); e1 /= np.linalg.norm(e1); e2 = np.cross(d, e1)
    az = np.arctan2(R @ e2, R @ e1)
    hist, edges = np.histogram(az[sel], 72); k = np.argmax(hist); a0 = 0.5 * (edges[k] + edges[k + 1])
    return sel & (np.abs(np.angle(np.exp(1j * (az - a0)))) < np.radians(25)), r


def handle_bands(P, F):
    m, r = handle_wedge(P)
    Q, f, rr = P[m], F[m], r[m]
    mu = Q.mean(0); n = np.linalg.svd(Q - mu, full_matrices=False)[2][2]
    off = (Q - mu) @ n
    out = []
    for lo, hi in BANDS:
        b = (rr >= lo) & (rr < hi)
        if b.sum() < 200:
            continue
        meds, within = [], []
        for fr in np.unique(f[b]):
            o = off[b & (f == fr)]
            if len(o) >= 20:
                meds.append(np.median(o)); within.append(np.subtract(*np.percentile(o, [95, 5])))
        out.append(dict(band_mm=[lo * 1e3, hi * 1e3], n=int(b.sum()), frames=len(meds),
                        all_width_mm=round(float(np.subtract(*np.percentile(off[b], [95, 5]))) * 1e3, 2),
                        between_mm=round(float(np.subtract(*np.percentile(meds, [95, 5]))) * 1e3, 2),
                        within_mm=round(float(np.median(within)) * 1e3, 2)))
    return out


# ---------------------------------------------------------------------------------------------- stages
def stage_unit():
    res = {}
    S = io_gt.SCRATCH
    for p in [f'{S}/obs/ep41_white_pot_align.npz', f'{S}/data/scan/x.npz', f'{S}/loc/a/b.npz', '/x/ep1.parquet',
              '/x/MOCAP/a.npz']:
        try:
            io_gt.load_obs(p); res[p] = 'NOT REFUSED'
        except ValueError:
            res[p] = 'refused'
    try:
        io_gt.load_obs(io_gt.obs_path('white_pot_lid', 2), keys=('pts', 'pose')); res['key pose'] = 'NOT REFUSED'
    except ValueError:
        res['key pose'] = 'refused'
    # a symlink into a forbidden directory is refused through realpath
    lnk = f'{OUT}/unit_link.npz'
    if os.path.lexists(lnk):
        os.remove(lnk)
    os.symlink(f'{S}/obs/ep41_white_pot_align.npz', lnk)
    try:
        io_gt.load_obs(lnk); res['symlink to align'] = 'NOT REFUSED'
    except ValueError:
        res['symlink to align'] = 'refused'
    os.remove(lnk)
    ok = all(v == 'refused' for v in res.values())
    jl(f'{OUT}/unit.jsonl', dict(test='io_gt_refusals', ok=ok, detail=res))
    print('refusals ok', ok)
    # poses / calib
    P = io_gt.load_poses(2); K = io_gt.load_calib()['K']
    jl(f'{OUT}/unit.jsonl', dict(test='poses_calib', keys=sorted(P), T=int(len(P['world_T_cam'])),
                                 K=np.round(K, 3).tolist()))
    # download path of load_poses into a private cache (never overwrites data/sweep)
    tmp = f'{OUT}/dl_test'
    try:
        Pd = io_gt.load_poses(2, sweep_dir=tmp)
        same = all(np.allclose(Pd[k], P[k]) for k in P)
        jl(f'{OUT}/unit.jsonl', dict(test='poses_download', ok=bool(same)))
        print('download ok', same)
    except Exception as e:  # noqa: BLE001
        jl(f'{OUT}/unit.jsonl', dict(test='poses_download', ok=False, err=str(e)))
        print('download failed', e)
    # injection-recovery on real points (lid ep2, a mid-size file)
    for name in ('ep2_white_pot_lid',):     # the pot (2 x 2 min) was dropped for time; run inject('ep41_white_pot')
        inject(name)


def inject(name, rot_deg=1.0, trans_mm=1.5, seed=7):
    """Add a known per-frame rigid error (AR(1) in time, rho 0.8, stationary sd rot_deg / trans_mm per component,
    about the cloud median) to an observation file, refine, and compare the recovered corrections with the inverse
    of the injected ones (both gauge-centred)."""
    from scipy.spatial.transform import Rotation
    m = re.match(r'ep(\d+)_(.+)', name); ep, obj = int(m.group(1)), m.group(2)
    obs = io_gt.load_obs(io_gt.obs_path(obj, ep))
    P = obs['pts'].astype(np.float64); F = obs['frame']; c0 = np.median(P, 0)
    fids = np.unique(F); rng = np.random.default_rng(seed)
    a = np.zeros((len(fids), 6)); sd = np.r_[[math.radians(rot_deg)] * 3, [trans_mm * 1e-3] * 3]
    a[0] = rng.normal(0, 1, 6) * sd
    for i in range(1, len(fids)):
        a[i] = 0.8 * a[i - 1] + math.sqrt(1 - 0.64) * rng.normal(0, 1, 6) * sd
    a -= a.mean(0)
    pert = dict(obs)
    Pp = P.copy(); Cp = obs['cam'].astype(np.float64).copy()
    order = np.argsort(F, kind='stable'); _, st, ct = np.unique(F[order], return_index=True, return_counts=True)
    for i, (s0, c) in enumerate(zip(st, ct)):
        g = order[s0:s0 + c]; R = Rotation.from_rotvec(a[i, :3]).as_matrix()
        Pp[g] = (P[g] - c0) @ R.T + c0 + a[i, 3:]; Cp[g] = (Cp[g] - c0) @ R.T + c0 + a[i, 3:]
    pert['pts'] = Pp.astype(np.float32); pert['cam'] = Cp.astype(np.float32)
    t0 = time.time()
    # baseline: corrections refine finds on the unperturbed file (its own jitter estimate)
    _, rep0 = refine_frames(obs)
    _, rep = refine_frames(pert)
    # expected correction = inverse of the injected error composed with the baseline correction (small-angle: sum)
    def vec(r):
        cc = r['corr']; return np.c_[Rotation.from_matrix(cc['R']).as_rotvec(), cc['t'] + 0 * cc['t']]
    v0, v1 = vec(rep0), vec(rep)
    # correction about each run's own c0 (both runs use the median of their own points; the shift is < 1 mm)
    fit = np.array([p['fitted'] for p in rep['per_frame']]) & np.array([p['fitted'] for p in rep0['per_frame']])
    rec = v1 - v0                      # what refine attributes to the injection
    exp = -a                           # perfect recovery undoes the injection
    out = dict(test='inject_recover', file=name, rot_sd_deg=rot_deg, trans_sd_mm=trans_mm, frames=int(fit.sum()),
               sec=round(time.time() - t0, 1))
    for j, lab in enumerate(['rx', 'ry', 'rz', 'tx', 'ty', 'tz']):
        x, y = exp[fit, j], rec[fit, j]
        sc = 180 / math.pi if j < 3 else 1e3
        out[lab] = dict(corr=round(float(np.corrcoef(x, y)[0, 1]), 3), inj_sd=round(float(x.std() * sc), 3),
                        err_sd=round(float((y - x).std() * sc), 3))
    out['res_before_mm'] = rep['res_before_med_mm']; out['res_after_mm'] = rep['res_after_med_mm']
    out['res_after_unperturbed_mm'] = rep0['res_after_med_mm']
    jl(f'{OUT}/unit.jsonl', out)
    print(json.dumps(out))


def stage_falsifier(tag='v2', deg_frac=None):
    """tag v1 = deg_frac 0 (the pre-registered run, written before v2 existed); v2 = degeneracy-aware default.
    The v2 main refinement is the shipped refined copy; v1 outputs live in OUT/v1/."""
    kw = {} if deg_frac is None else dict(deg_frac=deg_frac)
    out = f'{OUT}/falsifier.jsonl' if tag == 'v1' else f'{OUT}/falsifier_{tag}.jsonl'
    main_dir = io_gt.REFINED_DIR if tag == 'v2' else f'{OUT}/{tag}'
    for ep in (41, 42):
        obs = io_gt.load_obs(io_gt.obs_path('white_pot', ep))
        P0 = obs['pts'].astype(np.float64); F = obs['frame']
        before = handle_bands(P0, F)
        jl(out, dict(ep=ep, variant='raw', bands=before))
        # main: full refinement (also the shipped refined copy)
        ref, rep = refine_frames(obs, verbose=True, **kw)
        save_refined(ref, rep, f'{main_dir}/ep{ep}_white_pot.npz')
        after = handle_bands(ref['pts'].astype(np.float64), F)
        jl(out, dict(ep=ep, variant='refined', bands=after,
                     summary={k: v for k, v in rep.items() if k not in ('per_frame', 'corr', 'params')}))
        # held-out control: the handle wedge takes no part in the fit or the consensus
        wedge, _ = handle_wedge(P0)
        ref_h, rep_h = refine_frames(obs, fit_mask=~wedge, verbose=True, **kw)
        save_refined(ref_h, rep_h, f'{OUT}/heldout{"" if tag == "v1" else "_" + tag}/ep{ep}_white_pot_nohandle.npz')
        after_h = handle_bands(ref_h['pts'].astype(np.float64), F)
        jl(out, dict(ep=ep, variant='refined_handle_heldout', wedge_pts=int(wedge.sum()), bands=after_h,
                     summary={k: v for k, v in rep_h.items() if k not in ('per_frame', 'corr', 'params')}))
        for lab, bb in (('raw', before), ('refined', after), ('heldout', after_h)):
            print(ep, lab, [(b['band_mm'], b['between_mm'], b['within_mm']) for b in bb], flush=True)


def stage_split():
    """Post-hoc control (added after the pre-registered run, so NOT part of the falsifier): hold out only the OUTER
    handle (wedge, r >= 180 mm) from fit and consensus; the inner handle (r < 180 mm) and the body still constrain
    the tilt. If the corrections are real pose errors, the held-out outer bands (180-220, 220-250 mm) must sharpen
    as in the full run; if the full-run sharpening was the handle fitting itself, they must not."""
    out = f'{OUT}/split.jsonl'
    for ep in (41, 42):
        obs = io_gt.load_obs(io_gt.obs_path('white_pot', ep))
        P0 = obs['pts'].astype(np.float64); F = obs['frame']
        wedge, r = handle_wedge(P0)
        outer = wedge & (r >= 0.18)
        ref, rep = refine_frames(obs, fit_mask=~outer)
        save_refined(ref, rep, f'{OUT}/heldout_outer/ep{ep}_white_pot_noouter.npz')
        bb = handle_bands(ref['pts'].astype(np.float64), F)
        jl(out, dict(ep=ep, variant='outer_handle_heldout', outer_pts=int(outer.sum()), bands=bb,
                     summary={k: v for k, v in rep.items() if k not in ('per_frame', 'corr', 'params')}))
        print(ep, 'outer held out', [(b['band_mm'], b['between_mm'], b['within_mm']) for b in bb], flush=True)


def obs_files():
    """Single-episode observation files present: obs_all/ preferred over obs/; *_align and joint files excluded;
    files still being written (no final JSON line in the .log, or modified < 120 s ago) are skipped."""
    names = {}
    for d in reversed(io_gt.OBS_DIRS):              # obs/ first, then obs_all/ overrides
        for f in glob.glob(f'{d}/ep*_*.npz'):
            b = os.path.basename(f)[:-4]
            if '_align' in b or not re.fullmatch(r'ep\d+_[a-z0-9_]+', b):
                continue
            log = f[:-4] + '.log'
            done = (not os.path.exists(log)) or open(log).read().strip().endswith('}')
            if done and time.time() - os.path.getmtime(f) > 120:
                names[b] = f
    return dict(sorted(names.items(), key=lambda kv: os.path.getsize(kv[1])))


def stage_all(shard='0/1', force=False, reverse=False):
    i, n = map(int, shard.split('/'))
    files = obs_files()
    todo = [k for j, k in enumerate(files) if j % n == i]
    if reverse:             # a second worker from the largest file down; it skips what the other one wrote
        todo = todo[::-1]
    for name in todo:
        dst = f'{io_gt.REFINED_DIR}/{name}.npz'
        t0 = time.time()
        obs = io_gt.load_obs(files[name])
        reused = os.path.exists(dst) and not force
        if reused and reverse:
            print('exists', name); continue
        if reused:              # written by another stage (falsifier): statistics only
            ref = io_gt.load_obs(dst); rep = json.load(open(dst[:-4] + '.refine.json'))
        else:
            try:
                ref, rep = refine_frames(obs)
            except Exception as e:  # noqa: BLE001
                jl(f'{OUT}/all.jsonl', dict(file=name, src=files[name], error=repr(e))); print('FAIL', name, e); continue
            save_refined(ref, rep, dst)
        ps0 = patch_spread(obs); ps1 = patch_spread(ref)
        row = dict(file=name, src=files[name], dst=dst, reused=reused, sec=round(time.time() - t0, 1), patch_before=ps0,
                   patch_after=ps1,
                   refine_sec=rep.get('sec'),
                   **{k: v for k, v in rep.items() if k not in ('per_frame', 'corr', 'params', 'passes', 'c0', 'sec')})
        jl(f'{OUT}/all.jsonl', row)
        print(name, json.dumps({k: row[k] for k in ('res_before_med_mm', 'res_after_med_mm', 'rot_deg_p50',
                                                    'trans_mm_p50', 'bound_hits')}), ps0.get('between_mm'),
              ps1.get('between_mm'), ps0.get('within_mm'), flush=True)


def stage_report():
    """Table of the 'all' rows (last row per file) and the files that were expected but not present."""
    rows = {}
    for l in open(f'{OUT}/all.jsonl'):
        d = json.loads(l); rows[d['file']] = d
    keys = ('res_before_med_mm', 'res_after_med_mm', 'rot_deg_p50', 'rot_deg_p90', 'trans_mm_p50', 'trans_mm_p90',
            'bound_hits', 'frames_with_frozen_dir', 'frames_fitted', 'frames_skipped')
    tab = []
    for f, d in sorted(rows.items()):
        if 'error' in d:
            tab.append(dict(file=f, error=d['error'])); continue
        pb, pa = d['patch_before'], d['patch_after']
        tab.append(dict(file=f, **{k: d.get(k) for k in keys},
                        patch_between_mm=[pb.get('between_mm'), pa.get('between_mm')],
                        patch_within_mm=[pb.get('within_mm'), pa.get('within_mm')],
                        patch_frac_b_gt_w=[pb.get('frac_between_gt_within'), pa.get('frac_between_gt_within')]))
    missing = [n for n in EXPECTED_LATE if n not in rows]
    json.dump(dict(rows=tab, missing=missing), open(f'{OUT}/all_summary.json', 'w'), indent=1)
    for t in tab:
        print(json.dumps(t))
    print('missing', missing)


def stage_balls():
    rows = []
    for f in sorted(glob.glob(f'{io_gt.REFINED_DIR}/ep*_*.npz')):
        b = os.path.basename(f)[:-4]
        if b.endswith('.corr'):
            continue
        m = re.match(r'ep(\d+)_(.+)', b); ep, obj = int(m.group(1)), m.group(2)
        obs = io_gt.load_obs(f, keys=('pts', 'cam', 'frame'))
        t0 = time.time()
        balls = ball_scan(obs)
        row = dict(file=b, obj=obj, ep=ep, n=len(balls), balls=balls, sec=round(time.time() - t0, 1))
        jl(f'{OUT}/balls.jsonl', row); rows.append(row)
        print(b, 'accepted', [round(x['r_mm'], 2) for x in balls if x['accepted']], 'rejected',
              [round(x['r_mm'], 2) for x in balls if not x['accepted']], flush=True)
    summarize_balls(rows)


def summarize_balls(rows=None):
    if rows is None:
        rows = [json.loads(l) for l in open(f'{OUT}/balls.jsonl')]
    per_obj = {}
    for r in rows:
        per_obj.setdefault(r['obj'], []).extend([dict(b, ep=r['ep']) for b in r['balls'] if b['accepted']])
    phys = []
    for obj, bl in per_obj.items():
        groups = []                       # same object frame across episodes: centres within 10 mm = one ball
        for b in sorted(bl, key=lambda x: -x['n']):
            c = np.array(b['c'])
            for g in groups:
                if np.linalg.norm(c - g['c']) < 0.010:
                    g['m'].append(b); break
            else:
                groups.append(dict(c=c, m=[b]))
        for g in groups:
            rr = [x['r_mm'] for x in g['m']]
            phys.append(dict(obj=obj, c=np.round(g['c'], 4).tolist(), n_ep=len({x['ep'] for x in g['m']}),
                             r_med_mm=round(float(np.median(rr)), 2), r_all=[round(x, 2) for x in rr]))
    r_all = np.array([x['r_mm'] for bl in per_obj.values() for x in bl])
    r_multi = np.array([p['r_med_mm'] for p in phys if p['n_ep'] >= 2])
    summ = dict(detections=int(len(r_all)), physical=len(phys), physical_multi_ep=int(len(r_multi)))
    for lab, v in (('all_detections', r_all), ('physical_multi_ep', r_multi)):
        if len(v):
            summ[lab] = dict(median=round(float(np.median(v)), 2), p25=round(float(np.percentile(v, 25)), 2),
                             p75=round(float(np.percentile(v, 75)), 2), mad=round(float(np.median(np.abs(v - np.median(v)))), 2),
                             min=round(float(v.min()), 2), max=round(float(v.max()), 2))
    json.dump(dict(summary=summ, physical=phys), open(f'{OUT}/balls_summary.json', 'w'), indent=1)
    print(json.dumps(summ))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['unit', 'falsifier', 'all', 'balls', 'balls_summary', 'report', 'split'])
    ap.add_argument('--reverse', action='store_true')
    ap.add_argument('--shard', default='0/1'); ap.add_argument('--force', action='store_true')
    ap.add_argument('--tag', default='v2'); ap.add_argument('--deg_frac', type=float, default=None)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); os.makedirs(io_gt.REFINED_DIR, exist_ok=True)
    {'unit': stage_unit, 'falsifier': lambda: stage_falsifier(a.tag, a.deg_frac), 'balls': stage_balls, 'balls_summary': summarize_balls,
     'report': stage_report, 'split': stage_split, 'all': lambda: stage_all(a.shard, a.force, a.reverse)}[a.stage]()
