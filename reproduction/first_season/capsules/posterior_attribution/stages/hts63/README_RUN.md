# HTS63 run instructions

The package first searches recursively under:

`${USER_DATA_ROOT}/Downloads/HTS_CHAIN_CACHE_STORE`

Preflight:
```bash
HTS63_PREFLIGHT_ONLY=1 bash ${USER_DATA_ROOT}/Downloads/HTS63_RUN_PACKAGE/run_hts63.sh
```

Full run:
```bash
bash ${USER_DATA_ROOT}/Downloads/HTS63_RUN_PACKAGE/run_hts63.sh
```

Expected outputs:
- `HTS63_RESULTS_FOR_REVIEW.zip`
- `HTS63_RESULTS_FOR_REVIEW.zip.sha256`
- `HTS63_RUN_LOG.txt`
