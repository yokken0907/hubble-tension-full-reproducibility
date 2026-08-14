# Blind Execution Contract

## 1. Classification

- `TASK_TYPE = PROJECT_INTERNAL_ALTERNATE_IMPLEMENTATION`
- `BLIND_TO_PRIOR_NUMERICAL_RESULTS = YES`
- `EXTERNAL_SCIENTIFIC_VALIDATION = NO`
- `NEW_PHYSICAL_CLAIM = NO`
- `SCIENTIFIC_INTERPRETATION = NO`

This is an implementation-diversity check. It is not an independent external
replication and must not be described as one.

## 2. Permitted inputs

Only the following package contents may be used:

- `INPUTS/ULambdaCDM1.h5`
- `INPUTS/LambdaCDM2b.h5`
- `INPUTS/LambdaCDM2d.h5`
- `SOURCE_MANIFEST.tsv`
- this contract and `OUTPUT_SCHEMA.md`

## 3. Prohibited information and actions

Do not:

- browse the web;
- retrieve the source repository or paper;
- search for TDCOSMO numerical results;
- use any previous HTS68 code, output, report, table, correction patch, or
  identifier crosswalk;
- ask the user for expected values;
- tune the implementation after comparison with an expected result;
- perform weighted posterior calculations;
- infer or report agreement/disagreement with a paper;
- make a Hubble-tension or cosmological claim.

If any prohibited information is encountered, stop and record
`BLINDNESS_COMPROMISED = YES` without continuing the numerical comparison.

## 4. Source-integrity gate

Before opening any HDF5 file, independently calculate SHA256 for all three
inputs and require exact equality with `SOURCE_MANIFEST.tsv`.

A mismatch is a hard stop:

- `SOURCE_HASH_GATE = FAIL`
- do not open or analyze the mismatching file.

## 5. Required HDF5 audit

For each file, inspect the file itself and record:

1. top-level object names and object types;
2. all file-level attributes, represented without alteration;
3. shape and dtype of each top-level dataset;
4. decoded parameter names and their zero-based column indices;
5. whether parameter names are unique;
6. whether `samples` is two-dimensional;
7. whether the number of sample columns equals the number of parameter names;
8. whether there is exactly one parameter whose decoded name is exactly `h0`;
9. sample count and parameter count;
10. whether every value in the `h0` column is finite.

The H0 column must be selected from the decoded `parameters` dataset only.
Do not select a column by a hard-coded numeric index.

## 6. Quantile definition

Use every row with equal weight. Do not thin, resample, reweight, or discard
finite values.

For each probability p in {0.16, 0.50, 0.84}, use the following deterministic
linear interpolation rule:

1. Sort the finite H0 values in ascending order as x[0], ..., x[n-1].
2. Compute h = (n - 1) * p.
3. Let i = floor(h), j = ceil(h).
4. Return q(p) = x[i] + (h - i) * (x[j] - x[i]).

This is equivalent to the common Type-7 / `linear` quantile definition.

Output floating-point values with enough precision to round-trip a binary64
value (for example, 17 significant decimal digits).

## 7. Implementation independence

Write a new implementation from this specification. Do not reconstruct,
translate, or imitate any unavailable prior implementation.

The implementation language is unrestricted. The result package must contain
all source code and exact execution commands.

## 8. Pre-registered later comparison rule

The blind implementation itself must not perform this comparison. The separate
audit thread will compare results only after the output ZIP is frozen.

The comparison rule is fixed in advance:

- source hashes: exact string equality;
- names, shapes, attributes and indices: exact equality after UTF-8 decoding;
- quantiles: `abs(delta) <= 1e-10` OR
  `abs(delta) <= 1e-12 * max(abs(a), abs(b))`;
- no post-result adjustment of tolerance.

## 9. Required terminal state

Create exactly one archive named:

`TDCOSMO_BLIND_SENTINEL_RESULTS_FOR_REVIEW.zip`

The archive must conform to `OUTPUT_SCHEMA.md`, include an internal
`SHA256SUMS.txt`, and contain no paper comparison or PASS claim relative to
prior work.
