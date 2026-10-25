"""Names of the 16 contact slots of our references (mano_<side>_object_contact_{positions,normals,part_ids}).

pipeline/mkref.py stage (e) fills slot k from probe CONTACT_SLOT_NAMES[k]: the five tip sites (thumb .. pinky), the five
DP sites, thumb_MCP_VL and the index .. pinky MP sites, then the palm (mean of five palm frames). From 2026-10-25 mkref
also writes these names as the contact_slot_names column.

Do not label slots with the mano_link_names column: it lists MANO links (palm, thumb1 .. pinky3), which describes the
kit's own labeller, not mkref. Reading it as slot labels called the thumb tip "palm" and the palm "pinky3"
(docs/research/approaches-2026-10-25/approach3-grasp-taxonomy.md §9; slot_order_check.py).
"""
CONTACT_SLOT_NAMES = ['thumb_tip_site', 'index_tip_site', 'middle_tip_site', 'ring_tip_site', 'pinky_tip_site',
                      'thumb_DP_site', 'index_DP_site', 'middle_DP_site', 'ring_DP_site', 'pinky_DP_site',
                      'thumb_MCP_VL_site', 'index_MP_site', 'middle_MP_site', 'ring_MP_site', 'pinky_MP_site',
                      'palm']                                        # == pipeline/mkref.py CONTACT_SLOT_NAMES (tests)
DIGITS = ('thumb', 'index', 'middle', 'ring', 'pinky')


def slot_names(table):
    """Probe name of each contact slot of a reference (pyarrow table): its contact_slot_names column, or mkref's order
    for older mkref references (raw_motion_file 'poses|hands'). Anything else is refused: its slots may be MANO-ordered."""
    if 'contact_slot_names' in table.column_names:
        names = table.column('contact_slot_names')[0].as_py()
        if names:
            return list(names)
    raw = table.column('raw_motion_file')[0].as_py() if 'raw_motion_file' in table.column_names else None
    if not raw or '|' not in raw:
        raise ValueError(f'not an mkref reference (raw_motion_file {raw!r}) and no contact_slot_names column: '
                         'its contact slots may be in MANO link order')
    return list(CONTACT_SLOT_NAMES)


def short(name):
    """'thumb_tip_site' -> 'thumb_tip', 'thumb_MCP_VL_site' -> 'thumb_MCP', 'palm' -> 'palm'."""
    return name.replace('_site', '').replace('_VL', '')


def digit(name):
    """'thumb', 'index', 'middle', 'ring', 'pinky' or 'palm'."""
    return name.split('_')[0]


def digit_slots(names):
    """{'thumb': [0, 5, 10], ..., 'palm': [15]} for the mkref order."""
    return {g: [k for k, n in enumerate(names) if digit(n) == g] for g in DIGITS + ('palm',)}


if __name__ == '__main__':
    import argparse
    import numpy as np
    import pyarrow.parquet as pq
    p = argparse.ArgumentParser(description='Per-window contact shares of one hand on one object, per slot and per digit '
                                            '(any slot of the digit). Our references only; no ground truth.')
    p.add_argument('ref')
    p.add_argument('windows', nargs='+', help='SIDE:OBJECT:F0-F1 (frames F0 .. F1-1)')
    p.add_argument('--per', choices=('contact', 'frames'), default='contact',
                   help='denominator: frames with any contact on the object (default) or all frames of the window')
    p.add_argument('--mano', action='store_true',
                   help='label slots with mano_link_names instead (the old, wrong reading; to reproduce earlier tables)')
    a = p.parse_args()
    t = pq.read_table(a.ref)
    objs = t.column('object_body_names')[0].as_py()
    if a.mano:
        names = [n.replace('link_', '') for n in t.column('mano_link_names')[0].as_py()]
        labels, dig = names, {g: [k for k, n in enumerate(names) if n.startswith(g)] for g in DIGITS + ('palm',)}
    else:
        names = slot_names(t)
        labels, dig = [short(n) for n in names], digit_slots(names)
    print(f'{a.ref}\nlabels: {"mano_link_names (old reading)" if a.mano else "mkref slot order"}; shares over '
          f'{"contact frames" if a.per == "contact" else "all window frames"}')
    for w in a.windows:
        side, obj, fr = w.split(':'); f0, f1 = map(int, fr.split('-')); j = objs.index(obj)
        nrm = np.array(t.column(f'mano_{side}_object_contact_normals')[0].as_py(), float)[f0:f1]
        pid = np.array(t.column(f'mano_{side}_object_contact_part_ids')[0].as_py())[f0:f1]
        on = (np.linalg.norm(nrm, axis=-1) > 1e-3) & (pid == j + 1)
        anyc = on.any(1)
        base = on[anyc] if a.per == 'contact' else on
        if not len(base):
            print(f'{w}: no contact frames'); continue
        sl = sorted(((float(base[:, k].mean()), labels[k]) for k in range(len(labels))), reverse=True)
        print(f'{w}: {int(anyc.sum())}/{f1 - f0} contact frames | digits '
              + ' '.join(f'{g} {base[:, ks].any(1).mean():.2f}' for g, ks in dig.items())
              + ' | slots ' + ', '.join(f'{lab} {v:.2f}' for v, lab in sl if v >= 0.05))
