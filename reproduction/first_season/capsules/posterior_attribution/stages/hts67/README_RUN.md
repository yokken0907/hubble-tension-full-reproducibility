# HTS67 run instructions

Place this folder in Windows Downloads as:

`${USER_DATA_ROOT}\Downloads\HTS67_RUN_PACKAGE`

The default shared cache is:

`${USER_DATA_ROOT}\Downloads\HTS_CHAIN_CACHE_STORE`

It must contain the retained `HTS63` cache. The exact HTS62 and HTS66_CORR result ZIPs may be anywhere below Downloads; the runner searches recursively and verifies their frozen SHA256 values.

## Preflight only

```bash
HTS67_PREFLIGHT_ONLY=1 bash ${USER_DATA_ROOT}/Downloads/HTS67_RUN_PACKAGE/run_hts67.sh
```

## Full run

```bash
bash ${USER_DATA_ROOT}/Downloads/HTS67_RUN_PACKAGE/run_hts67.sh
```

## Outputs

- `HTS67_RESULTS_FOR_REVIEW.zip`
- `HTS67_RESULTS_FOR_REVIEW.zip.sha256`
- `HTS67_RUN_LOG.txt`

## Optional overrides

```bash
export HTS_CACHE_STORE=/path/to/HTS_CHAIN_CACHE_STORE
export HTS67_HTS62_RESULTS_OVERRIDE=/path/to/HTS62_RESULTS_FOR_REVIEW.zip
export HTS67_HTS66_RESULTS_OVERRIDE=/path/to/HTS66_CORR_RESULTS_FOR_REVIEW.zip
```

No network acquisition is performed. Missing or ambiguous sources produce a HOLD package rather than an implicit substitution.
