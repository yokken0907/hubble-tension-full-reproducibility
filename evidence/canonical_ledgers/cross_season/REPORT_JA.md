# Hubble Tension 1st × 2nd Season 横断監査報告書

## 0. 正式判定

```text
CROSS_SEASON_AUDIT = COMPLETE_WITH_SCOPE
FIRST_SEASON_SCIENTIFIC_MAP = RETAINED_WITH_MATERIAL_LATER_QUALIFICATIONS
SECOND_SEASON_ROLE = TARGETED_REENTRY_AND_DEPTH_AUDIT
TRUE_SCIENTIFIC_CONTRADICTION = NONE_IDENTIFIED
NEW_CROSS_SEASON_METHOD_STRUCTURE = ESTABLISHED_WITHIN_AUDITED_RECORDS
SINGLE_CAUSE_OF_HUBBLE_TENSION = NOT_ESTABLISHED
CORRECTED_OR_PREFERRED_H0 = NOT_ESTABLISHED
HUBBLE_TENSION_RESOLUTION = NOT_ESTABLISHED
NEW_PHYSICS = NOT_ESTABLISHED
```

## 1. 要約

1st seasonの科学地図は、2nd season後も**広域の依存関係・数値traceability・再入場条件の地図**として全体的に有効である。2nd seasonが直接再検査したのはGWTC、Pantheon+ BBC、H0DN特異共分散、H0DN SN Ia残差・来歴の狭い領域であり、BAO、DESI、CMB、ACT、MCP/CF4、lensed SNの1st-season数値結果を再検査したわけではない。したがって「全地図が2nd seasonで独立確認された」とは言わない。

真正の科学的矛盾は見つからなかった。一方、重要な限定はある。

1. HTV114のH0DN結果は、固定された公開方程式表現と擬逆行列規約内では正確に再現され、cutoff掃引にも安定だった。この元判定は保持される。
2. B03Aは、同じ問題を厳密に同値な非直交行標準化へ移すとH0が`-0.052445422611000936 km/s/Mpc`変化することを示した。従って元の「安定」は一般表現不変性へ拡張できない。
3. B03B Phase 0は、凍結1切片モデルで277行SNブロックを`a_B`と分散へ圧縮してもH0推定が厳密に保存されることを示した。しかし同時に、`206.76063643732414`の残差chi-square情報が圧縮で消えることも示した。parameter inferenceへの十分性とmodel diagnosticへの十分性は別である。
4. HTV29のBBC項の代数的局在は保持される。しかしB02とB03Bは、truth-level BiasCor bundleとexecuted runから最終`m_b_corr`行への来歴が閉じないことを具体化した。BBC overcorrectionや原因の主張には進めない。
5. GWTCでは1st-seasonのFROZEN_OPENが一括解除されたのではない。2nd-season B01で現在のheadline posterior quantile再現はPASSしたが、公開25.7%比較の旧側posterior provenanceは`HOLD_NOT_UNIQUE`のまま残った。

両seasonを合わせることで、再現可能性は単純な三層階段よりも、artifact identity、output traceability、mathematical invariance、diagnostic sufficiency、executed lineage、generative/causal closureの六軸ベクトルとして扱う方が正確だと分かった。

## 2. 正本と完全性

指定された二つのmaster ZIPは、ユーザー指定SHA-256および外側sidecarと一致した。

| 正本 | bytes | SHA-256 | ZIP CRC | 付属検証器 |
|---|---:|---|---|---|
| 1st season master | 408,753 | `3e6df9f5…952663c` | PASS | `PASS manifest=36 embedded_zip_crc=PASS` |
| 2nd season master | 20,712,523 | `cc15c96a…e964940` | PASS | `checks=32 pass=32 fail=0` |

内包された比較上重要な9 canonical packageについて、合計263件の内部`SHA256SUMS.txt`参照を再照合し、全件一致した。B03A master verifierは18件、B03B master verifierは80 gateをPASSした。

既知のarchive hygiene事項は科学結果と分離した。

- 1st season元science scopeには外側sidecar 443件中1件のvisible mismatchがある。対象はchain cache index packageで、ZIP CRCと内部index/guide checksumは整合している。masterは科学破損ではなくarchive hygiene issueと分類する。
- 2nd season元フォルダには修正前Phase1Fを指すstale delivery recordがあったが、現行B03B masterは修正版hash `137e8c6f…01d6b03`を正本として内包し、stale recordを除外している。

