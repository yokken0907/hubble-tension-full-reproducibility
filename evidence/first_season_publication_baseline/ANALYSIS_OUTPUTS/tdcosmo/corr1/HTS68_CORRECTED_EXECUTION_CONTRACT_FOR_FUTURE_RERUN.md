# HTS68 corrected execution contract for a future rerun

Contract ID: `HTS68_CORRECTED_EXECUTION_CONTRACT_FOR_FUTURE_RERUN`  
Contract version: `CORR1`  
Prepared: 2026-07-24 (UTC)  
Current authorization: `HOLD_SOURCE_IDENTITY_CONTRACT_INCOMPLETE`

## 1. Status and timing

This contract is for a possible future rerun only. It was prepared after the original HTS68 results and is therefore post-hoc with respect to those results. It cannot retroactively convert original HTS68 into a prefrozen confirmatory analysis.

Original HTS68 analysis mode:

`POSTHOC_FORMALIZED_EXPLORATORY_PUBLIC_CHAIN_RECONSTRUCTION`

A future run may use a prospective label only if this contract, all expected hashes, all gates, the exact script revision, and the paper version are frozen and approved before any scientific input is opened.

## 2. Authorized scope

If separately authorized after the HOLD is resolved, the future script may:

- verify source identities and required-input hashes;
- open the frozen 28 public HDF5 exports only after source gate PASS;
- run the existing structural checks;
- calculate the existing equal-weight marginal quantiles;
- compare those quantiles with the frozen independent Table 6 reference TSV;
- produce the existing descriptive nested-posterior shift map.

It may not, under this contract:

- retrieve or substitute sources;
- add files, models, priors, chains, datasets, or parameter searches;
- run MCMC or likelihood code;
- calculate an independent significance;
- infer causal attribution or systematic localization;
- claim that any layer controls precision;
- describe the same implementation as an independent recomputation.

## 3. Frozen source identity

| Identity element | Expected value | Current state |
|---|---|---|
| Git remote URL | `https://github.com/TDCOSMO/TDCOSMO2025_public.git` | frozen |
| Git commit SHA | `d7f38db341f68be1df0d9ac1fc528c45113f94cf` | frozen |
| Public-chain file set | exact 28-file set in §4 | frozen |
| Public-chain SHA256 | one exact hash per file in §4 | frozen |
| Paper identifier | `arXiv:2506.03023` | frozen |
| Paper version | `UNRESOLVED_MUST_BE_FROZEN_BEFORE_RERUN` | unresolved; mandatory HOLD |
| Paper PDF SHA256 | `e94a728864f3afe9cc7672b97918ff366863a55df183ba116c3ceff526a7f5c7` | frozen |
| Paper Table 6 reference TSV SHA256 | `1cd322aa9e1131bd6a81702e1b81d3afb49f0388b59825983573e05d260d00ed` | frozen for CORR1 unresolved-version table; must change when version is resolved |
| Repository `README.md` SHA256 | `20ba4944985c1435b1b111f713a58968e8468c430022fec11ab526797b6e89f5` | frozen |
| Repository `likelihood_sampling.py` SHA256 | `45825cbe3104a8bbd73f1001c6ede7fa08105e4c26e09486115639a3855b5a42` | frozen |

The paper-version sentinel is not a wildcard. It is an explicit unresolved state and must force HOLD. After independent version identification, the contract, TSV rows, patch constant, and TSV SHA256 must be updated together before approval.

## 4. Exact 28-file chain set and hashes

