# Europe PMC search -> citation + abstract (data only)
import sys, json, urllib.request, urllib.parse, os, ssl
q = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + urllib.parse.urlencode(dict(query=q, resultType='core', format='json', pageSize=n))
ctx = ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt')
proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
opener = urllib.request.build_opener(urllib.request.ProxyHandler({'https': proxy}), urllib.request.HTTPSHandler(context=ctx))
import time
d = None
for k in range(4):
    try:
        d = json.load(opener.open(url, timeout=60)); break
    except Exception as e:
        print('ERR', k, e, file=sys.stderr); time.sleep(3 + 4*k)
if d is None: sys.exit(1)
for r in d.get('resultList', {}).get('result', []):
    print('###', r.get('authorString','')[:120], '|', r.get('title'), '|', r.get('journalTitle') or r.get('journalInfo',{}).get('journal',{}).get('title'), r.get('pubYear'),
          '| pmid', r.get('pmid'), '| pmcid', r.get('pmcid'), '| doi', r.get('doi'))
    print(r.get('abstractText', '(no abstract)'))
    print()
