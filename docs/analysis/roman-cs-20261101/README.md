# Roman's compressed-sensing proposal (1 Nov 2026): two quick checks [M, synthetic signals on our real frame times]

Roman proposed (WhatsApp, 1 Nov 11:58–12:00 UTC):
1. randomly remove samples from the 20 Hz frames and reconstruct the spectrum many times ("artificial random timings");
2. stabilise ("lock") each object in the image first;
3. handle spatial jitter and temporal jitter.

Script: `cs_test.py DATA_DIR` (public episode parquets; reads only `capture_time`). Output: `cs_test_out.txt`.

## Results
- **Random removal from a uniform grid cannot separate aliases [M].**
  - Kept 24 of 40 uniform samples (2 s at 20 Hz). A 13 Hz sine fits the remaining samples equally well at
    7 / 13 / 27 / 33 Hz (fit quality 1.000 for all four).
  - A sinusoid and its aliases agree on every grid point, so they agree on every subset of the grid.
  - Resampling is still useful to put error bars on frequencies inside 0–10 Hz (jackknife / bootstrap). It cannot
    recover anything above 10 Hz.
- **The dataset has real timestamp jitter [M].**
  - `capture_time` steps are 50.0 ms on average, sd 1.0–4.3 ms per episode (mean 1.63 ms over 21 public episodes).
  - Lag-1 correlation of the steps is ≈ −0.5. That is the signature of independent jitter around a uniform clock.
  - The `timestamp` column is an exact uniform 49.37 ms grid.
- **If that jitter is the true exposure time, it breaks aliasing [M, synthetic].**
  - A 63 Hz sine sampled at ep2's real capture times over 2 s, recovered by least-squares periodogram.
  - True peak found in 50 / 50 trials at amplitude/noise 10; 27 / 50 at 2; 11 / 50 at 1; 4 / 50 at 0.5; 0 / 50 at 0.2.

## Open questions (best practice before any claim)
1. **Is `capture_time` the exposure time, or the host's receive time?** The −0.5 lag-1 correlation fits either.
   - Test [H, $0]: room lights flicker at 100 Hz (50 Hz mains) or 120 Hz (60 Hz mains). Background intensity sampled
     at `capture_time` should show that line. If it does, the jitter is real sampling. If it only shows up with the
     uniform grid, the stamps are transport noise.
2. **The noise floor in the locked object frame.** Object pose tracks have ~1–6 mm noise, far above sub-mm
   vibrations. Phase-based sub-pixel motion on the stabilised object patch could reach ~0.01 px.
   - Test: power spectral density on untouched objects (floor) vs held objects (any peak above it?).
3. **Physical low-pass filters.**
   - Exposure time averages motion inside each frame. Its sinc response attenuates frequencies near and above
     1 / exposure time.
   - Video compression (inter-frame coding) can erase sub-pixel temporal detail.
   - Both set an upper frequency limit independent of sampling.
4. **Calibrate detection limits with injected synthetic vibrations** before reading any peak as a natural frequency.
