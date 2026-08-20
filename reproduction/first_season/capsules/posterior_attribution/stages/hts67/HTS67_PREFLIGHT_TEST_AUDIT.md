# HTS67 preflight test audit

The synthetic self-test checks:

1. full 6D = tangent-normal 2D + conditional 4D distance-squared closure
2. fixed-block Shapley closure
3. exact endpoint-swap invariance for both symmetric metrics
4. valid canonical correlations
5. equality of arithmetic-covariance and precision-mean metrics when endpoint covariances are identical

The runtime independent audit reconstructs all saved symmetric rows and all leave-one-chain-out rows directly from the selected raw chains.
