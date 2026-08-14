#!/usr/bin/env python3
from pathlib import Path
import argparse,subprocess,sys,json,hashlib,urllib.request,shutil,csv

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/"publication_evidence/provenance/SOURCE_REGISTRY.tsv"

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def run(cmd):
    print("+"," ".join(map(str,cmd)))
    subprocess.run([str(x) for x in cmd],check=True)

def clone(repo,commit,dest):
    if not dest.exists():
        run(["git","clone","--no-checkout",repo,dest])
    run(["git","-C",dest,"fetch","--all","--tags"])
    run(["git","-C",dest,"checkout","--detach",commit])

def zenodo(record_id,filename,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    api=f"https://zenodo.org/api/records/{record_id}"
    print("+ GET",api)
    with urllib.request.urlopen(api) as r:
        meta=json.load(r)
    candidates=[f for f in meta.get("files",[]) if f.get("key")==filename]
    if len(candidates)!=1:
        raise RuntimeError(f"Zenodo record {record_id}: unique file {filename!r} not found")
    url=candidates[0]["links"]["self"]
    print("+ GET",url)
    with urllib.request.urlopen(url) as r, dest.open("wb") as w:
        shutil.copyfileobj(r,w)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=ROOT/"external")
    ap.add_argument("--skip-tdcosmo",action="store_true")
    a=ap.parse_args()
    out=a.root; out.mkdir(parents=True,exist_ok=True)

    clone("https://github.com/StefCas789/H0DN.git","cc0a4b9f36e65470d514f254a3c5cffa463fbd94",out/"H0DN")
    clone("https://github.com/PantheonPlusSH0ES/DataRelease.git","c447f0fea703fcd0fff57de5000947b5ca81286b",out/"PantheonPlus")
    if not a.skip_tdcosmo:
        clone("https://github.com/TDCOSMO/TDCOSMO2025_public.git","d7f38db341f68be1df0d9ac1fc528c45113f94cf",out/"TDCOSMO")

    zenodo("16919645","H0_dark_combined.json",out/"GWTC4/H0_dark_combined.json")
    zenodo("20378418","H0_dark_combined_gw170817.json",out/"GWTC5/H0_dark_combined_gw170817.json")

    # Verify every registry row whose local mapping is known.
    registry=list(csv.DictReader(REG.open(encoding="utf-8"),delimiter="\t"))
    mapping={
      "H0DN_SN_TABLE":out/"H0DN/data/sn1a_hf_pp.dat",
      "H0DN_SN_COVARIANCE":out/"H0DN/data/sn1a_covar_pp.dat",
      "H0DN_CONFIG":out/"H0DN/h0_constrainer/configs/config.ini",
      "H0DN_EQUATIONS":out/"H0DN/h0_constrainer/h0_constrainer/equations.py",
      "H0DN_SOLVER":out/"H0DN/h0_constrainer/h0_constrainer/solver.py",
      "PANTHEONPLUS_TABLE":out/"PantheonPlus/Pantheon+_Data/4_DISTANCES_AND_COVAR/Pantheon+SH0ES.dat",
      "PANTHEONPLUS_STAT_SYS":out/"PantheonPlus/Pantheon+_Data/4_DISTANCES_AND_COVAR/Pantheon+SH0ES_STAT+SYS.cov",
      "PANTHEONPLUS_STATONLY":out/"PantheonPlus/Pantheon+_Data/4_DISTANCES_AND_COVAR/Pantheon+SH0ES_STATONLY.cov",
      "GWTC4_POSTERIOR":out/"GWTC4/H0_dark_combined.json",
      "GWTC5V1_POSTERIOR":out/"GWTC5/H0_dark_combined_gw170817.json",
    }
    fail=[]
    byid={r["source_id"]:r for r in registry}
    for sid,p in mapping.items():
        r=byid[sid]
        if not p.is_file(): fail.append((sid,"missing")); continue
        if r["expected_bytes"] and p.stat().st_size!=int(r["expected_bytes"]): fail.append((sid,"size"))
        if r["sha256"] and sha(p)!=r["sha256"]: fail.append((sid,"sha256"))
    if fail:
        for x in fail: print("FAIL",x,file=sys.stderr)
        raise SystemExit(1)
    print(f"status=PASS fetched_root={out} verified_files={len(mapping)}")

if __name__=="__main__":
    main()
