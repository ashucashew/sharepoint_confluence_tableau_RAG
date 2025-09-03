from .base_connector import BaseConnector, Document
from .confluence_connector import ConfluenceConnector
from .tableau_connector import TableauConnector
from .sharepoint_connector import SharePointConnector
from .sync_manager import DataSyncManager

def get_connector(source_name: str, config: dict = None) -> BaseConnector:
    """Factory function to get a connector for a specific data source"""
    if source_name.lower() == "confluence":
        return ConfluenceConnector(config or {})
    elif source_name.lower() == "sharepoint":
        return SharePointConnector(config or {})
    elif source_name.lower() == "tableau":
        return TableauConnector(config or {})
    else:
        raise ValueError(f"Unknown data source: {source_name}")

__all__ = [
    'BaseConnector',
    'Document',
    'ConfluenceConnector',
    'TableauConnector',
    'SharePointConnector',
    'DataSyncManager',
    'get_connector'
] 