初回の1st master verifier呼出では作業ディレクトリ前提を満たさず`MANIFEST.tsv`を見つけられなかった。package rootから再実行してPASSした。これは操作記録であり、master内容のFAILではない。

## 3. 1st seasonの科学地図は有効か

### 判定

`YES, AS A DEPENDENCY_AND_TRACEABILITY_MAP_WITH_SCOPE`

有効性を支える理由は三つある。

1. 2nd seasonの4枝は、1st seasonが残した具体的な再入場点から自然に派生している。GWTC posterior、BBC truth closure、H0DN数値規約、SN/covariance診断である。
2. 1st seasonの中心非主張、すなわち単一原因、corrected H0、新物理、naive branch combinationの禁止は、2nd seasonの全結果と整合する。
3. 1st seasonが区別したoutput traceability、shared dependency、source不足、独立実装不足は、2nd seasonでより細分化されただけで、破棄されていない。

ただし地図は完結したvalidation mapではない。2nd seasonはH0DNで新しい数学的・診断的問題を発見したため、1st seasonの「PASS_WITH_SCOPE」を一般pipeline validationと読む余地はさらに狭くなった。

また、BAO–BBNの約6.8%`r_d` budget、DESI response atlas、CMB共通方向、ACT variant center stability、HTS67 metric sensitivity、MCP/CF4、lensed SNは2nd seasonで直接再検査していない。これらは元scope内で保持されるが、2nd seasonによる追加確認とは数えない。

## 4. 主要な確認・強化・限定

### 4.1 GWTC — FROZEN_OPENの部分解消と問いの分裂

1st seasonの`FS-B12` / `FS-X03-GWTC`は、official posterior filesとmatched contractが不足し、posterior metricを凍結できない状態だった。

2nd-season B01では、GWTC-4とGWTC-5の現在のheadline posterior productをbyte固定し、別に書かれたType-7 percentile実装で公式一桁値を再現した。

- GWTC-4: `76.6 +13.0/-9.5`
- GWTC-5: `71.0 +9.0/-7.1`
- custom vs NumPy: 6/6 PASS
- headline components: 6/6 PASS

一方、published 25.7% metricの旧側`gw_dark_O4a`を一意なposterior bytesへ結ぶ公式registryは不足した。headline pairだけから得た`28.547849%`は別の診断量であり、25.7%再現ではない。

従って横断関係は、

```text
1st original = FROZEN_OPEN_LOCAL_POSTERIOR_FILES_MISSING
later Gate A = PASS_HEADLINE_OUTPUT_REPRODUCTION
later Gate B = HOLD_METRIC_POSTERIOR_PAIR_PROVENANCE_NOT_UNIQUE
```

である。元FROZEN_OPENが誤りだったのではなく、新しい公開productにより問いを分けられるようになった。

### 4.2 Pantheon+ BBC — 代数的局在を保持し、truth closureのHOLDを強化

HTV29は、released corrected-vector上のfixed-effect slopeを、bias-removed proxyとexplicit bias contributionへ代数分解した。

```text
corrected slope        = -0.12933311010615167
bias-removed proxy     = +0.0036889531241988084
explicit BBC term      = -0.13302206323035054
closure residual       = -6.16e-17
```

この結果は、最終vector上で記録された傾きがどの明示項に載っているかを同定する。2nd seasonはこの代数関係を反証していない。

B02は、固定公開commitで、

`BiasCor truth -> matched fit -> BBC pre/post vector -> corresponding covariance`

を同一sample・order・configuration・byte provenanceの下で一意に閉じられないことを確認した。必要な約2 GB BiasCor products、truth/fit mapping、pre/post vector、matched covariance、run manifest等は公開状態で一意に固定できなかった。

従って、

```text
HTV29 algebraic downstream localization = RETAINED
BBC correction validity = NOT ADJUDICATED
B02 truth-level execution = NOT_STARTED
B02 source readiness = HOLD_SOURCE_INCOMPLETE
BBC overcorrection = NOT ESTABLISHED
```

