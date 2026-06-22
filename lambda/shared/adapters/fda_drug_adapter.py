from typing import List

from shared.adapters.base_adapter import BaseRecallAdapter
from shared.models import CanonicalRecallRecord


class FDADrugAdapter(BaseRecallAdapter):
    SOURCE_NAME = "FDA_DRUG"
    CATEGORY = "DRUG"
    API_BASE_URL = "https://api.fda.gov/drug/enforcement.json"

    def fetch_raw_records(self, since_date: str = None, limit: int = 100) -> List[dict]:
        date_start = self.yyyymmdd(since_date) if since_date else "20200101"
        data = self.get_json(
            {
                "search": f"report_date:[{date_start}+TO+20991231]",
                "limit": min(limit, 100),
            }
        )
        return data.get("results", []) if isinstance(data, dict) else []

    def normalize(self, raw: dict) -> CanonicalRecallRecord:
        distribution = raw.get("distribution_pattern", "")
        reason = raw.get("reason_for_recall", "")
        return CanonicalRecallRecord(
            source=self.SOURCE_NAME,
            source_recall_id=raw.get("recall_number", raw.get("event_id", "")),
            title=reason[:120],
            description=reason,
            classification=raw.get("classification", ""),
            status=raw.get("status", ""),
            recall_date=self.iso_from_yyyymmdd(raw.get("report_date", "")),
            company=raw.get("recalling_firm", ""),
            product_description=raw.get("product_description", ""),
            distribution=distribution,
            states=self.parse_states(distribution),
            category=self.CATEGORY,
            hazard_type=self._infer_drug_hazard(reason),
            quantity=raw.get("product_quantity", ""),
            source_url=f"https://api.fda.gov/drug/enforcement.json?search=recall_number:{raw.get('recall_number', '')}",
            source_metadata={
                "city": raw.get("city", ""),
                "state": raw.get("state", ""),
                "country": raw.get("country", ""),
                "voluntary_mandated": raw.get("voluntary_mandated", ""),
                "code_info": raw.get("code_info", ""),
                "openfda": raw.get("openfda", {}),
            },
        )

    def _infer_drug_hazard(self, reason: str) -> str:
        reason_lower = (reason or "").lower()
        if any(word in reason_lower for word in ["cgmp", "gmp", "manufacturing"]):
            return "Manufacturing Defect"
        if any(word in reason_lower for word in ["contamina", "impurity", "particulate"]):
            return "Contamination"
        if any(word in reason_lower for word in ["label", "misbranded", "incorrect"]):
            return "Mislabeling"
        if any(word in reason_lower for word in ["potency", "subpotent", "superpotent", "dissolution"]):
            return "Potency Issue"
        if any(word in reason_lower for word in ["sterility", "non-sterile"]):
            return "Sterility Failure"
        return "Other"
