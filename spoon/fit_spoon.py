#!/usr/bin/env python3
"""SKELETON (not run): fit the wooden-spoon template's continuous parameters to stereo observations of the RESTING
spoon (mask + depth + triangulated markers) on a Colab GPU, then rebuild the watertight asset with spoon_template.py.

Status: written 2026-10-13 as a documented plan plus code scaffolding. It has NOT been executed: torch is not installed
locally, the observation export does not exist yet, and installing anything here was out of scope. Every function body
marked TODO must be completed and unit-tested on Colab before use. Read colab/spoon/README.md first.

Why fit at all (note 13 Stage C, note 20):
  * CD-O is insensitive to the fit (any complete spoon-shaped mesh scores 0.11-0.16 cm). What matters is the FRAME: the
    organisers' R1 frame of their (hidden) scan. On our default template the y (roll) bit is a near-tie
    (skew toward M2 = -0.0038 => frame A by a hair; noisy P(B) ~0.43). The sign moves with the bowl bend (~0.006 per mm),
    the M1/M2 lateral asymmetry (~0.012 per mm) and the marker heights. So the fit must deliver a POSTERIOR for
    skew_y (and skew_x), not just a point estimate.
  * The template is also the marker model for the tracker and the sim asset. Origin/tilt stability: ~3 mm / ~0.6 deg
    (note 13 Stage C proxy T1).

Observations (prepared on CPU, one .npz per (episode, frame) of a STATIC rest segment; no ground truth anywhere):
  K (3,3)            rectified left-camera intrinsics (ego_cam_c as given, notes 11/15/20; b/c same-index pairs)
  hw (2,)            image height, width
  mask (H,W) bool    spoon mask (note 20 round-3 flat-object mask: local brightness on the stereo table + metric
                     footprint; excludes hands; for 35/36/37 f0..f3 and the end-of-clip rests 35/37/3)
  depth (H,W) f32    metric depth (SGBM / FoundationStereo on the dy-FIELD-rectified pair, note 20 B2), 0 = invalid
  conf (H,W) f32     optional per-pixel weight (left-right consistency, texture); pale wood is textureless => weak
  plane (4,)         table plane n.x + d = 0 in the camera frame, n pointing up (RANSAC on SGBM, note 20 B1)
  markers (3,3)      triangulated M1, M2, M3 centres (camera frame, metres), identity from the triangle (53/153/194 mm)
  markers_sd (3,)    per-marker 3-D sd (M1 is the weak one in mono: 3-10 mm depth spread, note 20)
  meta               episode, frame, camera names, rest-segment id
  Optional extra views: cam-a silhouette with its own K/extrinsics (2x resolution; rolling shutter is irrelevant at rest).
Use only rest frames (spoon untouched). Per note 20 the rest roll is -2.5 +- 3 deg, so contact is on the convex bowl back
and the handle: the contact term below encodes that without hand labels.

Unknowns:
  theta (shared): FIT_PARAMS below (body planform/thickness/bend, marker centres in the construction frame).
  pose_i in SE(3) per rest SEGMENT (construction frame -> camera), initialised by Kabsch on the 3 markers.
Fixed: marker sphere radius 7.2 mm, stem geometry, tessellation (RES), handle/neck aspect 1.0 (note 20: round rod).

Loss (all terms robust, weighted; pure torch by default, nvdiffrast optional):
  L_depth   observed points (mask & valid depth, back-projected) -> unsigned distance to the posed template surface
            (point-to-triangle distance against the visible faces, or a chamfer to dense surface samples);
            Huber 2 mm. This constrains the concave face, rim and handle top (what the camera sees at rest).
  L_model   posed, camera-facing model samples (normal . view < 0) -> nearest observed point (2 mm Huber). Visibility:
            self-occlusion is small at rest (handle over the bowl only at grazing views); nvdiffrast z-buffer if available.
  L_sil     projected visible model samples outside the mask (distance-transform lookup, grid_sample) + mask boundary
            pixels far from the projected model silhouette (2-D chamfer). Sub-pixel matters: 1 px ~ 1 mm at 0.55 m.
  L_mark    Mahalanobis distance of posed model marker centres to the triangulated ones (sd per marker).
  L_contact softmin over model points of the height above the table ~ 0 (touching) + relu(-height)^2 (no penetration).
  L_prior   Gaussian priors from FIT_PARAMS (keeps unobserved parameters, e.g. the bowl back, at their priors).
Optimise with Adam (lr 1e-3 on unconstrained params, 3 stages: poses only -> + planform -> all), 2-4k iterations;
float32 on GPU is fine (mm-scale geometry in metres).

Uncertainty and the frame decision (the main deliverable):
  1. Bootstrap over rest segments/episodes (resample with replacement, B ~ 50) or a Laplace approximation (Hessian of
     the loss at the optimum w.r.t. theta) -> theta samples.
  2. For each sample: spoon_template.build_spoon(params) on CPU -> frame_report() -> skew_x, skew_y (toward M2), skew_z,
     rule labels, noisy P(B). Report the distribution of skew_y and P(skew_y > 0), i.e. P(frame B | mid-axis rule).
  3. Falsifiers: leave-one-episode-out depth/silhouette residuals (must not exceed the in-sample ones by > 30%);
     fitted marker triangle within 1.5 mm of 53.0/153.2/194.2; total length within the 0.30 m +- 7% ruler bracket;
     the posed model must not penetrate the table by > 1 mm in any rest frame.
  Do NOT force frame B: the organisers' answer, or this posterior, decides it (note 13 item 4, note 20).

Run on Colab (after completing the TODOs):
  pip install torch (preinstalled on Colab) [+ optionally nvdiffrast]
  python fit_spoon.py --obs /content/spoon_obs --out /content/spoon_fit --device cuda --iters 3000 --bootstrap 50
  python spoon_template.py --params /content/spoon_fit/fitted_params.json --out /content/spoon_fit/asset --variants
"""
import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spoon_template as st  # noqa: E402  (numpy geometry; its loft functions also accept xp=torch)

