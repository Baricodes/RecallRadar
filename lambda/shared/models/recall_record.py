from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class CanonicalRecallRecord:
    """Universal recall shape emitted by every source adapter."""

    source: str
    source_recall_id: str
    recall_id: str = ""
    title: str = ""
    description: str = ""
    classification: str = ""
    status: str = ""
    recall_date: str = ""
    company: str = ""
    product_description: str = ""
    distribution: str = ""
    states: list = field(default_factory=list)
    category: str = ""
    hazard_type: str = ""
    quantity: str = ""
    quantity_numeric: Optional[int] = None
    source_url: str = ""
    images: list = field(default_factory=list)
    ai_severity_score: Optional[int] = None
    ai_risk_summary: str = ""
    ai_hazard_tags: list = field(default_factory=list)
    source_metadata: dict = field(default_factory=dict)
    ingested_at: str = ""
    ttl: int = 0

    def __post_init__(self):
        self.source_recall_id = str(self.source_recall_id or "").strip()
        self.recall_id = self.recall_id or f"{self.source}#{self.source_recall_id}"
        if not self.ingested_at:
            self.ingested_at = datetime.now(timezone.utc).isoformat()
        if not self.ttl:
            self.ttl = int(datetime.now(timezone.utc).timestamp()) + (180 * 86400)

    def to_dynamodb_item(self) -> dict:
        """Convert the canonical record to a DynamoDB item with Phase 1 compatibility fields."""
        item = asdict(self)
        recall_date = self.recall_date or self.ingested_at[:10]
        report_date = recall_date.replace("-", "")
        is_nationwide = "Nationwide" in self.states
        affected_states = [] if is_nationwide else self.states

        item.update(
            {
                "PK": self.recall_id,
                "SK": recall_date,
                "GSI1PK": self.source,
                "GSI1SK": recall_date,
                "GSI2PK": self.category,
                "GSI2SK": recall_date,
                # Existing dashboard/API fields retained during the Phase 3 migration.
                "report_date": report_date,
                "recall_number": self.source_recall_id,
                "recalling_firm": self.company,
                "reason_for_recall": self.description,
                "distribution_pattern": self.distribution,
                "affected_states": affected_states,
                "is_nationwide": is_nationwide,
                "product_quantity": self.quantity,
            }
        )

        return {key: value for key, value in item.items() if value not in ("", None, [], {})}
