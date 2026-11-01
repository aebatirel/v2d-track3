"""[D] Placement error of every SAM 3D fit variant, computed exactly from one scan registration per raw mesh:
T_ideal = A o T_fit (A from decomp_before.jsonl), error of variant T_v: E_v = T_ideal o T_v^-1 (maps our placed mesh
onto the true placement). Shape error is a property of the raw mesh and is the same for all variants.
Writes analysis.json and tables.md.
"""
import json, sys
import numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/diag/sam-placement')
from common import *  # noqa


def sym_rot(obj, R, V, k):
    """rotation error as the kit counts it: axial -> tilt of the symmetry axis; half-turn -> min over the half turn."""
    from scipy.spatial.transform import Rotation as Rot
    if obj not in SYM:
        return angle_deg(R)
    a = V[:, k]
    if SYM[obj] == 'axial':
        return math.degrees(math.acos(np.clip((R @ a) @ a, -1, 1)))
    return min(angle_deg(R), angle_deg(R @ Rot.from_rotvec(a * math.pi).as_matrix()))


def describe(E, X, obj, d):
    s, R, t = E
    c = X.mean(0)
    Ec = apply(E, c[None])[0]
    V = np.array(d['scan_pca'])
    k = d.get('sym_axis_pca')
    tw = [swing_twist(R, V[:, i])[1] for i in range(3)]
    axis = np.abs(V.T @ rot_axis(R))
    out = dict(size_pct=(1 / s - 1) * 100, rot=angle_deg(R), rot_kit=sym_rot(obj, R, V, k if k is not None else 0),
               axis_pca=axis.round(2).tolist(), twist_pca=np.round(tw, 1).tolist(),
               trans_mm=float(np.linalg.norm(Ec - c) * 1e3), trans_pca_mm=np.round((V.T @ (c - Ec)) * 1e3, 1).tolist(),
               addlike_mm=float(np.linalg.norm(apply(E, X) - X, axis=1).mean() * 1e3),
               add_rigid_mm=float(np.linalg.norm((X - c) @ R.T + Ec - X, axis=1).mean() * 1e3))
    if k is not None:
        out['sym_tilt'], out['sym_roll'] = swing_twist(R, V[:, k])
    # symmetry-aware ADD~ (what the kit's ADD counts): min over the declared symmetry group S, acting about the
    # scan's symmetry axis through the true centroid E(c), of mean |S(E(x)) - x|
    EX = apply(E, X)
    RX = (X - c) @ R.T + Ec                     # same, with the scale error removed (the kit normalises scale)
    for key, Z in (('add_sym_mm', EX), ('add_sym_rigid_mm', RX)):
        if obj in SYM:
            from scipy.spatial.transform import Rotation as Rot
            angs = np.linspace(0, 2 * np.pi, 72, endpoint=False) if SYM[obj] == 'axial' else [0, np.pi]
            best = np.inf
            for th in angs:
                S = Rot.from_rotvec(V[:, k] * th).as_matrix()
                best = min(best, float(np.linalg.norm((Z - Ec) @ S.T + Ec - X, axis=1).mean()))
            out[key] = best * 1e3
        else:
            out[key] = float(np.linalg.norm(Z - X, axis=1).mean() * 1e3)
    return out


