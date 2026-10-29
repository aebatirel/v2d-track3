"""G0 code checks (mesh v5 spec section 3.2 / E10): the inference code never imports the diagnostic mesh module and
reads the ground-truth 'pose' field only in the places allowed to: the scorers, the diagnostics, the oracle mode (refused
under SPLIT=eval by pipeline_ep.sh) and perception's own scoring block after inference."""
import glob, os, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED_FILES = {'diag.py', 'oracle_poses.py'}          # plus score_*.py
SCORING_MARK = '# ---------- scoring'
POSE = re.compile(r"\[\s*['\"]pose['\"]\s*\]|\.get\(\s*['\"]pose['\"]")


def test_pipeline_never_imports_mesh_diag():
    for f in glob.glob(f'{REPO}/pipeline/*.py'):
        assert 'mesh_diag' not in open(f).read(), f


def test_pose_reads_only_where_allowed():
    for f in glob.glob(f'{REPO}/pipeline/*.py'):
        name = os.path.basename(f)
        if name in ALLOWED_FILES or name.startswith('score_'):
            continue
        src = open(f).read()
        head = src.split(SCORING_MARK)[0] if SCORING_MARK in src else src
        assert not POSE.search(head), f'{name} reads a pose field before any scoring block'


def test_oracle_refused_on_eval():
    src = open(f'{REPO}/pipeline/pipeline_ep.sh').read()
    assert 'PERC=oracle needs mocap; not allowed with SPLIT=eval' in src
