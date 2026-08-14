# HOLD・再入場条件・season閉鎖ゲート

## season閉鎖判定

```text
BRANCH_01 = COMPLETE_WITH_SCOPE
BRANCH_02 = HOLD_SOURCE_INCOMPLETE_WITH_EXPLICIT_REENTRY_GATE
BRANCH_03A = CLOSED_WITH_SCOPE / MASTER_COMPLETE
BRANCH_03B = CLOSED_AT_PUBLIC_EVIDENCE_FRONTIER_WITH_SCOPE
ACTIVE_SCIENTIFIC_BRANCH = NONE
SECOND_SEASON = CLOSED_WITH_SCOPE_AND_REENTRY_GATES
```

HOLDを含むことはseason閉鎖を妨げない。ここでのHOLDは未整理な作業ではなく、「公開証拠が追加されない限り同じ問いを続行しても一意な科学検査へ進めない」という停止条件である。

## Branch 01再入場

25.7% comparatorに対応するold-side `gw_dark_O4a` posterior bytes、official registry、checksum、version identityが一意に公開された場合。

## Branch 02再入場

nominal BiasCor truth bytes、matched fit、pre/post vector、同一sample/orderのcovariance、実行manifest/configurationが公式・versioned・public recordとして固定された場合。

## Branch 03A再入場

公開H0DN側が特異共分散・零空間処理・生成モデルをmaterialに改訂した場合、または独立数値/統計レビューにより現在の限定claimを変更すべき新証拠が得られた場合。

## Branch 03B再入場

exact run manifest、base NML、FITRES/bias-correction output、row-level lineage、KCOR execution identity等、最終 `m_b_corr` rowまでを一意に結ぶ新しい公開実行来歴証拠が得られた場合。

## 禁止される自動再開

- 別のrankingを試すだけ
- 行削除・共分散縮小を新モデル根拠なしに試す
- 欠落posteriorやrun assetを推定置換する
- 既存HOLDを「未完だから」という理由だけで再実行する

次段で新しいトップレベル目的へ進む場合は、新seasonとして開始する。
