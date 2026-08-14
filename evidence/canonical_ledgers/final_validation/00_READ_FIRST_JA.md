# 最初に読む文書

このパッケージは、ハッブルテンション監査プロジェクトの1st season、
2nd season、cross-season監査を受けた、論文化前の最終内部検証・閉鎖監査記録である。

論文原稿ではない。新しいH0値、補正H0、テンション解消、原因systematic、
BBC overcorrection、pipeline error、new physicsを主張しない。

最初に `REPORT_JA.md` を読み、次に以下を参照する。

- `INTERNAL_VALIDATION_CONTRACT.md`: 新規結果を見る前に凍結した検証契約
- `INFORMATION_GAIN_DECISION_LEDGER.tsv`: 実施・不実施の判断
- `VALIDATION_LEDGER.tsv`: 実施した検証と結果
- `CLAIM_AND_NONCLAIM_LEDGER.tsv`: claim境界
- `HOLD_REENTRY_AND_STOP.tsv`: STOPと再入場条件
- `EVIDENCE_LOCATOR.tsv`: season master内の証拠位置
- `results/internal_validation_results.json`: 新規数理検証の全数値

クリーン展開後の再検証は次の2コマンドで行う。

```bash
python scripts/run_internal_validations.py --verify-recorded
python scripts/verify_package.py
```

正式な最終状態は次のとおりである。

```text
FINAL_INTERNAL_VALIDATION = PASS
PROJECT_INTERNAL_VALIDATION_PROGRAM = CLOSED_WITH_SCOPE
ACTIVE_INTERNAL_SCIENTIFIC_BRANCH = NONE
STOP_CURRENT_FROZEN_EVIDENCE = YES
EXTERNAL_REPLICATION_AND_OFFICIAL_PRODUCT_GATES = OPEN
PUBLICATION_DRAFTING = NOT_PERFORMED
```
