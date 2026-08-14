# HTS60 run instructions

The package first searches recursively under:

`${USER_DATA_ROOT}/Downloads/HTS_CHAIN_CACHE_STORE`

Preflight:
```bash
HTS60_PREFLIGHT_ONLY=1 bash ${USER_DATA_ROOT}/Downloads/HTS60_RUN_PACKAGE/run_hts60.sh
```

Full run:
```bash
bash ${USER_DATA_ROOT}/Downloads/HTS60_RUN_PACKAGE/run_hts60.sh
```

Expected outputs:
- `HTS60_RESULTS_FOR_REVIEW.zip`
- `HTS60_RESULTS_FOR_REVIEW.zip.sha256`
- `HTS60_RUN_LOG.txt`
