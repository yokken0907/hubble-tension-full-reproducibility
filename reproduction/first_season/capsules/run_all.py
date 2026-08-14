#!/usr/bin/env python3
from pathlib import Path
import argparse,subprocess,sys
ROOT=Path(__file__).resolve().parent
def main():
 a=argparse.ArgumentParser();a.add_argument('--cmb-output',type=Path,default=Path('_outputs/cmb'));a.add_argument('--posterior-cache',type=Path,default=Path('_external_cache'));a.add_argument('--posterior-work',type=Path,default=Path('_work/posterior'));a.add_argument('--posterior-output',type=Path,default=Path('_outputs/posterior'));a.add_argument('--fetch',action='store_true');a.add_argument('--verify',action='store_true');x=a.parse_args()
 cmb=ROOT/'cmb_fixed_seed_bootstrap';subprocess.run([sys.executable,cmb/'run_analysis.py','--moments',cmb/'inputs/FROZEN_GAUSSIAN_MOMENTS.tsv','--out',x.cmb_output,'--bootstrap-draws','1000','--seed','10199'],check=True)
 if x.verify:subprocess.run([sys.executable,cmb/'verify_output.py','--output-dir',x.cmb_output],check=True)
 pa=ROOT/'posterior_attribution';cmd=[sys.executable,pa/'run_all.py','--cache',x.posterior_cache,'--work',x.posterior_work,'--output',x.posterior_output]+(['--fetch-inputs'] if x.fetch else [])+(['--verify'] if x.verify else []);subprocess.run(cmd,check=True)
if __name__=='__main__':main()
