#!/usr/bin/env python3
from pathlib import Path
import argparse,csv,hashlib,sys
p=argparse.ArgumentParser();p.add_argument('--mean',required=True);p.add_argument('--cov',required=True);a=p.parse_args();root=Path(__file__).resolve().parent
manifest=list(csv.DictReader((root/'INPUT_MANIFEST.tsv').open(encoding='utf-8'),delimiter='\t'))
paths={'mean':Path(a.mean),'covariance':Path(a.cov)}
fail=False
for r in manifest:
 q=paths[r['ROLE']]; h=hashlib.sha256(q.read_bytes()).hexdigest(); ok=q.stat().st_size==int(r['BYTES']) and h==r['SHA256']; print(r['ROLE'], 'PASS' if ok else 'FAIL', h); fail|=not ok
raise SystemExit(1 if fail else 0)
