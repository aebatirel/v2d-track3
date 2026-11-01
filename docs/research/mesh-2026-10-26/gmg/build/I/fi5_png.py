"""PREREG F-I5.14 (T-I13 public): one PNG per episode from fi5_png_data.py output and the episode summary (reads JSON /
npz only; run with any Python that has matplotlib, e.g. the MediaPipe venv).

  python fi5_png.py <RUN/fi5png/ep<N>.json> <summary_ep<N>.json> <out.png>
Panels per pair: (1) collider overlap along the track (one object's 2 mm collider samples inside the other's pieces),
default pieces solid, delivered pieces dashed, with the build run, S frames and overshoot frames marked; (2) a 3 mm slab
section at the guest's rest pose: receiver default pieces (grey), failed carve (red outline points) or delivered carve
(green), guest at T_rest (blue); (3) S (hands-off rest) mean displacement per S frame, default vs carved / failed carve.
"""
import json
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402


def main():
    dj, sj, out = sys.argv[1:4]
    D = json.load(open(dj))
    Sm = json.load(open(sj))
    DS = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else {}
    Z = np.load(dj[:-5] + '.npz')
    pairs = list(D['pairs'])
    fig, axs = plt.subplots(len(pairs), 3, figsize=(16, 4.6 * len(pairs)), squeeze=False,
                            gridspec_kw=dict(width_ratios=[2.2, 1.3, 1.0]))
    for i, key in enumerate(pairs):
        P = D['pairs'][key]
        R = Sm['pairs'].get(key, {})
        ax = axs[i][0]
        fr = P['frames']
        cols = ['#1f6fb4', '#d9631e']
        for j, (k, ser) in enumerate(sorted(P['overlap'].items())):
            side, name = k.split('|')
            ax.plot(fr, ser, ls='-' if name == 'default' else '--', color=cols[0 if side.split('<-')[0] ==
                                                                             key.split('|')[0] else 1],
                    lw=1.4 if name == 'default' else 1.0, label=f'{side} ({name} pieces)')
        if P.get('run'):
            ax.axvspan(P['run'][0], P['run'][1], color='0.9', zorder=0, label='engaged run (receiver side)')
        for f in P.get('s_frames') or []:
            ax.axvline(f, color='green', lw=1, ls=':')
        for f in P.get('overshoot') or []:
            ax.axvline(f, color='red', lw=0.6, alpha=0.5)
        ax.set_xlabel('frame'); ax.set_ylabel('collider overlap (cm$^3$)')
        dsp = (DS.get('pairs') or {}).get(key) or {}
        rc = R.get('receiver') or dsp.get('receiver')
        gname = R.get('guest') or dsp.get('guest')
        ttl = (f"ep{D['ep']} {key}: {'in scope' if R.get('in_scope') else 'out of scope'}"
               + (f", receiver {rc}" if rc else '') + f"; delivered: {R.get('deliver') or 'default'}")
        ax.set_title(ttl, fontsize=10)
        ax.legend(fontsize=7, loc='upper left')
        ax = axs[i][1]
        k0 = key.replace('|', '__')
        if f'{k0}__recv_default' in Z.files:
            for nm, c, s in (('body_recv', '0.85', 0.3), ('body_guest', '#aec7e8', 0.3),
                             ('recv_default', '0.45', 2.0), ('recv_failed', '#d62728', 0.8),
                             ('recv_delivered', '#2ca02c', 0.8), ('guest_rest', '#1f6fb4', 1.2)):
                if f'{k0}__{nm}' not in Z.files:
                    continue
                A = Z[f'{k0}__{nm}']
                if nm == 'recv_delivered' and not str(R.get('deliver', '')).startswith('carved'):
                    continue
                if len(A):
                    ax.scatter(A[:, 1] * 1e3, -A[:, 0] * 1e3, s=s, c=c, lw=0,
                               label={'body_recv': f'{rc} body (SHELL surface)',
                                      'body_guest': f"{gname} body at rest",
                                      'recv_default': f'{rc} default pieces', 'recv_failed': f'{rc} failed carve',
                                      'recv_delivered': f'{rc} delivered carve',
                                      'guest_rest': f"{gname} pieces at rest"}[nm])
            ax.set_aspect('equal'); ax.set_xlabel('mm (receiver principal horizontal axis)')
            ax.set_ylabel('mm (up)')
            ax.set_title('side view at the hands-off rest pose' + (' (S frame; pair out of scope)' if not R.get('in_scope')
                                                                  else '') + ' (pieces = 2 mm samples)', fontsize=8)
            ax.legend(fontsize=6, markerscale=6, loc='lower left')
        else:
            ax.text(0.5, 0.5, 'no rest pose (no hands-off static frame)', ha='center', va='center',
                    fontsize=9, transform=ax.transAxes)
            ax.set_axis_off()
        ax = axs[i][2]
        acc = (R.get('acceptance') or {}).get('S') or {}
        dg = R.get('diag_S_rows') or {}
        rows = []
        if acc.get('default'):
            rows = [('default', acc['default']), ('carved' if str(R.get('deliver', '')).startswith('carved') else
                                                  'carved (failed, not delivered)', acc.get('carved') or [])]
        elif dg:
            rows = [('default', dg.get('default') or []), ('failed carve (report only)', dg.get('carved_failed') or [])]
        elif ((DS.get('pairs') or {}).get(key) or {}).get('S'):
            rows = [('delivered default (diagnostic F-I5.14 (7))',
                     [dict(f=r['frame'], **r['default']) for r in DS['pairs'][key]['S']])]
        if rows:
            fs = [r['f'] for r in rows[0][1]]
            x = np.arange(len(fs))
            for j, (nm, rr) in enumerate(rows):
                vals = [r.get('disp_mm') or 0 for r in rr]
                off = (j - 0.5) * 0.38 if len(rows) > 1 else 0.0
                ax.bar(x[:len(vals)] + off, vals, 0.36, label=nm,
                       color=['0.55', '#2ca02c' if nm == 'carved' else '#d62728'][j])
                for xi, v in zip(x, vals):
                    ax.text(xi + off, v, f'{v:.1f}', ha='center', va='bottom', fontsize=7)
            ax.axhline(4.0, color='k', ls='--', lw=0.8, label='S bound 4 mm')
            ax.set_xticks(x); ax.set_xticklabels([f'f{f}' for f in fs])
            ax.set_ylabel('mean guest displacement, hands off (mm)')
            ax.set_title('S (16 copies, 2 s, receiver fixed)', fontsize=9)
            ax.legend(fontsize=7)
        else:
            why = 'not run: ' + ('out of scope' if not R.get('in_scope') else
                                 ((R.get('acceptance') or {}).get('S') or {}).get('why') or 'no S frame / no table')
            ax.text(0.5, 0.5, why, ha='center', va='center', fontsize=9, transform=ax.transAxes, wrap=True)
            ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(out, dpi=90)
    print('wrote', out)


if __name__ == '__main__':
    main()
