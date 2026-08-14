# GWTC-4 / GWTC-5 \(H_0\) metric provenance source freeze V1

## 結論

```text
SOURCE_FREEZE = COMPLETE
GWTC4_HEADLINE_POSTERIOR_FILE_IDENTITY = PASS
GWTC5_HEADLINE_POSTERIOR_FILE_IDENTITY = PASS
INTERVAL_DEFINITION = FIXED_WITH_IMPLEMENTATION_NOTE
AVERAGE_UNCERTAINTY_DEFINITION = PASS
METRIC_CODE_PATH_IDENTIFICATION = PASS
METRIC_POSTERIOR_PAIR_PROVENANCE = NOT_UNIQUE
OVERALL_GATE = HOLD_METRIC_PROVENANCE_NOT_UNIQUE
POSTERIOR_QUANTILE_REPRODUCTION = NOT_EXECUTED
METRIC_25P7_REPRODUCTION_FROM_POSTERIOR_PAIR = NOT_EXECUTED_HOLD
SCIENTIFIC_EXPANSION = NO
```

GWTC-4とGWTC-5の論文headline posteriorに対応する公式配布ファイルは、それぞれ次の1本に固定できる。

- GWTC-4: `SOURCES/GWTC4/H0_dark_combined.json`
- GWTC-5: `SOURCES/GWTC5/H0_dark_combined_gw170817.json`

68.3%区間の実装は、中央値と15.865・84.135百分位点から作る等裾区間である。下側・上側誤差を中央値からの差として計算し、論文用関数では各値を小数第1位へ丸める。「平均不確かさ」は下側・上側誤差の算術平均である。

25.7%を表示する公式notebookのコード経路も特定できた。しかし、その経路は上記2本のposteriorを直接比較していない。GWTC-5側は現行posteriorから求めた後に1桁へ丸めた誤差 \(7.1,9.0\) を使い、GWTC-4側は`H0_summarydata.json["gw_dark_O4a"]`の非丸め誤差を使う。この混合経路は25.7%を算術的に生成する。

一方、`gw_dark_O4a`は別のsummary生成notebookによる再処理値であり、GWTC-4論文headline \(76.6^{+13.0}_{-9.5}\) と一致しない。さらに、その生成notebookが参照する`O4a_cosmology_results_paths_SR9.json`は公式配布物に含まれず、参照posteriorのバイト列を一意に固定できない。したがって、25.7%を「GWTC-4とGWTC-5の公式headline posterior pairから得たmetric」としては一意に再現できず、指定どおりHOLDとした。

## 読む順序

1. `AUDIT/HEADLINE_POSTERIOR_IDENTITY.md`
2. `AUDIT/DEFINITION_AND_25P7_PROVENANCE.md`
3. `AUDIT/GATE_STATUS.tsv`
4. `AUDIT/NEXT_STAGE_CONTRACT.md`
5. `AUDIT/SOURCE_FREEZE.tsv`
6. `SHA256SUMS.txt`

## 範囲

このパッケージはsource freezeと定義監査だけを含む。posterior分位点の独立再計算、likelihood、sampler、event-level解析、他probeとの統合は実行していない。25.7%に関して行った数値操作は、公式ファイル内に既に記録された誤差値を、公式notebookに書かれた式へ代入したprovenance arithmetic traceだけである。

