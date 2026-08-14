#!/usr/bin/env python3
from pathlib import Path
import tempfile,subprocess,sys,hashlib,shutil

ROOT=Path(__file__).resolve().parents[1]
expected=ROOT/"expected/manuscript_assets"
tmp=Path(tempfile.mkdtemp(prefix="ht_asset_verify_"))

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
try:
    subprocess.run([sys.executable,str(ROOT/"tools/reproduce_manuscript_assets.py"),"--output",str(tmp)],check=True)
    E={p.name:sha(p) for p in expected.glob("*") if p.is_file()}
    G={p.name:sha(p) for p in tmp.glob("*") if p.is_file()}
    if E!=G:
        print("status=FAIL expected/generated asset mismatch",file=sys.stderr)
        print("expected-only",sorted(E.keys()-G.keys()),file=sys.stderr)
        print("generated-only",sorted(G.keys()-E.keys()),file=sys.stderr)
        for k in sorted(E.keys() & G.keys()):
            if E[k]!=G[k]: print("hash-mismatch",k,file=sys.stderr)
        raise SystemExit(1)
    print(f"status=PASS manuscript_assets={len(E)} byte_exact_generated_match=YES")
finally:
    shutil.rmtree(tmp,ignore_errors=True)
