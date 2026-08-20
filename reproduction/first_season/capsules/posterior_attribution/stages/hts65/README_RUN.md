# HTS65 run instructions

The package first searches recursively under:

`${USER_DATA_ROOT}/Downloads/HTS_CHAIN_CACHE_STORE`

Preflight:
```bash
HTS65_PREFLIGHT_ONLY=1 bash ${USER_DATA_ROOT}/Downloads/HTS65_RUN_PACKAGE/run_hts65.sh
```

Full run:
```bash
bash ${USER_DATA_ROOT}/Downloads/HTS65_RUN_PACKAGE/run_hts65.sh
```

Expected outputs:
- `HTS65_RESULTS_FOR_REVIEW.zip`
- `HTS65_RESULTS_FOR_REVIEW.zip.sha256`
- `HTS65_RUN_LOG.txt`
