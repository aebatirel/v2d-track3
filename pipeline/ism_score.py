"""Instance-segmentation scoring after SAM-6D's ISM (Lin et al., CVPR 2024; github.com/JiehongLin/SAM-6D,
Instance_Segmentation_Model/model/detector.py + model/loss.py), re-implemented for perc2 (2026-11-02, [H], off by
default; DET_ISM in perc2.py). GT-free: proposals, our depth, our mesh templates.

For each (object, proposal):
  semantic   = mean of the top-5 cosine similarities of the proposal's DINOv2 CLS token with the object's templates
               (ISM 'avg_5'; perc2 already computes exactly this as `sim`);
  best view  = the template with the highest CLS similarity;
  appearance = masked-patch score with that template (ISM MaskedPatch_MatrixSimilarity.compute_straight): for each
               valid proposal patch, the best cosine over the template's valid patches, averaged over proposal patches;
  geometric  = IoU of the proposal's box with the box of the object's points rotated by the best view's rotation and
               moved to the mean 3-D point of the proposal's depth (ISM project_template_to_image + compute_iou);
  visible    = share of the template's valid patches whose best match in the proposal exceeds 0.5 (ISM
               compute_visible_ratio);
  final      = (semantic + appearance + geometric * visible) / (2 + visible)   (ISM run_inference_custom.py).
Differences from ISM: our proposals (SAM2 automatic + re-proposals, not SAM ViT-H), our 42 icosphere template views
rendered grey with nvdiffrast (not BlenderProc colour renders), object points centred on the mesh's box centre.
"""
import numpy as np, torch, torch.nn.functional as F


def patch_valid(masks224):
    """masks224: [B, 224, 224] float {0,1} -> [B, 256] bool (14x14 average pool > 0.5, ISM validpatch_thresh)."""
    return (F.avg_pool2d(masks224[:, None], 14, 14).flatten(1) > 0.5)


def dino_feats(dino, x):
    """x: [B,3,224,224] normalised. Returns CLS [B,C] (normalised) and patch tokens [B,256,C]."""
    f = dino.forward_features(x)
    return F.normalize(f['x_norm_clstoken'], dim=-1), f['x_norm_patchtokens']


def masked_patches(patch, valid):
    return F.normalize(patch * valid[..., None].float(), dim=-1)


def appearance(qp, rp):
    """qp: [N, P, C] query masked patches; rp: [N, P, C] reference masked patches (one best template per query)."""
    sim = torch.bmm(qp, rp.transpose(1, 2))
    best = sim.max(-1).values
    factor = torch.count_nonzero(qp.sum(-1), dim=-1) + 1e-6
    return (best.sum(-1) / factor).clamp(0, 1)


def visible_ratio(qp, rp, thr=0.5):
    sim = torch.bmm(qp, rp.transpose(1, 2)).max(1)[0]
    valid = torch.count_nonzero(sim, dim=1) + 1e-6
    return torch.count_nonzero(sim * (sim > thr), dim=1) / valid


def geometric(R_best, pts, masks, depth, K):
    """R_best: [N,3,3] best-view object->camera rotations; pts: [M,3] object points (centred); masks: list of N bool
    HxW; depth: HxW metres; K: 3x3. Returns IoU [N] (0 where the mask has no depth)."""
    out = np.zeros(len(masks))
    H, W = depth.shape
    for i, m in enumerate(masks):
        v, u = np.nonzero(m & (depth > 0))
        if len(v) < 10:
            continue
        z = depth[v, u]; t = np.array([((u - K[0, 2]) * z / K[0, 0]).mean(), ((v - K[1, 2]) * z / K[1, 1]).mean(), z.mean()])
        X = pts @ R_best[i].T + t
        uv = (X @ K.T); uv = uv[:, :2] / uv[:, 2:3]
        uv[:, 0] = uv[:, 0].clip(0, W - 1); uv[:, 1] = uv[:, 1].clip(0, H - 1)
        a = np.r_[uv.min(0), uv.max(0)]
        vv, uu = np.nonzero(m); b = np.array([uu.min(), vv.min(), uu.max(), vv.max()], float)
        iw = max(0.0, min(a[2], b[2]) - max(a[0], b[0])); ih = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
        inter = iw * ih; uni = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
        out[i] = inter / uni if uni > 0 else 0.0
    return out


def final_scores(q_cls, q_patch, q_valid, t_cls, t_patch, t_valid, t_rot, pts, masks, depth, K):
    """One object vs N proposals. q_*: proposals ([N,C], [N,P,C], [N,P]); t_*: templates ([T,C], [T,P,C], [T,P],
    [T,3,3]). Returns dict of numpy arrays (semantic, appearance, geometric, visible, final, best)."""
    s = q_cls @ t_cls.T                                              # [N, T]
    sem = s.topk(min(5, s.shape[1]), dim=1).values.mean(1)
    best = s.argmax(1)
    qp = masked_patches(q_patch, q_valid); rp = masked_patches(t_patch[best], t_valid[best])
    app = appearance(qp, rp); vis = visible_ratio(qp, rp)
    geo = torch.as_tensor(geometric(t_rot[best.cpu().numpy()], pts, masks, depth, K), device=sem.device, dtype=sem.dtype)
    fin = (sem + app + geo * vis) / (2 + vis)
    return {k: v.detach().float().cpu().numpy() for k, v in
            dict(semantic=sem, appearance=app, geometric=geo, visible=vis, final=fin, best=best).items()}
