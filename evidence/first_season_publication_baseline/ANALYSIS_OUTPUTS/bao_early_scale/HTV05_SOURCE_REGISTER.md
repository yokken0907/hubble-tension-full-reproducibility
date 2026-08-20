# Source Register

Accessed / fixed: 2026-07-20

## S01 DESI Collaboration

**DESI DR2 Results II: Measurements of Baryon Acoustic Oscillations and Cosmological Constraints**  
arXiv:2503.14738, version 3 / Phys. Rev. D 112, 083515 (2025)

Used for:
- definitions of r_d, D_M, D_H
- statement that BAO directly constrains D_M/r_d and D_H/r_d
- standard-r_d fitting relation
- DESI+BBN and DESI+CMB parameter results
- 2.3 sigma BAO-CMB discrepancy
- wCDM and w0waCDM data-swap matrix
- SN-sample dependence of dynamical-dark-energy preference

## S02 Official Cobaya BAO data

Repository: `CobayaSampler/bao_data`  
Directory: `desi_bao_dr2`

Files:
- `desi_gaussian_bao_ALL_GCcomb_mean.txt`
- `desi_gaussian_bao_ALL_GCcomb_cov.txt`

Used for:
- exact 13-element BAO Gaussian vector
- exact covariance
- independent two-parameter flat-LambdaCDM re-fit

## S03 DESI official DR2 cosmology data documentation

Used for:
- official release status of chains and maximization products
- definitions of external CMB, SN and BBN likelihood components
- recognition that common `CMB` combinations contain Planck primary data and
  Planck/ACT lensing rather than independent H0 votes

## S04 Riess et al. 2025

**The Perfect Host: JWST Cepheid Observations in a Background-Free SN Ia Host Confirm No Bias in Hubble-Constant Measurements**  
arXiv:2509.01667

Used for:
- H0 = 73.49 ± 0.93 local calibration input
- conditional required-r_d calculation

## Reproduction boundary

The BAO Gaussian fit is newly executed and reproducible from bundled files.

The BBN conversion is a fitting-formula sanity check, not a re-run of the
DESI CLASS/Cobaya likelihood.

The model-extension table is a transcription of published marginalized
constraints and was not re-sampled.
