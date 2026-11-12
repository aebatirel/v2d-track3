import os, sys, time
from huggingface_hub import HfApi
api = HfApi()
repo = 'aebatirel/v2d-track3-container'
U = os.path.dirname(os.path.abspath(__file__))
T = '/tmp/claude-0/-home-user-v2d-track3/40ae8bef-a6ac-5623-abee-9e3e721c7845/scratchpad/container/Imitation.Tech-v2d-submission.tar.zst'
api.create_repo(repo, repo_type='model', private=False, exist_ok=True)
print('repo ready', flush=True)
api.upload_file(path_or_fileobj=f'{U}/README.md', path_in_repo='README.md', repo_id=repo,
                commit_message='Add README: how to load, verify and reproduce')
api.upload_file(path_or_fileobj=f'{U}/Imitation.Tech-v2d-submission.tar.zst.sha256',
                path_in_repo='Imitation.Tech-v2d-submission.tar.zst.sha256', repo_id=repo,
                commit_message='Add checksum file')
print('small files done', flush=True)
t0 = time.time()
api.upload_file(path_or_fileobj=T, path_in_repo='Imitation.Tech-v2d-submission.tar.zst', repo_id=repo,
                commit_message='Add the verification container image archive (pack 13h)')
print(f'tarball uploaded in {time.time()-t0:.0f}s', flush=True)
