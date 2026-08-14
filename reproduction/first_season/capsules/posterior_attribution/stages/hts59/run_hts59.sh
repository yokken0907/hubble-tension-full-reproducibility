#!/usr/bin/env bash
set -u
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOWNLOADS="${HTS59_DOWNLOADS:-$(dirname "$PKG_DIR")}"
STORE="${HTS_CACHE_STORE:-$DOWNLOADS/HTS_CHAIN_CACHE_STORE}"
OUT="${HTS59_OUTPUT:-$DOWNLOADS/HTS59_RESULTS_FOR_REVIEW}"
ZIPOUT="${HTS59_ZIP_OUTPUT:-$DOWNLOADS/HTS59_RESULTS_FOR_REVIEW.zip}"
LOG="${HTS59_LOG:-$DOWNLOADS/HTS59_RUN_LOG.txt}"
mkdir -p "$DOWNLOADS" "$STORE"
echo "HTS59 package directory: $PKG_DIR" | tee "$LOG"
echo "HTS59 shared cache store: $STORE" | tee -a "$LOG"
echo "HTS59 stage cache: ${HTS59_CACHE:-$STORE/HTS59}" | tee -a "$LOG"
echo "HTS59 output directory: $OUT" | tee -a "$LOG"
cd "$PKG_DIR" || exit 1
python3 - <<'PY' 2>&1 | tee -a "$LOG"
import hashlib
from pathlib import Path
bad=[]
for line in Path('CURRENT_SHA256SUMS.txt').read_text().splitlines():
    if not line.strip():continue
    expected,name=line.split(None,1);p=Path(name.strip());got=hashlib.sha256(p.read_bytes()).hexdigest()
    print(f'{p.name}:', 'OK' if got==expected else 'FAIL')
    if got!=expected:bad.append(p.name)
if bad:raise SystemExit('checksum failure: '+', '.join(bad))
PY
rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || exit "$rc"
python3 - <<'PY' 2>&1 | tee -a "$LOG"
import numpy
print('HTS59 dependency check PASS')
PY
rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || exit "$rc"
python3 "$PKG_DIR/selftest_hts59.py" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || exit "$rc"
if [ "${HTS59_PREFLIGHT_ONLY:-0}" = "1" ]; then echo 'HTS59 preflight-only check completed successfully.' | tee -a "$LOG"; exit 0; fi
HTS59_DOWNLOADS="$DOWNLOADS" HTS_CACHE_STORE="$STORE" HTS59_OUTPUT="$OUT" HTS59_ZIP_OUTPUT="$ZIPOUT" python3 "$PKG_DIR/run_hts59.py" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}; echo "HTS59 python exit code: $rc" | tee -a "$LOG"; exit "$rc"