# name: (prior mean, prior sd, lower, upper). Units: metres / degrees. Means = template defaults (params.json);
# sds = measurement brackets from notes 13/20 (see README "Uncertainties").
FIT_PARAMS = {
    "total_length": (0.307, 0.006, 0.27, 0.34),
    "bowl_length": (0.095, 0.005, 0.08, 0.11),
    "bowl_width": (0.052, 0.003, 0.04, 0.065),
    "bowl_widest_frac": (0.50, 0.08, 0.30, 0.70),
    "bowl_depth": (0.010, 0.003, 0.004, 0.020),
    "bowl_thickness": (0.005, 0.001, 0.003, 0.008),
    "rim_height": (0.002, 0.002, -0.004, 0.008),
    "bowl_bend": (0.0013, 0.0008, -0.004, 0.006),
    "bowl_pitch_deg": (0.0, 3.0, -10.0, 10.0),
    "neck_station": (0.105, 0.008, 0.090, 0.130),
    "neck_width": (0.016, 0.002, 0.011, 0.022),
    "handle_station": (0.172, 0.010, 0.140, 0.200),
    "handle_d_start": (0.0188, 0.0010, 0.015, 0.024),
    "handle_d_max": (0.0213, 0.0010, 0.017, 0.026),
    "handle_d_end": (0.0188, 0.0010, 0.015, 0.024),
}
# Marker centres (construction frame, metres) are fitted as free 3-vectors with the WLS solution of params.json as the
# prior mean (sd from its covariance, floored at 1 mm); they are written back as the m_* note-20 entries (see export).


