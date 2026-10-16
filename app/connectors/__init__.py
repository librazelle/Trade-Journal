from .bls_rss import BLSRSSConnector
from .fed_rss import FedRSSConnector

# Connector failures are isolated by the worker; core storage remains shared.
CONNECTORS = [
    FedRSSConnector(),
    BLSRSSConnector(),
]
