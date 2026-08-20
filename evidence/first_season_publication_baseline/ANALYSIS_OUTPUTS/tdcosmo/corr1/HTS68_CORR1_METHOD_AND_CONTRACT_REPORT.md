# HTS68 CORR1 — method and contract correction report

Date: 2026-07-24 (UTC)  
Correction package: `HTS68_CORR1_METHOD_AND_CONTRACT_ONLY`  
Scope: method, execution contract, source identity, audit terminology, claim boundary, and canonical classification only

## 1. Outcome

HTS68 is retained as a useful scientific reconstruction of public posterior exports, but it is not treated as a prefrozen confirmatory test. Its corrected analysis mode is:

`POSTHOC_FORMALIZED_EXPLORATORY_PUBLIC_CHAIN_RECONSTRUCTION`

The corrected canonical interim classification is:

`PASS_TDCOSMO2025_PUBLIC_CHAIN_CONTRACT_AND_DESCRIPTIVE_NESTED_POSTERIOR_SHIFT_MAPPING_WITH_REQUIRED_METHOD_AND_CONTRACT_CORRECTION`

Short management classification:

`PASS_WITH_REQUIRED_CONTRACT_CORRECTION`

This correction does not retract the existing numerical outputs, reject HTS68, or overwrite the original artifacts. It changes the evidential status and permitted wording. The original result cannot be cited as equivalent to a prospectively frozen falsification test.

## 2. Work performed and prohibited work

This package was prepared from existing HTS68 method text, script constants, source-freeze records, and existing audit tables. No chain was opened or statistically reanalysed. No quantile, MCMC, likelihood, significance, or new scientific calculation was performed. No paper text was parsed, no source was downloaded, and no external search or additional exploration was performed.

The only mechanical computations performed for this correction were file hashing, patch syntax/application checks, manifest creation, and ZIP integrity checks.

## 3. Execution-contract timing

The available HTS68 artifacts do not prove that the execution contract, source identities, and central gates were fixed before the scientific results were generated. A contract written now therefore cannot retroactively establish prospective freezing.

Accordingly:

- previous treatment as `PREFROZEN_CONFIRMATORY_ANALYSIS`: not supported;
- corrected treatment: `POSTHOC_FORMALIZED_EXPLORATORY_PUBLIC_CHAIN_RECONSTRUCTION`;
- any future rerun may be called prospectively contracted only if its complete contract and hashes are fixed before any source is read for result generation.

## 4. Source-identity enforcement

The original script recorded source identity but did not compare all observed values against frozen expectations. `HTS68_SOURCE_ENFORCEMENT_PATCH.diff` changes the future-rerun script so that source identity is checked before any HDF5 file is opened.

The preflight gate requires exact agreement for:

- Git remote URL;
- Git commit SHA;
- the exact set of 28 expected public-chain filenames;
- SHA256 for every one of the 28 chain files;
- paper PDF SHA256;
- paper identifier;
- paper version;
- SHA256 for every other required input read by the script, including the independent Table 6 reference TSV.

Any missing value or mismatch produces `HOLD` and a nonzero exit before scientific result generation.

The original HTS68 records `arXiv:2506.03023` and the PDF SHA256, but do not record a paper version. Because this correction may not retrieve or inspect new source material, the corrected future contract intentionally records:

`PAPER_VERSION = UNRESOLVED_MUST_BE_FROZEN_BEFORE_RERUN`

The supplied patch therefore must HOLD until an authorized future preparation step independently establishes the version, updates the reference table, and updates its frozen SHA256 before execution.

## 5. Paper Table 6 statement

The original script did not extract Table 6 from the PDF. Its twelve reference rows were manually embedded in Python. Those values are now separated into `HTS68_PAPER_TABLE6_REFERENCE.tsv`, which records the release model ID, model label, paper table row, H0 median and interval-error magnitudes, paper identifier, paper version status, transcription method, and source location.

Permitted statement:

> 公開chainから算出済みの等重みquantileが、独立source tableへ転記されたpaper Table 6 reference valuesと一致した。

Not permitted:

> PDFから論文表を再現した。

