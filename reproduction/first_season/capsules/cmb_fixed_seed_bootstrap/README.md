# E001 - CMB fixed-seed amplitude-bootstrap replay

This capsule replays the registered CMB amplitude-bootstrap calculations underlying N025 and N026. It begins from frozen Gaussian posterior moments rather than CMB spectra, likelihoods, chains, or the original posterior-generation environment.

## Fixed method

- implementation: `run_analysis.py`, ported without changing the scientific calculation;
- input: `inputs/FROZEN_GAUSSIAN_MOMENTS.tsv`;
- RNG: NumPy `default_rng`;
- seed: `10199`;
- bootstrap draws: `1000`;
- classification: `COMPLETE_WITH_SCOPE`.

## Run

```bash
python run_analysis.py --moments inputs/FROZEN_GAUSSIAN_MOMENTS.tsv --out _outputs --bootstrap-draws 1000 --seed 10199
python verify_output.py --output-dir _outputs
```

The replay reproduces the registered 2.05-sigma local descriptive contrast and 1.59-sigma omnibus result. It is project-internal computational replay, not external independent validation or reconstruction of the originating CMB likelihoods.

Fresh clean-replay log, environment, classification, and checksums are retained under `fresh_replay_records/`.
