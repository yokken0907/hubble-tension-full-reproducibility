# Method Note

- Implementation language: Python 3.13.5.
- Libraries: NumPy 2.3.5; h5py 3.15.1.
- Byte-string decoding: every element of the `parameters` dataset was decoded exactly with UTF-8; byte-valued file attributes, if present, were also decoded with UTF-8 for valid JSON representation.
- H0 location: the zero-based column index was obtained only by finding the unique decoded parameter name exactly equal to `h0`; no numeric column index was hard-coded.
- Quantile algorithm: all H0 rows were used with equal weight. Values were sorted ascending. For each p in {0.16, 0.50, 0.84}, h = (n - 1) * p, i = floor(h), j = ceil(h), and q(p) = x[i] + (h - i) * (x[j] - x[i]).
- Serialization: `top_level_objects` is compact JSON listing each sorted top-level name and its HDF5 object type. `file_attributes_json` is compact valid JSON containing every file-level attribute; JSON escaping preserves embedded newlines and other characters.
- Blindness confirmation: no external source, paper, repository, prior implementation, prior numerical result, expected value, correction patch, or identifier crosswalk was consulted.
- Weighting confirmation: no thinning, resampling, reweighting, or weighted posterior calculation was performed.
- Warning or deviation: none.
