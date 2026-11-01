"""CPU test of the pack guard for the eval-10 njmax diagnostic (BUILD.md section 4): tools/no_oracle.py (and
tools/pack_swap_rollouts.py through it) must refuse every name and checkpoint of the diagnostic and still accept every pack
input it accepted before. Runs the guard as the pack scripts do (python -I tools/no_oracle.py WORDS, cwd = repo).
  1 accept: every REAL checkpoint found locally (pack checkpoints, e10v's, the ep11 gate's), as words and as one kit JSON;
    their stored sim limits are stock; e10v's names and look-alikes;
  2 the store listing (Oct 29, 134,908 paths): the old rule (git HEAD's BAD) vs the new one -> newly refused: none;
  3 refuse by name: the run id, its store paths, the perc2e10nj* folders, results/ev10_nj, EP:DIR words;
  4 refuse by content under NEUTRAL names (FIX dir): a 1024 stand-in of e10v's real s43 checkpoint (limits only), the
    diagnostic-like checkpoint (perc2e10njs43 paths + limits) and its 512 copy (paths only), a kit JSON naming the
    stand-in, a neutral symlink onto a results/ev10_nj folder, an evaluator episode JSON naming the diagnostic checkpoint;
    the old guard (git HEAD) accepted each of these;
  5 tools/pack_swap_rollouts.py: a legit swap builds byte-identically with the old and the new tool (no --skip-no-oracle);
    a swap whose .json names results/ev10_nj is refused; a renamed swap (neutral .json) whose parquet metadata names
    the diagnostic's reference is refused by the new tool and was not by the old one.
Usage: python -I guard_test.py --repo REPO --scratch S --fix DIR --py PY --packpy PACKPY --kit KIT --out OUT.json
"""
import argparse, glob, hashlib, importlib.util, json, os, re, shutil, struct, subprocess, sys

ap = argparse.ArgumentParser()
for k in ('repo', 'scratch', 'fix', 'py', 'packpy', 'kit', 'out', 'standin'):
    ap.add_argument('--' + k, required=True)
A = ap.parse_args()
R, S = A.repo, A.scratch
GUARD = f'{R}/tools/no_oracle.py'; res = dict(checks=[]); fails = []
shutil.rmtree(A.fix, ignore_errors=True); os.makedirs(A.fix)
old_dir = f'{A.fix}/old_repo'; os.makedirs(f'{old_dir}/tools'); os.makedirs(f'{old_dir}/ops/provenance')
for f in ('tools/no_oracle.py', 'tools/pack_swap_rollouts.py'):
    open(f'{old_dir}/{f}', 'w').write(subprocess.run(['git', '-C', R, 'show', f'68f1421:{f}'],   # the build's base commit
                                                     capture_output=True, text=True, check=True).stdout)
shutil.copy(f'{R}/ops/provenance/denylist.json', f'{old_dir}/ops/provenance/')
OLD_GUARD = f'{old_dir}/tools/no_oracle.py'


def load(p, name):
    spec = importlib.util.spec_from_file_location(name, p); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


NEW, OLD = load(GUARD, 'no_oracle_new'), load(OLD_GUARD, 'no_oracle_old')


def need(ok, what):
    res['checks'].append(dict(ok=bool(ok), what=what)); print(('PASS ' if ok else 'FAIL ') + what, flush=True)
    if not ok:
        fails.append(what)


def guard(*words, g=GUARD):
    p = subprocess.run([sys.executable, '-I', g, *words], capture_output=True, text=True, cwd=R)
    return p.returncode, (p.stdout + p.stderr).strip().replace('\n', ' | ')


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


# ------------------------------------------------------------------ 1 accept
cks = {}
for p in sorted(glob.glob(f'{S}/e1conf/**/*.safetensors', recursive=True) + glob.glob(f'{S}/ev10retrain/review/dl/**/*.safetensors', recursive=True)
                + glob.glob(f'{S}/nj/dl/**/*.safetensors', recursive=True)):
    if os.path.getsize(p) > 1 << 20:
        cks.setdefault(sha(p), p)
