"""ORACLE (public): A3 side check. rest_settle on mkref stage-(b) joints with vs without mkref's 6 mm joint
depenetration (ep0, ep2): score both settled references vs mocap (* and lib)."""
import sys, json, types, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/tools'); sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import leak_tierA as LT
S = sys.argv[1]; W = f'{S}/leak/oracle_tierA'; R = '/home/user/v2d-track3'
a = types.SimpleNamespace(kit=f'{S}/map/scoring/kit/v2d_submission_kit', perc=f'{S}/refine/in', t3=f'{S}/map/scoring/t3', lib=f'{R}/meshes/library_v3',
                          xgeom=f'{R}/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json', xtrk=f'{R}/docs/research/work/leak-decomp-20261030/tierA/xstar_trk.json')
out = {}
for ep in (0, 2):
    D = LT.load(a, ep); out[ep] = {}
    for arm in ('P_base', 'O_base'):
        for v in ('', '_depen'):
            Z = np.load(f'{W}/a3/ep{ep}/{arm}{v}_settle.npz')
            s = LT.scored(D.names, Z['OBJ_settle'], D.gt, D.H, D.REGk, D.REGg)
            out[ep][arm + v] = dict(star=s['star']['AUC'], lib=s['lib']['AUC'], stats=json.loads(str(Z['stats'])))
        Zn, Zd = np.load(f'{W}/a3/ep{ep}/{arm}_settle.npz'), np.load(f'{W}/a3/ep{ep}/{arm}_depen_settle.npz')
        out[ep][arm + '_maxdiff_cm'] = round(float(np.abs(Zn['OBJ_settle'][..., :3, 3] - Zd['OBJ_settle'][..., :3, 3]).max() * 100), 3)
        print(ep, arm, 'no depen *', out[ep][arm]['star'], 'depen *', out[ep][arm + '_depen']['star'], 'lib', out[ep][arm]['lib'], out[ep][arm + '_depen']['lib'],
              'max pos diff cm', out[ep][arm + '_maxdiff_cm'], flush=True)
json.dump(out, open(f'{W}/a3_depen_check.json', 'w'), indent=1)
