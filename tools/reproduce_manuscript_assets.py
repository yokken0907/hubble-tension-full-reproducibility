#!/usr/bin/env python3
from pathlib import Path
import csv, json, argparse, tempfile
from decimal import Decimal

ROOT=Path(__file__).resolve().parents[1]
PE=ROOT/"publication_evidence"

def write_tsv(path, fields, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline="") as f:
        cw=csv.DictWriter(f,fields,delimiter="\t",lineterminator="\n")
        cw.writeheader(); cw.writerows(rows)

def load_json(rel):
    return json.loads((PE/rel).read_text(encoding="utf-8"))

def public_matrix_rows():
    src=PE/"evidence/cross_season/EVIDENCE_COORDINATE_MATRIX.tsv"
    rows=list(csv.DictReader(src.open(encoding="utf-8"),delimiter="\t"))
    smap={"PASS":"SUPPORTED","MIXED":"PARTIAL","HOLD":"UNRESOLVED","FAIL":"NOT_PRESERVED","NOT_TESTED":"NOT_EVALUATED"}
    dims=[
      ("F0_status","data_product_identity"),
      ("F1_status","numerical_output_traceability"),
      ("F2_status","relation_between_representations"),
      ("F3_status","target_inference_preservation"),
      ("F4_status","diagnostic_information_retention"),
      ("F5_status","computational_provenance"),
      ("F6_status","generative_or_causal_support"),
    ]
    out=[]
    for r in rows:
        q={"case_id":r["case_id"],"case_name":r["case_name"]}
        for old,new in dims: q[new]=smap[r[old]]
        rationale=r["rationale"].replace("frozen ","fixed-version ").replace("Frozen ","Fixed-version ").replace("same-CID","same-name").replace("Same-CID","Same-name")
        limitation=r["limitation"].replace("frozen ","fixed-version ").replace("Frozen ","Fixed-version ").replace("same-CID","same-name").replace("Same-CID","Same-name")
        q.update(rationale=rationale,supporting_artifact=r["supporting_artifact"],limitation=limitation)
        out.append(q)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,default=None,help="Output directory (default: new temporary directory outside repository)")
    a=ap.parse_args()
    out=a.output if a.output is not None else Path(tempfile.mkdtemp(prefix="hubble-tension-publication-assets-"))
    out.mkdir(parents=True,exist_ok=True)

    t1=[
      dict(topic="Local ladder / BBC",examined_object="Released corrected vector and structural decompositions",supported_result="A reported fixed-effect slope was algebraically localized to the explicit BBC term plus a near-zero bias-removed proxy",not_established="No end-to-end truth-level validation, BBC overcorrection, or causal defect",evidence_needed="Matched truth, fit, pre/post vectors, covariance, and run manifest",claim_id="P-FS-002"),
      dict(topic="BAO-BBN bridge",examined_object="Fixed H0*r_d relation",supported_result="Approximate -6.8% local-H0 sound-horizon budget",not_established="Model- and definition-dependent budget, not new physics",evidence_needed="Matched early-model likelihood or profile products",claim_id="P-FS-003"),
      dict(topic="CMB-DESI geometry",examined_object="Released constraints and response directions",supported_result="Near-common Omega_m-h*r_d direction described",not_established="Shared-source geometry is not an independent causal explanation",evidence_needed="Joint simulations, cross-CMB covariance, full posteriors",claim_id="P-FS-004"),
      dict(topic="DESI response-direction analysis",examined_object="Same released vector under mode decompositions",supported_result="An intermediate-redshift common-isotropic BAO response direction was high leverage in the released vector; a response direction in the first luminous-red-galaxy bin provided a contrast",not_established="Multiple bases are not multiple observations or raw-pipeline tests",evidence_needed="Aligned raw variants and joint/cross-fit covariance",claim_id="P-FS-005"),
      dict(topic="ACT variants",examined_object="Official public chains",supported_result="Tested centers were stable within a correlated-source variant set",not_established="Not a complete component-likelihood analysis",evidence_needed="New independent product or exact component likelihood",claim_id="P-FS-006"),
      dict(topic="TDCOSMO",examined_object="Public chain products",supported_result="Alternate implementation recovered 13/13 structures, 39/39 quantiles within tolerance, and 12/12 Table 6 rows at published precision",not_established="Output-level traceability only; not likelihood, sampler, or astrophysical-model reproduction",evidence_needed="Original likelihood, sampler configuration, diagnostics, and portable environment",claim_id="P-FS-008"),
      dict(topic="Local flow / MCP-CF4",examined_object="Publicly released local-flow products",supported_result="Single-galaxy dominance was rejected within the specified tests; dependencies were mapped",not_established="Joint-flow inference remains open",evidence_needed="Distance samples, joint covariance, zero-point cross-covariance, likelihood",claim_id="P-FS-009"),
      dict(topic="H0DN network",examined_object="Public data, design matrix, covariance, and solver specification",supported_result="Baseline and fixed-representation solver behavior were recovered",not_established="Correlated peculiar-velocity and covariance generation remain incomplete",evidence_needed="Official source matrix/removal vector or author package",claim_id="P-FS-010"),
      dict(topic="Methods",examined_object="Non-ladder routes",supported_result="Shared assumptions and data were mapped",not_established="No naive averaging of dependent analyses",evidence_needed="Compatible likelihood specifications and cross-route covariance",claim_id="P-FS-011"),
    ]
    write_tsv(out/"MAIN_TABLE1_BROAD_DEPENDENCY_CLUSTERS.tsv",list(t1[0]),t1)

    t2=[
      dict(case="TDCOSMO chains",supported_result="Structure, quantiles, printed Table 6 values",not_established="Original likelihood/sampler or astrophysical validation",key_unresolved_requirement="Portable likelihood and sampling environment",claim_id="P-FS-008"),
      dict(case="GWTC-4/5 v1",supported_result="Six headline percentiles and displayed intervals",not_established="Exact reproduction of the published v1 25.7% uncertainty reduction from the examined public headline pair",key_unresolved_requirement="Public legacy product or numerical realization that yields 25.7% under the stated 68%-CI average-uncertainty metric",claim_id="P-SS-001;P-SS-002"),
      dict(case="Pantheon+ BBC",supported_result="Final-vector identity and downstream algebraic localization",not_established="End-to-end truth-level correction validation or overcorrection claim",key_unresolved_requirement="Versioned truth-to-fit-to-pre/post-to-covariance bundle and executed configuration",claim_id="P-SS-003"),
      dict(case="H0DN covariance",supported_result="Baseline, rank, cutoff stability, and off-support projected-loss test",not_established="General non-invariance, corrected H0, or physical cause",key_unresolved_requirement="Covariance generative model, unrounded inputs, and external replication",claim_id="P-SS-004;P-SS-006"),
      dict(case="SN compression",supported_result="One-intercept target likelihood",not_established="Residual adequacy or pattern",key_unresolved_requirement="Residual-level diagnostics relevant to the question",claim_id="P-SS-007"),
      dict(case="Same-name residual and provenance analysis",supported_result="Residual localization and extensive public candidate mapping",not_established="Exact production history, dependence, or cause",key_unresolved_requirement="Versioned run manifest and row-level production provenance",claim_id="P-SS-008;P-SS-009"),
    ]
    write_tsv(out/"MAIN_TABLE2_PRINCIPAL_DISTINCTIONS.tsv",list(t2[0]),t2)

    f1=[
      dict(order=1,node="Initial broad survey",role="Dependency and public-product traceability map"),
      dict(order=2,node="Focused public-product analyses",role="GWTC, Pantheon+ BBC, H0DN covariance, and supernova diagnostics"),
      dict(order=3,node="Consistency review",role="Align claims, source products, numerical specifications, quantities, and versions"),
      dict(order=4,node="Final validation",role="Retest the numerical and logical mechanisms most relevant to the publication"),
      dict(order=5,node="Publication synthesis",role="Report supported conclusions and evidential limits without introducing a new scientific analysis"),
    ]
    write_tsv(out/"MAIN_FIGURE1_ANALYSIS_PROGRESSION.tsv",list(f1[0]),f1)

    m=public_matrix_rows()
    write_tsv(out/"MAIN_FIGURE2_REPRODUCIBILITY_EVIDENCE_MATRIX.tsv",list(m[0]),m)

    iv=load_json("results/internal_validation_results_recorded.json")
    methods=iv["h0dn"]["methods"]
    order=["scipy_pinv","svd_gesvd","eigh_evd","support_gelsy"]
    ta=[]
    for k in order:
        x=methods[k]
        fmt14=lambda v: str(Decimal(str(v)).quantize(Decimal("0.00000000000001")))
        ta.append(dict(path=x["label"],baseline_h0=fmt14(x["h0_original"]),transformed_h0=fmt14(x["h0_standardized"]),delta_h0=fmt14(x["delta_h0"])))
    write_tsv(out/"SUPPA_TABLE_A1_SOLVER_CHECKS.tsv",list(ta[0]),ta)

    exp=load_json("evidence/EXPECTED_PRINCIPAL_RESULTS.json")
    fa=[
      dict(state="Public baseline",h0=exp["h0dn"]["h0"],context_sigma=exp["h0dn"]["sigma_h0"],interpretation="Fixed public code/data/numerical specification"),
      dict(state="Row-rescaled projected loss",h0=exp["h0dn"]["h0"]+exp["h0dn"]["off_support_projected_loss_delta_h0"],context_sigma=exp["h0dn"]["sigma_h0"],interpretation="Off-support projected-loss diagnostic; not an independent measurement"),
    ]
    write_tsv(out/"SUPPA_FIGURE_A1_SOURCE.tsv",list(fa[0]),fa)

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
      dict(variant="Full fixed covariance",chi2_display="11.209315063602716",chi2_raw=cov["PHASE1A_FULL"]["chi2"],df=39,interpretation="Low; primary result"),
      dict(variant="No rowwise velocity term",chi2_display="14.734236",chi2_raw=cov["STAT_SYS_NO_ROWWISE_VELOCITY"]["chi2"],df=39,interpretation="Low statistic persists"),
      dict(variant="Pantheon+ statistical-only (STATONLY) covariance",chi2_display="16.233447508593247",chi2_raw=cov["STAT_ONLY"]["chi2"],df=39,interpretation="p=4.856832550848106e-4 under specified tail calculation"),
    ]
    write_tsv(out/"SUPPB_TABLE_B2_COVARIANCE_VARIANTS.tsv",list(b2[0]),b2)

    fb1=[
      dict(item="intercept",value=exp["sn_compression"]["intercept"],meaning="center of fixed one-intercept likelihood"),
      dict(item="standard_error",value=exp["sn_compression"]["standard_error"],meaning="curvature scale"),
      dict(item="omitted_residual_chi2",value=exp["sn_compression"]["omitted_residual_chi2"],meaning="parameter-independent residual term"),
      dict(item="fixture_residual_chi2_first",value=exp["sn_compression"]["synthetic_residual_chi2_first"],meaning="same compression, residual pattern A"),
      dict(item="fixture_residual_chi2_second",value=exp["sn_compression"]["synthetic_residual_chi2_second"],meaning="same compression, residual pattern B"),
    ]
    write_tsv(out/"SUPPB_FIGURE_B1_SOURCE.tsv",list(fb1[0]),fb1)

    fb2=[
      dict(order=1,stage="Public candidate photometric inputs",status="PARTIAL_THEN_COMPLETE_CANDIDATE_COVERAGE",detail="38/69 direct; remaining 31 connected under target-excluded survey mapping; combined 69/69"),
      dict(order=2,stage="Observation payload comparison",status="BOUNDED",detail="0/48 byte-exact reuse; 4/48 single-rounding numeric compatibility"),
      dict(order=3,stage="Filter assets",status="MAPPED",detail="434/434 row-filter records; 6744/6744 observations covered"),
      dict(order=4,stage="Public configuration references",status="MAPPED",detail="7/7 data series"),
      dict(order=5,stage="Executed BBC intermediates to final corrected row",status="UNRESOLVED",detail="Unique executed manifest and row-level production provenance not recovered"),
    ]
    write_tsv(out/"SUPPB_FIGURE_B2_PROVENANCE_FRONTIER.tsv",list(fb2[0]),fb2)

    print(f"status=PASS output={out} files={len(list(out.glob('*.tsv')))}")

if __name__=="__main__":
    main()
