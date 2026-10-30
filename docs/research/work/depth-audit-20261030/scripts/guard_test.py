"""Guard regression test for refine.assert_inference_input (30 Oct 2026, after verifier 1's defect 3). Path checks only:
no file is opened. (a) every inference input recorded by the public audits, refine/in, the mesh library and the S2
tracks must be accepted; (b) every ground-truth output of this study and of its verifiers (label files under .../gt/,
calib_gt/) must be refused. Usage: python -I guard_test.py REPO SCRATCHPAD AUDIT_DIR"""
import glob, json, os, sys
REPO, S, D = sys.argv[1:4]
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import refine
W = f'{S}/daudit'
def ok(p):
    try:
        refine.assert_inference_input(p); return True
    except AssertionError:
        return False
# (a) every inference input recorded by the 20 public audits, plus every file in refine/in and the mesh library
acc = []
for j in sorted(glob.glob(f'{D}/audit/public/ep*/audit.json')):
    d = json.load(open(j))['inputs']
    for k, v in d.items():
        if k == 'meshes':
            acc += [m['path'] for m in v.values()]
        elif isinstance(v, dict) and 'path' in v:
            acc.append(v['path'])
acc += sorted(glob.glob(f'{S}/refine/in/ep*/*'))
acc += sorted(glob.glob(f'{REPO}/meshes/library_v3/*'))
acc += sorted(glob.glob(f'{S}/daudit/work/s2/ep*/*'))
bad_acc = [p for p in acc if not ok(p)]
# refine/in may legitimately hold files the guard refuses (result.json etc. are written by perc2); report them
print('inference paths checked', len(acc), 'refused', len(bad_acc))
for p in bad_acc: print('  REFUSED', p)
# (b) ground-truth outputs of this study and of the verifiers: all must be refused
gt = sorted(glob.glob(f'{W}/work/gt/**/*', recursive=True)) + sorted(glob.glob(f'{D}/calib_gt/**/*', recursive=True))
gt += sorted(glob.glob(f'{W}/vgeo_out/glob*/*')) + sorted(glob.glob(f'{W}/vstat/calib_rerun/*'))
gt = [p for p in gt if os.path.isfile(p)]
leak = [p for p in gt if ok(p)]
print('ground-truth paths checked', len(gt), 'accepted', len(leak))
for p in leak: print('  ACCEPTED', p)
sys.exit(1 if (bad_acc or leak) else 0)
