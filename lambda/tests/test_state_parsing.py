import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.state_parsing import CONTIGUOUS_STATES, parse_distribution_pattern


def test_multi_state_abbreviations():
    result = parse_distribution_pattern("FL, MI, MS, and OH.")
    assert result["affected_states"] == ["FL", "MI", "MS", "OH"]
    assert result["is_nationwide"] is False


def test_nationwide():
    result = parse_distribution_pattern("Distributed nationwide through retail stores.")
    assert result["is_nationwide"] is True
    assert set(result["affected_states"]) == CONTIGUOUS_STATES
    assert len(result["affected_states"]) == 51  # 50 states + DC


def test_state_of_california():
    result = parse_distribution_pattern("State of California")
    assert result["affected_states"] == ["CA"]
    assert result["is_nationwide"] is False


def test_mixed_nationwide_and_states():
    result = parse_distribution_pattern("NY, NJ, CT, PA, and online sales nationwide")
    assert result["is_nationwide"] is True
    assert set(result["affected_states"]) == CONTIGUOUS_STATES


def test_empty_pattern():
    result = parse_distribution_pattern("")
    assert result == {"affected_states": [], "is_nationwide": False}


def test_retail_distribution_phrase():
    result = parse_distribution_pattern("Distributed in TX and LA through retail stores")
    assert result["affected_states"] == ["LA", "TX"]
    assert result["is_nationwide"] is False
