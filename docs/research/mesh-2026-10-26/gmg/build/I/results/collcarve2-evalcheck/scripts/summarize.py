"""Summary of the eval precheck (evalcheck.py per-frame records + contacts.py) -> evalcheck_summary.json.
Usage: python -I summarize.py CONFIG.json GEO_DIR CONTACT_DIR OUT.json"""
import json
import os
import sys

import numpy as np

SMAX_MM, OV_CM3 = 4.0, 1.0


def mx(a, idx):
    idx = np.asarray(idx)
    if not len(idx):
        return dict(max=None, frame=None)
    v = np.asarray(a)[idx]
    i = int(np.argmax(v))
    return dict(max=round(float(v[i]), 2), frame=int(idx[i]))


def block(fr, names, sel):
    rows, P, O = fr['rows'], fr['pair'], fr['obj']
    idx = np.nonzero(sel)[0]
    g = lambda k: np.array([p[k] for p in P])
    Vf, Vp, Vv = g('V_faithful'), g('V_packed'), g('V_visual')
    out = dict(frames=int(len(idx)))
    fa = [r['fails'] for r in rows]
    out['frames_failing'] = int(sum(1 for i in idx if fa[i]))
    out['failing_frames'] = [int(i) for i in idx if fa[i]]
    out['n_ov_faithful_gt0'] = int((Vf[idx] > 0).sum())
    out['n_ov_faithful_ge1cm3'] = int((Vf[idx] >= OV_CM3).sum())
    out['n_ov_packed_ge1cm3'] = int((Vp[idx] >= OV_CM3).sum())
    out['n_ov_visual_ge1cm3'] = int((Vv[idx] >= OV_CM3).sum())
    out['max_V_faithful_cm3'] = mx(Vf, idx)
    out['max_V_packed_cm3'] = mx(Vp, idx)
    out['max_V_visual_cm3'] = mx(Vv, idx)
    per = {}
    for n in names:
        o = O[n]
        h = lambda k: np.array([x[k] for x in o])
        per[n] = dict(n_fail_a_table=int(sum(1 for i in idx if f'a_table:{n}' in fa[i])),
                      n_fail_b_float=int(sum(1 for i in idx if f'b_float:{n}' in fa[i])),
                      max_pen_faithful_mm=mx(h('pen_faithful_mm'), idx), max_pen_visual_mm=mx(h('pen_visual_mm'), idx),
                      max_pen_packed_mm=mx(h('pen_packed_mm'), idx),
                      max_float_faithful_mm=mx(h('float_faithful_mm'), idx),
                      max_float_visual_mm=mx(h('float_visual_mm'), idx),
                      n_off_support=int(h('off_support')[idx].sum()) if len(idx) else 0)
    out['objects'] = per
    return out


def cavity(fr, sel):
    P = fr['pair']
    idx = np.nonzero(sel)[0]
    g = lambda k: np.array([p[k] for p in P])
    cav, rpk, only, vis = g('V_gvis_in_rcavity'), g('V_gvis_in_rpk'), g('V_gvis_in_rpk_only'), g('V_visual')
    dpk, dvis = g('depth_pk_mm'), g('depth_vis_mm')
    inc = idx[cav[idx] >= OV_CM3]
    out = dict(frames=int(len(idx)), frames_guest_in_receiver_cavity=int(len(inc)),
               cavity_frames=[int(i) for i in inc][:400],
               max_V_guest_in_cavity_cm3=mx(cav, idx), max_V_gvis_in_rpk_cm3=mx(rpk, idx),
               max_V_gvis_in_rvis_cm3=mx(vis, idx), max_V_gvis_in_rpk_only_cm3=mx(only, idx),
               n_frames_rpk_only_ge1cm3=int((only[idx] >= OV_CM3).sum()),
               n_cavity_frames_rpk_only_ge1cm3=int((only[inc] >= OV_CM3).sum()),
               n_cavity_frames_rpk_ge1cm3=int((rpk[inc] >= OV_CM3).sum()),
               n_cavity_frames_rvis_ge1cm3=int((vis[inc] >= OV_CM3).sum()),
               n_cavity_frames_rpk_le0p1cm3=int((rpk[inc] <= 0.1).sum()),
               max_depth_pk_mm=mx(dpk, idx), max_depth_vis_mm=mx(dvis, idx),
               max_V_gvis_in_rpk_cavity_frames_cm3=mx(rpk, inc), max_V_rpk_only_cavity_frames_cm3=mx(only, inc))
    out['packed_blocks_beyond_visual'] = bool(out['n_cavity_frames_rpk_only_ge1cm3'] > 0)
    out['packed_blocks'] = bool(out['n_cavity_frames_rpk_ge1cm3'] > 0)
    return out


