# Hubble Tension — 2nd Season Master Reference Package v1.0.0

## 目的

このパッケージは、2nd seasonで実施された4つの科学枝を、後続シーズン・横断監査・新規論文作成から一意に参照できる**閉鎖基準面**として固定する。

```text
SECOND_SEASON_STATUS = CLOSED_WITH_SCOPE_AND_REENTRY_GATES
ACTIVE_SCIENTIFIC_BRANCH = NONE
HUBBLE_TENSION_RESOLUTION = NOT_ESTABLISHED
CORRECTED_H0 = NOT_PROVIDED
NEW_PHYSICS = NOT_ESTABLISHED
```

2nd seasonの閉鎖は「ハッブルテンション問題全体の終了」を意味しない。各枝が、公開証拠で到達可能な範囲まで完了したか、明示的な再入場条件を伴うHOLDへ到達したことを意味する。

## 正本として内包する枝マスター

- B01 GWTC-4/5 standard-siren posterior traceability
- B02 Pantheon+ BBC truth-level closure source readiness
- B03A H0DN singular covariance / pseudoinverse audit
- B03B H0DN SN Ia same-CID residual-deficit audit

各枝マスターは元バイトを変更せず内包している。

## 推奨読解順

1. `01_SECOND_SEASON_SCIENTIFIC_SUMMARY_JA.md`
2. `02_BRANCH_STATUS_REGISTRY.tsv`
3. `03_CLAIM_AND_NONCLAIM_LEDGER.tsv`
4. `04_KEY_NUMERICAL_RESULTS.tsv`
5. `05_HOLD_REENTRY_AND_SEASON_CLOSURE_GATES_JA.md`
6. `06_CROSS_SEASON_COMPARISON_INTERFACE_JA.md`
7. 必要な枝の `canonical_branch_masters/` を開く

## 元2nd seasonフォルダ

元投入ZIP：`2nd season.zip`  
SHA-256：`9cf896f1d37460ebb46f2082b57ea2085685ce6c75fe7046065510873e220a8c`

このmasterは元フォルダ全体の単純複製ではない。後続比較に必要な**現行正本4枝**を内包し、旧pause snapshotや重複作業物はidentityだけを記録する。
