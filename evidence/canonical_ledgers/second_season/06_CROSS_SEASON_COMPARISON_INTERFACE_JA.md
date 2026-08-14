# 1st × 2nd season 横断比較インターフェース

この文書は横断監査そのものではなく、次段で比較すべきanchorを固定する。

外部peer master：

- `HUBBLE_TENSION_FIRST_SEASON_MASTER_REFERENCE_PACKAGE_v1.0.0.zip`
- SHA-256: `3e6df9f557485de1bb21c54bb129af78943e8e5d08da036e648d251dd952663c`
- 本2nd-season masterには非内包

## 推奨comparison anchors

### X01 GWTC
1st seasonで公開posterior入力不足として残ったGWTC状態と、B01のheadline output reproduction PASS / published-metric pair provenance HOLDを照合する。

### X02 BBC truth closure
1st seasonのBBC truth-level closure未完了境界と、B02のsource-readiness `HOLD_SOURCE_INCOMPLETE` を照合する。

### X03 H0DN numerical stability
1st seasonの固定表現内cutoff/solver stabilityと、B03Aのgeneral non-orthogonal representation non-invariance / support inconsistencyを照合する。

### X04 SN compression and diagnostics
1st seasonのSN/BBC algebraic localizationと、B03Bの「H0にはexact sufficientな圧縮でもresidual diagnostic情報を失う」結果を照合する。

### X05 reproducibility layers
候補仮説：

1. output/numerical reproduction
2. mathematical/representation invariance
3. generative/execution lineage reproduction

この三層が異なることを両seasonの正式claim ledgerから独立に検証する。現時点では横断新規claimとして確定しない。

## 横断監査で守ること

- 後のseason知識で過去seasonの元判定を上書きしない。
- `original_status` と `later_qualification` を分離する。
- headline numberの再現をpipeline/generative validationへ昇格させない。
- 2nd seasonからcorrected H0やtension resolutionを導かない。
