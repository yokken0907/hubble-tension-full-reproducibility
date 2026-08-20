# Hubble Tension 1st × 2nd Season 横断監査 — 最初に読む文書

## 位置付け

本パッケージは、次の二つのseason masterを正本とした非遡及的な横断監査である。

1. `HUBBLE_TENSION_FIRST_SEASON_MASTER_REFERENCE_PACKAGE_v1.0.0.zip`  
   SHA-256: `3e6df9f557485de1bb21c54bb129af78943e8e5d08da036e648d251dd952663c`
2. `HUBBLE_TENSION_SECOND_SEASON_MASTER_REFERENCE_PACKAGE_v1.0.0.zip`  
   SHA-256: `cc15c96a45865f22fcd13c2ef03c8cccc39af8fa6dcace4a25f229d07e964940`

外部資料は追加していない。master直下の正式ledgerと、masterに内包されたcanonical packageだけを証拠集合として用いた。

## 正式な横断判定

```text
CROSS_SEASON_AUDIT_STATUS = COMPLETE_WITH_SCOPE
FIRST_SEASON_MAP = RETAINED_AS_DEPENDENCY_AND_TRACEABILITY_MAP
TRUE_CROSS_SEASON_SCIENTIFIC_CONTRADICTIONS = 0
MATERIAL_LATER_QUALIFICATIONS = PRESENT
CORRECTED_H0 = NOT_ESTABLISHED
HUBBLE_TENSION_CAUSE = NOT_ESTABLISHED
HUBBLE_TENSION_RESOLUTION = NOT_ESTABLISHED
NEW_PHYSICS = NOT_ESTABLISHED
```

1st seasonの科学地図は全体として維持される。ただし「広域の依存・traceability地図」としての有効性であり、全pipeline・全表現・全生成過程のvalidationを意味しない。2nd seasonは特にH0DNとSN Iaで、固定規約内の再現可能性に二つの重要な限定を追加した。

- 固定表現・固定solver内の数値安定性は、一般の同値表現に対する不変性を保証しない。
- H0 parameter inferenceに厳密十分な圧縮でも、残差・適合度・生成モデル診断には不十分になり得る。

## 推奨読解順

1. `REPORT_JA.md`
2. `METHOD_AND_EVIDENCE_MODEL_JA.md`
3. `CROSS_SEASON_CLAIM_CROSSWALK.tsv`
4. `CONTRADICTION_AND_QUALIFICATION_LEDGER.tsv`
5. `EVIDENCE_STATE_MATRIX.tsv`
6. `NEW_CROSS_SEASON_PROPOSITIONS.tsv`
7. `UNRESOLVED_PRIORITIES_AND_REENTRY.tsv`
8. `PUBLICATION_ARCHITECTURE_JA.md`
9. `EVIDENCE_LOCATOR.tsv`

## 重要な読み方

- `original_status`は当時の正式判定であり、後続結果で上書きしない。
- `later_qualification`は後から得た限定・分解・新証拠である。
- `PASS`は各contract内のPASSであり、他の証拠軸へ自動昇格しない。
- `HOLD`は誤り・陰性結果・異常の同義語ではない。
- 同一sourceの再表現や内部AI再実装を、独立観測または外部独立再現として数えない。

## 正本を同梱しない理由

本パッケージは二つのseason masterを再配布せず、ファイル名、SHA-256、byte数、内部証拠位置を固定する。元masterが利用可能な環境では、`scripts/verify_against_masters.py`でhash、ZIP CRC、claim ID、主要数値の横断整合性を再検査できる。
