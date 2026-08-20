#!/usr/bin/env python3
from pathlib import Path
import csv, hashlib, sys

ROOT=Path(__file__).resolve().parents[1]
CROSS=ROOT/"publication_evidence/evidence/CLAIM_EVIDENCE_CROSSWALK.tsv"

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

rows=list(csv.DictReader(CROSS.open(encoding="utf-8"),delimiter="\t"))
fail=[]
for r in rows:
    p=ROOT/"publication_evidence"/r["evidence_path"]
    if not p.exists():
        fail.append((r["claim_id"],"MISSING",str(p)))
        continue
    got=sha(p)
    if got!=r["artifact_sha256"]:
        fail.append((r["claim_id"],"HASH_MISMATCH",got,r["artifact_sha256"]))
if fail:
    for x in fail: print("\t".join(map(str,x)),file=sys.stderr)
    print(f"status=FAIL claims={len(rows)} failures={len(fail)}")
    raise SystemExit(1)
print(f"status=PASS claims={len(rows)} evidence_hashes={len(rows)}")
