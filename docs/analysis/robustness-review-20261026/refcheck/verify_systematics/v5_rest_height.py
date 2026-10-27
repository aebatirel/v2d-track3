"""V5 (verify_systematics): resting heights, my own rest definition.
Rest = mocap kit-anchor speed < 1 mm/frame AND angular speed < 0.5 deg/frame, contiguous blocks of >= 10 frames;
report the FIRST and the LAST such block of each object (trimmed by 2 frames each side).
Heights in the table frame: ours = our path (reference / perception in the reference's table frame), table z 0.600;
mocap table height h = median lowest scan vertex of the object that is lowest at its first rest block; also with
h = 0.600 fixed. Centre = kit anchor (body point of our mesh registered to the scan's surface centroid).
Usage: python -I v5_rest_height.py OUT.json [eps]"""
import json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vload import *  # noqa
import v2_scale_lag_tilt as V


def blocks(mask, minlen=10, trim=2):
    out, i, T = [], 0, len(mask)
    while i < T:
        if mask[i]:
            j = i
            while j < T and mask[j]:
                j += 1
            if j - i >= minlen:
                out.append(np.arange(i + trim, j - trim) if j - i > 2 * trim + 2 else np.arange(i, j))
            i = j
        else:
            i += 1
    return out


def lowest(M, verts):
    return np.einsum('tij,vj->tvi', M[:, :3, :3], verts)[..., 2].min(1) + M[:, 2, 3]


def main():
    eps = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else sorted(CE)
    out = {}
    for ep in eps:
        if ep == 23:
            continue
        names, gt, _ = mocap(ep)
        d = ref_dir(ep); tfp = f'{d}/table_frame.npz' if d else f'{ST}/{V.STALE_TF.format(ep)}'
        TF = np.load(tfp); Tt = TF['T_table_from_world']; tz = float(TF['table_z'])
        P = perc(ep)
        srcs = {'perc': ({n: np.einsum('ij,tjk->tik', Tt, P[n]) for n in names}, V.LIB_PERC[ep])}
        if d:
            srcs['ref'] = (refparq(ref_final(ep)), V.LIB_REF[ep]); srcs['pre'] = (refparq(f'{d}/e2s_reference.parquet'), V.LIB_REF[ep])
        # mocap rest blocks and table height
        rest, lowg, pg = {}, {}, {}
        for s, n in enumerate(names):
            ca, B, sa, sv = V.reg(ep, s, n, srcs['perc'][1])
            g = gt[n]; pg[n] = g[:, :3, :3] @ sa + g[:, :3, 3]
            sp = np.r_[0, np.linalg.norm(np.diff(pg[n], axis=0), axis=1)] * 1000
            ang = np.r_[0, np.degrees(R.from_matrix(np.einsum('tji,tjk->tik', g[1:, :3, :3], g[:-1, :3, :3])).magnitude())]
            bl = blocks((sp < 1.0) & (ang < 0.5))
            rest[n] = (bl[0], bl[-1]) if bl else None
            lowg[n] = lowest(g, sv)
        firsts = {n: float(np.median(lowg[n][rest[n][0]])) for n in names if rest[n] is not None}
        h = min(firsts.values()); hfrom = min(firsts, key=firsts.get)
        row = dict(table_frame=tfp[len(ST) + 1:], mocap_table_h=round(h, 4), h_from=hfrom,
                   mocap_first_rest_lowest={n: round(v, 4) for n, v in firsts.items()}, sources={})
        for k, (ours, lib) in srcs.items():
            r = {}
            for s, n in enumerate(names):
                if rest[n] is None:
                    continue
                ca, B, sa, sv = V.reg(ep, s, n, lib)
                ov = np.asarray(V.vf(f'{REPO}/meshes/{lib}/{n}.glb')[0])
                po = ours[n][:, :3, :3] @ ca + ours[n][:, :3, 3]
                lo = lowest(ours[n], ov)
                rr = {}
                for lab, fr in (('first', rest[n][0]), ('last', rest[n][1])):
                    co = np.median(po[fr, 2] - tz); cg = np.median(pg[n][fr, 2] - h); cg6 = np.median(pg[n][fr, 2] - 0.600)
                    rr[lab] = dict(frames=[int(fr[0]), int(fr[-1])], centre_err_mm=round(float(co - cg) * 1000, 1),
                                   centre_err_mm_h600=round(float(co - cg6) * 1000, 1),
                                   ours_lowest_mm=round(float(np.median(lo[fr]) - tz) * 1000, 1),
                                   mocap_lowest_mm=round(float(np.median(lowg[n][fr]) - h) * 1000, 1))
                    rr[lab]['lowest_err_mm'] = round(rr[lab]['ours_lowest_mm'] - rr[lab]['mocap_lowest_mm'], 1)
                r[n] = rr
            row['sources'][k] = r
        out[ep] = row
        print(ep, json.dumps(row), flush=True)
    json.dump(out, open(sys.argv[1], 'w'), indent=1)


if __name__ == '__main__':
    main()
