#!/usr/bin/env python3
"""Usage (from the kit root): KAGGLE_API_TOKEN=placeholder python tools/kaggle_upload.py submit/v2d_submit.py FILE --track track_3 [--only METRIC ...] -m MSG --wait
Run the kit's v2d_submit.py with the Kaggle token injected by the session's network proxy (Authorization header).
The kaggle client pre-checks its token by sending it in a request body, which the proxy cannot fill, so that one
client-side check is replaced by a placeholder username; Kaggle still authenticates every call with the real token."""
import runpy, sys
from kaggle.api import kaggle_api_extended as m
m.KaggleApi._introspect_token = lambda self, token: 'proxy-auth'
script = sys.argv[1]; sys.argv = [script] + sys.argv[2:]
sys.path.insert(0, '.')
runpy.run_path(script, run_name='__main__')
