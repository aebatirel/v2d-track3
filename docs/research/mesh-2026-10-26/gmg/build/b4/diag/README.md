# B4 round-2 diagnostics (dev, GT-free; not part of any run)

- `det_diag.py EP...`: frame-0 det proposals holding each object's projected track origin (det keys `masks`,
  `mask_shape` only) against the object's final frame-0 owned points of the v4 bundle: area, cover, precision, IoU.
- `f0_diag.py EP HEAD.bin`: where the pixels of an object's chosen proposal go at frame 0 (edge filter, 8 mm table
  band, hand capsules, cube); HEAD.bin = the first frames of our stereo depth file, read with an HTTP range request
  from the HF store (`cache/depth/public/ep<N>/depths_fs0.5.npy`, bytes 0-12.8 MB). Reads the run's MediaPipe hands
  and the bundle's table plane directly (outside the guard).

Inputs: our depth, our tracks, the calibration, the det masks, our bundles and hands. No scan, mesh, mocap, parquet
pose or library file. Results are quoted in `../../B4.md` (round 2) and DEVIATIONS B4-R2.1 and B4-R2.6.
