import hashlib
from datetime import datetime
from typing import List

from shared.adapters.base_adapter import BaseRecallAdapter
from shared.models import CanonicalRecallRecord


class USDAFSISAdapter(BaseRecallAdapter):
    SOURCE_NAME = "USDA"
    CATEGORY = "MEAT_POULTRY"
    API_BASE_URL = "https://www.fsis.usda.gov/fsis/api/recall/v/1"

    def fetch_raw_records(self, since_date: str = None, limit: int = 100) -> List[dict]:
        records = self.get_json(timeout=60)
        if not isinstance(records, list):
            return []
        if since_date:
            records = [
                record
                for record in records
                if record.get("field_recall_date", "") >= since_date
            ]
        return records[:limit]

    def normalize(self, raw: dict) -> CanonicalRecallRecord:
        risk_level = raw.get("field_risk_level", "")
        classification = {
            "High": "Class I",
            "Medium": "Class II",
            "Low": "Class III",
            "Marginal": "Class III",
        }.get(risk_level, risk_level or "Class III")
        states_raw = raw.get("field_states", "")
        states = [state.strip() for state in states_raw.split(",") if state.strip()]
        recall_date = self._parse_date(raw.get("field_recall_date", ""))
        recall_number = raw.get("field_recall_number") or self._fallback_id(raw, recall_date)

        return CanonicalRecallRecord(
            source=self.SOURCE_NAME,
            source_recall_id=recall_number,
            title=raw.get("field_title", "")[:200],
            description=raw.get("field_recall_reason", raw.get("field_title", "")),
            classification=classification,
            status="Ongoing" if raw.get("field_active_notice") == "True" else "Completed",
            recall_date=recall_date,
            company=raw.get("field_company_name", ""),
            product_description=raw.get("field_products", ""),
            distribution=states_raw or "Unknown",
            states=states or ["Unknown"],
            category=self.CATEGORY,
            hazard_type=self._infer_meat_hazard(raw),
            quantity=raw.get("field_quantity", ""),
            source_url="https://www.fsis.usda.gov/recalls-alerts",
            source_metadata={
                "risk_level_raw": risk_level,
                "establishment": raw.get("field_establishment", ""),
                "closed_date": raw.get("field_closed_date", ""),
                "archive_recall": raw.get("field_archive_recall", ""),
            },
        )

    def _parse_date(self, date_str: str) -> str:
        if not date_str:
            return ""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            return date_str[:10]

    def _fallback_id(self, raw: dict, recall_date: str) -> str:
        hash_input = f"{raw.get('field_title', '')}{recall_date}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]

    def _infer_meat_hazard(self, raw: dict) -> str:
        reason = (raw.get("field_recall_reason", "") or raw.get("field_title", "")).lower()
        if any(word in reason for word in ["listeria", "salmonella", "e. coli", "clostridium"]):
            return "Contamination - Biological"
        if any(word in reason for word in ["foreign", "metal", "plastic", "bone fragment"]):
            return "Contamination - Foreign Object"
        if any(word in reason for word in ["undeclared", "allergen", "mislabel"]):
            return "Mislabeling - Allergen"
        if any(word in reason for word in ["temperature", "undercooked", "undercook"]):
            return "Temperature Abuse"
        if "no inspection" in reason or "uninspected" in reason:
            return "Uninspected Product"
        return "Other"
