from .bls_rss import BLSRSSConnector
from .fed_rss import FedRSSConnector
from .media_rss import (
    BBCBusinessRSSConnector,
    BBCEconomicsRSSConnector,
    BBCWorldRSSConnector,
    GuardianBusinessRSSConnector,
    GuardianWorldRSSConnector,
)

# Failures are isolated per connector; one publisher being unavailable must not
# prevent official macro sources or other publishers from polling.
CONNECTORS = [
    FedRSSConnector(),
    BLSRSSConnector(),
    BBCEconomicsRSSConnector(),
    BBCBusinessRSSConnector(),
    BBCWorldRSSConnector(),
    GuardianBusinessRSSConnector(),
    GuardianWorldRSSConnector(),
]
