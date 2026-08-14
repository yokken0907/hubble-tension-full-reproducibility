#!/usr/bin/env python3
from pathlib import Path
import argparse, subprocess, sys, shutil, tempfile, csv

ROOT = Path(__file__).resolve().parents[1]


def run(cmd, cwd=None):
    print('+', ' '.join(map(str, cmd)))
    subprocess.run([str(x) for x in cmd], cwd=cwd, check=True)


def main():
    ap = argparse.ArgumentParser(
        description='Run public-input reproductions in an isolated working copy so the frozen repository is never modified.'
    )
    ap.add_argument('--external-root', type=Path, default=ROOT / 'external')
    ap.add_argument('--skip-tdcosmo', action='store_true')
    ap.add_argument('--keep-work', action='store_true', help='keep the temporary working directory for inspection')
    a = ap.parse_args()
    ext = a.external_root.resolve()

    temp_root = Path(tempfile.mkdtemp(prefix='ht_external_reproduction_'))
    pe_work = temp_root / 'publication_evidence'
    shutil.copytree(ROOT / 'publication_evidence', pe_work)

    try:
        # H0DN final-validation test vectors are rebuilt only inside the disposable copy.
        tv = pe_work / 'test_vectors'
        run([
            sys.executable,
            pe_work / 'scripts/rebuild_test_vectors_from_h0dn.py',
            '--upstream', ext / 'H0DN',
            '--output-root', tv,
        ])
        run([
            sys.executable,
            pe_work / 'scripts/run_internal_validations.py',
            '--root', pe_work,
            '--verify-recorded',
        ])

        # Same-CID / covariance verification reads official public inputs directly.
        run([
            sys.executable,
            pe_work / 'scripts/independent_verify_same_cid.py',
            '--h0dn', ext / 'H0DN',
            '--pantheonplus', ext / 'PantheonPlus',
        ])

        # GWTC scripts expect fixed relative input paths. Populate them only in the disposable copy.
        for src, dst in [
            (ext / 'GWTC4/H0_dark_combined.json', pe_work / 'INPUTS/GWTC4/H0_dark_combined.json'),
            (ext / 'GWTC5/H0_dark_combined_gw170817.json', pe_work / 'INPUTS/GWTC5/H0_dark_combined_gw170817.json'),
        ]:
            if not src.is_file():
                raise FileNotFoundError(src)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        run([sys.executable, pe_work / 'scripts/reproduce_gwtc_quantiles.py'], cwd=pe_work)

        if not a.skip_tdcosmo:
            manifest = pe_work / 'evidence/tdcosmo/SOURCE_MANIFEST_13_CHAINS.tsv'
            td_work = temp_root / 'tdcosmo_work'
            inp = td_work / 'INPUTS'
            out = temp_root / 'tdcosmo_output'
            inp.mkdir(parents=True)
            shutil.copy2(manifest, td_work / 'SOURCE_MANIFEST.tsv')
            rows = list(csv.DictReader(manifest.open(encoding='utf-8'), delimiter='\t'))
            for r in rows:
                matches = list((ext / 'TDCOSMO').rglob(r['filename']))
                if len(matches) != 1:
                    raise RuntimeError(f"{r['filename']}: expected one source file, got {len(matches)}")
                shutil.copy2(matches[0], inp / r['filename'])
            run([
                sys.executable,
                pe_work / 'scripts/reproduce_tdcosmo_outputs.py',
                '--package-root', td_work,
                '--output-parent', out,
            ])

        print(f'status=PASS external_reproduction_suite=COMPLETE work={temp_root}')
    finally:
        if a.keep_work:
            print(f'kept_work={temp_root}')
        else:
            shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == '__main__':
    main()
