# 元2nd seasonフォルダの完全性・整理事項

## 機械的監査

元投入：`2nd season.zip`

- SHA-256: `9cf896f1d37460ebb46f2082b57ea2085685ce6c75fe7046065510873e220a8c`
- bytes: `60717246`
- outer entries: 51（files 36 / directories 15）
- outer ZIP CRC: PASS
- nested ZIP: 16 / 16 CRC PASS
- outer `.sha256` sidecars: 15 / 15 PASS

4つの現行branch masterについて内部 `SHA256SUMS.txt` も全件PASS：

- B01: 44/44
- B02: 20/20
- B03A: 18/18 + master verifier PASS
- B03B: 33/33 + master verifier 80/80 PASS

historical pause snapshotも22/22内部checksum PASS。

## 整理事項1 — Phase1F delivery_verification.json

`08_SNIA_CROSS_SERIES_INPUT_DEPENDENCY_AUDIT_PHASE1F/delivery_verification.json` は修正前Phase1Fを指す。

- 記録hash: `751d983a188def2e96f899f18691c06e2356f98deb91982c444a8c7794f2dec1`
- 現行正式Phase1F hash: `137e8c6fe95426996eca6504f95995d8e522a20468b93e9c2844156a601d6b03`

これは科学破損ではない。03B masterは現行修正版を正本として内包済み。本masterにはこのstale delivery recordを取り込まない。物理フォルダから削除してよい。

## 整理事項2 — GWTC source-freeze V1

`GWTC45_H0_METRIC_PROVENANCE_SOURCE_FREEZE_V1.zip` は外側sidecarを持たないが、CORR1とBranch01 masterにより履歴artifactとしてidentityが固定されている。現行科学正本は `V1_CORR1` とBranch01 master。V1を削除する必要はないが、現行入力として使わない。

## 整理事項3 — 2026-07-26 pause snapshot

`90_HISTORICAL_PAUSE_SNAPSHOT_2026-07-26` は当時Branch03が未選定だった状態を保存するhistorical snapshotであり、現在状態ではない。hash/CRCは正常。保存してよいが、current statusとして参照しない。
