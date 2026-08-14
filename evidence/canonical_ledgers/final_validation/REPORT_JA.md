# ハッブルテンション監査プロジェクト 最終内部検証・閉鎖監査報告

## 正式判定

```text
FINAL_INTERNAL_VALIDATION = PASS
H0DN_REPRESENTATION_NONINVARIANCE_INTERNAL = STRONGLY_RECONFIRMED
H0DN_MECHANISM = CONSISTENT_WITH_SINGULAR_MP_GEOMETRY
SN_PARAMETER_SUFFICIENCY_VS_DIAGNOSTIC_SUFFICIENCY = CONFIRMED_WITHIN_FROZEN_MODEL
SAME_CID_CONTRAST_ROBUSTNESS = CANONICAL_EVIDENCE_REVALIDATED
ADDITIONAL_HIGH_INFORMATION_INTERNAL_TEST = NONE_IDENTIFIED
PROJECT_INTERNAL_VALIDATION_PROGRAM = CLOSED_WITH_SCOPE
STOP_CURRENT_FROZEN_EVIDENCE = YES
PUBLICATION_DRAFTING = NOT_PERFORMED
```

このSTOPは、現在の凍結証拠を私達だけで再解析し続ける内部プログラムを閉じる。
外部再現、新しい公式product、将来の論文化を閉じるものではない。

## 1. 正本と完全性

科学的正本2点と参照用cross-season packageは指定SHA-256に一致し、ZIP CRCを通過した。

- 1st-season master: `3e6df9f5...52663c`
- 2nd-season master: `cc15c96a...e964940`
- cross-season package: `9719fae...166e60cf`

付属検証器の再実行結果は、1st masterがmanifest 36件とembedded ZIP CRCをPASS、
2nd masterが32/32 PASS、cross-season packageが56/56 PASS、両masterへの直接照合が
18/18 PASSであった。

関連canonical packageも再検証した。

- H0DN singular-covariance package: 16/16 verification gates PASS
- SN compression Phase 0: OVERALL PASS
- same-CID Phase 1C: 24/24 gates PASS、separate independent verifier PASS

Phase 1Cの最初の再実行は、指定した作業コピーに公式STATONLY covariance実体が無く、
入力配置エラーで停止した。byte hashがsource lockと一致する実体を別の凍結Git objectから
配置して再実行した。これは科学結果のFAILではなく、最終結果や分類を変更していない。

## 2. 情報利得による実施選択

新規計算前に契約をSHA-256
`5a54607d6004c88215e2981dce5a0a4ff1012c4505885487ef27b57db7a0b7d5`
で凍結した。

新たに実施したのは二つだけである。

1. H0DN実行列を複数の線形代数経路で解き、非直交表現変更の機構を厳密小規模例と照合する。
2. SN Ia 277行ブロックの1切片圧縮恒等式を別実装と人工例で確認する。

same-CIDについては、canonical Phase 1Cが既に別null-space basis、Cholesky対固有分解、
32直交座標変換、独立parser/eigendecomposition、rank/df bookkeepingを包含していた。
同じ統計量を別basisで再び計算してもclaimを実質的に変えないため、新規branchは作らず、
canonical verifierの再実行だけで閉じた。

BBC、SN executed lineage、GWTC old comparator、TDCOSMO originating likelihood、
DESI raw variants等は、現行masterの再分解では閉じない。新しい公式productまたは外部証拠を
必要とするHOLDとして維持した。

## 3. H0DN特異共分散・擬逆結果

### 3.1 実データ行列による別経路確認

未改変H0DN commit
`cc0a4b9f36e65470d514f254a3c5cffa463fbd94`から、255×64 design matrix、
255-vector、255×255 covarianceを取得した。covariance rankは183、nullityは72である。

| project-internal solver | original H0 | standardized H0 | ΔH0 | rank |
| --- | ---: | ---: | ---: | ---: |
| SciPy Moore–Penrose | 73.49875364360722 | 73.44630822099480 | -0.05244542261242 | 183→183 |
| explicit SVD (`gesvd`) | 73.49875364360699 | 73.44630822099464 | -0.05244542261235 | 183→183 |
| symmetric eigendecomposition (`evd`) | 73.49875364360624 | 73.44630822099427 | -0.05244542261197 | 183→183 |
| retained-support whitening + `gelsy` | 73.49875364360646 | 73.44630822099603 | -0.05244542261043 | 183→183 |

