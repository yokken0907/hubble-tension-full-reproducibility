# 再現性frameworkの最終内部整理

## 更新理由

cross-season監査の六軸frameworkは、今回も探索・整理上有効だった。
ただしH0DNとSN compressionを並べると、旧A2の
`mathematical equivalence / invariance` は二つの異なる問いを含む。

- 方程式や残差vectorがinvertible coordinate transformで代数的に対応するか。
- 採用したsolver/statistical policyのtarget inferenceがその変換・圧縮で保存されるか。

H0DNは前者がYESでも後者がNOになり得る。SN scalar compressionは全データ表現として
invertibleではないが、限定targetについて後者がYESになり得る。そこで両者を分ける。

## 七座標working framework

| ID | coordinate | 問い |
| --- | --- | --- |
| F0 | artifact identity | 同じbytes/version/sourceを参照しているか |
| F1 | numerical/output traceability | headline数値・outputを固定規約で回収できるか |
| F2 | algebraic representation relation | 表現間の代数的対応・invertibility・lossinessは何か |
| F3 | target-inference invariance/sufficiency | 指定targetのlikelihood/estimate/covarianceを保存するか |
| F4 | diagnostic/model-support sufficiency | residual、GoF、support、model診断に十分か |
| F5 | executed lineage/provenance | 実run、config、intermediate、final row/outputを結べるか |
| F6 | generative/causal closure | 生成過程・原因・物理的解釈まで閉じるか |

## 今回の2例

| case | F2 | F3 | F4 |
| --- | --- | --- | --- |
| H0DN singular Moore–Penrose | exact invertible row-coordinate change | FAIL for tested non-orthogonal scaling | HOLD: literal rounded-data support inconsistent |
| SN 277→scalar compression | lossy data compression | PASS for frozen one-intercept target | FAIL for residual chi-square/pattern |

## 境界

この七座標は、監査済み記録の混同を減らすworking frameworkである。
自然界、統計学、再現性一般に「本質的に七軸ある」という普遍命題ではない。
事例に応じて統合・追加・削除を許す。
