# 横断監査方法と証拠モデル

## 1. 監査単位

監査単位はPhase数やファイル数ではなく、各season masterが正式に固定した**命題**である。1st seasonの20 claim/nonclaim、16 branch、7 cross-season anchorを基礎に、2nd seasonのtop-level claimと内包branch masterのclaimを対応付けた。

比較では次の四つを分離した。

1. masterから直接得た事実
2. canonical package内の数値・status
3. 今回再計算した単純な整合量
4. 今回初めて付した横断関係・方法論的推論

外部論文・Web・新規大規模解析は使用していない。

## 2. 非遡及規則

各命題を次の形で保存した。

```text
original proposition
+ original status and scope
+ later evidence
+ cross-season relation
= current bounded reading
```

関係分類は次のとおりである。

- `CONFIRMED`: 同じ限定命題を後続証拠が支持。
- `CONFIRMED_AND_SHARPENED`: 元命題を保持し、境界または再入場条件を具体化。
- `RETAINED_LATER_QUALIFIED`: 元命題は元scope内で成立するが、より広い読解を後続結果が制限。
- `PARTIAL_REENTRY_SPLIT`: 旧HOLD/FROZEN_OPENの一部だけが解け、別の下位問いはHOLDのまま。
- `METHOD_GENERALIZED`: 個別枝の方法上の注意が、複数対象にまたがる横断命題へ拡張。
- `NOT_RETESTED`: 2nd seasonは対象を直接検査していない。
- `TRUE_CONTRADICTION`: 同一命題・同一source/product・重なるcontract・同じ時間状態で両立しない結果。

最後の条件を満たす真正の科学的矛盾は0件だった。

## 3. 三層モデルの再評価

事前候補だった三層、

1. numerical/output reproduction
2. mathematical/representation invariance
3. generative/run/provenance reproduction

は方向として支持された。しかし線形な三層だけでは、二つの重要な差を表せない。

- exact parameter compressionが残差診断情報を失う場合
- source byte identityが強くてもexecuted-run lineageが閉じない場合

そこで本監査は、再現可能性を一個のPASS/HOLDや単純な階段ではなく、次の**六軸証拠ベクトル**として表す。

| 軸 | 問い | 代表例 |
|---|---|---|
| A0 Artifact identity / authority | どのbyte、version、sample、row orderか一意か | GWTC headlineはPASS、旧`gw_dark_O4a`はHOLD |
| A1 Numerical/output traceability | 凍結出力・公開コードからheadline量を回収できるか | TDCOSMO、GWTC、H0DN baseline |
| A2 Mathematical equivalence / invariance | 同じ数学的問題の同値表現・solver規約で結果が保たれるか | H0DN row scalingで限定的FAIL |
| A3 Diagnostic sufficiency / adequacy | 圧縮・summaryが残差、適合度、依存診断を保持するか | SN scalar compressionはH0に十分、残差には不十分 |
| A4 Executed lineage / provenance | 入力から設定、run、FITRES/sampler、最終行まで一意に追えるか | BBC、SN、GWTC旧比較、TDCOSMO likelihoodで未閉鎖 |
| A5 Generative / causal closure | covariance、truth model、物理原因、pipeline妥当性まで支持されるか | 全体として未確立、H0DNはsupport HOLD |

三層候補との対応は、旧Layer 1が主にA0+A1、旧Layer 2がA2、旧Layer 3がA4+A5に相当する。A3が独立に必要であり、A0とA4も分ける必要がある。

## 4. 六軸は線形階層ではない

上位軸が下位軸を自動的に含むとは限らない。

- H0DNはA1がPASSでもA2の一般不変性検査に限定的FAILがある。
- SN圧縮はA2のparameter equivalenceがPASSでもA3の残差情報を失う。
- TDCOSMOはA0/A1が強くてもA4のlikelihood/sampler生成は未再現。
- BBCは最終vector上の代数関係を追えてもA4/A5のtruth closureはHOLD。

従って「再現できた／できない」という一語の分類は、今回の証拠には粗すぎる。

## 5. 矛盾判定の反証手順

見かけ上対立する記述には、次の順で反証を試みた。

1. 対象quantityは同じか。
2. source bytes、release、sampleは同じか。
3. contractと変換族は同じか。
4. 結果が作られた時点は同じか。
5. output、diagnostic、lineage、generative claimを混同していないか。

この手順により、H0DN stability、SN compression、GWTC source availability、BBC localization、TDCOSMO chronologyの見かけ上の対立は、scope・quantity・timeの差として解けた。

## 6. 今回の単純再計算

新しいH0推定は行わず、保存値の整合だけを計算した。

- HTV114 baseline H0とB03A baseline H0の差：`+2.56e-12 km/s/Mpc`
- baseline sigma差：`+1.42e-14 km/s/Mpc`
- B03A row-standardization shift：baseline sigmaの約`0.06484`倍
- HTV29 slope closure残差：`-6.16e-17`
- same-name contrastは自由度の`14.1304%`に対しchi-squareの`5.4214%`

これらは新しい科学推定ではなく、master内保存値の横断整合チェックである。

## 7. 独立性境界

本監査、既存の第二実装、別構成の内部クロスチェックはAI支援下の同一プロジェクト内検証である。外部研究者による独立再現、専門家査読、公式pipeline validationとは呼ばない。
