#!/usr/bin/env python3
from pathlib import Path
import argparse,json,math
p=argparse.ArgumentParser();p.add_argument('--actual',required=True);a=p.parse_args();root=Path(__file__).resolve().parent
exp=json.loads((root/'EXPECTED_OUTPUT.json').read_text()); act=json.loads(Path(a.actual).read_text()); tol={'omega_m':2e-10,'omega_m_sigma':2e-10,'H0_rd_km_s':2e-5,'H0_rd_sigma_km_s':2e-5,'chi2':2e-8,'PTE':2e-8}
fail=False
for k,v in exp.items():
 ok=(act.get(k)==v) if k=='dof' else abs(float(act.get(k))-float(v))<=tol[k]; print(k,'PASS' if ok else 'FAIL',act.get(k),v); fail|=not ok
raise SystemExit(1 if fail else 0)
