#!/usr/bin/env bash
set -u
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOWNLOADS="${HTS67_DOWNLOADS:-$(dirname "$PKG_DIR")}"
STORE="${HTS_CACHE_STORE:-$DOWNLOADS/HTS_CHAIN_CACHE_STORE}"
OUT="${HTS67_OUTPUT:-$DOWNLOADS/HTS67_RESULTS_FOR_REVIEW}"
ZIPOUT="${HTS67_ZIP_OUTPUT:-$DOWNLOADS/HTS67_RESULTS_FOR_REVIEW.zip}"
LOG="${HTS67_LOG:-$DOWNLOADS/HTS67_RUN_LOG.txt}"
mkdir -p "$DOWNLOADS" "$STORE"
echo "HTS67 package directory: $PKG_DIR" | tee "$LOG"
echo "HTS67 shared cache store: $STORE" | tee -a "$LOG"
echo "HTS67 stage metadata cache: ${HTS67_CACHE:-$STORE/HTS67}" | tee -a "$LOG"
echo "HTS67 output directory: $OUT" | tee -a "$LOG"
cd "$PKG_DIR" || exit 1
python3 - <<'PY' 2>&1 | tee -a "$LOG"
import hashlib
from pathlib import Path
bad=[]
for line in Path('CURRENT_SHA256SUMS.txt').read_text().splitlines():
    if not line.strip():
        continue
    expected,name=line.split(None,1)
    path=Path(name.strip())
    observed=hashlib.sha256(path.read_bytes()).hexdigest()
    print(f'{path.name}:', 'OK' if observed==expected else 'FAIL')
    if observed!=expected:
        bad.append(path.name)
if bad:
    raise SystemExit('checksum failure: '+', '.join(bad))
PY
rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || exit "$rc"
python3 - <<'PY' 2>&1 | tee -a "$LOG"
import numpy
print('HTS67 dependency check PASS')
PY
rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || exit "$rc"
python3 "$PKG_DIR/selftest_hts67.py" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || exit "$rc"
if [ "${HTS67_PREFLIGHT_ONLY:-0}" = "1" ]; then
  echo 'HTS67 preflight-only check completed successfully.' | tee -a "$LOG"
  exit 0
fi
HTS67_DOWNLOADS="$DOWNLOADS" HTS_CACHE_STORE="$STORE" HTS67_OUTPUT="$OUT" HTS67_ZIP_OUTPUT="$ZIPOUT" python3 "$PKG_DIR/run_hts67.py" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}
echo "HTS67 python exit code: $rc" | tee -a "$LOG"
exit "$rc"
