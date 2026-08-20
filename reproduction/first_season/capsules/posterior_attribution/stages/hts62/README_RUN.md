# HTS62 run instructions

The package first searches recursively under:

`${USER_DATA_ROOT}/Downloads/HTS_CHAIN_CACHE_STORE`

Preflight:
```bash
HTS62_PREFLIGHT_ONLY=1 bash ${USER_DATA_ROOT}/Downloads/HTS62_RUN_PACKAGE/run_hts62.sh
```

Full run:
```bash
bash ${USER_DATA_ROOT}/Downloads/HTS62_RUN_PACKAGE/run_hts62.sh
```

Expected outputs:
- `HTS62_RESULTS_FOR_REVIEW.zip`
- `HTS62_RESULTS_FOR_REVIEW.zip.sha256`
- `HTS62_RUN_LOG.txt`
