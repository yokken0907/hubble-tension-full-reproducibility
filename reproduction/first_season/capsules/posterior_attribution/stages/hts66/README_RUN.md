# HTS66 run instructions

Place the exact HTS59–HTS65 result ZIPs in Downloads or under:

`${USER_DATA_ROOT}/Downloads/HTS_CHAIN_CACHE_STORE`

Preflight:
```bash
HTS66_PREFLIGHT_ONLY=1 bash ${USER_DATA_ROOT}/Downloads/HTS66_RUN_PACKAGE/run_hts66.sh
```

Full run:
```bash
bash ${USER_DATA_ROOT}/Downloads/HTS66_RUN_PACKAGE/run_hts66.sh
```

Expected outputs:
- `HTS66_RESULTS_FOR_REVIEW.zip`
- `HTS66_RESULTS_FOR_REVIEW.zip.sha256`
- `HTS66_RUN_LOG.txt`
