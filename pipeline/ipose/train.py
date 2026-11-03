"""Train the pot network.
  R:   python train.py OUT --synth 'DIR/synth_*.npz' --epochs 40
  R+M: python train.py OUT --synth 'DIR/synth_*.npz' --real 'DIR/real_*.npz' --init R/ckpt.pt --epochs 10
With --real, each epoch draws len(real) real and len(real) synth samples (1 : 1). Saves OUT/ckpt.pt and OUT/train_log.json.
"""
import argparse, glob, json, os, sys, time, math
import numpy as np, torch, torch.nn.functional as F, trimesh
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import PotNet

p = argparse.ArgumentParser()
p.add_argument('out'); p.add_argument('--synth', required=True); p.add_argument('--real', default=None)
p.add_argument('--init', default=None); p.add_argument('--epochs', type=int, default=40)
p.add_argument('--bs', type=int, default=32); p.add_argument('--lr', type=float, default=3e-4)
p.add_argument('--mesh', default=f'{os.path.dirname(os.path.abspath(__file__))}/../../meshes/ipose/white_pot.glb')
p.add_argument('--workers', type=int, default=6); p.add_argument('--max_iters', type=int, default=0)
a = p.parse_args()
os.makedirs(a.out, exist_ok=True)
dev = 'cuda' if torch.cuda.is_available() else 'cpu'
torch.manual_seed(0); np.random.seed(0)
v = np.asarray(trimesh.load(a.mesh, force='mesh').vertices)
CEN, HALF = (v.min(0) + v.max(0)) / 2, (v.max(0) - v.min(0)) / 2 * 1.05


def load(pattern):
    fs = sorted(glob.glob(pattern)); assert fs, pattern
    D = [np.load(f) for f in fs]
    return {k: np.concatenate([d[k] for d in D]) for k in ('img', 'xyz', 'vis', 'full')}


class DS(torch.utils.data.Dataset):
    def __init__(self, d, aug=True): self.d, self.aug = d, aug
    def __len__(self): return len(self.d['img'])
    def __getitem__(self, i):
        g = self.d['img'][i].astype(np.float32) / 255
        if self.aug:
            r = np.random
            g = np.clip(g * r.uniform(0.7, 1.3) + r.uniform(-0.15, 0.15), 0, 1) ** r.uniform(0.8, 1.25)
            g = np.clip(g + r.normal(0, r.uniform(0, 0.02), g.shape), 0, 1)
        xyz = (self.d['xyz'][i].astype(np.float32) - CEN) / HALF
        return (torch.from_numpy(g[None].astype(np.float32)), torch.from_numpy(xyz.transpose(2, 0, 1).copy()),
                torch.from_numpy(self.d['vis'][i].astype(np.float32)), torch.from_numpy(self.d['full'][i].astype(np.float32)))


S = DS(load(a.synth))
if a.real:
    Rl = DS(load(a.real))
    nper = len(Rl)
    mk = lambda: torch.utils.data.ConcatDataset([Rl, torch.utils.data.Subset(S, np.random.choice(len(S), nper, replace=len(S) < nper))])
else:
    mk = lambda: S
net = PotNet(pretrained=a.init is None).to(dev)
if a.init:
    net.load_state_dict(torch.load(a.init, map_location=dev, weights_only=False)['model'])
n_ep = len(mk())
iters = a.epochs * math.ceil(n_ep / a.bs)
if a.max_iters: iters = min(iters, a.max_iters)
opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=1e-4)
sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.lr, total_steps=iters, pct_start=0.03, anneal_strategy='cos')
scaler = torch.amp.GradScaler(enabled=dev == 'cuda')
print(f'samples/epoch {n_ep} iters {iters} device {dev}', flush=True)
it, t0, logs = 0, time.time(), []
while it < iters:
    dl = torch.utils.data.DataLoader(mk(), batch_size=a.bs, shuffle=True, num_workers=a.workers, drop_last=True,
                                     pin_memory=dev == 'cuda', persistent_workers=False)
    run = {}
    for g, xyz, vis, full in dl:
        g, xyz, vis, full = g.to(dev), xyz.to(dev), vis.to(dev), full.to(dev)
        with torch.autocast(dev, dtype=torch.bfloat16 if dev == 'cpu' else torch.float16, enabled=True):
            lv, lf, px = net(g)
        px = px.float()
        lx = ((px - xyz).abs().sum(1) * vis).sum() / vis.sum().clamp(min=1)
        lm = F.binary_cross_entropy_with_logits(lv.float(), vis) + 0.5 * F.binary_cross_entropy_with_logits(lf.float(), full)
        loss = lx + lm
        opt.zero_grad(set_to_none=True)
        scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sch.step()
        for k, x in (('loss', loss), ('xyz', lx), ('mask', lm)):
            run[k] = run.get(k, 0) + float(x.detach())
        run['n'] = run.get('n', 0) + 1
        it += 1
        if it % 100 == 0 or it == iters:
            row = {k: round(run[k] / run['n'], 4) for k in ('loss', 'xyz', 'mask')}
            row.update(it=it, secs=round(time.time() - t0), lr=sch.get_last_lr()[0]); logs.append(row); run = {}
            print(json.dumps(row), flush=True)
        if it % 2000 == 0 or it == iters:
            torch.save(dict(model=net.state_dict(), cen=CEN, half=HALF, it=it, args=vars(a)), f'{a.out}/ckpt.pt')
            json.dump(logs, open(f'{a.out}/train_log.json', 'w'))
        if it >= iters: break
print('done', it, round(time.time() - t0), flush=True)
