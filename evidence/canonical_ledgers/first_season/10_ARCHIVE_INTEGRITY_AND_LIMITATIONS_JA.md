# アーカイブ完全性と検証範囲

## 本マスター作成時の科学scope

対象：`01_HTV_HTS_CORE_DEPENDENCY_AUDIT` と `02_TDCOSMO_BLIND_SENTINEL_PROJECT`

```text
files                  = 1090
bytes                  = 760551435
ZIP archives           = 365
ZIP CRC pass           = 365/365
external sidecars      = 443
sidecar pass           = 442/443
sidecar mismatch       = 1
```

唯一の外側sidecar不一致は次である。

`01_HTV_HTS_CORE_DEPENDENCY_AUDIT/03_キャッシュ関連/HTS_CHAIN_CACHE_STORE_INDEX_PACKAGE.zip.sha256`

現ZIP SHA-256：`55a1c898999524f515e8baa60f1a655fd4e5722287a742a4fc90a91dfec0672c`

sidecar記載：`a2484df1143bc139b56e2523d4c3fb49d879b4fdba37d51eb4ba820254a430bd`

ZIP CRCはPASSし、内部のindex/guide checksumは整合する。科学結果の破損とは分類せず、
現在byte列と旧外側sidecarの不一致を可視化したarchive hygiene issueとして保持する。

## 検証したもの

- 全365 science-scope ZIPのCRC
- 全443外側sidecarの対象byte列照合
- 全science-scope fileのSHA-256 inventory
- 内包したcanonical reference packageのbyte identity
- master manifestと決定論的ZIP生成

## 実行していないもの

- HTV/HTS全Phaseの科学計算を最初から再実行
- 全外部sourceの再取得
- chain/MCMC/likelihoodの新規計算
- canonical scientific classificationの変更

本マスターは、既存正式成果物を索引・統合・固定したものである。
