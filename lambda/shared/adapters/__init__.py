from .cpsc_adapter import CPSCAdapter
from .fda_device_adapter import FDADeviceAdapter
from .fda_drug_adapter import FDADrugAdapter
from .fda_food_adapter import FDAFoodAdapter
from .nhtsa_adapter import NHTSAAdapter
from .usda_fsis_adapter import USDAFSISAdapter

ADAPTERS = {
    FDAFoodAdapter.SOURCE_NAME: FDAFoodAdapter,
    FDADrugAdapter.SOURCE_NAME: FDADrugAdapter,
    FDADeviceAdapter.SOURCE_NAME: FDADeviceAdapter,
    CPSCAdapter.SOURCE_NAME: CPSCAdapter,
    USDAFSISAdapter.SOURCE_NAME: USDAFSISAdapter,
    NHTSAAdapter.SOURCE_NAME: NHTSAAdapter,
}

__all__ = [
    "ADAPTERS",
    "CPSCAdapter",
    "FDADeviceAdapter",
    "FDADrugAdapter",
    "FDAFoodAdapter",
    "NHTSAAdapter",
    "USDAFSISAdapter",
]