| Filename | Expected SHA256 |
|---|---|
| `LambdaCDM1a.h5` | `c46bf18d72b03835c1c1cc9bc5b38a752e3e3185d5beaf3833fe750e6c6ef161` |
| `LambdaCDM1b.h5` | `5a04e219bbabfc8d16b3448731a35d592d4bd132e30ddf75fb8dde6659ab2acd` |
| `LambdaCDM1c.h5` | `13bbdbc41758389cec1c21e0ee649a48cac82a6b38ce2052310cea9ba99841bf` |
| `LambdaCDM1d.h5` | `14a7e790fd91386cd97cb26690b5a9fc8269488fbb440890ba3e3d97c361d7b8` |
| `LambdaCDM2a.h5` | `2d4dd6ea2370f190fcb8a695d003b3337f7c0f0b6d4d8f9f73d1908bb8d57be7` |
| `LambdaCDM2b.h5` | `93387730574ff82d5c03326eb1e69bf97d1c783221d19842383755376aabbea9` |
| `LambdaCDM2c.h5` | `808dc197fcc7fa695f6f27fcfa87964b99510dfc03e12af71e26fcd606cb7296` |
| `LambdaCDM2d.h5` | `e62c0fb6877809efb36ea415e40566a676a93d76a7bcc6152ee8f114ae6b4ee6` |
| `LambdaCDM3a.h5` | `ed7e069c4c5f2b33552649dd508a43c900da831e000475dfd0486ec1d0768bb6` |
| `LambdaCDM3b.h5` | `4a745a04110f4443766449c438d0ca129d63cd0ce08ab32053b277e030139435` |
| `ULambdaCDM1.h5` | `96f96ca0c1eb2ad8b7fd1bba0f7ea7c945179c3e553d03322eeee0a8ec632af3` |
| `ULambdaCDM2.h5` | `a4d8f3f08e7d59841f5272e705a5216269473d2f2504672cf4640d35153c0a9c` |
| `ULambdaCDM3.h5` | `4daf0cc6d276aefb3a5e1e45f9a9d0346b1ad163b00377bf82d7bd18b32f2022` |
| `ULambdaCDM4.h5` | `f5ffc0a6ccd47ee81c81bba66eb61ea6c58db4aed15801622152e6b584323626` |
| `UoLambdaCDM.h5` | `caff596a1396d7e34b4c99b9231d7a65c5a5e3ccad52b80d494001289341fd18` |
| `UwCDM.h5` | `4eda5aaa14ea4acdcbe53e75d37614771e10f47e69a3bd2d5f7c9e878c35710c` |
| `Uw_0w_aCDM.h5` | `657d93b7c0fa4df2eb8e1b374c9061964df1d7e26f166b13794d241178fb316c` |
| `Uw_phiCDM.h5` | `27dc48414a1b429ee61f084f7d53de2f782848c37b2f43ddcdde5948d2cb6111` |
| `oLambdaCDM.h5` | `d1d4ce10c4bd0fcf6f31328679a0b6b0c27bbb9b9e6abed36efb0dfc7bab908a` |
| `wCDM1.h5` | `b277a3bf5da1983c4852cfd6f63efe8a0e211b32b163d8651a9492abb98e348a` |
| `wCDM2.h5` | `07d44238d213ed7237cca6ca8fa9d42c8644936b78156838fc8940d95390e2fa` |
| `wCDM3.h5` | `2ecfa671db610a9ed0c06026a44fde0e75ca055e0647b0a6f24c3f7983d32040` |
| `w_0w_aCDM1.h5` | `1b41f39c3f4b04cfdc1713108879c2a4e9df342c4f1467cd2ec6fe58d44ef575` |
| `w_0w_aCDM2.h5` | `2ab389b10986930a8b8b7953c35f479242a67d35f995d6e04ade2ce52118cff8` |
| `w_0w_aCDM3.h5` | `ac2f67dd93bb495c59f76a63361d575bd1befb87604e3ce1543434ee4f68e473` |
| `w_0w_aCDM4.h5` | `bf8e555f08e886763a1e0aef99a5d55b9d0dd6c16f71d8421d80f584d429e7ee` |
| `w_phiCDM1.h5` | `61819e1803e714047c7e31cc1ceb9d8cea3836c8fa67d7e0ecdeb4b1eed0c9ef` |
| `w_phiCDM2.h5` | `7526a5dc3b8430e77a0833572db21b497a889c634636f6710ed2acb30721288c` |

