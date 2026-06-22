from datetime import datetime
from typing import List

from shared.adapters.base_adapter import BaseRecallAdapter
from shared.models import CanonicalRecallRecord


class CPSCAdapter(BaseRecallAdapter):
    SOURCE_NAME = "CPSC"
    CATEGORY = "CONSUMER_PRODUCT"
    API_BASE_URL = "https://www.saferproducts.gov/RestWebServices/Recall"

    def fetch_raw_records(self, since_date: str = None, limit: int = 100) -> List[dict]:
        records = self.get_json(
            {
                "format": "json",
                "RecallDateStart": since_date or self.default_since_date(),
            },
            timeout=60,
        )
        return records[:limit] if isinstance(records, list) else []

    def normalize(self, raw: dict) -> CanonicalRecallRecord:
        products = raw.get("Products", [])
        manufacturers = raw.get("Manufacturers", [])
        hazards = raw.get("Hazards", [])
        injuries = raw.get("Injuries", [])

        product_desc = "; ".join(
            product.get("Name", "") or product.get("Description", "")
            for product in products
            if product.get("Name") or product.get("Description")
        )
        company = manufacturers[0].get("Name", "Unknown") if manufacturers else "Unknown"
        hazard_name = hazards[0].get("Name", "Unknown") if hazards else "Unknown"
        hazard_type = hazards[0].get("HazardType", "") if hazards else ""
        images = [image.get("URL", "") for image in raw.get("Images", []) if image.get("URL")]
        remedies = "; ".join(
            remedy.get("Name", "") for remedy in raw.get("Remedies", []) if remedy.get("Name")
        )

        return CanonicalRecallRecord(
            source=self.SOURCE_NAME,
            source_recall_id=str(raw.get("RecallID", "")),
            title=raw.get("Title", "")[:200],
            description=raw.get("Description", ""),
            classification=self._derive_cpsc_severity(hazard_name, injuries),
            status="Ongoing",
            recall_date=self._parse_cpsc_date(raw.get("RecallDate", "")),
            company=company,
            product_description=product_desc or raw.get("Title", ""),
            distribution="Nationwide",
            states=["Nationwide"],
            category=self.CATEGORY,
            hazard_type=hazard_type or hazard_name,
            quantity=raw.get("Units", ""),
            source_url=raw.get("URL", ""),
            images=images,
            source_metadata={
                "recall_number": raw.get("RecallNumber", ""),
                "manufacturers": [manufacturer.get("Name", "") for manufacturer in manufacturers],
                "retailers": [retailer.get("Name", "") for retailer in raw.get("Retailers", [])],
                "remedies": remedies,
                "injuries": [{"name": injury.get("Name", "")} for injury in injuries],
                "product_types": [product.get("Type", "") for product in products],
            },
        )

    def _parse_cpsc_date(self, date_str: str) -> str:
        if not date_str:
            return ""
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return date_str[:10]

    def _derive_cpsc_severity(self, hazard_name: str, injuries: list) -> str:
        hazard_lower = (hazard_name or "").lower()
        if any(word in hazard_lower for word in ["death", "fatal", "electrocution", "asphyxiation"]):
            return "Class I"
        if injuries or any(word in hazard_lower for word in ["burn", "laceration", "choking", "fire"]):
            return "Class II"
        return "Class III"
