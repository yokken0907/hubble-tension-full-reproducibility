# 1st Season Master Reference Package — 最初に読む文書

## 目的

本パッケージは、ハッブルテンション検証 **1st seasonの科学監査状態**を、
後続season・別スレッド・将来の横断論文化で再利用できる形に固定した
マスター参照パッケージである。

対象は次の二系列に限定する。

1. `01_HTV_HTS_CORE_DEPENDENCY_AUDIT`
2. `02_TDCOSMO_BLIND_SENTINEL_PROJECT`

既存の投稿原稿、公開リポジトリ、公開準備・再構築作業記録は意図的に収録対象外とした。
本パッケージは論文パッケージではなく、**科学的経緯・結果・依存関係・HOLD・再開条件を固定する研究アンカー**である。

## 現在の位置付け

```text
FIRST_SEASON_STATUS = CLOSED_WITH_SCOPE
SEASON_ROLE = BROAD_DEPENDENCY_MAPPING_AND_TRACEABILITY_BASELINE
HUBBLE_TENSION_CAUSE = NOT_ESTABLISHED
CORRECTED_H0 = NOT_PROVIDED
NEW_PHYSICS = NOT_CLAIMED
```

1st seasonは、単一原因の同定ではなく、公開H0推論を構成する観測経路・
共分散・posterior geometry・source contract・再現可能性の地図を作り、
各枝を `PASS_WITH_SCOPE`、`CLOSED_WITH_SCOPE`、`FROZEN_OPEN`、`HOLD`
などへ分類した段階である。

## 推奨読解順

1. `01_FIRST_SEASON_SCIENTIFIC_SUMMARY_JA.md`
2. `03_BRANCH_STATUS_LEDGER.tsv`
3. `04_CLAIM_AND_NONCLAIM_LEDGER.tsv`
4. `06_DEPENDENCY_AND_SHARED_SOURCE_MAP_JA.md`
5. `07_HOLD_REENTRY_AND_OPEN_QUESTIONS_JA.md`
6. `08_CROSS_SEASON_COMPARISON_INTERFACE_JA.md`
7. 必要に応じて `canonical_reference_packages/`

## 正本関係

本マスターは元の1st season科学フォルダを置換しない。元データ・全Phase成果物の
正本は外部の1st seasonアーカイブであり、本パッケージはその状態を要約・索引化し、
重要な統合監査・閉鎖パッケージだけをバイト変更せず内包する。

再構成済み全体アーカイブのSHA-256：

`64048a39842bfed467e77db0f6c72348995001a4c2ca079367d24b25ac7d97ce`

## 使用上の禁止

- Phase数を独立証拠数として数えない。
- 同一公開vector・同一posterior endpointの座標変換を独立観測として合算しない。
- `FROZEN_OPEN`や`HOLD`を失敗・反証・異常発見と読み替えない。
- 診断ablationを修正H0または代替likelihoodとして扱わない。
- 後続seasonの知見で1st season当時のstatusを黙って書き換えない。
- 原因、新物理、ハッブルテンション解決を本パッケージから主張しない。
