"""Stage C evaluator (reads GT; run only AFTER inference). Maps tracker poses (VO frame) to the mocap world with
 - MODE=reg : the stage-A registration Treg only (VO drift stays in the error; what a VO-camera tracker would deliver), or
 - MODE=regD: Treg * D(t) (stage-A drift-corrected cameras; GT-informed, diagnosis only: isolates the marker-pose error).
GT compared at tau = t + SH (default -0.5: b/c frame t shows GT row t - 0.5).
Reports per object x status x segment: translation / rotation / ADD (mm, mesh vertices) medians and p90, coverage.
usage: [MODE=reg] [SH=-0.5] c/ev17.py c/trk_<ep><tag>.npz"""
import sys, os, json, numpy as np
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17')
import lib17 as L, det17lib as D, seg17
MODE = os.environ.get('MODE', 'reg'); SH = float(os.environ.get('SH', -0.5))
def verts(n, k=3000):
    import trimesh
    p = f'{L.PUB}/mesh/{n}/{n}.glb'
    if not os.path.exists(p): p = f'{L.PUB}/mesh/{n}/{n}_visual.glb'
    V = np.vstack([g.vertices for g in trimesh.load(p).geometry.values()]); rng = np.random.default_rng(0)
    return V[rng.choice(len(V), min(k, len(V)), replace=False)]
def load(fn):
    z = np.load(fn, allow_pickle=False); ep = int(os.path.basename(fn).split('_')[1].split('.')[0]); return z, ep
def to_mocap(z, ep, n_i, T, key=''):
    RG = json.load(open(f'out/reg2_{ep}.json')); VO = np.load(f'out/vo_public_{ep}.npy'); Treg = np.array(RG['Treg'])
    Rs, ts = z[f'R{key}_{n_i}'][:T], z[f't{key}_{n_i}'][:T]; Ro, to = np.zeros_like(Rs), np.zeros_like(ts)
    for t in range(T):
        if MODE == 'regD':
            Pb = np.eye(4); Pb[:3, :3] = np.array(RG['cams_b'][t]['Rwc']); Pb[:3, 3] = RG['cams_b'][t]['C']; M = Pb @ np.linalg.inv(VO[t])
        else: M = Treg
        Ro[t] = M[:3, :3] @ Rs[t]; to[t] = M[:3, :3] @ ts[t] + M[:3, 3]
    return Ro, to
def errors(Ro, to, gt, j, V, T, sh=SH):
    et, er, ea = np.zeros(T), np.zeros(T), np.zeros(T)
    for t in range(T):
        Rg, tg = D.gt_interp(gt, j, t + sh)
        et[t] = np.linalg.norm(to[t] - tg) * 1000; er[t] = np.degrees(np.linalg.norm(Rot.from_matrix(Rg.T @ Ro[t]).as_rotvec()))
        ea[t] = np.linalg.norm(V @ (Ro[t] - Rg).T + (to[t] - tg), axis=1).mean() * 1000
    return et, er, ea
def auc_add(ea_mm):
    th = np.arange(1, 10) * 10.0; ax = np.linspace(0, 1, len(th)); return float((getattr(np, "trapezoid", None) or np.trapz)([np.mean(ea_mm < x) for x in th], ax))
if __name__ == '__main__':
    z, ep = load(sys.argv[1]); T = int(z['T']); gt = L.load_gt(ep); seg = seg17.segments(gt)[0]; SEG = ['rest', 'held', 'carried']
    print(f'{sys.argv[1]} MODE {MODE} SH {SH} T {T} runtime {np.mean(z["tim"]):.2f} s/frame')
    for i, n in enumerate(z['objs']):
        j = gt['names'].index(n); V = verts(n); Ro, to = to_mocap(z, ep, i, T); et, er, ea = errors(Ro, to, gt, j, V, T)
        stt = z[f'status_{i}'][:T]; sg = seg[:T, j]
        print(f'  {n}: AUC(ADD, this trajectory, no policy) {auc_add(ea):.3f}; status 3/2/1/0 = ' + ' / '.join(f'{np.mean(stt==s):.2f}' for s in (3, 2, 1, 0)))
        for s in range(3):
            m = sg == s
            if m.sum() < 3: continue
            line = f'    {SEG[s]:8s} n{m.sum():4d} fix>=2 {np.mean(stt[m] >= 2):.2f} fix3 {np.mean(stt[m] == 3):.2f} |'
            for lab, mm in (('fix3', m & (stt == 3)), ('fix2', m & (stt == 2)), ('all', m)):
                if mm.sum() >= 2: line += f' {lab} n{mm.sum()} t {np.median(et[mm]):.1f}/{np.percentile(et[mm], 90):.1f} r {np.median(er[mm]):.2f}/{np.percentile(er[mm], 90):.2f} ADD {np.median(ea[mm]):.1f}/{np.percentile(ea[mm], 90):.1f} |'
            print(line)
        if str(z['PRIOR']) == 'gt' if 'PRIOR' in z.files else False:
            Rq, tq = to_mocap(z, ep, i, T, 'p'); pt, pr, pa = errors(Rq, tq, gt, j, V, T)
            print(f'    PRIOR-ONLY (emulated model-based, PN {z["PN"].tolist()}): AUC {auc_add(pa):.3f}; t {np.median(pt):.1f} r {np.median(pr):.2f} ADD {np.median(pa):.1f} | FUSED AUC {auc_add(ea):.3f}')
            for s in range(3):
                m = (sg == s) & (stt >= 2)
                if m.sum() >= 3: print(f'      {SEG[s]:8s} fix frames n{m.sum()}: prior ADD {np.median(pa[m]):.1f} -> fused {np.median(ea[m]):.1f} mm; fused worse than prior in {np.mean(ea[m] > pa[m]):.2f}')
        np.save(sys.argv[1].replace('.npz', f'_err{i}_{MODE}.npy'), np.c_[et, er, ea, stt, sg])
    # scorer-style: one rigid transform from slot 0 (first object) at frame 0, applied to every object and frame
    for key, lab in (('', 'tracker/fused'), ('p', 'prior-only')):
        if key and not ('PRIOR' in z.files and str(z['PRIOR']) == 'gt'): continue
        objs = list(z['objs']); i0 = 0; n0 = objs[0]
        if gt['names'][0] != n0: print('  (slot 0 not tracked; scorer-style skipped)'); continue
        R0, t0 = to_mocap(z, ep, 0, T, key); Rg0, tg0 = D.gt_interp(gt, 0, 0 + SH)
        RA = Rg0 @ R0[0].T; tA = tg0 - RA @ t0[0]; aucs = []
        for i, n in enumerate(objs):
            j = gt['names'].index(n); Ro, to = to_mocap(z, ep, i, T, key); Ro = np.einsum('ij,tjk->tik', RA, Ro); to = to @ RA.T + tA
            et, er, ea = errors(Ro, to, gt, j, verts(n), T); aucs.append(auc_add(ea))
        print(f'  SCORER-STYLE ({lab}; slot-0 frame-0 alignment) AUC per object ' + ' '.join(f'{n}:{a:.3f}' for n, a in zip(objs, aucs)) + f' mean {np.mean(aucs):.3f}')
