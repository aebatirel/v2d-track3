#!/bin/bash
# usage: pm.sh "query" [n]  -> top-n PubMed abstracts (text)
sleep 1; q=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote_plus(sys.argv[1]))" "$1"); n=${2:-1}
ids=$(curl -sS --max-time 30 "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=$q&retmode=json&retmax=$n" | python3 -c "import json,sys;print(','.join(json.load(sys.stdin)['esearchresult']['idlist']))")
echo "=== QUERY: $1 -> $ids"
[ -n "$ids" ] && curl -sS --max-time 30 "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=$ids&rettype=abstract&retmode=text"
sleep 1.5