pack7 = {v['sha256'] for v in json.load(open(f'{R}/results/submissions/20261030-track3g-candidate/checkpoints.json')).values()}
res['accept_checkpoints'] = dict(n=len(cks), pack7_found=len(pack7 & set(cks)), pack7=len(pack7))
bad = [p for p in cks.values() if guard(p)[0] != 0]
need(len(cks) >= 20 and not bad, f'{len(cks)} distinct real checkpoints (incl. {len(pack7 & set(cks))}/20 of pack 7, e10v s43, gl10A2, the ep11 gate) '
     f'each accepted as a word; refused: {bad[:3]}')
json.dump({str(i): p for i, p in enumerate(cks.values())}, open(f'{A.fix}/all_local_ck.json', 'w'))
rc, out = guard(f'{A.fix}/all_local_ck.json'); need(rc == 0, f'the same as one kit checkpoints JSON: rc {rc}')
nonstock = {p: NEW.ckpt_sim(p) for p in cks.values() if NEW.ckpt_sim(p)}
need(not nonstock, f'every real checkpoint stores the stock limits 512 / 256 (sim and env.sim): non-stock {list(nonstock)[:3]}')
words_ok = ['20261031-e10v-caf38fb', 'runs/20261031-e10v-caf38fb/results/perc2e10vs43_glock_public/ep10/best/policy.safetensors',
            'refs/perc2e10vs43_glockt/ep10', 'results/ev10_v4p/conf/r1/ep10/episode_000010.parquet', 'perc2e10vmck', '10:local:mck:perc2e10vs43',
            'ev10retrain', 'njmax', 'e10v', 'ev10', 'ev10_v4p', 'nj', 'results/glock_public/ep10', 'eval10-njmax-20261101']
bad = [w for w in words_ok if guard(w)[0] != 0]
need(not bad, f'{len(words_ok)} e10v names and look-alikes accepted; refused: {bad}')

# ------------------------------------------------------------------ 2 store listing
lst = [l.strip() for l in open(f'{S}/store_files.txt') if l.strip()]
old_ref = {p for p in lst if OLD.BAD.search(p)}; new_ref = {p for p in lst if NEW.BAD.search(p)}
res['store_listing'] = dict(paths=len(lst), old_refused=len(old_ref), new_refused=len(new_ref), newly_refused=sorted(new_ref - old_ref)[:20],
                            no_longer_refused=sorted(old_ref - new_ref)[:20])
need(new_ref >= old_ref and not (new_ref - old_ref), f'store listing ({len(lst)} paths, 29 Oct): old rule refuses {len(old_ref)}, new {len(new_ref)}; '
     f'newly refused {len(new_ref - old_ref)}, no longer refused {len(old_ref - new_ref)}')

# ------------------------------------------------------------------ 3 refuse by name
words_bad = ['20261101-e10nj-abc1234', 'runs/20261101-e10nj-abc1234/results/ev10_nj/summary.json', 'perc2e10njs43',
             'refs/perc2e10njs43_glockt/ep10', '/content/runs/perc2e10njs43_glock/ep10-s43/policy_60002304.safetensors',
             '/content/results/perc2e10njs43_glock_public/ep10/best/policy.safetensors', '/content/results/ev10_nj/ck512/policy.safetensors',
             'results/ev10_nj/conf1024/r1/ep10/episode_000010.parquet', '10:local:mck:perc2e10njs43', 'ck=/content/results/ev10_nj/ck512/policy.safetensors',
             '20261101-e10nj-abc1234@results/ev10_nj']
r = {w: guard(w) for w in words_bad}
need(all(v[0] != 0 for v in r.values()), f'{len(words_bad)} diagnostic names refused by the new guard: accepted {[w for w, v in r.items() if v[0] == 0]}')
need(all(guard(w, g=OLD_GUARD)[0] == 0 for w in words_bad), 'the old guard (git 68f1421) accepted every one of them (the names are new)')

