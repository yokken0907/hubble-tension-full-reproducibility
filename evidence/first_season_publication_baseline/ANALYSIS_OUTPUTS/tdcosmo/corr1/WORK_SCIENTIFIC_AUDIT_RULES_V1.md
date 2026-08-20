# Work scientific audit rules V1

Version: `V1`  
Effective: 2026-07-24 (UTC)  
Scope: all scientific verification work in this Project

This file must be read before a new scientific verification begins. If a later project rule conflicts with this version, the conflict and superseding authority must be recorded before work starts.

## Mandatory rules

1. **Pre-result freeze.** The execution contract, source identity, and principal gates must be fixed before result generation.

2. **Post-hoc labeling.** A contract created or materially changed after results exist must be labeled post-hoc and must not be presented as prospectively frozen.

3. **Code-enforced source freeze.** A source-freeze declaration is insufficient by itself. Code must compare observed identifiers and hashes with frozen expected values and must HOLD or FAIL on missing values or mismatches before scientific calculation.

4. **Claim/gate alignment.** The central scientific claim and the formal classification gate must match. A central comparison outside the gate must be explicitly labeled descriptive and outside the formal PASS gate.

5. **Independent-audit definition.** Confirmation by the same code, the same implementation, a copy or superficial refactor, or the same generating workflow must not be called an independent audit or independent recomputation.

6. **Inference separation.** Descriptive posterior shift, statistical association, independent significance, and causal attribution are distinct levels and must be reported separately.

7. **Restricted causal/control terms.** `dominant`, `controls`, and `localized cause` must not be used unless a corresponding prospectively specified validation and formal gate support the term.

8. **Independent paper-reference table.** Paper reference values must not be embedded directly in analysis code. They must be stored in an independently hashed table with paper identifier, version, row/location, and transcription or extraction method.

9. **Visible failures and omissions.** FAIL, HOLD, missing inputs, and audits not performed must remain visible in successful artifacts and summaries; they must not be hidden by an overall PASS label.

10. **Effort is not evidence.** Runtime duration, number of generated files, compute volume, and length of a report are not scientific progress or validation evidence.

11. **No self-issued final certificate.** A generating workflow must not issue a final independent certificate for its own result. Before external audit, success classifications are provisional with respect to independent validation.

12. **Classification change record.** Any change to a canonical classification must record the previous classification, the new classification, the reason, and whether numerical artifacts were changed, retained, or withdrawn.

## Minimum pre-execution record

Before result generation, record:

- question and permitted claim;
- prohibited interpretations;
- exact code revision;
- exact source locators, identifiers, versions, and hashes;
- exact expected file set;
- required-input hashes;
- formal gates and thresholds;
- outcome logic;
- independence status;
- approval timestamp.

If any required field is unresolved, execution status is `HOLD_CONTRACT_INCOMPLETE`.

## Minimum result record

Every scientific result package must expose:

- source-identity gate output;
- all formal gate outcomes;
- failures, HOLDs, and missing audits;
- classification and claim boundary;
- whether the execution contract was pre-result or post-hoc;
- whether an independent alternate implementation was completed.

## Amendment rule

A future revision must be a new versioned file. It must preserve a change log from V1 and may not silently rewrite the meaning of a prior classification.
