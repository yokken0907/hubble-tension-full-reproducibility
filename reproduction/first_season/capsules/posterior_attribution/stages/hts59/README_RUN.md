# HTS59 run instructions

The package searches recursively under `${USER_DATA_ROOT}/Downloads/HTS_CHAIN_CACHE_STORE` before any acquisition.

Preflight:
```bash
HTS59_PREFLIGHT_ONLY=1 bash ${USER_DATA_ROOT}/Downloads/HTS59_RUN_PACKAGE/run_hts59.sh
```

Full run:
```bash
bash ${USER_DATA_ROOT}/Downloads/HTS59_RUN_PACKAGE/run_hts59.sh
```

Outputs: `HTS59_RESULTS_FOR_REVIEW.zip`, sidecar SHA256 and `HTS59_RUN_LOG.txt`.
