# Execution environment

The historical HTV05 package records the Python implementation but not a fully frozen package environment. This reproduction contract, introduced in v1.6.1 and carried forward unchanged in v1.7.0, therefore records a tested compatible environment without claiming it is the original environment.

Tested compatible environment:

```text
Python 3.13.5
NumPy 2.3.5
SciPy 1.17.0
```

The calculation is a two-parameter Gaussian fit. It performs no MCMC, posterior reconstruction, observational correction, or new scientific analysis.
