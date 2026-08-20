# HTS62 canonicalization audit

`PASS_FIXED_BLOCK_SHAPLEY_AND_ORDER_SENSITIVITY_AUDIT`

Integrity:
- outer ZIP SHA256: `bc6557b0b6eae13b2553ecbf39ad17c6c6e7c7bf7027c2de2f97827cdbaad936`
- ZIP CRC: PASS
- internal SHA256 manifest: 27/27 PASS
- independent raw-chain and all-LOO reconstruction: PASS
- maximum Shapley closure error: `3.55e-15`

Primary findings:
- BARYON_TILT share is about 0.987–0.988 for both PR4-to-fixed directions and
  ACT-to-fixed reverse.
- original-to-fixed is TAU_AMPLITUDE-dominant: forward 0.722 and reverse 0.606.
- BASE-to-ACT and several BASE-forward edges are order-sensitive, with order-sensitivity
  fractions up to 0.519.
- maximum block canonical correlation is 0.621.
- all support, numerical, LOO and burn-in gates pass.

The block labels are fixed coordinate groupings, not causal sectors.
