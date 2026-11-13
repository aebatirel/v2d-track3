"""T3 inputs (fixed, GT-free): the probe's GT-free pick per object (results/gen-probe/selection.json) -> placed mesh path
(the probe's own Sim(3)-placed file, i.e. the exact mesh it scored) + that episode's observed points (obs_all npz)."""
import json, os
SCR = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
REPO = '/home/user/v2d-track3'
GEN = f'{SCR}/gen/mesh-20261029-gen-f3fbeb0/results/gen'
SEL = f'{REPO}/docs/research/mesh-2026-10-26/results/gen-probe/selection.json'
MAN = f'{REPO}/docs/research/mesh-2026-10-26/results/gen-probe/score_manifest.tsv'


def picks():
    man = {}
    for line in open(MAN):
        p = line.rstrip('\n').split('\t')
        man[p[0]] = p[2].replace('<scratchpad>', SCR)
    out = []
    for s in json.load(open(SEL))['selection']:
        lab = s['pick']                     # e.g. gen/sam3d/ep41_white_pot_k279_s7
        ep = lab.split('/')[-1].split('_')[0]
        out.append(dict(object=s['object'], pick=lab, model=lab.split('/')[1], episode=ep,
                        placed=man[lab], obs=f'{SCR}/obs_all/{ep}_{s["object"]}.npz'))
    return out


if __name__ == '__main__':
    for p in picks():
        print(json.dumps(p))