# ------------------------------------------------------------------ 4 refuse by content, neutral names
def edit_ck(src, dst, paths=None, limits=None):  # test-only header edit (canonical, buffer copied)
    b = open(src, 'rb').read(); n = struct.unpack('<Q', b[:8])[0]; h = json.loads(b[8:8 + n]); c = json.loads(h['__metadata__']['user.resolved_config_json'])
    if paths:
        c['output_dir'] = '/content/runs/perc2e10njs43_glock/ep10-s43'
        c['task']['parquet'] = c['reference']['parquet'] = "/content/refs/perc2e10njs43_glockt/ep10/processed/sequence_id=t3_ep010/robot_name=sharpa_wave"
    if limits:
        for blk in (c['sim'], c['env']['sim']):
            blk['njmax'], blk['nconmax'] = limits
    h['__metadata__']['user.resolved_config_json'] = json.dumps(c, sort_keys=True, separators=(',', ':'))
    hb = json.dumps(h, separators=(',', ':')).encode(); hb += b' ' * (-len(hb) % 8)
    os.makedirs(os.path.dirname(dst), exist_ok=True); open(dst, 'wb').write(struct.pack('<Q', len(hb)) + hb + b[8 + n:])


e10v = [p for p in cks.values() if sha(p) == 'bcc51063339de4f36b46c343f53e5b5e52791dd24c31b4ee98de9b8d721882e8']
need(bool(e10v), 'e10v seed 43\'s real chosen checkpoint (sha256 bcc51063…) is present locally')
N = f'{A.fix}/neutral'
cases = {}
edit_ck(e10v[0], f'{N}/a/policy.safetensors', limits=(1024, 512)); cases['1024 stand-in of e10v s43 (limits only), neutral name'] = f'{N}/a/policy.safetensors'
edit_ck(e10v[0], f'{N}/b/policy.safetensors', paths=True, limits=(1024, 512)); cases['diagnostic-like checkpoint (perc2e10njs43 paths + 1024), neutral name'] = f'{N}/b/policy.safetensors'
subprocess.run([A.py, '-I', f'{R}/tools/e10nj.py', 'cksim', '--src', f'{N}/b/policy.safetensors', '--dst', f'{N}/c/policy.safetensors',
                '--from', '1024', '512', '--to', '512', '256'], check=True, capture_output=True)
cases['its 512 copy (tools/e10nj.py cksim; stock limits, perc2e10njs43 paths), neutral name'] = f'{N}/c/policy.safetensors'
json.dump({'10': f'{N}/a/policy.safetensors'}, open(f'{N}/kit_checkpoints.json', 'w')); cases['kit checkpoints JSON naming the stand-in'] = f'{N}/kit_checkpoints.json'
os.makedirs(f'{A.fix}/box/results/ev10_nj/conf1024/r1/ep10'); open(f'{A.fix}/box/results/ev10_nj/conf1024/r1/ep10/episode_000010.parquet', 'w').write('x')
os.symlink(f'{A.fix}/box/results/ev10_nj/conf1024', f'{N}/draws'); cases['neutral symlink onto results/ev10_nj/conf1024'] = f'{N}/draws'
json.dump(dict(checkpoint='/content/results/perc2e10njs43_glock_public/ep10/best/policy.safetensors', checkpoint_sha256='0' * 64),
          open(f'{N}/episode_000010.json', 'w')); cases['evaluator episode JSON naming the diagnostic checkpoint'] = f'{N}/episode_000010.json'
r = {k: guard(p) for k, p in cases.items()}; ro = {k: guard(p, g=OLD_GUARD) for k, p in cases.items()}
res['content_cases'] = {k: dict(new_rc=r[k][0], new=r[k][1][-260:], old_rc=ro[k][0]) for k in cases}
need(all(v[0] != 0 for v in r.values()), f'{len(cases)} neutral-name cases refused by content: accepted {[k for k, v in r.items() if v[0] == 0]}')
need(all(v[0] == 0 for v in ro.values()), f'the old guard accepted every one of them: refused {[k for k, v in ro.items() if v[0] != 0]}')
rs = guard(A.standin)
need(rs[0] != 0 and 'changed evaluation physics' in rs[1], f'the cksim_test 1024 stand-in of the packed gl10A2 checkpoint is refused by its limits: {rs[1][-200:]}')

# ------------------------------------------------------------------ 5 pack_swap_rollouts
import pyarrow.parquet as pq                                                        # noqa: E402
P9 = f'{S}/pack9ap/pack9ap2'; base = f'{R}/results/submissions/20261031-track3i-candidate/build_9aplus/track3_submission.parquet'
ok14 = f'{S}/pack9b/fixtures2/ok14/episode_000014.parquet'; commit = 'https://github.com/aebatirel/v2d-track3/commit/' + '23ee07584ece67f8317c4469dd22f88fcb405423'


