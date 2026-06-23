import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.analytics_utils import to_dynamodb_item


def test_to_dynamodb_item_converts_nested_floats_to_decimal():
    item = {
        "PK": "TREND#MONTHLY",
        "total_recalls": 4,
        "avg_count": 1.25,
        "nested": [{"pct_closed": 33.3}],
    }

    result = to_dynamodb_item(item)

    assert result["total_recalls"] == 4
    assert result["avg_count"] == Decimal("1.25")
    assert result["nested"][0]["pct_closed"] == Decimal("33.3")
