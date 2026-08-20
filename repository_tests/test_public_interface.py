from pathlib import Path
import csv

ROOT=Path(__file__).resolve().parents[1]

def test_repository_version_and_publication_pdf_policy():
    assert (ROOT/"VERSION").read_text(encoding="utf-8").strip()=="1.1"
    assert not (ROOT/"manuscript").exists()
    assert not list(ROOT.rglob("*.pdf"))

def test_claim_matrix_uses_documented_replay_classes():
    rows=list(csv.DictReader((ROOT/"docs/PAPER_REPRODUCTION_MATRIX.tsv").open(encoding="utf-8"),delimiter="\t"))
    allowed={"EXACT_REEXECUTION_WITH_PUBLIC_INPUTS","DETERMINISTIC_EVIDENCE_REPLAY","EXACT_DATA_FREE_FIXTURE","BOUNDED_TRACEABILITY_REPLAY"}
    assert len(rows)==33
    assert {r["reproduction_class"] for r in rows} <= allowed

def test_required_public_commands_exist():
    for rel in ["tools/verify_repository.py","tools/run_repository_tests.py","tools/run_offline_reproduction.py","tools/reproduce_manuscript_assets.py"]:
        assert (ROOT/rel).is_file()