となる。2nd seasonは1stのBBC結果を否定せず、その結果が到達していない生成・truth層をより明確にした。

### 4.3 H0DN — 固定表現内再現の直接確認と一般不変性の限定

HTV114とB03Aは同じ上流commitに基づき、baselineをほぼbit-levelの差だけで再現した。

| 量 | HTV114 | B03A | 後者−前者 |
|---|---:|---:|---:|
| H0 | 73.49875364360406 | 73.49875364360662 | `+2.56e-12` |
| sigma(H0) | 0.8088000253378311 | 0.8088000253378453 | `+1.42e-14` |
| covariance rank | 183 | 183 | 0 |

HTV114の`1e-14`から`1e-7`までのabsolute cutoff sweepでH0 spread=0という結果は保持される。B03Aも固定cutoffと32置換での安定性を確認した。

しかしB03Aは、厳密に同値な非直交行標準化
`(A,y,C) -> (DA,Dy,DCD)`でH0が`-0.052445422611000936 km/s/Mpc`移動することを一次契約で示した。これはbaseline sigmaの約`0.06484`倍、H0の約`0.0714%`であり、テンション解消量ではないが、数理的には0ではない。

さらに、covariance nullspaceで`P0 A`は数値的に0だが`||P0 y||2=0.1887490826897376 mag`であり、公開rounded yと特異covarianceを文字どおりの退化Gaussianとして読むと`HOLD_INCONSISTENT_SUPPORT`となった。

従って現在の限定読解は、

```text
fixed representation numerical reproduction = PASS
tested cutoff/permutation stability = PASS
general non-orthogonal representation invariance = FAIL_FOR_TESTED_SCALING
literal degenerate-Gaussian support = HOLD_INCONSISTENT_SUPPORT
public H0DN value is wrong = NOT ESTABLISHED
corrected H0 = NOT ESTABLISHED
```

である。これは1st resultの取消しではなく、1st master自身が留保したgeneral representation invarianceを後から実際に検査した結果である。

### 4.4 H0DN shared covariance — 役割は保持、確率解釈はモデル相対化

HTV114は、共有host covarianceを外す診断でsigmaが小さくなり、反復情報を独立扱いする偽の高精度を防ぐ役割を記録した。B03Aは60個の素共分散成分を再構成し、PSD sensitivityとpseudoinverse constraint discardを分離した。

この後続結果は「共有情報を無視すべきでない」という構造的結論を支持する。一方、B03A support HOLDにより、公開特異Gaussian全体の確率モデルが完全に妥当だとする読解はできない。従って`shared covariance prevents naive false precision`は、**実装されたモデルと反復方程式構造内**の命題として保持する。

### 4.5 SN Ia — H0への十分性と残差診断への不十分性

B03B Phase 0は、凍結1切片・固定共分散モデルで277行SN Hubble-flow blockを`a_B`とその分散へ圧縮しても、全network parameterとH0が数値的に保存されることを確立した。

同時に、非圧縮版にはscalar版より`206.76063643732414`大きいparameter-independent residual chi-squareがある。従って圧縮はH0 parameter inferenceにはexact sufficientだが、goodness-of-fit、redshift/survey/velocity/population extensionの診断には不十分である。

Phase 1Aは残差不足をsame-name 39 contrast dfへ局在した。

- total: `206.760636 / 276`
- same-name contrasts: `11.209315 / 39`
- between-name: `195.551321 / 237`
- 39 dfは全自由度の`14.1304%`だがchi-squareの`5.4214%`

Phase 1BはH0DN 277行と公式HF 277行を一対一対応し、277×277 STAT+SYS covarianceの`76,729/76,729`要素がfloat64完全一致することを確認した。Phase 1Cではlow-dispersion flagがSTATONLYでも残った。

Phase 1D–1Fは69 same-CID rowsを69個のcompatible public input candidatesへ限定的に接続したが、final`m_b_corr`行へのdirect executed ancestryは確立しなかった。48 pair中byte-exact OBS reuseは0、single numeric compatibilityは4で、異CID負対照にも同種の一致があった。

従って、低残差の**所在**といくつかの単純説明の不十分さは確立したが、公開covariance過大評価、重複行、survey、較正、BBC、共通pipeline等の**原因**は確立していない。

