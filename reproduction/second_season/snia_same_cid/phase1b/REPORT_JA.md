# Phase 1B報告：同一名複数行の来歴監査

## 結論

最終277/277対応は、カタログ項目と共分散数値指紋を組み合わせた共同来歴
結果である。H0DN 277行のうち、275行はカタログ項目だけで一意になった。
`2009cz`の2行だけはカタログ段階で多義的であり、公式STAT+SYS共分散対角を
数値指紋として必要とした。宣言した第二段階の後には、未対応、多義的対応、
公式行再利用はいずれも0件で、公式`USED_IN_SH0ES_HF=1`の全277行と一対一に
対応した。

同一名30群はすべて異survey群で、同一survey反復群は0だった。対応順で
抽出した公式277×277 STAT+SYS部分行列は、H0DN共分散と76,729要素すべてが
`float64`完全一致し、最大絶対差は0だった。

正式ステータス：
`AUDIT_COMPLETE_PROVENANCE_AND_COVARIANCE_LINEAGE_TRACED`

境界マーカー：
`PROVENANCE_ONLY_NO_ROW_MODIFICATION_NO_COVARIANCE_CORRECTION_NO_CORRECTED_H0_NO_TENSION_RESOLUTION`

## 問いと固定出典

Phase 1Aでは、低い残差カイ二乗が同一名行間の39コントラスト自由度へ偏って
局在した。しかし文字列の完全一致だけでは、複数行の由来や共分散値・行順の
公式リリースとの対応までは決まらない。Phase 1Bは、各H0DN行の公式行・
survey codeと、その対応順における共分散の数値一致だけを検査した。

| 出典 | 固定コミット | 主要ファイル |
| --- | --- | --- |
| H0DN | `cc0a4b9f36e65470d514f254a3c5cffa463fbd94` | `data/sn1a_hf_pp.dat`, `data/sn1a_covar_pp.dat` |
| Pantheon+SH0ES DataRelease | `c447f0fea703fcd0fff57de5000947b5ca81286b` | `Pantheon+SH0ES.dat`, `Pantheon+SH0ES_STAT+SYS.cov` |

関連READMEを含む9ファイルを、コミット、Git blob、バイト数、SHA-256で
固定した。上流データ本体は再配布しない。

## 訂正後の二段階照合

候補は常に公式`USED_IN_SH0ES_HF=1`行へ限定する。単一の有効設定は
`provenance/ACTIVE_MATCHING_CONFIG.json`である。

第一段階は次のカタログ項目だけを使う。

- H0DN `name`と公式`CID`の完全一致。
- `m_b`と`m_b_corr`の絶対差が`0.000500000001`以下。
- `zhel`対`zHEL`、`zcmb`対`zCMB`の絶対差がそれぞれ
  `0.000005000001`以下。

第一段階では`m_b_corr_err_DIAG`も共分散値も使用しない。各H0DN行を
`CATALOG_ONLY_UNIQUE`、`CATALOG_ONLY_AMBIGUOUS`、
`CATALOG_ONLY_UNMATCHED`に分類する。

第二段階へ進むのはカタログ段階で多義的な行だけである。候補公式行の印字済み
STAT+SYS共分散対角平方根とH0DN `err_m_b`との差に
`0.000005000001`を適用し、`COVARIANCE_DIAGONAL_REQUIRED`、
`AMBIGUOUS_AFTER_ALL_RULES`、`UNMATCHED_AFTER_ALL_RULES`を決める。

候補は公式行index、`CID`、`IDSURVEY`で決定論的に並べる。別名辞書、
大文字小文字変換、曖昧検索、手動割当、行順によるtie-breakは使わない。

| 対応依存分類 | 行数 |
| --- | ---: |
| `CATALOG_ONLY_UNIQUE` | 275 |
| `CATALOG_ONLY_AMBIGUOUS` | 2 |
| `CATALOG_ONLY_UNMATCHED` | 0 |
| `COVARIANCE_DIAGONAL_REQUIRED` | 2 |
| `AMBIGUOUS_AFTER_ALL_RULES` | 0 |
| `UNMATCHED_AFTER_ALL_RULES` | 0 |
| 最終一対一対応 | 277 |
| 公式行再利用 | 0 |

