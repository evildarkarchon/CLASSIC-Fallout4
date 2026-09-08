"""Source reports distinguish intentional binding ownership from actual drift."""

import check_parity_gate as gate


def test_binding_only_rows_do_not_report_source_drift():
    """An explicit unmapped core owner keeps its runtime duty, not a source mismatch."""
    report = {
        "summary": {
            "tier1_contract_total": 1,
            "tier1_matched": 0,
            "tier1_missing_rust": 0,
            "tier1_missing_python": 0,
            "tier1_signature_mismatch": 0,
            "tier1_gap_total": 0,
        },
        "contract_results": [{"status": "unmapped"}],
    }
    assert "Tier-1 gate passed." in gate.render_tier1_gate_markdown(report)
