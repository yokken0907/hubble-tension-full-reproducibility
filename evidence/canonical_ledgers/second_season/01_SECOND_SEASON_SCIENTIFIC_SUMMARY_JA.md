# 2nd season 科学的総括

## 1. seasonの役割

1st seasonがハッブル定数推論の広域的な依存関係地図を作ったのに対し、2nd seasonは公開証拠で再入場可能になった狭い問題を深掘りした。対象はGWTC-4/5 headline posterior、Pantheon+ BBC truth-level closure readiness、H0DN特異共分散、H0DN SN Ia same-CID残差不足である。

## 2. Branch 01 — GWTC-4/5 posterior traceability

固定された公開headline posteriorに対し、独立に書いたHyndman–Fan type 7線形percentile実装で公式一桁値を再現した。

- GWTC-4: `76.6 +13.0 / -9.5`
- GWTC-5: `71.0 +9.0 / -7.1`

一方、論文等で示される25.7%改善metricの旧側 `gw_dark_O4a` posterior byte provenanceは公開記録上で一意に固定できず、Gate Bは `HOLD_NOT_UNIQUE` のまま。headline pairから直接計算した28.547849%は診断値であり、25.7%の再現ではない。

## 3. Branch 02 — Pantheon+ BBC source readiness

公開公式資料を固定して、`BiasCor truth -> matched fit -> BBC pre/post vector -> corresponding covariance` を一意に結ぶtruth-level closure bundleが公開状態だけでは構成できないことを確認した。

従ってsource-readiness auditは完了したが、truth-level scientific executionは開始せず、`HOLD_SOURCE_INCOMPLETE`。BBC補正が誤っているという結果ではない。

## 4. Branch 03A — H0DN singular covariance

公開H0DN基準値を再現した一方、255×255共分散はrank 183 / nullity 72の特異PSDであり、Moore–Penrose処理は固定cutoff・置換には安定でも、厳密に同値な非直交対角行変換に対してH0が `-0.052445422611000936 km/s/Mpc` 移動した。

さらに `P0 A` は数値的に0だが `||P0 y||2 = 0.1887490826897376 mag` で、公開された退化Gaussianの厳密台に対する `HOLD_INCONSISTENT_SUPPORT` を記録した。これは公開H0DN値が誤り、修正H0が得られた、あるいはハッブルテンションが解決したという意味ではない。

## 5. Branch 03B — SN Ia same-CID residual deficit

277-object Pantheon+ Hubble-flow blockでは、scalar intercept compressionは固定一切片モデルのH0に対して数値的に完全十分だったが、206.760636のparameter-independent residual chi-square情報を失う。

その残差不足は39 same-CID/same-name contrast dfへ局在し、STATONLYまで低分散フラグが残った。277行と公式HF 277行、277×277共分散は完全対応。Phase 1D–1Fで69行すべてを限定された公開input candidateへ接続し、48 same-CID pair中byte-exact OBS共有は0、単一numeric compatibilityは4だった。

ただしexact executed run -> FITRES/bias correction -> final `m_b_corr` row lineageは公開資料から閉じず、原因は未同定。新しい実行来歴証拠が出るまで本枝を再開しない。

## 6. 2nd season全体の結論

2nd seasonは、最終数値を再現できることと、数学的表現不変性、生成・実行来歴の再現性が別問題であることを複数枝から具体化した。これは次段の1st×2nd横断監査で検討すべき方法論的候補であり、このmaster単独では新しい統合科学claimとして昇格させない。

2nd seasonから、corrected H0、新たなtension significance、新物理、単一原因、測定修正は得られていない。
