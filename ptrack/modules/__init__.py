from .models import TrackingIdentifier, TrackingState, TrackingSupplier, TrackingUpdateItem, IsDataclass, PackageState
from .dhl_de import DHL_DE_Config, DHL_DE
from .asendia import AsendiaConfig, AsendiaTracking

ALL_MODULES = {
    'dhl': (DHL_DE, DHL_DE_Config),
    'asendia': (AsendiaTracking, AsendiaConfig),
}
