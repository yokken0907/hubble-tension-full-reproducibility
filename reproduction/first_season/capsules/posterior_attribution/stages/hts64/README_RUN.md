# HTS64 run instructions

The package first searches recursively under:

`${USER_DATA_ROOT}/Downloads/HTS_CHAIN_CACHE_STORE`

Preflight:
```bash
HTS64_PREFLIGHT_ONLY=1 bash ${USER_DATA_ROOT}/Downloads/HTS64_RUN_PACKAGE/run_hts64.sh
```

Full run:
```bash
bash ${USER_DATA_ROOT}/Downloads/HTS64_RUN_PACKAGE/run_hts64.sh
```

Expected outputs:
- `HTS64_RESULTS_FOR_REVIEW.zip`
- `HTS64_RESULTS_FOR_REVIEW.zip.sha256`
- `HTS64_RUN_LOG.txt`