The audit request used the term “weighted quantile.” The original HTS68 code used `numpy.quantile` and the existing chain-contract audit records no weight dataset. Calling that computation weighted would be unsupported. This subpoint is therefore partially accepted and corrected to “equal-weight quantile.” No quantiles were recomputed for CORR1.

## 6. Independent-audit status

`HTS68 independent alternate-implementation recomputation = NOT_DONE`

A rerun with the HTS68-generating script, a copied script, or the same implementation is not an independent alternate-implementation recomputation and must not be described as double audit.

The existing independent-audit bundle includes project-level integrity work and an HTS67 audit. It does not include an HTS68 alternate-implementation recomputation. CORR1 records that limitation and does not attempt a new recomputation.

## 7. Scientific claim boundary

The only permitted central descriptive wording is:

> 比較可能な公開nested posteriorでは、SLACS追加に関連するH0 medianおよびlambda_int medianの記述的shiftが、SL2S追加に関連するshiftより一貫して大きい。これは因果帰属、独立significance、systematicの同定を意味しない。

SLACSとSL2Sの同時追加には非加法的interactionがあり得る。したがって、単独追加の差を加算分解、因果寄与、または独立効果として解釈しない。

HTS68では、SLACSによるH0の制御、支配的原因、systematicの局在、Hubble tensionの説明、または因果componentの同定を表す断定を使用しない。

precisionをどのlayerが支配するかについて独立したformal gateはないため、precision controlを確定結論としない。

## 8. Formal PASS gate

CORR1では `SLACS-associated shift > SL2S-associated shift` をformal PASS gateへ追加しない。その位置づけを明示的に:

`descriptive observation outside the formal PASS gate`

とする。

Future-rerun formal PASS gateは次に限定する:

1. source-identity preflightが完全一致でPASSする;
2. 28 chainの構造契約がPASSする;
3. 等重みquantileと独立reference tableの丸め精度比較がPASSする。

記述的shiftの方向・大小、因果帰属、独立significance、precision control、Hubble tensionの説明はformal PASSの条件でも帰結でもない。

## 9. External-audit disposition

| Audit item | Disposition | Implementation |
|---:|---|---|
| 1. HTS68 position | ACCEPTED | Post-hoc formalized exploratory public-chain reconstructionへ再分類。 |
| 2. Source identity enforcement | ACCEPTED | URL、commit、28-file set、全chain hash、PDF hash、paper ID/version、必須input hashをHDF5 open前に強制。version未確定中はHOLD。 |
| 3. Paper-value wording and independent table | PARTIALLY_ACCEPTED | PDF抽出表現を撤回しreference TSVへ分離。元実装にweight処理がないため“weighted”のみ採用せず“equal-weight”へ修正。 |
| 4. Independent-audit definition | ACCEPTED | HTS68 alternate implementationを`NOT_DONE`と明記し、同一実装を独立監査から除外。 |
| 5. Scientific wording limitation | ACCEPTED | 指定された安全な記述的表現、因果・significance・systematic同定の禁止、interaction注意を採用。 |
| 6. Gate/claim alignment | ACCEPTED | SLACS対SL2S比較をformal PASS外のdescriptive observationと明記。precision control結論を不許可。 |
| 7. Canonical interim classification | ACCEPTED | 指定された長分類と短分類を採用。REJECT・全面撤回は行わない。 |
| 8. Permanent Work audit rules | ACCEPTED | `WORK_SCIENTIFIC_AUDIT_RULES_V1.md`に12規則を固定。 |
| 9. Correction-only artifact set | ACCEPTED | 指定7ファイル、SHA256 manifest、ZIPを別成果物として作成。既存HTS68は変更なし。 |

No item is classified `REJECTED_WITH_REASON`.

## 10. Limitations and next authorization boundary

CORR1 itself does not authorize a future chain rerun. Before a future rerun:

1. paper version must be independently established;
2. the version must be entered into both contract and reference TSV;
3. the updated TSV hash and all executable/input hashes must be frozen;
4. the contract must be approved before any scientific input is opened;
5. an independent alternate implementation, if desired, must be separately specified and implemented.

Until those conditions are met, future execution is `HOLD_SOURCE_IDENTITY_CONTRACT_INCOMPLETE`.
