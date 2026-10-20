# Run only CoACD's manifold check path cheaply: preprocess_mode auto with a huge threshold (1 hull) and report log lines.
import sys, subprocess
for p in sys.argv[1:]:
    r=subprocess.run([sys.executable,'-c',f'''
import sys,numpy as np
sys.path.insert(0,"/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/pylib11"); import coacd
coacd.set_log_level("info"); d=np.load("{p}")
coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(d["v"],dtype=np.float64),np.ascontiguousarray(d["f"],dtype=np.int64)),threshold=1.0,max_convex_hull=1,preprocess_mode="auto",merge=False,mcts_iterations=1,mcts_nodes=1,resolution=100)
'''],capture_output=True,text=True)
    s=r.stdout+r.stderr
    if not any("Manifold" in x for x in s.splitlines()): print(s[-800:])
    flags=[x.split('] ')[-1].strip() for x in s.splitlines() if any(k in x for k in ['Manifoldness','intersection','Unclosed','orientation'])]
    print(p,flags,flush=True)
