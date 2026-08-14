# HOLD・FROZEN_OPEN・再開条件

## 状態の意味

- `CLOSED_WITH_SCOPE`: 凍結した問いは閉じた。新しいsourceまたは別の問いなしに反復しない。
- `FROZEN_OPEN`: 科学的価値はあるが、必要な公開productが不足している。
- `HOLD`: 現行evidenceでは規約・source・独立性の問題を閉じられない。
- `EXTERNAL_REENTRY_ONLY`: 同じ材料の再分解ではなく、外部で正当化された新情報が必要。

## 優先再開条件

1. **Pantheon+ BBC truth closure**  
   truth-level BiasCor、aligned truth/fitted、pre/post vector、matched covariance。
2. **DESI MIDZ common-mode raw robustness**  
   aligned reconstruction/fiducial/weight/mock variantsとjoint/cross-fit covariance。
3. **GWTC posterior metric**  
   official posterior filesのlocal hash freezeとmatched population/parameter contract。
4. **MCP/CF4 joint flow**  
   constrained-realization covariance、distance samples、zero-point cross-covariance、likelihood。
5. **H0DN correlated PV**  
   source repository、matrix、removal vector、またはauthor reproduction package。
6. **Lensed supernova**  
   更新photometry/lens model、新しいimage、または有用な長time delay。
7. **HTS67 metric question**  
   外部で正当化された共通metric、joint likelihood、component-separated posterior。

## TDCOSMO閉鎖後の再開

TDCOSMO alternate-implementation branchは、外部独立実装、元likelihood/sampler環境、
source-integrity問題、materially changed release、または新しい狭い反証可能質問がある場合のみ
再考する。単に全28 fileへ広げる、plotを増やす、stage数を増やすことは再開理由にならない。

## 自動実行

本マスターは再開条件を記録するが、どの枝にも自動実行を許可しない。
