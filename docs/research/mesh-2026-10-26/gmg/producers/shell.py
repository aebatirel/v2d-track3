"""P-SHELL (SPEC section 8; minimal form for build step B1): the route-A thin shell autokit/shell.thin_shell over the
owned points (own == 0) at the unseen-wall thickness t0 (measured two-sided thickness kept where both faces were
seen), <= 4000 faces. Also the reference s of veto V3. Not yet in B1: the closing by the support plane where the
object rests (SPEC section 8 table, section 9 rule 3b; build step B8). A thin shell completes nothing beyond the
thickness behind its observed face; its partner clip is the construction-time V2 (a) check (complete.clip_check),
reported with the candidate."""
from __future__ import annotations

import numpy as np

from gmg import complete
from gmg.producers import Candidate


def produce(ctx, frames=None):
    from autokit import shell as SH
    b, obj, t0 = ctx['bundle'], ctx['obj'], float(ctx['t0'])
    obs = b.obs(obj)
    m = np.asarray(obs['own']) == 0
    if frames is not None:
        m &= np.isin(np.asarray(obs['frame']), np.asarray(list(frames)))
    sub = {k: np.asarray(obs[k])[m] for k in ('pts', 'cam', 'frame')}
    mesh, rep = SH.thin_shell(sub, t=t0, return_report=True)
    keep = ('points', 'frames', 'samples', 'two_sided_frac', 'two_sided_T_mm_p10_50_90', 'sheet_area_cm2', 'faces',
            'watertight', 'bodies', 'area_cm2', 'volume_cm3', 'extents_cm', 'islands_dropped', 'sec', 'empty')
    report = {k: rep.get(k) for k in keep if k in rep}
    report['partner_clip'] = complete.clip_check(mesh, b, obj)
    flags = ['no_support_closing_B8']
    if report['partner_clip']['deep_total']:
        flags.append('partner_deep_samples')
    cid = 'shell_t' + f'{t0 * 1e3:.2f}'.replace('.', 'p')
    return [Candidate(cid=cid, producer='P-SHELL', cls='SHELL',
                      mesh=mesh, params=dict(t0_mm=round(t0 * 1e3, 4)), n_params=0, t_mm=round(t0 * 1e3, 4),
                      built_on_frames='all' if frames is None else 'subset', flags=flags, report=report)]
