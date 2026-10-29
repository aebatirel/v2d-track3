"""Contact slot names (2026-10-25): mkref's contact_slot_names column and tools/contact_slots.py must describe the probe
order mkref fills (PROBE_SITES, then the palm), never mano_link_names. The kit round trip runs only with V2D (a
video_to_data checkout at the evaluator pin) and SLOT_REF (a processed reference task directory) set."""
import importlib.util, os, sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools'))
import contact_slots as cs  # noqa: E402


def mkref():
    spec = importlib.util.spec_from_file_location('mkref', os.path.join(REPO, 'pipeline', 'mkref.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def table(**cols):
    pa = pytest.importorskip('pyarrow')
    return pa.table({k: [v] for k, v in cols.items()})


def test_helper_matches_mkref_probe_order():
    mk = mkref()
    assert mk.CONTACT_SLOT_NAMES == mk.PROBE_SITES + ['palm'] == cs.CONTACT_SLOT_NAMES
    assert mk.N_SLOTS == len(cs.CONTACT_SLOT_NAMES) == 16
    src = open(os.path.join(REPO, 'pipeline', 'mkref.py')).read()
    assert "probes = [frames[:, ix[f'{side}_{s}'], :3] for s in PROBE_SITES]" in src, 'compute_contacts probe order moved'
    assert 'contact_slot_names=list(CONTACT_SLOT_NAMES)' in src and 'data.contact_slot_names = list(CONTACT_SLOT_NAMES)' in src


def test_digit_slots_and_short_names():
    d = cs.digit_slots(cs.CONTACT_SLOT_NAMES)
    assert d == {'thumb': [0, 5, 10], 'index': [1, 6, 11], 'middle': [2, 7, 12], 'ring': [3, 8, 13],
                 'pinky': [4, 9, 14], 'palm': [15]}
    assert [cs.short(n) for n in cs.CONTACT_SLOT_NAMES][::5] == ['thumb_tip', 'thumb_DP', 'thumb_MCP', 'palm']


def test_slot_names_column_fallback_and_refusal():
    names = list(cs.CONTACT_SLOT_NAMES)
    assert cs.slot_names(table(contact_slot_names=names[::-1], raw_motion_file='x')) == names[::-1]
    assert cs.slot_names(table(raw_motion_file='/c/poses.npz|/c/hands.npz')) == names     # older mkref reference
    with pytest.raises(ValueError):
        cs.slot_names(table(raw_motion_file='/kit/seq.npz'))                             # kit labeller: MANO order


@pytest.mark.skipif(not (os.environ.get('V2D') and os.environ.get('SLOT_REF')), reason='needs V2D and SLOT_REF')
def test_kit_roundtrip(tmp_path):
    """Stage (e) write path with the kit's own logger and FlashCHORD's load_reference (evaluator pin)."""
    import numpy as np
    import pyarrow.parquet as pq
    v2d, ref = os.environ['V2D'], os.environ['SLOT_REF']
    sys.path[:0] = [os.path.join(v2d, 'robotic_grounding', 'source', 'robotic_grounding'),
                    os.path.join(v2d, 'robotic_grounding', 'flash_chord', 'src')]
    mk = mkref()
    lay = dict(n_frames=67, n_fingers=22, n_tasks=11)
    Kit, MSD = mk.patch_logger(lay), mk.patch_logger(lay, slot_names=True)
    import robotic_grounding.retarget.data_logger as dl
    assert dl.ManoSharpaData is Kit and 'contact_slot_names' not in Kit._schema.names    # E2S keeps the kit class
    data = MSD.from_parquet(ref)
    data.contact_slot_names = list(mk.CONTACT_SLOT_NAMES)
    data.save_to_parquet(str(tmp_path), partition_cols=['sequence_id', 'robot_name'])
    task = tmp_path / f'sequence_id={data.sequence_id}' / 'robot_name=sharpa_wave'
    (f,) = list(task.glob('*.parquet'))
    t = pq.read_table(f)
    assert cs.slot_names(t) == mk.CONTACT_SLOT_NAMES
    assert t.column('mano_link_names')[0].as_py()[0] == 'link_palm'
    old, back = Kit.from_parquet(ref), Kit.from_parquet(str(task))
    assert all(getattr(old, k) == getattr(back, k) for k in Kit._schema.names)
    from flash_chord.data.loader import load_reference
    r0 = load_reference(ref, control_fps=20.0, motion_speed=1.0)
    r1 = load_reference(str(task), control_fps=20.0, motion_speed=1.0)
    for s in ('left', 'right'):
        assert np.array_equal(r0._contact_part_ids[s], r1._contact_part_ids[s])
        assert np.array_equal(r0._contact_pos_w[s], r1._contact_pos_w[s])
        assert np.array_equal(r0._wrist_pos_w[s], r1._wrist_pos_w[s])
