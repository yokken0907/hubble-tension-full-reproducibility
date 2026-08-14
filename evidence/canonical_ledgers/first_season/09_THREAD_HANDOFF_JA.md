# 新規スレッド引継ぎ文書

あなたはハッブルテンション検証1st seasonの科学監査状態を引き継ぐ。

## 必ず保持する状態

- 1st seasonは広域依存関係・traceability mapとして `CLOSED_WITH_SCOPE`。
- 単一原因、修正H0、新物理、テンション解決は確立していない。
- PASSは各凍結contract内のPASSであり、全pipeline・全systematicsの証明ではない。
- HOLD/FROZEN_OPENは、必要sourceまたは独立性条件が満たされていない状態。
- 既存Phaseを独立証拠数として加算しない。
- TDCOSMO別実装はoutput-level traceabilityであり、外部独立replicationではない。

## 最初に読むもの

1. `00_READ_FIRST_JA.md`
2. `01_FIRST_SEASON_SCIENTIFIC_SUMMARY_JA.md`
3. `03_BRANCH_STATUS_LEDGER.tsv`
4. `04_CLAIM_AND_NONCLAIM_LEDGER.tsv`
5. `08_CROSS_SEASON_COMPARISON_INTERFACE_JA.md`

## 後続seasonとの作業

突き合わせ時は、1st season側のclaim IDとcross-season anchor IDを保持し、後続season側の
結果を別列へ追加する。過去statusを黙って再分類しない。

## 許可されない進行

- source triggerなしのFROZEN_OPEN再実行
- arbitrary metric/basis grid
- diagnostic ablationからの修正H0
- survey・装置・modelの原因順位付け
- 新物理またはテンション解決の主張
