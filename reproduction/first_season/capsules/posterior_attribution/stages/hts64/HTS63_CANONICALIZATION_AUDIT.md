# HTS63 canonicalization audit

`PASS_EXACT_VARIABLE_SHAPLEY_AND_OWEN_COALITION_AUDIT`

Integrity:
- outer ZIP SHA256: `66edffe6d416957a5ae75f5fc258b784bde0a76edf5feeacd54f328a38a406b7`
- ZIP CRC: PASS
- internal SHA256 manifest: 27/27 PASS
- independent raw-chain and all-LOO reconstruction: PASS
- maximum allocation closure/reconciliation error: `7.11e-15`

Primary classification counts:
- N_S_DOMINANT: 6
- OMEGA_B_DOMINANT: 1
- ORDER_SENSITIVE: 4
- COALITION_SENSITIVE: 1
- MIXED_VARIABLE: 2

The strongest direct allocations are PR4-to-fixed forward n_s share 0.939 and
ACT-to-fixed reverse omega_b share 0.779. BASE-to-ACT forward changes its top coordinate
from n_s under unrestricted Shapley to omega_b under Owen allocation.
