#!/usr/bin/env python3
from pathlib import Path
import csv, json, argparse, shutil
from decimal import Decimal

ROOT=Path(__file__).resolve().parents[1]
PE=ROOT/"publication_evidence"

def write_tsv(path, fields, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fields,delimiter="\t")
        w.writeheader(); w.writerows(rows)

def load_json(rel):
    return json.loads((PE/rel).read_text(encoding="utf-8"))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,default=ROOT/"_reproduced/manuscript_assets")
    a=ap.parse_args()
    out=a.output; out.mkdir(parents=True,exist_ok=True)

    # Main Table 1: exact scientific row content, each row keyed to its evidence claim.
    t1=[
      dict(cluster="Local ladder / BBC",audited_object="Released corrected vector and structural decompositions",established="A recorded fixed-effect slope was algebraically localized to the explicit BBC term plus a near-zero bias-removed proxy",boundary="No truth-level closure, BBC overcorrection, or causal defect",reentry="Matched truth, fit, pre/post vectors, covariance, and run manifest",claim_id="P-FS-002"),
      dict(cluster="BAO-BBN bridge",audited_object="Frozen H0*r_d contract",established="Approximate -6.8% local-H0 sound-horizon budget",boundary="Contract-dependent budget, not new physics",reentry="Matched early-model likelihood or profile products",claim_id="P-FS-003"),
      dict(cluster="CMB-DESI geometry",audited_object="Released constraints and response directions",established="Near-common Omega_m-h*r_d direction described",boundary="Shared-source geometry is not an independent causal explanation",reentry="Joint simulations, cross-CMB covariance, full posteriors",claim_id="P-FS-004"),
      dict(cluster="DESI influence atlas",audited_object="Same released vector under mode decompositions",established="MIDZ_COMMON_ISO was a high-leverage released-vector mode; LRG1_DM provided a counter-anchor",boundary="Multiple bases are not multiple observations or raw-pipeline tests",reentry="Aligned raw variants and joint/cross-fit covariance",claim_id="P-FS-005"),
      dict(cluster="ACT variants",audited_object="Official public chains",established="Tested centers were stable within a correlated-source variant set",boundary="Not a complete component-likelihood audit",reentry="New independent product or exact component likelihood",claim_id="P-FS-006"),
      dict(cluster="TDCOSMO",audited_object="Public chain products",established="Alternate implementation recovered 13/13 structures, 39/39 quantiles within tolerance, and 12/12 Table 6 rows at published precision",boundary="Output-level traceability only; not likelihood, sampler, or astrophysical-model reproduction",reentry="Original likelihood, sampler configuration, diagnostics, and portable environment",claim_id="P-FS-008"),
      dict(cluster="Local flow / MCP-CF4",audited_object="Public route interface",established="Single-galaxy dominance was rejected within the frozen tests; dependencies were mapped",boundary="Joint-flow inference remains open",reentry="Distance samples, joint covariance, zero-point cross-covariance, likelihood",claim_id="P-FS-009"),
      dict(cluster="H0DN network",audited_object="Public data, design, covariance, and code contract",established="Baseline and frozen-representation solver behavior were recovered",boundary="Correlated peculiar-velocity and covariance generation remain incomplete",reentry="Official source matrix/removal vector or author package",claim_id="P-FS-010"),
      dict(cluster="Cross-route synthesis",audited_object="Non-ladder routes",established="Shared assumptions and data were mapped",boundary="No naive averaging of dependent branches",reentry="Compatible likelihood contracts and cross-route covariance",claim_id="P-FS-011"),
    ]
    write_tsv(out/"MAIN_TABLE1_FIRST_SEASON_CLUSTERS.tsv",list(t1[0]),t1)

    t2=[
      dict(case="TDCOSMO chains",what_passed="Structure, quantiles, printed Table 6 values",what_did_not_follow="Original likelihood/sampler or astrophysical validation",unresolved="Portable likelihood and sampling environment",claim_id="P-FS-008"),
      dict(case="GWTC-4/5 v1",what_passed="Six headline percentiles and displayed intervals",what_did_not_follow="Provenance of the v1 25.7% historical metric",unresolved="Exact old comparator and mapping",claim_id="P-SS-001;P-SS-002"),
      dict(case="Pantheon+ BBC",what_passed="Final-vector identity and downstream algebraic localization",what_did_not_follow="Truth-level correction closure or overcorrection claim",unresolved="Versioned truth->fit->pre/post->covariance bundle",claim_id="P-SS-003"),
      dict(case="H0DN covariance",what_passed="Baseline, rank, cutoff stability, and off-support projected-loss test",what_did_not_follow="General non-invariance, corrected H0, or physical cause",unresolved="Covariance generative model, unrounded inputs, and external replication",claim_id="P-SS-004;P-SS-006"),
      dict(case="SN compression",what_passed="One-intercept target likelihood",what_did_not_follow="Residual adequacy or pattern",unresolved="Retained residual diagnostics for the question asked",claim_id="P-SS-007"),
      dict(case="Same-CID lineage",what_passed="Residual localization and extensive public candidate mapping",what_did_not_follow="Executed ancestry, dependence, or cause",unresolved="Exact run manifest and final-row ancestry",claim_id="P-SS-008;P-SS-009"),
    ]
    write_tsv(out/"MAIN_TABLE2_PRINCIPAL_DISTINCTIONS.tsv",list(t2[0]),t2)

    # Figure 1 source graph
    f1=[
      dict(order=1,node="First Season",role="Broad dependency map"),
      dict(order=2,node="Second Season",role="Focused public-product audits"),
      dict(order=3,node="Cross-Season Audit",role="Proposition/scope alignment"),
      dict(order=4,node="Final Internal Validation",role="Highest-information mechanism retests"),
      dict(order=5,node="STOP",role="No further same-frozen-evidence internal analysis"),
      dict(order=6,node="Publication",role="Downstream synthesis; no scientific reopening"),
    ]
    write_tsv(out/"MAIN_FIGURE1_AUDIT_PROGRESSION.tsv",list(f1[0]),f1)

    # Figure 2 is directly the frozen coordinate matrix.
    shutil.copy2(PE/"evidence/cross_season/EVIDENCE_COORDINATE_MATRIX.tsv",out/"MAIN_FIGURE2_EVIDENCE_COORDINATE_MATRIX.tsv")

    iv=load_json("results/internal_validation_results_recorded.json")
    methods=iv["h0dn"]["methods"]
    order=["scipy_pinv","svd_gesvd","eigh_evd","support_gelsy"]
    ta=[]
    for k in order:
        m=methods[k]
        fmt14=lambda x: str(Decimal(str(x)).quantize(Decimal("0.00000000000001")))
        ta.append(dict(path=m["label"],baseline_h0=fmt14(m["h0_original"]),transformed_h0=fmt14(m["h0_standardized"]),delta_h0=fmt14(m["delta_h0"])))
    write_tsv(out/"SUPPA_TABLE_A1_SOLVER_CHECKS.tsv",list(ta[0]),ta)

    exp=load_json("evidence/EXPECTED_PRINCIPAL_RESULTS.json")
    fa=[
      dict(state="Frozen baseline",h0=exp["h0dn"]["h0"],context_sigma=exp["h0dn"]["sigma_h0"],interpretation="Frozen public contract"),
      dict(state="Row-standardized projected loss",h0=exp["h0dn"]["h0"]+exp["h0dn"]["off_support_projected_loss_delta_h0"],context_sigma=exp["h0dn"]["sigma_h0"],interpretation="Off-support projected-loss diagnostic; not independent measurement"),
    ]
    write_tsv(out/"SUPPA_FIGURE_A1_SOURCE.tsv",list(fa[0]),fa)

    same=load_json("results/audit_summary.json")
    total=exp["sn_compression"]["omitted_residual_chi2"]
    within=exp["same_cid"]["phase1a_full_chi2"]
    between=total-within
    b1=[
      dict(component="Same-name/multirow contrasts",chi2=f"{within:.15f}",df=39,share_percent=f"{100*within/total:.2f}"),
      dict(component="Between-name modes",chi2=f"{between:.14f}",df=237,share_percent=f"{100*between/total:.2f}"),
      dict(component="Total",chi2=f"{total:.12f}",df=276,share_percent="100.00"),
    ]
    write_tsv(out/"SUPPB_TABLE_B1_RESIDUAL_LOCALIZATION.tsv",list(b1[0]),b1)

    cov=load_json("results/covariance_baselines.json")
    b2=[
      dict(variant="Full frozen covariance",chi2_display="11.209315063602716",chi2_raw=cov["PHASE1A_FULL"]["chi2"],df=39,interpretation="Low; canonical result"),
      dict(variant="No rowwise velocity term",chi2_display="14.734236",chi2_raw=cov["STAT_SYS_NO_ROWWISE_VELOCITY"]["chi2"],df=39,interpretation="Low flag persists"),
      dict(variant="STATONLY covariance",chi2_display="16.233447508593247",chi2_raw=cov["STAT_ONLY"]["chi2"],df=39,interpretation="p=4.856832550848106e-4 under registered tail rule"),
    ]
    write_tsv(out/"SUPPB_TABLE_B2_COVARIANCE_VARIANTS.tsv",list(b2[0]),b2)

    fx=load_json("evidence/final_validation/exact_fixtures/SN_EQUAL_COMPRESSION_UNEQUAL_RESIDUAL_FIXTURE.json")
    fb1=[
      dict(item="frozen_intercept",value=exp["sn_compression"]["intercept"],meaning="center of fixed one-intercept likelihood"),
      dict(item="frozen_standard_error",value=exp["sn_compression"]["standard_error"],meaning="curvature scale"),
      dict(item="omitted_residual_chi2",value=exp["sn_compression"]["omitted_residual_chi2"],meaning="parameter-independent residual term"),
      dict(item="fixture_residual_chi2_first",value=exp["sn_compression"]["synthetic_residual_chi2_first"],meaning="same compression, residual pattern A"),
      dict(item="fixture_residual_chi2_second",value=exp["sn_compression"]["synthetic_residual_chi2_second"],meaning="same compression, residual pattern B"),
    ]
    write_tsv(out/"SUPPB_FIGURE_B1_SOURCE.tsv",list(fb1[0]),fb1)

    fb2=[
      dict(order=1,stage="Public candidate photometric inputs",status="PARTIAL_THEN_COMPLETE_CANDIDATE_COVERAGE",detail="38/69 direct; remaining 31 bridged under target-excluded survey mapping; combined 69/69"),
      dict(order=2,stage="Observation payload comparison",status="BOUNDED",detail="0/48 byte-exact reuse; 4/48 single-rounding numeric compatibility"),
      dict(order=3,stage="Filter assets",status="MAPPED",detail="434/434 row-filter records; 6744/6744 observations covered"),
      dict(order=4,stage="Configuration-level anchors",status="MAPPED",detail="7/7 data series"),
      dict(order=5,stage="Executed BBC intermediates to final m_b_corr row",status="HOLD",detail="unique executed manifest/ancestry not recovered"),
    ]
    write_tsv(out/"SUPPB_FIGURE_B2_LINEAGE_FRONTIER.tsv",list(fb2[0]),fb2)

    print(f"status=PASS output={out} files={len(list(out.glob('*.tsv')))}")

if __name__=="__main__":
    main()