def main():
    dec = {}
    for f in ('decomp_before.jsonl', 'decomp_other.jsonl'):
        if os.path.exists(f'{OUT}/{f}'):
            for l in open(f'{OUT}/{f}'):
                r = json.loads(l); dec[(r['model'], r['obj'], r['seed'])] = r
    fits = {}
    if os.path.exists(f'{OUT}/fits.jsonl'):
        for l in open(f'{OUT}/fits.jsonl'):
            r = json.loads(l); fits[(r['obj'], r['seed'], r['variant'])] = r
    rows = []
    for obj in OBJS:
        for seed in (42, 7):
            d = dec.get(('sam3d', obj, seed))
            if d is None:
                continue
            rp, pp = gen_paths('sam3d', obj, seed)
            raw = load_mesh(rp); M, _ = surf(raw, 4000, seed=1)
            Tfit, _ = recover_T(raw, load_mesh(pp))
            A = (d['scale_A'], np.array(d['R']), np.array(d['t']))
            Tid = compose(A, Tfit)
            row = dict(obj=obj, seed=seed, shape_mm=d['shape_mm'], shape90_mm=d['shape90_mm'],
                       ext_ratio=d['ext_ratio_pca'], ray_vs_perp=d['ray_vs_perp'], alt_gap=d['alt_gap'],
                       s_ideal=Tid[0], s_fit=Tfit[0], variants={})
            row['variants']['sim3_fit'] = describe(compose(Tid, inv(Tfit)), apply(Tfit, M), obj, d)
            for v in ('vis', 'vis_slib', 'lib', 'lib_vis'):
                f = fits.get((obj, seed, v))
                if f is None:
                    continue
                T = (f['s'], np.array(f['R']), np.array(f['t']))
                row['variants'][v] = describe(compose(Tid, inv(T)), apply(T, M), obj, d)
                row['variants'][v]['s'] = f['s']
            # post-hoc GT-free gate [H]: use lib unless its own registration is ambiguous (second-best start > 30 deg
            # away within 0.1 mm) on an object the kit does not declare symmetric; then keep sim3_fit
            fl = fits.get((obj, seed, 'lib'))
            if fl is not None and 'lib' in row['variants']:
                gap = (fl['lib_second_mm'] - fl['lib_symdist_mm']) if fl.get('lib_second_mm') is not None else 9.9
                use = 'lib' if (gap >= 0.1 or obj in SYM) else 'sim3_fit'
                row['variants']['lib_gated'] = dict(row['variants'][use], gate=use, lib_gap_mm=gap)
            rows.append(row)
    json.dump(rows, open(f'{OUT}/analysis.json', 'w'), indent=1)
    # library and other models: the decomposition directly
    other = [r for k, r in dec.items() if k[0] != 'sam3d']
    L = []
    L.append('## SAM 3D placement error in our frame vs the scan [D]\n')
    L.append('size = our mesh size / true - 1; rot = full rotation error; kit-rot = as the kit counts it (cups: tilt of '
             'the symmetry axis only; lid: modulo the half turn); twist about scan PCA axes long/mid/short; trans = '
             'centroid offset; ADD~ = mean point displacement (all effects); shape = sym. mean distance to the scan '
             'after the best similarity; ext = extents / scan extents along scan PCA long/mid/short; ray/perp = '
             'extent ratio along our crop camera ray over the perpendicular mean.\n')
    L.append('| object | seed | size % | rot deg | kit-rot | twist L/M/S deg | trans mm | offset L/M/S mm | ADD~ mm | ADD~sym mm | shape mm | ext L/M/S | ray/perp |')
    L.append('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for r in rows:
        b = r['variants']['sim3_fit']
        L.append(f"| {r['obj']} | {r['seed']} | {b['size_pct']:+.1f} | {b['rot']:.1f} | {b['rot_kit']:.1f} | "
                 f"{'/'.join(f'{x:.0f}' for x in b['twist_pca'])} | {b['trans_mm']:.1f} | {'/'.join(f'{x:+.0f}' for x in b['trans_pca_mm'])} | {b['addlike_mm']:.1f} | {b['add_sym_mm']:.1f} | "
                 f"{r['shape_mm']:.1f} | {'/'.join(f'{x:.2f}' for x in r['ext_ratio'])} | {r['ray_vs_perp']:.2f} |")
    L.append('\n## Fix variants: ADD~sym mm (size %, kit-rot deg) per SAM 3D mesh [D]\n')
    L.append('ADD~sym = mean point displacement, minimised over the declared symmetry group (cups: any roll; lid: half turn), '
             'like the kit ADD. All variants are GT-free fits; the error is measured against the scan [D].\n')
    vs = ['sim3_fit', 'vis', 'vis_slib', 'lib', 'lib_vis', 'lib_gated']
    L.append('| object | seed | ' + ' | '.join(vs) + ' |')
    L.append('|---|---|' + '---|' * len(vs))
    agg = {v: [] for v in vs}
    for r in rows:
        cells = []
        for v in vs:
            e = r['variants'].get(v)
            if e is None:
                cells.append('-'); continue
            agg[v].append(e)
            cells.append(f"{e['add_sym_mm']:.1f} ({e['size_pct']:+.0f}%, {e['rot_kit']:.0f}°)")
        L.append(f"| {r['obj']} | {r['seed']} | " + ' | '.join(cells) + ' |')
    L.append('\n| summary | ' + ' | '.join(vs) + ' |')
    L.append('|---|' + '---|' * len(vs))
    for name, fn in [('median ADD~sym mm', lambda es: np.median([e['add_sym_mm'] for e in es])),
                     ('mean ADD~sym mm', lambda es: np.mean([e['add_sym_mm'] for e in es])),
                     ('ADD~sym <= 10 mm', lambda es: sum(e['add_sym_mm'] <= 10 for e in es)),
                     ('median ADD~sym, scale removed (kit-like) mm', lambda es: np.median([e['add_sym_rigid_mm'] for e in es])),
                     ('mean ADD~sym, scale removed mm', lambda es: np.mean([e['add_sym_rigid_mm'] for e in es])),
                     ('median abs size %', lambda es: np.median([abs(e['size_pct']) for e in es])),
                     ('median kit-rot deg', lambda es: np.median([e['rot_kit'] for e in es])),
                     ('kit-rot > 90 (flip)', lambda es: sum(e['rot_kit'] > 90 for e in es)),
                     ('kit-rot > 20', lambda es: sum(e['rot_kit'] > 20 for e in es)),
                     ('n', lambda es: len(es))]:
        L.append(f'| {name} | ' + ' | '.join(f'{fn(agg[v]):.1f}' if agg[v] else '-' for v in vs) + ' |')
    L.append('\n## Other placed meshes, decomposition vs the scan [D]\n')
    L.append('| model | object | seed | size % | rot deg | trans mm | ADD~ mm | shape mm | ext L/M/S | ray/perp |')
    L.append('|---|---|---|---|---|---|---|---|---|---|')
    for r in sorted(other, key=lambda r: (r['model'], OBJS.index(r['obj']), r['seed'] or 0)):
        L.append(f"| {r['model']} | {r['obj']} | {r['seed']} | {r['size_err_pct']:+.1f} | {r['rot_deg']:.1f} | "
                 f"{r['trans_mm']:.1f} | {r['addlike_mm']:.1f} | {r['shape_mm']:.1f} | "
                 f"{'/'.join(f'{x:.2f}' for x in r['ext_ratio_pca'])} | {r['ray_vs_perp']:.2f} |")
    open(f'{OUT}/tables.md', 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