2行の一覧と全候補差分は
`results/covariance_diagonal_required_rows.tsv`および
`results/row_mapping_dependency.tsv`に保存した。

## `m_b_corr_err_DIAG`の訂正診断

固定README上は`m_b_corr_err_DIAG`が共分散対角由来と説明されているが、
公開された列値と公開STAT+SYS共分散対角平方根は数値的に一致しない。
本監査はこの文書・データ不一致の理由を確定しない。H0DN `err_m_b`は後者と
H0DN印字精度で一致する。

| 最終277行での診断 | 結果 |
| --- | ---: |
| カタログ列対行列が`0.000000500001`以内 | 0 |
| カタログ列対行列の最大絶対差 | `0.14130297508896889` |
| H0DN対行列が`0.000005000001`以内 | 277 |
| H0DN対行列の最大絶対差 | `4.959714075936095e-06` |
| 原因分類 | `UNRESOLVED_DOCUMENTATION_DATA_DISCREPANCY` |

これは観測された数値関係の記録であり、丸め、版差、生成手順、文書記載、
その他の候補原因のいずれかを選ぶものではない。

## 同一名複数行

| 項目 | 結果 |
| --- | ---: |
| 同一名複数行群 | 30 |
| 対象行 | 69 |
| 2行群 | 21 |
| 3行群 | 9 |
| 全行が異なるsurvey codeの群 | 30 |
| 同一survey反復群 | 0 |
| 複合型群 | 0 |

69行のsurvey内訳は、CSP 16、LOSS1 7、SOUSA 3、LOSS2 16、CFA2 1、
CFA3S 3、CFA3K 15、CFA4p2 8である。全証拠は
`results/multirow_group_summary.tsv`と
`results/multirow_row_evidence.tsv`に収録した。

## 共分散比較と証拠限界

最終公式index列から、印字済み1701×1701 STAT+SYS共分散を変更せずに
277×277部分行列を抽出した。

| 診断 | 結果 |
| --- | ---: |
| 比較要素 | 76,729 |
| 完全一致 | 76,729 |
| 不一致 | 0 |
| 最大絶対差 | 0 |

これは許容差付き比較ではなく`float64`値の要素完全一致である。要素欠落、
転記差、追加の丸め差、行順不一致を示す数値的証拠は認められなかった。
この一致だけから、過去の行列生成手順までは確定できない。

公式印字済み全行列には、転置相手と一致しない要素が778個あり、最大差は
`3.0000000000038676e-08`である。`AMEND-002`に診断を記録し、一次比較前に
対称化、平均化、丸め、置換を行っていない。

公式対角を2行の識別へ用いたため、その後の76,729要素比較を、行識別に用いた
全情報から完全に独立した検査とは表現しない。この依存関係は行台帳と
機械可読summaryに明示した。

## 科学的解釈

固定した二つのリポジトリの範囲では、Phase 1Aの局在を、単純な行欠落、
割当上の行再利用、同一survey反復、対応行順の不一致、部分行列の数値転記差で
説明する根拠は得られなかった。一方、公開共分散の校正適否、低カイ二乗の
原因、因果関係は確定しない。

共分散校正監査は将来のPhase 1C候補になり得るが、本パッケージには
Phase 1Cの検定も結果も含めない。

## プロトコル改訂

初期契約と`AMEND-001`〜`AMEND-003`はそのまま保持した。`AMEND-003`は、
初期の`m_b_corr_err_DIAG`照合が277行すべて0候補となったこと、および
訂正規則を訂正後の対応結果を見る前に固定したことを記録する。

`AMEND-004`は`results_observed=YES`、
`interpretation_affected=NO`である。裏付けのない説明を除去し、
カタログのみの識別と共分散補助の識別を分離し、文書・データ不一致を
未解決として記録し、共分散主張を観測された数値一致へ限定した。
277/277対応、survey分類、共分散値、正式ステータス、科学的境界は変わらない。

## 非主張

本監査は、行修正、survey選別、共分散修正、修正`a_B`、`M_B`、`H0`、
ハッブルテンション有意度を計算しない。行の統計的独立性、公開共分散の
正しさ、上流プロジェクトによる承認・査読も示さない。