ΔH0の4経路間spreadは `1.9895e-12 km/s/Mpc` であった。

固有分解から構成した64×64 normal systemを80桁Decimal消去法で解くと、

- original H0: `73.49875364360781316678...`
- standardized H0: `73.44630822099609594345...`
- ΔH0: `-0.05244542261171722333...`

となった。double解との差は各座標系で約 `1.6e-12`、`1.8e-12 km/s/Mpc` であり、
最終normal solveの倍精度丸めではこの差を説明できない。

固定seedによる密な直交座標変換4試行では、最大H0変化は
`1.5085e-10 km/s/Mpc` だった。一方、非直交な対角標準化では、変換後擬逆精度を
元座標へ戻した行列と元の擬逆精度とのrelative Frobenius defectが
`3.8046837415446405e-4` であった。

covariance-nullspaceへのdesign projectionはFrobenius norm
`1.0381e-13`、data projectionはL2 norm `0.18874908268972845` である。
すなわち、凍結したrounded-data formulationでは、parameterを変えても消せない
nullspace成分が残るという既存support HOLDを別計算でも支持する。

### 3.2 厳密な2×2機構例

完全な有理数計算で、

```text
C = [[1,1],[1,1]], A = [[1],[1]], y = [1,0]
```

を用いた。Moore–Penrose GLS estimateは元座標で `1/2`、
`diag(1,2)`による非直交変換後に `1/5`、90度の直交回転後は `1/2` である。
rankは1のままで、null vectorはAを消すがyを消さず、support inconsistencyも保持される。

これは「特異行列のMoore–Penrose逆は一般の非直交congruenceに対して共変ではない」ことが、
浮動小数点や特定libraryなしでも起こる機構を示す。

### 3.3 bounded conclusion

今回の内部証拠から、H0DNの観測された非不変性を、単一library、単一分解法、
最終normal solveの丸め、または対角変換コードの偶然だけで説明する根拠は無くなった。
結果は、特異共分散、Euclidean geometryに依存するMoore–Penrose逆、
non-orthogonal congruence、nullspace/support inconsistencyの既知の数理構造と整合する。

ただし次は未確定である。

- upstream行列構築そのものの外部独立再実装
- unrounded yまたは明示的latent-error modelでのsupport
- covariance生成モデルの物理的妥当性
- 外部研究者・別組織による独立再現
- どの表現またはregularizationが科学的に正しいか

したがって、これはproject-internal evidenceとして十分強いが、external independent
replicationではなく、corrected H0も導かない。

## 4. SN parameter sufficiencyとdiagnostic sufficiency

固定SPD covariance `C`、277-vector `d`、共通1切片 `a` に対し、

```text
(d - 1 a)^T C^-1 (d - 1 a)
= chi2_min + (a - a_hat)^2 / V
```

が完全平方として成り立つ。ここで

```text
V = (1^T C^-1 1)^-1
a_hat = V 1^T C^-1 d
```

である。

別parserとCholesky/eigendecompositionで得た実データ値は、

- `a_hat = 0.7163834210954622`
- `sqrt(V) = 0.0018926416391806472`
- `chi2_min = 206.7606364373241`
- 7点profileの最大恒等式残差 = `3.4106e-13`

であった。

さらに `C=I` の3点人工例で、`(-1,0,1)` と `(-2,0,2)` は同じ圧縮平均0、
同じ圧縮分散1/3を持つが、残差chi-squareはそれぞれ2と8になる。

したがって、固定1切片・固定共分散Gaussian modelでparameterがこの切片だけを通じて
blockへ入る場合、`a_hat`と`V`はparameter-dependent likelihoodを保存する。
一方、残差pattern、goodness-of-fit、survey/redshift/flow/population依存、
別covariance/model比較への情報は保存しない。