### 4.6 TDCOSMOとGWTC — output reproductionの独立した例、生成再現ではない

1st-season TDCOSMO別実装は、3-file blind sentinelから12 Table 6 rows+1 controlへ拡張し、構造13/13、quantile 39/39、published precision 12/12をPASSした。これはproject-internal alternate implementationによるoutput-level traceabilityである。

2nd-season GWTCも、固定headline posteriorから公式一桁quantileを回収した。二つの対象は異なるが、共通して次を示す。

```text
successful output recovery
does not imply
originating likelihood / sampler / posterior-generation reproduction
```

TDCOSMOの元likelihood/sampler/convergence/model validationも、GWTCのevent-level analysis/galaxy catalog/selection functionも再現していない。内部別実装を外部独立再現とは呼ばない。

## 5. 真正の矛盾はあるか

`NONE IDENTIFIED`である。

主な見かけ上の対立は次のように解ける。

| 見かけ上の対立 | 解消理由 |
|---|---|
| H0DNはstable / H0DNはnon-invariant | 前者は固定表現・cutoff、後者は一般非直交同値変換 |
| SN compressionはexact sufficient / residual informationを失う | parameter inferenceとgoodness-of-fitで対象quantityが違う |
| 1st GWTCはfiles missing / 2nd headline PASS | 後から得たheadline productsと、依然欠ける旧25.7% comparatorは別 |
| BBC term localization PASS / truth closure HOLD | final-vector代数とtruth-to-run生成検証は別層 |
| dated integrated auditでTDCOSMO alternate NOT_DONE / first masterでCOMPLETE | 2026-07-25記録と2026-07-26 closeoutの時系列差 |
| Phase1D 38/69 / Phase1D+1Eで69/69 candidates | Phase1Eは別凍結規則による非遡及補足で、Phase1D主結果を変更しない |

## 6. 両seasonから新たに見える構造

### 6.1 再現可能性は一個の状態ではない

複数対象で、A1 output PASSとA2/A3/A4/A5のFAIL/HOLDが同居した。従って「再現済み」という一語だけで科学的再現性を表すことは不十分である。

### 6.2 十分性は問いに依存する

同じSN scalar summaryがH0にはexact sufficientであり、residual diagnosticには不十分だった。これは単に「情報を少し失う」という一般論ではなく、保存されるparameter方向と失われる276 residual dfが数値的に分離された具体例である。

### 6.3 公開再現性の反復ボトルネックはexecuted lineageにある

異なる対象で、最終productまたは公開inputは存在するが、その間の実行連鎖が閉じない。

- GWTC: published 25.7%のold-side posterior bytes/registry
- BBC: truth -> fit -> pre/post -> covariance
- SN: photometry candidate -> FITRES/bias correction -> final row
- TDCOSMO: likelihood/sampler/posterior generation

これは各pipelineが誤っているという証拠ではない。今回の正確な命題は、**公開された証拠集合から同一runの生成連鎖を一意に再構成できない事例が複数対象で再発した**、である。

### 6.4 同一sourceの再表現は独立証拠を増やさない

1st seasonのDESI/HTS59–67で得た原則は、2nd seasonのH0DN representation、SN compression、Phase連鎖でも重要だった。別座標、別summary、別stageは問いを分解するが、元data/sourceが同じなら独立観測数にはならない。

### 6.5 HOLDは科学的な停止結果になり得る

B02はsource-readiness auditを完了した上でtruth-level executionを開始せずHOLDとした。B01 Gate B、B03B executed lineageも同様である。HOLDは未整理な作業ではなく、追加証拠なしに推測置換へ進まないための肯定的な監査結果である。

## 7. ハッブルテンションについて現在言える範囲

### 言えること

- 公開H0推論の複数枝で、final outputまたはheadline量は限定contract内で再現できる。
- local ladder、SN、BBC、shared covariance、BAO/CMB/DESI/lensing/GW/flow routeには重複・共有依存・非加法性がある。
- H0DNでは固定表現の再現性と一般表現不変性を区別する必要がある。
- SN scalar compressionはH0を保つが、残差適合度を隠し得る。
- SN同一CID残差不足は39 contrast dfへ局在し、公開STATONLYまで残るが、原因は未同定である。
- 公開productとexecuted lineageの間に、複数対象で具体的な欠落がある。

