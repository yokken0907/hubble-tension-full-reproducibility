#!/usr/bin/env python3
from __future__ import annotations
import tempfile
from pathlib import Path
import hts66_common as c

def main():
    assert sorted(c.STAGES) == [59,60,61,62,63,64,65]
    assert len(c.STAGES) == 7
    rows = [
        {"edge":"E","direction":"FORWARD","burn_fraction_per_chain":"0.3"},
        {"edge":"E","direction":"REVERSE","burn_fraction_per_chain":"0.3"},
    ]
    idx = c.index_rows(rows)
    assert len(idx) == 2
    assert c.key_of(rows[0]) == ("E","FORWARD",0.3)
    summary = {
        "near_degenerate_cluster_count": 1,
        "near_degenerate_cluster_members": "SPT_PR4:modes-2,3",
        "HTS64_basis_sensitive_directed_edge_count": 14,
        "HTS64_max_rotation_top_share_range": 0.4,
        "HTS65_partition_sensitive_directed_edge_count": 3,
        "HTS65_partition_stable_directed_edge_count": 11,
        "HTS65_max_variable_owen_share_range": 0.1,
    }
    hierarchy = c.invariant_hierarchy(summary,1e-13,1e-14,1e-15)
    assert len(hierarchy) == 7
    assert hierarchy[-1]["status"] == "CLOSE_AFTER_HTS66"
    print("HTS66 SELFTEST PASS")

if __name__ == "__main__":
    main()
