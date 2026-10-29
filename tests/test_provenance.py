"""pipeline/provenance.py (mesh v5 spec section 3): deny by glob and by sha256, unknown provenance, tier propagation,
a changed artifact. Self-contained: a temporary deny-list (V2D_DENYLIST), no scans needed. Run: python -m pytest tests"""
import importlib, json, os, sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pipeline'))


@pytest.fixture
def P(tmp_path, monkeypatch):
    bad = tmp_path / 'scan_copy.bin'; bad.write_bytes(b'a public scan')
    import provenance
    dl = tmp_path / 'denylist.json'
    dl.write_text(json.dumps(dict(globs=['*/t3/mesh/*'], sha256={provenance.sha256(str(bad)): 'test scan'})))
    monkeypatch.setenv('V2D_DENYLIST', str(dl))
    mod = importlib.reload(provenance)
    return mod


def test_deny_glob_and_sha(P, tmp_path):
    (tmp_path / 't3' / 'mesh').mkdir(parents=True); scan = tmp_path / 't3' / 'mesh' / 'x.glb'; scan.write_bytes(b'x')
    with pytest.raises(P.Deny):
        P.check([dict(role='others', path=str(scan))])
    with pytest.raises(P.Deny):                                   # renamed copy of a deny-listed file
        P.check([dict(role='video', path=str(tmp_path / 'scan_copy.bin'))])


def test_unknown_provenance_is_deny(P, tmp_path):
    f = tmp_path / 'tracks.npz'; f.write_bytes(b't')
    with pytest.raises(P.Deny):
        P.check([dict(role='poses', path=str(f))])


def test_tiers_and_changed_artifact(P, tmp_path):
    v = tmp_path / 'v.mp4'; v.write_bytes(b'v'); t = tmp_path / 't.npz'; t.write_bytes(b't'); m = tmp_path / 'm.glb'; m.write_bytes(b'm')
    assert P.write(str(t), 'tracks', [dict(role='video', path=str(v))])['tier'] == 'P0'
    assert P.write(str(m), 'mesh', [dict(role='poses', path=str(t))])['tier'] == 'P0'
    p1 = tmp_path / 'p1.npz'; p1.write_bytes(b'p'); P.write(str(p1), 'tracks', [dict(role='video', path=str(v), tier='P1')])
    assert P.check([dict(role='poses', path=str(p1)), dict(role='mesh', path=str(m))]) == 'P1'
    m.write_bytes(b'changed')
    with pytest.raises(P.Deny):
        P.check([dict(role='mesh', path=str(m))])