No extra `.h5` file is permitted. Missing, extra, renamed, or hash-mismatched files cause HOLD before HDF5 open.

## 5. Required reference-table contract

Required file: `HTS68_PAPER_TABLE6_REFERENCE.tsv`

Required columns:

- `release_model_id`
- `model_label`
- `paper_table_row`
- `h0_median`
- `h0_lower_error_magnitude`
- `h0_upper_error_magnitude`
- `paper_identifier`
- `paper_version`
- `transcription_method`
- `source_location`

Required row set: exactly the twelve release IDs frozen by the patch. All rows must carry the expected paper identifier and version. The table is an independently stored transcription source; it is not evidence of automated PDF extraction.

## 6. Ordered gates

### Gate G0 — contract completeness

PASS only if:

- paper version is a resolved literal version, not the unresolved sentinel;
- script, contract, reference table, and required-input hashes have been frozen before execution;
- approval time precedes the first source read for result generation.

Otherwise: `HOLD_CONTRACT_INCOMPLETE`.

### Gate G1 — source identity, before HDF5 open

PASS only if every value in §§3–5 matches exactly. The script must write the expected and actual identities to `HTS68_SOURCE_IDENTITY_GATE.json`.

Any mismatch or missing value: `HOLD_SOURCE_IDENTITY_MISMATCH`, nonzero exit, and no HDF5 open.

### Gate G2 — chain structural contract

After G1 PASS only, apply the pre-existing structural checks to all 28 exports. Any failure: `HOLD_CHAIN_CONTRACT_FAILURE`.

### Gate G3 — independent-reference comparison

After G1 and G2 PASS only, calculate the pre-existing equal-weight 16/50/84-percentile summaries and compare the rounded values with the independent TSV. Any mismatch: `HOLD_PAPER_REFERENCE_MATCH_FAILURE`.

This gate does not claim PDF table extraction.

### Gate G4 — descriptive shift map

Generate the pre-existing nested-posterior descriptive mapping. The observation that SLACS-associated shifts exceed SL2S-associated shifts is:

`descriptive observation outside the formal PASS gate`

It does not alter PASS/HOLD classification.

## 7. Formal outcome logic

Formal PASS requires `G0 && G1 && G2 && G3`.

On PASS, classification:

`PASS_TDCOSMO2025_PUBLIC_CHAIN_CONTRACT_AND_DESCRIPTIVE_NESTED_POSTERIOR_SHIFT_MAPPING_WITH_REQUIRED_METHOD_AND_CONTRACT_CORRECTION`

Short classification:

`PASS_WITH_REQUIRED_CONTRACT_CORRECTION`

G4 is output mapping, not a claim gate. No formal gate establishes a precision-controlling layer.

## 8. Required reporting language

Permitted:

> 比較可能な公開nested posteriorでは、SLACS追加に関連するH0 medianおよびlambda_int medianの記述的shiftが、SL2S追加に関連するshiftより一貫して大きい。これは因果帰属、独立significance、systematicの同定を意味しない。

Required interaction qualification:

> SLACSとSL2Sの同時追加には非加法的interactionがあり得る。

Required independent-audit status:

`HTS68 independent alternate-implementation recomputation = NOT_DONE`

Without a separately validated gate, reporting must not assert SLACS control of H0, a dominant cause, localization of a systematic, an explanation of the Hubble tension, identification of a causal component, or control of precision by any layer.

## 9. Independent implementation

The generating script, a copy, a refactor preserving the same algorithm, or the same author checking the same output is not an independent alternate implementation. A separate audit requires independently written computation logic, separately frozen inputs and tolerances, and a comparison protocol fixed before results are viewed.

## 10. Change control

Any contract amendment must record:

- field changed;
- previous value;
- new value;
- reason;
- timestamp;
- whether any result had already been generated;
- whether the run must be reclassified as post-hoc.

No mismatch may be waived inside a successful run. A corrected source requires a new contract version and new hashes.
