# DESI DR2 BAO Gaussian-fit reproduction contract

This directory records the identified implementation, exact external-input hashes, tested environment, run command, expected output, and validation utilities for the two-parameter flat-LambdaCDM DESI DR2 BAO Gaussian fit reported in the manuscript.

## Reproduction status

`REEXECUTABLE_WITH_EXTERNAL_FIXED_INPUTS`

The small third-party mean vector and covariance are not redistributed here. Obtain the named public files and verify their byte size and SHA-256 using `verify_inputs.py` before execution. The historical source-repository commit was not fixed; the hashes, rather than an inferred commit, define the accepted inputs.

## Boundary

This reproduces only the 13-component Gaussian BAO fit for `(Omega_m, H0 r_d)`. It does not reproduce the DESI collaboration likelihood stack, chains, Boltzmann-code calculations, BBN calibration, or any new posterior analysis.

## Files

- `run_fit.py`: identified implementation adapted from the preserved HTV05 code for explicit file arguments and PTE output.
- `INPUT_MANIFEST.tsv`: public locators, byte sizes, and fixed hashes.
- `ENVIRONMENT.md` and `requirements.txt`: tested compatible environment.
- `RUN_COMMAND.txt`: invocation.
- `EXPECTED_OUTPUT.json`: frozen expected values.
- `verify_inputs.py` and `verify_expected_output.py`: integrity and result checks.
