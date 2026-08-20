# HTS58 canonicalization audit

`PASS_BIDIRECTIONAL_EMPIRICAL_OVERLAP_AND_ASYMMETRY_AUDIT`

Integrity:
- outer ZIP SHA256: `0404dda2488a448a49c64749a47a036e940ae02ff80f73447b6583819b91145c`
- ZIP CRC: PASS
- internal SHA256 manifest: PASS
- independent raw-chain bidirectional reconstruction: exact

Primary 30% examples:
- ACT_TO_FULL_FIXED: forward z 1.450804, reverse z 1.804363, 68% IoU 0.099123, 95% IoU 0.434582, rank separation 0.742838.
- ORIGINAL_TO_FIXED_RELEASE: forward z 0.037337, reverse z 0.053749, 68% IoU 0.959204, 95% IoU 0.984860.

Boundary: correlated release-posterior overlap only; not independent tension significance.
