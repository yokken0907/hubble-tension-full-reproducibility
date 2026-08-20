# HTS60 canonicalization audit

`PASS_CONDITIONAL_4D_EIGENMODE_LOCALIZATION_AUDIT`

Integrity:
- outer ZIP SHA256: `32249ddf93aeada9defc689d4f270fa2da2cf68a82ba8a014bea39a6e250d617`
- ZIP CRC: PASS
- internal SHA256 manifest: 28/28 PASS
- independent reconstruction: PASS
- maximum mode decomposition closure error: `1.28e-13`

Primary diagnostics:
- minimum conditional eigenvalue: `0.0402961`
- maximum conditional condition number: `48.6990`
- maximum LOO conditional-distance drift: `0.103376`
- maximum LOO top-one fraction drift: `0.061101`
- maximum burn conditional-distance change: `0.172649`
- maximum burn top-one fraction change: `0.040266`

Important boundary:
SPT_PR4 conditional eigenvalues 2 and 3 are `0.972280` and `1.027828`. Their individual eigenvectors can rotate inside a nearly degenerate two-dimensional subspace. HTS60 does not establish unique physical identities for those two labels.