一般化できるのはこの線形Gaussian完全平方構造までである。任意の非線形model、
parameter-dependent covariance、複数design directions、selection model、生成過程へ
自動的に一般化してはならない。

## 5. same-CID residual-deficit localization

新しいcontrast statisticは計算しなかった。canonical Phase 1Cの24 gatesを凍結sourceで
再実行し全件PASS、独立parser/null-space/eigendecomposition verifierもPASSした。

既存証拠は以下を既に確認している。

- 30 multi-row groups、69 rows、39 contrast degrees of freedom
- alternative null-space basisとのchi-square差は最大約 `1.42e-13`
- 5 covariance baselines × 32 orthogonal trials、160比較の最大差
  `1.24345e-14`
- Cholesky対eigendecomposition一致
- rank 39、group-annihilation誤差約 `3.33e-16`
- STATONLYでもlow-dispersion flagが残る
- 277/277 row mapping、76,729/76,729 covariance elements一致

よって、局在結果は特定Helmert coordinateの見かけではないという内部証拠は十分である。
ただし、quadratic-formのbasis invarianceは、同じcontrast subspaceと適切に変換したcovariance
に関する主張である。統計的独立性、共有露光、pipeline原因、row actionは確定しない。

## 6. 他の内部検証候補

両masterとcross-season未解決台帳を再点検したが、現在の私達だけで既存claimを実質的に
更新し得る追加検証は見つからなかった。

- BBC truth closure: matched truth/fit/pre-post/covariance/run manifest待ち
- SN final-row lineage: exact NML、FITRES、bias-correction output、row lineage待ち
- GWTC 25.7%: exact old-side posterior bytesとregistry待ち
- DESI MIDZ raw robustness: aligned raw variantsとjoint/cross-fit covariance待ち
- MCP/CF4: distance samples、flow covariance、zero-point cross-covariance、likelihood待ち
- H0DN correlated PV: exact source matrix/removal vector/reproduction package待ち
- TDCOSMO generation: originating likelihood、sampler、diagnostics、portable environment待ち
- HTS67 metric: 外部で正当化された共通metric待ち
- lensed SN: 新観測またはmaterially updated model待ち

同じmasterをさらに細分化することは、これらの不足を埋めない。

## 7. frameworkの更新

cross-seasonの六軸は有用だったが、最終検証により、従来A2に同居していた
「代数的に同じ問題を表すこと」と「target inferenceが不変であること」を分ける方が明確と
判断した。今後の作業frameworkは次の七座標を推奨する。

1. artifact identity
2. numerical/output traceability
3. algebraic representation relation/equivalence
4. target-inference invariance or sufficiency
5. diagnostic/model-support sufficiency
6. executed lineage/provenance
7. generative/causal closure

H0DNは、invertible coordinate changeという3番を満たしながら、Moore–Penrose policyの
4番がFAILし、literal degenerate-Gaussian supportの5番がHOLDになる。
SN compressionはlossy representationでありながら、凍結targetについて4番がPASSし、
残差診断の5番がFAILする。この分離が今回の二結果を最も少ない混同で記述する。

これは監査済み事例の整理frameworkであり、再現性に普遍的に必ず七軸あるという理論ではない。

## 8. STOPと次の工程

現在の凍結証拠について、ACTIVE INTERNAL SCIENTIFIC BRANCHは残っていない。
したがって、PROJECT-INTERNAL VALIDATION PROGRAMをここで`CLOSED_WITH_SCOPE`とし、
同一証拠の内部再解析に`STOP`を宣言する。

今後の必要物は三種類に分離する。

1. **external replication**
   - 最優先はH0DN非不変性・support結果の外部独立確認。
2. **new official products**
   - BBC truth-level matched bundle、SN executed-run lineage、GWTC old comparator等。
3. **publication**
   - project-internal claimは論文設計へ引き渡せる状態になった。ただし本監査では論文構成、
     title、abstract、introduction、投稿本文を作成していない。

新しい外部証拠、公式release、materialなH0DN改訂、または外部reviewによる具体的反証が無い限り、
内部検証branchを再開しない。
