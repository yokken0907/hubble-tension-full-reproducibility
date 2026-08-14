#!/usr/bin/env python3
from pathlib import Path
import csv,json,hashlib,sys,subprocess,py_compile,tempfile

ROOT=Path(__file__).resolve().parents[1]
fail=[]

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

# checksums
checks=ROOT/"SHA256SUMS.txt"
if checks.exists():
    for line in checks.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        h,rel=line.split("  ",1)
        p=ROOT/rel
        if not p.is_file(): fail.append(("checksum_missing",rel))
        elif sha(p)!=h: fail.append(("checksum_mismatch",rel))
else: fail.append(("missing","SHA256SUMS.txt"))

# manifest
man=ROOT/"MANIFEST.tsv"
if man.exists():
    rows=list(csv.DictReader(man.open(encoding="utf-8"),delimiter="\t"))
    listed={r["path"] for r in rows}
    actual={str(p.relative_to(ROOT)).replace("\\","/") for p in ROOT.rglob("*") if p.is_file() and p not in {ROOT/"MANIFEST.tsv",ROOT/"SHA256SUMS.txt"}}
    if listed!=actual:
        fail.append(("manifest_member_set",f"listed={len(listed)} actual={len(actual)} extra={sorted(listed-actual)[:3]} missing={sorted(actual-listed)[:3]}"))
    for r in rows:
        p=ROOT/r["path"]
        if p.is_file():
            if int(r["bytes"])!=p.stat().st_size: fail.append(("manifest_size",r["path"]))
            if r["sha256"]!=sha(p): fail.append(("manifest_hash",r["path"]))
else: fail.append(("missing","MANIFEST.tsv"))

# parse JSON and TSV, compile Python
json_count=tsv_count=py_count=0
for p in ROOT.rglob("*"):
    if not p.is_file(): continue
    try:
        if p.suffix.lower()==".json":
            json.loads(p.read_text(encoding="utf-8")); json_count+=1
        elif p.suffix.lower()==".tsv":
            with p.open(encoding="utf-8",newline="") as f:
                list(csv.reader(f,delimiter="\t"))
            tsv_count+=1
        elif p.suffix.lower()==".py":
            py_compile.compile(str(p),doraise=True,cfile=str(Path(tempfile.gettempdir())/(hashlib.sha256(str(p).encode()).hexdigest()+".pyc"))); py_count+=1
    except Exception as e:
        fail.append(("parse_or_compile",str(p.relative_to(ROOT)),repr(e)))

# claim matrix exact coverage
try:
    c=list(csv.DictReader((ROOT/"publication_evidence/evidence/CLAIM_EVIDENCE_CROSSWALK.tsv").open(encoding="utf-8"),delimiter="\t"))
    m=list(csv.DictReader((ROOT/"docs/PAPER_REPRODUCTION_MATRIX.tsv").open(encoding="utf-8"),delimiter="\t"))
    if {r["claim_id"] for r in c}!={r["claim_id"] for r in m}:
        fail.append(("claim_matrix_coverage",f"cross={len(c)} matrix={len(m)}"))
    if any(not r["reproduction_class"] or not r["runner"] for r in m):
        fail.append(("claim_matrix_empty_runner",""))
except Exception as e: fail.append(("claim_matrix",repr(e)))

# exact manuscript target identities
try:
    for r in csv.DictReader((ROOT/"docs/MANUSCRIPT_TARGETS.tsv").open(encoding="utf-8"),delimiter="\t"):
        p=ROOT/"manuscript"/r["filename"]
        if not p.is_file() or p.stat().st_size!=int(r["bytes"]) or sha(p)!=r["sha256"]:
            fail.append(("manuscript_target",r["filename"]))
except Exception as e: fail.append(("manuscript_targets",repr(e)))

# no obviously redistributed large third-party payloads
for p in ROOT.rglob("*"):
    if not p.is_file(): continue
    if p.suffix.lower() in {".h5",".hdf5"}:
        fail.append(("third_party_payload_present",str(p.relative_to(ROOT))))
    if p.stat().st_size>2_000_000:
        fail.append(("unexpected_large_file",f"{p.relative_to(ROOT)}:{p.stat().st_size}"))

# embedded publication-evidence verifier
cmd=[sys.executable,str(ROOT/"publication_evidence/scripts/verify_package.py")]
r=subprocess.run(cmd,cwd=ROOT/"publication_evidence",capture_output=True,text=True)
if r.returncode!=0:
    fail.append(("publication_evidence_verifier",r.stdout+r.stderr))

# claim evidence replay
r=subprocess.run([sys.executable,str(ROOT/"tools/replay_evidence_claims.py")],capture_output=True,text=True)
if r.returncode!=0:
    fail.append(("claim_replay",r.stdout+r.stderr))

if fail:
    for x in fail: print("FAIL\t"+"\t".join(map(str,x)),file=sys.stderr)
    print(f"status=FAIL failures={len(fail)} json={json_count} tsv={tsv_count} py={py_count}")
    raise SystemExit(1)
print(f"status=PASS json={json_count} tsv={tsv_count} py={py_count} claims=33")