# ----------------------------------------------------------------------------------------------------------------------
def load_observations(obs_dir):
    """Load every obs_*.npz in obs_dir. Returns a list of dicts (numpy). Expected keys: see module docstring."""
    obs = []
    for fn in sorted(os.listdir(obs_dir)):
        if fn.startswith("obs_") and fn.endswith(".npz"):
            z = np.load(os.path.join(obs_dir, fn), allow_pickle=True)
            o = {k: z[k] for k in z.files}
            o["file"] = fn
            for k in ("K", "mask", "depth", "plane", "markers"):
                if k not in o:
                    raise KeyError(f"{fn}: missing {k}")
            obs.append(o)
    if not obs:
        raise FileNotFoundError(f"no obs_*.npz in {obs_dir}")
    return obs


def kabsch(A, B):
    """Rigid R, t minimising |R A + t - B| (rows = points)."""
    ca, cb = A.mean(0), B.mean(0)
    H = (A - ca).T @ (B - cb)
    U, S, Vt = np.linalg.svd(H)
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    return R, cb - R @ ca


class TorchTemplate:
    """Differentiable body (fixed topology) + marker spheres. Body vertices come from spoon_template.station_profile /
    section_points evaluated with xp=torch; faces are taken once from spoon_template.body_mesh at the prior mean (the
    shorter-diagonal choice is frozen). Markers are separate spheres here (no union needed for fitting); the final
    watertight union is rebuilt by spoon_template.py from the exported parameters."""

    def __init__(self, torch, device, base_params, marker_prior):
        self.torch, self.device = torch, device
        self.base = st.resolve_params(base_params)
        self.base["end_cap_length"] = 0.5 * self.base["handle_d_end"]   # TODO: tie end cap to the fitted handle_d_end
        M, _ = st.resolve_length_and_markers(dict(self.base))
        V0, F0, info = st.body_mesh(dict(self.base, total_length=FIT_PARAMS["total_length"][0]))
        self.F = torch.as_tensor(F0, device=device)
        lay = st.loft_layout(st.RES)
        self.lay = {k: torch.as_tensor(v, device=device) for k, v in lay.items()}
        self.names = list(FIT_PARAMS)
        lo = np.array([FIT_PARAMS[k][2] for k in self.names]); hi = np.array([FIT_PARAMS[k][3] for k in self.names])
        mu = np.array([FIT_PARAMS[k][0] for k in self.names])
        self.lo, self.hi = torch.tensor(lo, device=device), torch.tensor(hi, device=device)
        u0 = np.log((mu - lo) / (hi - mu))                         # logit of the prior mean inside [lo, hi]
        self.u = torch.tensor(u0, device=device, requires_grad=True)
        self.markers = torch.tensor(marker_prior, device=device, requires_grad=True)   # (3,3) construction frame
        # TODO: fixed area-weighted barycentric samples per face for chamfer terms (re-weight by current areas)

    def params(self):
        th = self.lo + (self.hi - self.lo) * self.torch.sigmoid(self.u)
        p = dict(self.base)
        p.update({k: th[i] for i, k in enumerate(self.names)})
        p["end_cap_length"] = 0.5 * p["handle_d_end"]
        return p

    def body_vertices(self):
        """(N,3) torch vertices in the construction frame, same order as spoon_template.body_mesh (grid, tip, end)."""
        torch = self.torch
        p = self.params()
        prof = st.station_profile(p, self.lay, st.RES, torch)
        G = st.section_points(prof, self.lay, torch)                 # (ns, nphi, 3)
        # TODO: tip pole exactly as body_mesh (rim height + pitch/bend shear at s = 0); end pole at (0, 0, L)
        tip = torch.stack([p["rim_height"] * torch.ones((), device=self.device), torch.zeros((), device=self.device),
                           torch.zeros((), device=self.device)])
        end = torch.stack([torch.zeros((), device=self.device), torch.zeros((), device=self.device), p["total_length"]])
        return torch.cat([G.reshape(-1, 3), tip[None], end[None]], 0)

    def prior_loss(self):
        p = self.params()
        return sum(((p[k] - FIT_PARAMS[k][0]) / FIT_PARAMS[k][1]) ** 2 for k in self.names)