def main():
    cfg = json.load(open(sys.argv[1]))
    geo, con, outp = sys.argv[2], sys.argv[3], sys.argv[4]
    S = dict(_note='eval precheck summary (diagnostic only); see README.md', episodes={})
    for ep in cfg['episodes']:
        p = os.path.join(geo, f'ep{ep}_frames.json')
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        s, fr = d['summary'], d['per_frame']
        names = s['names']
        rows = fr['rows']
        H0 = np.array([r['H0'] for r in rows]); H30 = np.array([r['H30'] for r in rows])
        ALL = np.ones(len(rows), bool)
        e = dict(ref=cfg['episodes'][ep]['ref_store_path'], ref_md5=cfg['episodes'][ep]['ref_md5'],
                 ref_md5_match=cfg['episodes'][ep]['ref_md5_match'], packed_run=cfg['episodes'][ep]['packed_run'],
                 pieces=cfg['episodes'][ep]['pieces'], objects=s['objects'], receiver=s['receiver'],
                 guest=s['guest'], frames=s['frames'], fps=s['fps'], support=s['support'],
                 n_H0=s['n_H0'], n_H30=s['n_H30'], n_contact_label_frames=s['n_contact_frames'],
                 precheck=dict(H0=block(fr, names, H0), H30=block(fr, names, H30), all=block(fr, names, ALL)),
                 cavity=dict(all=cavity(fr, ALL), H0=cavity(fr, H0)))
        # per-object hand-free frames (contact labels attributed to the nearest object)
        po = {}
        for j, n in enumerate(names):
            free = np.array([not r['contact'][j] for r in rows])
            b = block(fr, names, free)
            po[n] = dict(frames=b['frames'], **b['objects'][n])
        e['precheck']['object_hand_free'] = po
        cp = os.path.join(con, f'ep{ep}_contacts.json')
        if os.path.exists(cp):
            c = json.load(open(cp))
            e['contacts'] = dict(max_nefc=c['max_nefc'], max_ncon=c['max_ncon'], overflow_any=c['overflow_any'],
                                 pieces=c['pieces'], frame_pick=c['frame_pick'],
                                 frames=[{k: v for k, v in a.items() if k != 'per_copy'} for a in c['frames']])
        S['episodes'][ep] = e
    json.dump(S, open(outp, 'w'), indent=1)
    for ep, e in S['episodes'].items():
        h = e['precheck']['H0']
        print(ep, e['receiver'], '<-', e['guest'], 'H0', h['frames'], 'fail', h['frames_failing'],
              'Vf', h['max_V_faithful_cm3'], 'Vp', h['max_V_packed_cm3'],
              {n: (o['max_pen_faithful_mm']['max'], o['max_float_faithful_mm']['max']) for n, o in h['objects'].items()},
              'cav', e['cavity']['all']['frames_guest_in_receiver_cavity'],
              'blk', e['cavity']['all']['packed_blocks_beyond_visual'], e['cavity']['all']['packed_blocks'],
              'nefc', e.get('contacts', {}).get('max_nefc'))


if __name__ == '__main__':
    main()