### 言えないこと

- corrected / preferred H0
- tension significanceの修正
- Hubble tensionの解消または有意な緩和
- BBC overcorrection
- H0DN、Pantheon+、TDCOSMO、GWTC等のpipelineが誤っているという断定
- 特定survey、SN、anchor、calibration、flow modelの原因断定
- 統計的依存から物理的因果への読み替え
- new physics

## 8. 追加検証の価値と停止条件

高価値な未解決点は残るが、同じmasterをさらに分解するだけの新Phaseは推奨しない。上位候補はすべて、外部独立性または新しい公式sourceを必要とする。

### 最優先A — H0DN表現・supportの外部数値確認

必要証拠：別研究者・別言語実装、未丸めy、covariance生成手順、潜在変数または明示的full-rank model、数値線形代数/統計専門家レビュー。

価値：2nd seasonで唯一、同値表現と退化Gaussian supportに直接触れた中心的な数理結果である。内部AI再実装だけでは外部確証が不足する。

### 最優先B — BBC truth-level closure bundle

必要証拠：official versioned BiasCor truth bytes、matched fit、pre/post vector、same-order covariance、run manifest/configuration、checksums。

価値：HTV29の代数的局在を、expected correctionかmodel mismatchかへ進める唯一の正当な再入場条件である。

### 最優先C — SN executed-run-to-final-row lineage

必要証拠：exact base NML、run manifest、FITRES、bias-correction output、row-level lineage、KCOR execution identity、same-CID covariance生成資料。

価値：39 contrast dfへの局在を、測定/fit/aggregation/generative dependencyへ接続するために必要である。

### 次順位

- DESI MIDZ raw robustness：aligned variant vectorsとjoint/cross-fit covariance。
- MCP/CF4 joint flow：distance samples、joint covariance、zero-point cross-covariance、likelihood。
- H0DN correlated PV：source matrix、removal vector、author reproduction package。
- GWTC 25.7% provenance：exact old-side posterior bytesとofficial registry。科学的範囲はmetric provenanceに限定。
- TDCOSMO full generation：元likelihood、sampler、convergence environmentまたは外部独立実装。既存quantileを増やすだけでは再開しない。
- HTS67：外部で正当化されたmetric/joint likelihood/component posterior。
- lensed SN：新しい観測またはmaterialに更新されたphotometry/lens model。

## 9. 論文化の自然な構成

一本の巨大統合論文より、**総論1本＋技術論文2本**が証拠構造に最も自然である。

1. 総論／方法論論文：公開H0推論におけるmulti-axis reproducibilityとexecuted-lineage gap。両seasonのcrosswalkと六軸matrixを中心にする。
2. 技術論文A：H0DN特異共分散、Moore–Penrose表現非不変性、degenerate-Gaussian support。
3. 技術論文B：SN Ia parameter-sufficient compression、残差不足の39 contrast局在、covariance/input lineage frontier。

GWTC、TDCOSMO、BBC source-readinessは総論のcase studyまたは技術supplementに置くのが自然である。単独短報にする場合も、「H0結果」ではなくoutput/provenance traceability noteとして設計する。

この構成は、H0DN二枝の鋭い問いと、広域方法論の異質性を分離し、stage数やcase数を独立証拠数として誤計上する危険を抑える。

## 10. 結論

1st seasonの価値は、広域の科学地図を作ったことにある。2nd seasonの価値は、その地図の一部へ戻り、同じ「再現」という語の内側に、output、representation、diagnostic、lineage、generative validityの別問題があることを具体的に示したことにある。

統合後の最も強い新規命題は、ハッブルテンションの原因や修正値ではない。

> 公開H0推論の再現可能性は二値ではなく、artifact identity、数値出力、数学的同値性、診断十分性、実行来歴、生成・因果妥当性を別々に記録しなければならない。今回の監査対象では、低い層のPASSと高い層のFAIL/HOLDが複数の具体例で同時に成立した。

この命題は両seasonを合わせて初めて明瞭になった。ただし、それ自体はcorrected H0、tension resolution、pipeline error、新物理を意味しない。
