"""Synthetic single-object episodes for the B5 score and select tests (no file is read; GT-free by construction).

A known closed mesh sits at the object origin. Each frame has a pinhole camera on a sphere around it (look-at), a
ray-cast depth image (geom.ray_ranges), owned points = the object pixels back-projected with Gaussian range noise
(sigma 1 mm, seeded), and grids voted as scripts/obs_points.py does: every voxel centre is projected into the frame;
FREE vote if the depth at its pixel lies more than 10 mm beyond it, hit vote if within one voxel of it on an object
pixel. Rays that miss the object end on a background at 1 m, so they carve the cube. The result is a gmg Bundle
(meta, obs, poses) with tier SYNTH; contact, rest and table are empty (V2 and V4 do not apply).
"""
from __future__ import annotations

import numpy as np
import trimesh

from gmg import geom
from gmg.bundle import Bundle, state_grid

F_PX, W, H = 200.0, 160, 120          # camera: focal length (px), image size: 2.5 mm pixels at 0.5 m
DIST = 0.5                            # camera distance (m)
BG = 1.0                              # background range for rays that miss the object (m)
VOX, HALF = 0.004, 0.15               # 4 mm grid over a +-0.15 m cube
FREE_MARGIN = 0.010                   # obs_points free margin (10 mm before the sample)
SIGMA = 0.001                         # range noise (m)


def look_at(c, target=(0.0, 0.0, 0.0), up=(0.0, 0.0, 1.0)):
    """cam_T_obj (4x4) of a camera at C (object frame) looking at TARGET: x right, y down, z forward."""
    c = np.asarray(c, np.float64); t = np.asarray(target, np.float64)
    z = t - c; z /= np.linalg.norm(z)
    up = np.asarray(up, np.float64)
    if abs(z @ up) > 0.99:
        up = np.array([0.0, 1.0, 0.0])
    x = np.cross(z, up); x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.stack([x, y, z])
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = -R @ c
    return T


def cam_centre(elev_deg, azim_deg, dist=DIST):
    e, a = np.radians(elev_deg), np.radians(azim_deg)
    return dist * np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def _rays():
    u, v = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
    d = np.stack([(u - W / 2) / F_PX, (v - H / 2) / F_PX, np.ones_like(u)], -1).reshape(-1, 3)
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def render(mesh, T):
    """(range along each pixel's unit ray, object mask, unit rays) in camera coordinates."""
    D = _rays()
    tris = np.asarray(mesh.vertices, np.float64)[np.asarray(mesh.faces, np.int64)]
    tc = tris @ T[:3, :3].T + T[:3, 3]
    r = geom.ray_ranges(tc, D)
    obj = np.isfinite(r)
    return np.where(obj, r, BG / np.maximum(D[:, 2], 1e-6)), obj, D


def episode(mesh, cams, name='obj', seed=0, stride=2, sigma=SIGMA):
    """Bundle of one object observed from CAMS (list of camera centres, object frame), one camera per extraction
    frame 0, stride, 2 stride, ..."""
    rng = np.random.default_rng(seed)
    n = len(cams)
    T_all = int(n * stride)
    lo = np.full(3, -HALF)
    shape = tuple(int(np.ceil(2 * HALF / VOX)) for _ in range(3))
    ax = [lo[k] + (np.arange(shape[k]) + 0.5) * VOX for k in range(3)]
    X = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3)
    hits = np.zeros(len(X), np.int32); free = np.zeros(len(X), np.int32)
    poses = np.repeat(np.eye(4)[None], T_all, axis=0)
    pts, cam, fr = [], [], []
    for i, c in enumerate(cams):
        f = i * stride
        T = look_at(c)
        poses[f] = T
        if i + 1 < n:
            poses[f + 1:f + stride] = T
        rng_, obj, D = render(mesh, T)
        noisy = rng_ + np.where(obj, rng.normal(0.0, sigma, len(rng_)), 0.0)
        Pc = D * noisy[:, None]
        Ti = np.linalg.inv(T)
        P = Pc[obj] @ Ti[:3, :3].T + Ti[:3, 3]
        pts.append(P); cam.append(np.repeat(Ti[:3, 3][None], len(P), 0)); fr.append(np.full(len(P), f))
        # obs_points voting: project the voxel centres, compare with the z-depth at their pixel
        zmap = (Pc[:, 2]).reshape(H, W)
        omask = obj.reshape(H, W)
        Xc = X @ T[:3, :3].T + T[:3, 3]
        z = Xc[:, 2]
        ok = z > 0.05
        pu = np.full(len(X), -1); pv = np.full(len(X), -1)
        pu[ok] = np.floor(F_PX * Xc[ok, 0] / z[ok] + W / 2).astype(int)
        pv[ok] = np.floor(F_PX * Xc[ok, 1] / z[ok] + H / 2).astype(int)
        ok &= (pu >= 0) & (pu < W) & (pv >= 0) & (pv < H)
        idx = np.nonzero(ok)[0]
        dv = zmap[pv[idx], pu[idx]]
        sdf = dv - z[idx]
        free[idx[sdf > FREE_MARGIN]] += 1
        hits[idx[(np.abs(sdf) < VOX) & omask[pv[idx], pu[idx]]]] += 1
    pts = np.concatenate(pts).astype(np.float32)
    obs = dict(pts=pts, cam=np.concatenate(cam).astype(np.float32), frame=np.concatenate(fr).astype(np.int32),
               own=np.zeros(len(pts), np.uint8), lo=lo, hi=lo + np.asarray(shape) * VOX, vox=VOX,
               hits=np.clip(hits, 0, 65535).reshape(shape).astype(np.uint16),
               free=np.clip(free, 0, 65535).reshape(shape).astype(np.uint16))
    obs['state'] = state_grid(obs['hits'], obs['free'])
    obs['shared'] = np.zeros(shape, np.uint16); obs['pocc'] = np.zeros(shape, np.uint16); obs['args'] = '{}'
    frames_with = set(np.unique(obs['frame']).tolist())
    meta = dict(schema='gmg-episode/1', split='synthetic', ep=-1, objects=[name], tier='SYNTH', T=T_all,
                stride=stride, vox=VOX, sigma_mm={name: sigma * 1e3}, contact={}, rest={}, table=None,
                good={name: [f in frames_with for f in range(T_all)]}, flags=['synthetic'])
    poses_d = {'world_T_cam': np.repeat(np.eye(4)[None], T_all, axis=0), f'cam_T_{name}': poses}
    return Bundle(meta, {name: obs}, poses_d)


def ring(elev, n, azim0=0.0):
    return [cam_centre(elev, azim0 + 360.0 * i / n) for i in range(n)]


# ------------------------------------------------------------------------------------------------ test objects
def cylinder(r=0.04, h=0.08):
    return trimesh.creation.cylinder(radius=r, height=h, sections=64)


def without_base(m, axis=2):
    """The same mesh without its bottom cap (faces whose normal points down along AXIS): open, not watertight."""
    keep = np.asarray(m.face_normals)[:, axis] > -0.9
    return trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces)[keep], process=False)


def disc(r=0.06, t=0.01):
    return trimesh.creation.cylinder(radius=r, height=t, sections=64).apply_translation([0, 0, t / 2])


def phantom_under(top, r=0.055, h=0.08):
    """TOP united (concatenated) with a phantom cylinder body hanging below z = 0 (the SAM 3D 'pot with lid' case)."""
    body = trimesh.creation.cylinder(radius=r, height=h, sections=64).apply_translation([0, 0, -h / 2])
    return trimesh.util.concatenate([top, body])
