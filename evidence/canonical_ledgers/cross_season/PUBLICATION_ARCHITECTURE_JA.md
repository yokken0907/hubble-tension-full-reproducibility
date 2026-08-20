# 論文化構成の評価

## 推奨：総論1本＋技術論文2本

証拠構造から最も自然なのは、一冊の巨大統合論文ではなく、次の三単位である。

### Paper A — 横断総論／方法論

中心問い：

> 公開H0推論のどの部分が再現可能で、identity、output、representation、diagnostic、executed lineage、generative validityのどこで閉じないか。

主要材料：

- `CROSS_SEASON_CLAIM_CROSSWALK.tsv`
- `EVIDENCE_STATE_MATRIX.tsv`
- GWTC、TDCOSMO、BBC、H0DN、SN Iaのbounded case study
- shared-sourceとnon-independenceの地図

中心claim：再現性は二値でも単純三層でもなく、六軸の証拠状態として記録すべきである。複数の監査対象でoutput PASSと上位軸のFAIL/HOLDが共存した。

非claim：corrected H0、tension resolution、pipeline error、new physics。

### Paper B — H0DN特異共分散

中心問い：

> 公開H0DNの特異GLS/MP解は、同値表現に対して不変か。また公開rounded dataは退化Gaussianの厳密なsupportに入るか。

主結果：

- baseline再現
- rank 183 / nullity 72
- cutoff・permutation安定性
- exact non-orthogonal row scalingで`ΔH0=-0.052445422611000936`
- `||P0 y||2=0.1887490826897376 mag`
- 37 host × 3 anchor interaction subspaceへの局在
- full-rank variance modelは存在例に限定

投稿前の最重要補強は、別研究者・別言語・専門家による外部確認である。

### Paper C — SN Ia圧縮・残差・来歴

中心問い：

> H0にexact sufficientなSN scalar compressionは何を失い、失われた残差はどこへ局在し、公開来歴はどこまで閉じるか。

主結果：

- scalar/full parameter equivalence
- omitted residual chi-square `206.76063643732414`
- 39 same-name contrast dfへの局在
- 277/277 row mappingと76,729/76,729 covariance equality
- low flag persists through STATONLY
- 69/69 compatible public input candidates with final ancestry unestablished
- 0/48 byte-exact OBS reuse、4/48 isolated numeric compatibility

Phase 1D–1Fの詳細表はsupplementへ置き、本文は問いの鎖とclaim boundaryを優先する。

## GWTC・TDCOSMO・BBCの扱い

これらはPaper Aのcase studyとして最も機能する。

- GWTC：headline output reproductionとhistorical comparator provenanceの分離
- TDCOSMO：内部alternate implementationとoriginating likelihood reproductionの分離
- BBC：downstream algebraic localizationとtruth-level closure readinessの分離

単独公開する場合は短いprovenance/traceability noteに限定し、新しいH0論文として設計しない。

## 一本の巨大統合論文を推奨しない理由

1. BAO、CMB、DESI、lensing、GW、SN、linear algebraは方法が異質である。
2. 1st seasonの多くは2nd seasonで再検査されていない。
3. stage数・basis数・case数を独立証拠数と誤読しやすい。
4. H0DN二枝の鋭い数理・統計結果が広域叙述に埋もれる。
5. claim boundaryと必要査読専門性が論文ごとに異なる。

## 推奨執筆順

科学的にはPaper BとPaper Cの技術論文を先に固定し、Paper Aを最後に統合する方が安全である。総論が技術結果を先取りせず、各技術論文の外部レビューで表現が変わった場合も非遡及的に更新できるためである。
