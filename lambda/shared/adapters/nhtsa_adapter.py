from typing import List

from shared.adapters.base_adapter import BaseRecallAdapter
from shared.models import CanonicalRecallRecord


class NHTSAAdapter(BaseRecallAdapter):
    SOURCE_NAME = "NHTSA"
    CATEGORY = "VEHICLE"
    API_BASE_URL = "https://data.transportation.gov/resource/aqh3-3rri.json"

    def fetch_raw_records(self, since_date: str = None, limit: int = 100) -> List[dict]:
        records = self.get_json(
            {
                "$limit": min(limit, 1000),
                "$order": "report_received_date DESC",
                "$where": f"report_received_date > '{since_date or self.default_since_date()}'",
            }
        )
        return records if isinstance(records, list) else []

    def normalize(self, raw: dict) -> CanonicalRecallRecord:
        raw_date = raw.get("report_received_date", "")
        make = raw.get("make", "Unknown")
        model = raw.get("model", "Unknown")
        year = raw.get("model_year", "")
        units_str = raw.get("potential_units_affected", "")
        quantity_numeric = self._parse_int(units_str)
        park_it = raw.get("park_it", "").lower() == "yes"
        park_outside = raw.get("park_outside", "").lower() == "yes"

        if park_it or park_outside:
            classification = "Class I"
        else:
            classification = self._severity_from_consequence(raw.get("consequence", ""))

        return CanonicalRecallRecord(
            source=self.SOURCE_NAME,
            source_recall_id=raw.get("nhtsa_campaign_number", ""),
            title=raw.get("subject", "")[:200],
            description=raw.get("summary", ""),
            classification=classification,
            status="Ongoing",
            recall_date=raw_date[:10],
            company=raw.get("manufacturer", ""),
            product_description=f"{year} {make} {model}".strip(),
            distribution="Nationwide",
            states=["Nationwide"],
            category=self.CATEGORY,
            hazard_type=self._infer_vehicle_hazard(raw),
            quantity=units_str,
            quantity_numeric=quantity_numeric,
            source_url="https://www.nhtsa.gov/recalls",
            source_metadata={
                "component": raw.get("component", ""),
                "consequence": raw.get("consequence", ""),
                "remedy": raw.get("remedy", ""),
                "make": make,
                "model": model,
                "model_year": year,
                "park_it": park_it,
                "park_outside": park_outside,
            },
        )

    def _parse_int(self, value: str):
        if not value:
            return None
        try:
            return int(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return None

    def _severity_from_consequence(self, consequence: str) -> str:
        consequence_lower = (consequence or "").lower()
        if any(word in consequence_lower for word in ["death", "fatal", "fire", "crash", "collision"]):
            return "Class I"
        if any(word in consequence_lower for word in ["injury", "loss of control", "stall"]):
            return "Class II"
        return "Class III"

    def _infer_vehicle_hazard(self, raw: dict) -> str:
        combined = f"{raw.get('component', '')} {raw.get('summary', '')}".lower()
        if any(word in combined for word in ["air bag", "airbag"]):
            return "Airbag Defect"
        if "brake" in combined:
            return "Brake Defect"
        if any(word in combined for word in ["fire", "fuel leak", "fuel line"]):
            return "Fire / Fuel Hazard"
        if "steering" in combined:
            return "Steering Defect"
        if any(word in combined for word in ["electrical", "wiring", "short circuit"]):
            return "Electrical Defect"
        if any(word in combined for word in ["seat belt", "seatbelt", "restraint"]):
            return "Restraint Defect"
        if any(word in combined for word in ["tire", "tyre"]):
            return "Tire Defect"
        if any(word in combined for word in ["engine", "power train", "stall"]):
            return "Powertrain Defect"
        if any(word in combined for word in ["software", "firmware"]):
            return "Software Defect"
        return "Other"
