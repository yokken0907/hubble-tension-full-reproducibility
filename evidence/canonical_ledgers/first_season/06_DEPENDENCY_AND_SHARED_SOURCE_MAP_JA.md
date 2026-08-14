# 依存関係・共有source・独立性の地図

## 原則

branch名の違いは、独立証拠を意味しない。以下のいずれかを共有する場合、結合時に
重複計上を避ける必要がある。

- 同じ公開data vectorまたはposterior endpoint
- 同じ較正資産・SNカタログ・DESI release
- 同じCMB prior・standard-ruler scale
- 同じflow、redshift、cosmographic convention
- 同じlikelihood familyまたはhierarchical assumption

## 主要共有関係

### DESI

HTV71–98のDM/DH、ISO/AP、common/differential、neutralization、deflated rankingは、
同じreleased BAO vector周辺のresponse atlasである。内部構造の局在には有用だが、
段階数を独立観測数として数えない。

### CMB release geometry

HTS59–67は同じ5 release endpointsを、座標、eigenmode、Shapley/Owen、partition、
metricで再評価した。同一endpointの追加分解はHTS66で閉鎖され、HTS67はmetric規約依存を
示した。

### ACT

frequency、array、calibration、tau、likelihood representation、robustness variantsは
ACT data/model componentsを共有する。個々のresponseを独立significanceとして合算しない。

### TDCOSMO

SLACS、SL2S、SLACS+SL2Sのnested posteriorはtime-delay dataとhierarchical assumptionsを
共有し、同時追加には非加法的interactionがあり得る。Pantheon+とDESI auxiliary layersは
局所SN枝・DESI枝とsource familyを共有する。

### H0DN / MCP / local flow

見かけ上別の経路でも、flow model、redshift処理、cosmographic conventionを共有し得る。
共同推論には明示的なcovariance/dependency contractが必要である。

## 結合可能性

安全に結合できるのは、各枝の**主張status、入力source、仮定、未解決条件**であり、
診断的H0 shiftやstage数を単純加算してはならない。
