#!/usr/bin/env python3
from pathlib import Path
import argparse, os, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
SUITES=[
    "reproduction/second_season/h0dn_singular_covariance",
    "reproduction/second_season/snia_same_cid/phase0",
    "reproduction/second_season/snia_same_cid/phase1a",
    "reproduction/second_season/snia_same_cid/phase1b",
    "reproduction/second_season/snia_same_cid/phase1c",
    "reproduction/second_season/snia_same_cid/phase1d",
    "reproduction/second_season/snia_same_cid/phase1e",
]

def run_suite(rel, env=None):
    cwd=ROOT/rel
    print(f"+ [{rel}] {sys.executable} -m pytest -q")
    subprocess.run([sys.executable,"-m","pytest","-q"],cwd=cwd,check=True,env=env)

def main():
    ap=argparse.ArgumentParser(description="Run phase-local test suites in isolated processes to avoid historical module-name collisions.")
    ap.add_argument("--pantheonplus-repo",type=Path,default=None,help="Optional Pantheon+ DataRelease checkout required for the Phase 1F suite.")
    a=ap.parse_args()
    for s in SUITES: run_suite(s)
    ran=len(SUITES)
    if a.pantheonplus_repo is not None:
        repo=a.pantheonplus_repo.resolve()
        if not repo.is_dir(): raise SystemExit(f"Pantheon+ repository not found: {repo}")
        env=os.environ.copy(); env["PANTHEONPLUS_REPO"]=str(repo)
        run_suite("reproduction/second_season/snia_same_cid/phase1f",env=env); ran+=1
        phase1f="YES"
    else:
        phase1f="NO_EXTERNAL_INPUT"
    print(f"status=PASS isolated_test_suites={ran} phase1f={phase1f}")

if __name__=="__main__": main()
