# usage: pm.py OUTDIR key "query" [key "query" ...]  -> esearch top 3, esummary, efetch abstract of top hit
import sys, json, time, urllib.request, urllib.parse, os
out = sys.argv[1]; args = sys.argv[2:]
E = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
def get(u):
    for i in range(4):
        try:
            with urllib.request.urlopen(u, timeout=60) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:
            time.sleep(2 + 2*i); err = e
    return 'ERR %s' % err
for k, q in zip(args[0::2], args[1::2]):
    js = json.loads(get(E + 'esearch.fcgi?db=pubmed&retmode=json&retmax=3&term=' + urllib.parse.quote(q)))
    ids = js['esearchresult']['idlist']; time.sleep(0.4)
    if not ids:
        print(k, 'NO HITS'); continue
    sm = json.loads(get(E + 'esummary.fcgi?db=pubmed&retmode=json&id=' + ','.join(ids))); time.sleep(0.4)
    lines = []
    for i in ids:
        d = sm['result'][i]
        pmc = [a['value'] for a in d.get('articleids', []) if a['idtype'] == 'pmc']
        doi = [a['value'] for a in d.get('articleids', []) if a['idtype'] == 'doi']
        lines.append('%s | %s | %s | %s %s:%s | doi %s | %s' % (i, d.get('sortfirstauthor'), d.get('title'), d.get('source'), d.get('pubdate'), d.get('pages'), doi, pmc))
    ab = get(E + 'efetch.fcgi?db=pubmed&rettype=abstract&retmode=text&id=' + ids[0]); time.sleep(0.4)
    open(os.path.join(out, 'pm_%s.txt' % k), 'w').write('\n'.join(lines) + '\n\n' + ab)
    print(k, '::', lines[0][:200])
