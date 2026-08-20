# HTS61 run instructions

The package first searches recursively under:

`${USER_DATA_ROOT}/Downloads/HTS_CHAIN_CACHE_STORE`

Preflight:
```bash
HTS61_PREFLIGHT_ONLY=1 bash ${USER_DATA_ROOT}/Downloads/HTS61_RUN_PACKAGE/run_hts61.sh
```

Full run:
```bash
bash ${USER_DATA_ROOT}/Downloads/HTS61_RUN_PACKAGE/run_hts61.sh
```

Expected outputs:
- `HTS61_RESULTS_FOR_REVIEW.zip`
- `HTS61_RESULTS_FOR_REVIEW.zip.sha256`
- `HTS61_RUN_LOG.txt`
