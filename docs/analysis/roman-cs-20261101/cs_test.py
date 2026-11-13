"""Roman's compressed-sensing idea, two quick numerical checks (no ground truth; synthetic signals on our real frame times).
(1) uniform 20 Hz grid, random subsets: is a 13 Hz vibration separable from its 7 Hz alias?
(2) the dataset's real capture_time (jittered): is a 63 Hz vibration separable from its aliases, at what noise level?
"""
import glob, sys
import numpy as np, pyarrow.parquet as pq
rng = np.random.default_rng(0)
files = sorted(glob.glob(sys.argv[1] + '/ep*/ep*.parquet')) + glob.glob(sys.argv[1] + '/../ep2.parquet')
J = []
for f in files:
    try:
        ct = np.array(pq.read_table(f, columns=['capture_time']).column(0).to_pylist(), float)
    except Exception:
        continue
    d = np.diff(ct); J.append((f.split('/')[-1], len(ct), d.mean() * 1e3, d.std() * 1e3, (ct - (ct[0] + np.arange(len(ct)) * d.mean())).std() * 1e3,
                              np.corrcoef(d[:-1], d[1:])[0, 1]))
print('capture_time per episode: file, frames, mean dt ms, sd dt ms, sd of offset from a uniform grid ms, lag-1 corr of dt')
for j in J[:8]:
    print('  %-14s %4d  %.3f  %.2f  %.2f  %+.2f' % j)
sd_all = np.mean([j[3] for j in J]); print('mean sd(dt) over %d episodes: %.2f ms' % (len(J), sd_all))

def ls_power(t, x, freqs):  # least-squares sinusoid fit power (Lomb-Scargle style), per frequency
    out = []
    for f in freqs:
        A = np.stack([np.sin(2 * np.pi * f * t), np.cos(2 * np.pi * f * t), np.ones_like(t)], 1)
        c, *_ = np.linalg.lstsq(A, x, rcond=None); r = x - A @ c; out.append(1 - r.var() / x.var())
    return np.array(out)

# (1) uniform grid, random removal
t = np.arange(40) / 20.0  # 2 s of video
x = np.sin(2 * np.pi * 13 * t + 0.4)
for trial in range(3):
    keep = np.sort(rng.choice(40, 24, replace=False))
    p = ls_power(t[keep], x[keep], [7.0, 13.0, 27.0, 33.0])
    print('(1) uniform grid, 24 of 40 samples kept, fit quality at 7 / 13 / 27 / 33 Hz:', np.round(p, 6))

# (2) real jittered times
ct = np.array(pq.read_table(files[-1], columns=['capture_time']).column(0).to_pylist(), float)
seg = ct[100:140] - ct[100]  # 2 s
freqs = np.arange(0.5, 250, 0.25)
f0 = 63.0
for snr in (10.0, 2.0, 1.0, 0.5, 0.2):
    wins = 0
    for trial in range(50):
        x = np.sin(2 * np.pi * f0 * seg + rng.uniform(0, 2 * np.pi)) + rng.normal(0, 1 / snr, len(seg))
        p = ls_power(seg, x, freqs); wins += abs(freqs[np.argmax(p)] - f0) < 0.5
    print('(2) jittered real times, 63 Hz, amplitude/noise = %.1f: true peak found in %d / 50 trials' % (snr, wins))
