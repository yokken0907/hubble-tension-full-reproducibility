# HTS64 canonicalization audit

`PASS_WITHIN_BLOCK_REPARAMETERIZATION_INVARIANCE_AUDIT`

Integrity:
- outer ZIP SHA256: `64eedb9fc07abfcd4e2c6f365c403f4d953d674e4a4554751e9ffc27406ab925`
- ZIP CRC: PASS
- internal SHA256 manifest: 28/28 PASS
- independent raw-chain and all-LOO reconstruction: PASS
- maximum total-distance invariance error: `1.14e-13`
- maximum fixed-block share invariance error: `1.33e-15`

Primary findings:
- all 14 directed edges are block-robust but variable-allocation basis-sensitive
- maximum top-coordinate share range across rotations: `0.465437`
- maximum effective-coordinate-count range: `1.921046`
- all support, numerical, LOO and burn-in gates pass
