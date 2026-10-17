from .bls_rss import BLSRSSConnector
from .fed_rss import FedRSSConnector
from .media_rss import (
    BBCBusinessRSSConnector,
    BBCWorldRSSConnector,
    GuardianBusinessRSSConnector,
    GuardianWorldRSSConnector,
)

# Failures are isolated per connector; one publisher being unavailable must not
# prevent official macro sources or other publishers from polling.
CONNECTORS = [
    FedRSSConnector(),
    BLSRSSConnector(),
    BBCWorldRSSConnector(),
    BBCBusinessRSSConnector(),
    GuardianWorldRSSConnector(),
    GuardianBusinessRSSConnector(),
]
