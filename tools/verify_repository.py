#!/usr/bin/env python3
from pathlib import Path
import csv,json,hashlib,sys,subprocess,py_compile,tempfile

ROOT=Path(__file__).resolve().parents[1]
fail=[]

def is_runtime_generated(p):
    rel=p.relative_to(ROOT)
    parts=set(rel.parts)
    return (
        ".pytest_cache" in parts
        or "__pycache__" in parts
        or p.suffix.lower() in {".pyc",".pyo"}
    )

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

# Repository version contract.
try:
    if (ROOT/"VERSION").read_text(encoding="utf-8").strip()!="1.1":
        fail.append(("version","VERSION is not 1.1"))
except Exception as e: fail.append(("version",repr(e)))

# Publication PDFs are deliberately outside this repository distribution.
if (ROOT/"manuscript").exists(): fail.append(("content_policy","unexpected manuscript directory"))
if (ROOT/"docs/MANUSCRIPT_TARGETS.tsv").exists(): fail.append(("content_policy","obsolete MANUSCRIPT_TARGETS.tsv present"))
for p in ROOT.rglob("*.pdf"):
    fail.append(("content_policy","unexpected PDF: "+str(p.relative_to(ROOT))))

# Root checksums.
checks=ROOT/"SHA256SUMS.txt"
if checks.exists():
    for line in checks.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        h,rel=line.split("  ",1)
        p=ROOT/rel
        if not p.is_file(): fail.append(("checksum_missing",rel))
        elif sha(p)!=h: fail.append(("checksum_mismatch",rel))
else: fail.append(("missing","SHA256SUMS.txt"))

# Root manifest.
man=ROOT/"MANIFEST.tsv"
if man.exists():
    rows=list(csv.DictReader(man.open(encoding="utf-8"),delimiter="\t"))
    listed={r["path"] for r in rows}
    actual={str(p.relative_to(ROOT)).replace("\\","/") for p in ROOT.rglob("*") if p.is_file() and not is_runtime_generated(p) and p not in {ROOT/"MANIFEST.tsv",ROOT/"SHA256SUMS.txt"}}
    if listed!=actual:
        fail.append(("manifest_member_set",f"listed={len(listed)} actual={len(actual)} extra={sorted(listed-actual)[:3]} missing={sorted(actual-listed)[:3]}"))
    for r in rows:
        p=ROOT/r["path"]
        if p.is_file():
            if int(r["bytes"])!=p.stat().st_size: fail.append(("manifest_size",r["path"]))
            if r["sha256"]!=sha(p): fail.append(("manifest_hash",r["path"]))
else: fail.append(("missing","MANIFEST.tsv"))

# Parse JSON/TSV and compile Python.
json_count=tsv_count=py_count=0
for p in ROOT.rglob("*"):
    if not p.is_file() or is_runtime_generated(p): continue
    try:
        if p.suffix.lower()==".json":
            json.loads(p.read_text(encoding="utf-8")); json_count+=1
        elif p.suffix.lower()==".tsv":
            with p.open(encoding="utf-8",newline="") as f: list(csv.reader(f,delimiter="\t"))
            tsv_count+=1
        elif p.suffix.lower()==".py":
            py_compile.compile(str(p),doraise=True,cfile=str(Path(tempfile.gettempdir())/(hashlib.sha256(str(p).encode()).hexdigest()+".pyc"))); py_count+=1
    except Exception as e:
        fail.append(("parse_or_compile",str(p.relative_to(ROOT)),repr(e)))

# Claim matrix exact ID coverage against the fixed evidence archive.
try:
    c=list(csv.DictReader((ROOT/"publication_evidence/evidence/CLAIM_EVIDENCE_CROSSWALK.tsv").open(encoding="utf-8"),delimiter="\t"))
    m=list(csv.DictReader((ROOT/"docs/PAPER_REPRODUCTION_MATRIX.tsv").open(encoding="utf-8"),delimiter="\t"))
    if {r["claim_id"] for r in c}!={r["claim_id"] for r in m}:
        fail.append(("claim_matrix_coverage",f"cross={len(c)} matrix={len(m)}"))
    allowed={"EXACT_REEXECUTION_WITH_PUBLIC_INPUTS","DETERMINISTIC_EVIDENCE_REPLAY","EXACT_DATA_FREE_FIXTURE","BOUNDED_TRACEABILITY_REPLAY"}
    unknown=sorted({r["reproduction_class"] for r in m}-allowed)
    if unknown: fail.append(("claim_matrix_class",str(unknown)))
    if any(not r["reproduction_class"] or not r["runner"] for r in m): fail.append(("claim_matrix_empty_runner",""))
except Exception as e: fail.append(("claim_matrix",repr(e)))

# No redistributed large third-party payloads.
for p in ROOT.rglob("*"):
    if not p.is_file() or is_runtime_generated(p): continue
    if p.suffix.lower() in {".h5",".hdf5"}: fail.append(("third_party_payload_present",str(p.relative_to(ROOT))))
    if p.stat().st_size>2_000_000: fail.append(("unexpected_large_file",f"{p.relative_to(ROOT)}:{p.stat().st_size}"))

# Embedded publication-evidence verifier.
r=subprocess.run([sys.executable,str(ROOT/"publication_evidence/scripts/verify_package.py")],cwd=ROOT/"publication_evidence",capture_output=True,text=True)
if r.returncode!=0: fail.append(("publication_evidence_verifier",r.stdout+r.stderr))

# Claim-evidence replay.
r=subprocess.run([sys.executable,str(ROOT/"tools/replay_evidence_claims.py")],capture_output=True,text=True)
if r.returncode!=0: fail.append(("claim_replay",r.stdout+r.stderr))

if fail:
    for x in fail: print("FAIL\t"+"\t".join(map(str,x)),file=sys.stderr)
    print(f"status=FAIL failures={len(fail)} json={json_count} tsv={tsv_count} py={py_count}")
    raise SystemExit(1)
print(f"status=PASS version=1.1 json={json_count} tsv={tsv_count} py={py_count} claims=33 publication_pdfs=0")
