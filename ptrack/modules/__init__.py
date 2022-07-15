from .models import TrackingIdentifier, TrackingState, TrackingSupplier, TrackingUpdateItem, IsDataclass, PackageState
from .dhl_de import DHL_DE_Config, DHL_DE
from .asendia import AsendiaConfig, AsendiaTracking
from .globalpost import GlobalPostTracking, GlobalPostSettings

ALL_MODULES = {
    'dhl': (DHL_DE, DHL_DE_Config),
    'asendia': (AsendiaTracking, AsendiaConfig),
    'globalpost': (GlobalPostTracking, GlobalPostSettings)
}
