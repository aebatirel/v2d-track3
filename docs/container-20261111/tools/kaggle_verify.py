"""Run the kit's verify_container.py with --kaggle, with the Kaggle token injected by the session's network proxy.
As tools/kaggle_upload.py in our repo: the kaggle client's one client-side token pre-check (token in a request body,
which the proxy cannot fill) is stubbed; Kaggle authenticates every call with the real token."""
import runpy, sys
from kaggle.api import kaggle_api_extended as m
m.KaggleApi._introspect_token = lambda self, token: 'proxy-auth'
script = sys.argv[1]; sys.argv = [script] + sys.argv[2:]
runpy.run_path(script, run_name='__main__')
