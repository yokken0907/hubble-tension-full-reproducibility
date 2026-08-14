# HTS43 canonicalization audit

## Decision

`PASS_CANONICALIZE_HTS43_CORR1`

The original HOLD was caused solely by an invalid count-based audit predicate for excluded non-chain files. The only discovered non-chain product, the baseline `minimum.txt`, was correctly excluded. The three variant archives did not contain equivalent products.

## Independent numerical verification

All response fields were recomputed from `HTS43_POSTERIOR_SUMMARY.tsv`.

- maximum delta arithmetic residual: 2.76e-10
- maximum baseline-width response residual: 4.89e-10
- maximum pooled-width response residual: 3.45e-10
- maximum width-ratio residual: 6.32e-12

No numerical correction was required.

## Scientific decision

The official ACT internal robustness variants move omega_c by at most 0.1159 baseline posterior SD and the frozen tangent center by at most 0.1140 baseline posterior SD. This branch is closed as a dominant explanation at the tested public-chain level.
