"""Summarise symm2 curves: secondary extrema, depth ratio, half-rise width."""
import numpy as np, json, sys
def summ(ang, y, kind):
    y = np.asarray(y, float); n = len(y); s = -1 if kind == 'corr' else 1   # turn corr into a cost
    c = s * y; f = c[0]; top = np.nanmax(c)
    lm = [i for i in range(1, n) if c[i] <= c[i - 1] and c[i] <= c[(i + 1) % n] and np.isfinite(c[i])]
    # half-rise width (deg) of the main basin
    half = f + 0.5 * (top - f); w = next((ang[i] for i in range(1, n // 2) if c[i] >= half), np.nan)
    wm = next((360 - ang[n - i] for i in range(1, n // 2) if c[n - i] >= half), np.nan)
    best = min(lm, key=lambda i: c[i]) if lm else None
    depth = (top - c[best]) / (top - f) if best is not None and top > f else 0.0   # 1 = perfect repeat, 0 = none
    return dict(f=s * f, top=s * top, sec=None if best is None else s * c[best], sec_at=None if best is None else ang[best],
                depth=float(depth), halfw=(float(w) + float(wm)) / 2, nmin=len(lm))
if __name__ == '__main__':
    for n in sys.argv[1:]:
        r = json.load(open(f'out/symm2_{n}.json')); ang = np.array(r['angles'])
        print(f"{n}: hp rms all {r['hp_rms_all']:.3f} nomk {r['hp_rms_nomk']:.3f}; marker area {r['marker_area_frac']:.3f}; n markers {len(r['markers'])}")
        for tag in ['all', 'nomk']:
            for k in ['geo', 'out2', 'cmad', 'corr']:
                q = summ(ang, r[tag][k], k); sc = 1000 if k == 'geo' else 1
                sec = 'none' if q['sec'] is None else f"{q['sec']*sc:.3f} @ {q['sec_at']:.0f}"
                print(f"  {tag:4s} {k:4s}: at0 {q['f']*sc:.3f}  worst {q['top']*sc:.3f}  best-other {sec}  depth {q['depth']:.2f}  half-rise width {q['halfw']:.0f} deg")
