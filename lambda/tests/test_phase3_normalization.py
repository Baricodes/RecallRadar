import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.adapters.cpsc_adapter import CPSCAdapter
from shared.adapters.fda_food_adapter import FDAFoodAdapter
from shared.adapters.nhtsa_adapter import NHTSAAdapter
from shared.models import CanonicalRecallRecord


def test_canonical_record_dynamodb_keys_and_compatibility_fields():
    record = CanonicalRecallRecord(
        source="FDA_FOOD",
        source_recall_id="F-1234-2026",
        classification="Class I",
        status="Ongoing",
        recall_date="2026-06-21",
        company="Example Foods",
        description="Possible salmonella contamination",
        product_description="Bagged salad",
        distribution="Nationwide",
        states=["Nationwide"],
        category="FOOD",
    )

    item = record.to_dynamodb_item()

    assert item["PK"] == "FDA_FOOD#F-1234-2026"
    assert item["SK"] == "2026-06-21"
    assert item["GSI1PK"] == "FDA_FOOD"
    assert item["GSI2PK"] == "FOOD"
    assert item["report_date"] == "20260621"
    assert item["recalling_firm"] == "Example Foods"
    assert item["is_nationwide"] is True


def test_fda_food_adapter_normalizes_openfda_record():
    record = FDAFoodAdapter().normalize(
        {
            "recall_number": "F-456-2026",
            "report_date": "20260620",
            "classification": "Class II",
            "status": "Ongoing",
            "recalling_firm": "Example Foods",
            "product_description": "Peanut butter",
            "reason_for_recall": "Undeclared milk allergen",
            "distribution_pattern": "Distributed in TX and LA through retail stores",
            "product_quantity": "500 jars",
        }
    )

    assert record.source == "FDA_FOOD"
    assert record.category == "FOOD"
    assert record.recall_date == "2026-06-20"
    assert record.states == ["LA", "TX"]
    assert record.hazard_type == "Mislabeling - Allergen"


def test_cpsc_adapter_flattens_nested_record():
    record = CPSCAdapter().normalize(
        {
            "RecallID": 100,
            "RecallDate": "06/21/2026",
            "Title": "Toy recall",
            "Description": "Small parts can detach.",
            "Products": [{"Name": "Toy blocks"}],
            "Hazards": [{"Name": "Choking hazard", "HazardType": "Choking"}],
            "Manufacturers": [{"Name": "Toy Co"}],
            "Images": [{"URL": "https://example.com/toy.jpg"}],
            "Units": "3,000 units",
        }
    )

    assert record.source == "CPSC"
    assert record.recall_date == "2026-06-21"
    assert record.product_description == "Toy blocks"
    assert record.company == "Toy Co"
    assert record.classification == "Class II"
    assert record.images == ["https://example.com/toy.jpg"]


def test_nhtsa_adapter_maps_park_outside_to_class_i():
    record = NHTSAAdapter().normalize(
        {
            "nhtsa_campaign_number": "26V001000",
            "report_received_date": "2026-06-19T00:00:00.000",
            "manufacturer": "Example Motors",
            "subject": "Battery fire risk",
            "summary": "A short circuit may cause a fire.",
            "make": "EXAMPLE",
            "model": "EV",
            "model_year": "2026",
            "potential_units_affected": "12,345",
            "park_outside": "Yes",
        }
    )

    assert record.source == "NHTSA"
    assert record.classification == "Class I"
    assert record.quantity_numeric == 12345
    assert record.product_description == "2026 EXAMPLE EV"
