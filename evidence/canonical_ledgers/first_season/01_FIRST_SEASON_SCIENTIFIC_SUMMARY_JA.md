# 1st Season 科学的総括

## 1. seasonの役割

1st seasonは、ハッブルテンションを単一仮説で説明する試みではなく、公開情報から
追跡できる推論経路を広く走査し、**何が再現でき、何が共有依存で、何が公開資産不足で
閉じないか**を分類した広域監査である。

主な系列は、HTV02–136、HTS01–68、およびHTS68後に別実装で閉鎖した
TDCOSMO blind sentinel / Table 6 extensionである。

## 2. 主要な科学的到達点

### 2.1 局所距離梯子・SN・BBC

単一zero point、単一SN、gray calibration、survey mixのいずれか一つだけを、
ハッブルテンションの十分な原因として確定していない。公開補正vectorの傾きは、
凍結された分解では明示的BBC寄与に強く対応した。一方、BiasCor truthからmatched fit、
pre/post vector、対応共分散までのtruth-level closureは公開資産不足で閉じていない。

### 2.2 BAO・BBN・初期宇宙スケール

BAOが主に `H0 × r_d` を拘束する構造を確認し、記録された契約下で高い局所H0へ
対応するには約6.8%の `r_d`低下が必要という予算を保持した。これは新物理の証拠ではなく、
候補モデルがCMB・BBN・LSS・DESIを同時に満たす必要を示す制約である。

### 2.3 DESI内部幾何・response atlas

同一released BAO vectorを複数の事前定義basisで分解し、
`MIDZ_COMMON_ISO`を高lever response、`LRG1_DM`をcounter-anchorとして局在した。
ただし、同じvectorの再表現であり、複数の独立観測ではない。物理的原因やoutlier判定は
公開されたaligned robustness vectorとcross-covarianceなしには閉じない。

### 2.4 CMB・ACT・SPT・release geometry

Planck、SPT、ACTからDESIへの変位には、Gaussian scope内で共通する
`Omega_m – h r_d`方向が見られた。単一装置またはPlanck単独を十分な原因として
確定していない。ACT DR6の公開variant群は中心値の安定性を示したが、variant間は
相関した同一source内診断であり、独立significanceとして合算できない。

HTS51–66では同じrelease endpointsに対する距離・eigenmode・coalition・partition解析を
進め、規約不変なcoreを保持して内部分解を閉鎖した。HTS67ではsymmetric poolingが
metric規約に感度を持つためHOLDとなった。

### 2.5 H0DN公開距離ネットワーク

公開baselineと複数scenarioを再現し、凍結された公開方程式表現と擬逆行列規約の内部では
cutoff感度が見られず、共分散blockは数値的に再構成された。共有共分散は高い中心値の
単独原因ではないが、反復情報を独立扱いした偽の高精度を防ぐ役割を持つ。

一方、exact correlated-PV再現、full cross-method covariance closure、完全なsystematics
marginalizationは未完了である。診断ablationは代替科学likelihoodではない。

### 2.6 TDCOSMO公開chainと別実装

HTS68の公開chain解析は、後にmethod/contract correctionを受け、post-hoc exploratoryな
output-level traceabilityとして保持された。その後、別に書かれた実装を3-file blind
sentinelで凍結し、12 flat-LambdaCDM Table 6 chainsと1 collision controlへ拡張した。

最終結果は、構造13/13 PASS、quantile 39/39が事前固定tolerance内、Table 6の12/12行が
published precisionで一致し、branchは `COMPLETE_WITH_SCOPE` で閉鎖された。
これは元likelihood・sampler・収束性・astrophysical modelの完全再現ではない。

### 2.7 その他の独立経路

GWTC、MCP/CF4、lensed supernovaなどは高い独立性を持ち得るが、1st season時点では
必要なposterior、joint likelihood、covariance、distance samples、または新観測が不足し、
再開条件を付した `FROZEN_OPEN` / `HOLD` として残った。

## 3. 総合結論

```text
STRUCTURAL_DEPENDENCY_MAPPING = STRONG_PROGRESS
OUTPUT_LEVEL_TRACEABILITY = MULTIPLE_PASS_WITH_SCOPE
MATHEMATICAL_OR_GENERATIVE_CLOSURE = PARTIAL
SINGLE_CAUSE_OF_HUBBLE_TENSION = NOT_ESTABLISHED
CORRECTED_H0 = NOT_ESTABLISHED
NEW_PHYSICS = NOT_ESTABLISHED
```

1st seasonの価値は、結果を一つへ平均することではなく、**同じsourceの再表現、
共有データ、外部product待ち、独立実装不足を区別したこと**にある。
