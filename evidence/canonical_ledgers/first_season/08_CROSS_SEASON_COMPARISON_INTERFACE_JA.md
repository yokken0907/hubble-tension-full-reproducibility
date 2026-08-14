# 後続seasonとの突き合わせインターフェース

## 目的

本ファイルは後続seasonの結論を1st seasonへ遡及注入するものではない。
1st seasonで固定された命題を、将来の2nd season以降のマスターと安全に照合するための
**比較アンカーID**を定義する。

## 比較アンカー

| anchor_id | 1st seasonで固定された状態 | 将来比較すべき軸 | 遡及的にしてはいけない処理 |
|---|---|---|---|
| FS-X01-H0DN-STABILITY | HTV114は凍結表現・public pinv contract内の数値安定性をPASS | 同値表現に対する不変性、support、solver policy | 後続結果でHTV114を「誤り」と上書きする |
| FS-X02-SN-BBC | 公開補正vectorの傾きはBBC寄与へ局在、truth closureはHOLD | parameter圧縮と残差診断、同一CID、生成来歴 | BBC誤り・誤差過大を先に仮定する |
| FS-X03-GWTC | official posterior local freeze待ちでFROZEN_OPEN | posterior identity、headline metric、旧比較posterior provenance | release名だけで同一contractとみなす |
| FS-X04-TDCOSMO | output-level alternate implementation COMPLETE_WITH_SCOPE | source identity、別実装、生成pipeline再現の階層 | output一致をfull likelihood reproductionと呼ぶ |
| FS-X05-DESI | same released vectorのresponse atlasはclosed-with-scope | 新release/robustness productでmode安定性を検証 | basis数を独立証拠数として数える |
| FS-X06-CMB | common descriptive directionを保持、causal origin open | joint covariance、direction uncertainty、component likelihood | 共通方向を共通原因と断定する |
| FS-X07-HOLDS | source不足を具体的reentry triggerとして保存 | trigger成立の有無と新しいcanonical package | HOLDを陰性結果や異常発見へ変換する |

## 将来の双season統合規則

1. 各seasonの元statusを保持する。
2. 後続結果は `LATER_QUALIFICATION` または `SUPERSESSION_WITH_REASON` として別列に置く。
3. 同じsourceを使う結果は独立数へ加算しない。
4. 数値shiftを合成する前に、共通data・parameter・covarianceを明示する。
5. 矛盾が見える場合は、結果値ではなく契約・support・生成過程の差を先に比較する。
6. 新規論文は双seasonマスターの整合性監査後に作成する。
