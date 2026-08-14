#!/usr/bin/env python3
from pathlib import Path
import argparse, subprocess, sys, tempfile, shutil

ROOT = Path(__file__).resolve().parents[1]


def run(cmd, cwd=None):
    print('+', ' '.join(map(str, cmd)))
    subprocess.run([str(x) for x in cmd], cwd=cwd, check=True)


def main():
    ap = argparse.ArgumentParser(description='Run the self-contained offline reproduction and integrity suite.')
    ap.add_argument(
        '--full-cmb',
        action='store_true',
        help='rerun the 1,000-draw fixed-seed CMB bootstrap; substantially slower than the default stored-output verification',
    )
    a = ap.parse_args()

    run([sys.executable, ROOT / 'tools/verify_repository.py'])
    run([sys.executable, ROOT / 'publication_evidence/scripts/verify_synthetic_fixtures.py'], cwd=ROOT / 'publication_evidence')
    run([sys.executable, ROOT / 'tools/replay_evidence_claims.py'])

    cmb = ROOT / 'reproduction/first_season/capsules/cmb_fixed_seed_bootstrap'
    if a.full_cmb:
        tmp = Path(tempfile.mkdtemp(prefix='ht_cmb_replay_'))
        try:
            out = tmp / 'out'
            run([
                sys.executable,
                cmb / 'run_analysis.py',
                '--moments', cmb / 'inputs/FROZEN_GAUSSIAN_MOMENTS.tsv',
                '--out', out,
                '--bootstrap-draws', '1000',
                '--seed', '10199',
            ])
            run([sys.executable, cmb / 'verify_output.py', '--output-dir', out])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        # The canonical project already retained a clean full replay. Verify those exact outputs quickly.
        # --full-cmb reruns the same fixed-input/fixed-seed contract from scratch.
        run([sys.executable, cmb / 'verify_output.py', '--output-dir', cmb / 'verified_replay_outputs'])

    run([sys.executable, ROOT / 'tools/verify_manuscript_assets.py'])
    print(f"status=PASS offline_reproduction_suite=COMPLETE full_cmb={'YES' if a.full_cmb else 'NO_STORED_FULL_REPLAY_VERIFIED'}")


if __name__ == '__main__':
    main()