def swap(tool, out, pqf, expect='ab' * 32):
    p = subprocess.run([A.packpy, '-I', tool, '--kit', A.kit, '--results', f'{P9}/results', '--meshes', f'{P9}/meshes', '--base', base,
                        '--python', A.packpy, '--code-commit', commit, '-o', out, '--swap', f'14={pqf}', '--expect-checkpoint', f'14={expect}'],
                       capture_output=True, text=True, cwd=R)
    return p.returncode, (p.stdout + p.stderr).strip()


o_old, o_new = f'{A.fix}/swap_old', f'{A.fix}/swap_new'
rc_o, out_o = swap(f'{old_dir}/tools/pack_swap_rollouts.py', o_old, ok14); rc_n, out_n = swap(f'{R}/tools/pack_swap_rollouts.py', o_new, ok14)
same = rc_o == rc_n == 0 and sha(f'{o_old}/track3_submission.parquet') == sha(f'{o_new}/track3_submission.parquet')
res['swap_legit'] = dict(rc_old=rc_o, rc_new=rc_n, sha_old=sha(f'{o_old}/track3_submission.parquet') if rc_o == 0 else None,
                         sha_new=sha(f'{o_new}/track3_submission.parquet') if rc_n == 0 else None, tail_new=out_n[-400:])
need(same, f'legit ep14 swap with the guard on: old and new tool both status 0, the same parquet (sha256 {str(res["swap_legit"]["sha_new"])[:12]}; '
     f'U1 of 1 Nov read 094d650fa306)')


def fixture(name, json_ck, json_pq, ref_pq):  # ok14 with its .json checkpoint / parquet and its parquet's reference_parquet replaced
    d = f'{A.fix}/{name}'; os.makedirs(d); t = pq.read_table(ok14); md = dict(t.schema.metadata)
    md[b'flash_chord.reference_parquet'] = ref_pq.encode(); pq.write_table(t.replace_schema_metadata(md), f'{d}/episode_000014.parquet')
    j = json.load(open(ok14[:-8] + '.json')); j['checkpoint'] = json_ck; j['parquet'] = json_pq or j['parquet']
    json.dump(j, open(f'{d}/episode_000014.json', 'w'), indent=1)
    return f'{d}/episode_000014.parquet'


NJREF = '/content/refs/perc2e10njs43_glockt/ep10/processed/sequence_id=t3_ep010/robot_name=sharpa_wave/ref_gl_ilc.parquet'
f1 = fixture('swap_v1', '/content/results/ev10_nj/ck512/policy.safetensors', NJREF, NJREF)
rc, out = swap(f'{R}/tools/pack_swap_rollouts.py', f'{A.fix}/swap_v1_out', f1)
need(rc != 0 and 'no_oracle.py refused' in out and not os.path.exists(f'{A.fix}/swap_v1_out'), f'swap whose .json names results/ev10_nj: refused, nothing built ({out[-160:]})')
f2 = fixture('swap_v2', '/workspace/pick/neutral/policy.safetensors', None, NJREF)
rc, out = swap(f'{R}/tools/pack_swap_rollouts.py', f'{A.fix}/swap_v2_out', f2)
need(rc != 0 and 'no_oracle.py refused' in out and not os.path.exists(f'{A.fix}/swap_v2_out'),
     f'renamed swap (neutral .json) whose parquet metadata names refs/perc2e10njs43_glockt: refused by the new tool ({out[-160:]})')
shutil.copy(GUARD, f'{old_dir}/tools/no_oracle.py')                                 # the old tool with the NEW guard beside it
rc, out = swap(f'{old_dir}/tools/pack_swap_rollouts.py', f'{A.fix}/swap_v2_oldtool', f2)
need(rc == 0, f'... while the old tool, even with the new guard, built it (rc {rc}): the metadata words are the cheap addition')
res['ok'] = not fails; res['failures'] = fails
json.dump(res, open(A.out, 'w'), indent=1)
print('RESULT: ' + ('ALL CHECKS PASS' if not fails else f'{len(fails)} FAILED: {fails}'))
sys.exit(0 if not fails else 1)