def losses(tpl, poses, obs_t, w):
    """Total loss and its terms. poses: list of (R (3,3), t (3,)) torch tensors per rest segment.
    TODO: implement L_depth, L_model, L_sil, L_mark, L_contact as described in the module docstring."""
    raise NotImplementedError("fit_spoon.py is a skeleton: implement the loss terms on Colab (see module docstring)")


def export_params(tpl, path):
    """Write a spoon_template.py --params JSON: fitted body values + marker centres converted back to the note-20
    style entries (stations, lateral and 'up' offsets relative to the handle axis) with small sds so the template's WLS
    reproduces them, plus marker_layout='note20' and total_length fixed (not 'auto')."""
    p = tpl.params()
    out = {k: float(p[k]) for k in tpl.names}
    M = tpl.markers.detach().cpu().numpy() * 1e3   # mm, construction frame: x = up (concave), y toward M2, z station
    out.update({
        "marker_layout": "note20",
        "m_station1": [float(M[0, 2]), 0.1], "m_dz12": [float(M[1, 2] - M[0, 2]), 0.1], "m_station3": [float(M[2, 2]), 0.1],
        "m_lat1": [float(-M[0, 1]), 0.1], "m_up1": [float(M[0, 0]), 0.1],
        "m_lat2": [float(M[1, 1]), 0.1], "m_up2": [float(M[1, 0]), 0.1],
        "m_lat3": [float(M[2, 1]), 0.1], "m_up3": [float(M[2, 0]), 0.1],
        "m_tri": [[float(np.linalg.norm(M[a] - M[b])), 0.1] for a, b in ((0, 1), (1, 2), (0, 2))],
    })
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    return out


def frame_posterior(param_samples):
    """CPU: rebuild each sampled template and collect the R1 skews / labels (the frame decision input)."""
    rows = []
    for ps in param_samples:
        b = st.build_spoon(st.resolve_params(ps))
        fr = st.frame_report(b["V"], b["F"], b["markers"])
        rows.append(dict(skew_x=fr["skew_toward_concave_x"], skew_y=fr["skew_toward_M2_y"], skew_z=fr["skew_toward_handle_z"],
                         label_mid=fr["mid"]["label"], label_x=fr["x"]["label"],
                         P_B_noisy=fr["noisy_mid_axis"].get("P_B_noisy_posterior")))
    sy = np.array([r["skew_y"] for r in rows])
    return dict(n=len(rows), P_skew_y_toward_M2=float((sy > 0).mean()), skew_y_mean=float(sy.mean()), skew_y_sd=float(sy.std()),
                frac_B_mid=float(np.mean([r["label_mid"] == "B" for r in rows])), rows=rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--obs", required=True, help="directory with obs_*.npz (see docstring)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--iters", type=int, default=3000)
    ap.add_argument("--bootstrap", type=int, default=0)
    ap.add_argument("--params-json", default=os.path.join(HERE, "params.json"), help="template params.json (priors)")
    args = ap.parse_args()
    import torch  # noqa: F401  (Colab)

    pj = json.load(open(args.params_json))
    marker_prior = np.array(pj["markers_construction_m"])
    obs = load_observations(args.obs)
    tpl = TorchTemplate(torch, args.device, {}, marker_prior)
    # pose init per rest segment: Kabsch(template markers -> triangulated markers)
    poses = []
    for o in obs:
        R, t = kabsch(marker_prior, np.asarray(o["markers"], float))
        poses.append((torch.tensor(R, device=args.device), torch.tensor(t, device=args.device)))
    # TODO: parameterise pose updates (axis-angle deltas), group observations by rest segment, build obs tensors
    # TODO: staged Adam optimisation calling losses(); log terms; early-stop on LOEO residual
    # TODO: bootstrap / Laplace -> parameter samples -> frame_posterior(); write fit_report.json
    os.makedirs(args.out, exist_ok=True)
    export_params(tpl, os.path.join(args.out, "fitted_params.json"))
    raise SystemExit("skeleton: optimisation loop not implemented (see TODOs)")


if __name__ == "__main__":
    main()
