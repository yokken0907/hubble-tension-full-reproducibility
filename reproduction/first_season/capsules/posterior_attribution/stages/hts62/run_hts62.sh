#!/usr/bin/env bash
set -u
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOWNLOADS="${HTS62_DOWNLOADS:-$(dirname "$PKG_DIR")}"
STORE="${HTS_CACHE_STORE:-$DOWNLOADS/HTS_CHAIN_CACHE_STORE}"
OUT="${HTS62_OUTPUT:-$DOWNLOADS/HTS62_RESULTS_FOR_REVIEW}"
ZIPOUT="${HTS62_ZIP_OUTPUT:-$DOWNLOADS/HTS62_RESULTS_FOR_REVIEW.zip}"
LOG="${HTS62_LOG:-$DOWNLOADS/HTS62_RUN_LOG.txt}"
mkdir -p "$DOWNLOADS" "$STORE"
echo "HTS62 package directory: $PKG_DIR" | tee "$LOG"
echo "HTS62 shared cache store: $STORE" | tee -a "$LOG"
echo "HTS62 stage cache: ${HTS62_CACHE:-$STORE/HTS62}" | tee -a "$LOG"
echo "HTS62 output directory: $OUT" | tee -a "$LOG"
cd "$PKG_DIR" || exit 1
python3 - <<'PY_CHECK62' 2>&1 | tee -a "$LOG"
import hashlib
from pathlib import Path
bad=[]
for line in Path('CURRENT_SHA256SUMS.txt').read_text().splitlines():
 if not line.strip():continue
 expected,name=line.split(None,1);p=Path(name.strip());got=hashlib.sha256(p.read_bytes()).hexdigest();print(f'{p.name}:','OK' if got==expected else 'FAIL')
 if got!=expected:bad.append(p.name)
if bad:raise SystemExit('checksum failure: '+', '.join(bad))
PY_CHECK62
rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || exit "$rc"
python3 - <<'PY_DEP62' 2>&1 | tee -a "$LOG"
import numpy
print('HTS62 dependency check PASS')
PY_DEP62
rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || exit "$rc"
python3 "$PKG_DIR/selftest_hts62.py" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}; [ "$rc" -eq 0 ] || exit "$rc"
if [ "${HTS62_PREFLIGHT_ONLY:-0}" = "1" ]; then echo 'HTS62 preflight-only check completed successfully.' | tee -a "$LOG"; exit 0; fi
HTS62_DOWNLOADS="$DOWNLOADS" HTS_CACHE_STORE="$STORE" HTS62_OUTPUT="$OUT" HTS62_ZIP_OUTPUT="$ZIPOUT" python3 "$PKG_DIR/run_hts62.py" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}; echo "HTS62 python exit code: $rc" | tee -a "$LOG"; exit "$rc"
