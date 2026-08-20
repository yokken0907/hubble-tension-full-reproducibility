# HTS43 CORR1 limited correction order

## Trigger

The original numerical execution completed, but the audit check `non_numbered_products_excluded` required at least four excluded non-chain files:

`len(excluded_nonchain_table) >= 4`

This was logically incorrect. Exclusion is required only for non-chain products that actually exist. The baseline archive contained one `minimum.txt` product and it was excluded. The three robustness archives did not expose a corresponding non-numbered product.

## Correction

- Preserve every posterior summary and response value.
- Change the audit predicate to: every discovered non-numbered product is excluded from numerical loading.
- Record the exact primary-input configuration differences separately.
- Do not infer causal meaning from variant abbreviations or output labels.

## Numerical impact

None. No posterior row, burn-in, parameter value, coordinate, or response table was changed.
