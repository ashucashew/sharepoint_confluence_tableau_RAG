from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from loguru import logger

class Document(BaseModel):
    """Represents a document from any data source"""
    id: str
    title: str
    content: str
    source_type: str
    source_url: Optional[str] = None
    metadata: Dict[str, Any] = {}
    last_modified: Optional[datetime] = None
    created_at: Optional[datetime] = None

class BaseConnector(ABC):
    """Base class for all data source connectors"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__
        logger.info(f"Initializing {self.name}")
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the data source"""
        pass
    
    @abstractmethod
    async def fetch_documents(self) -> List[Document]:
        """Fetch all documents from the data source"""
        pass
    
    @abstractmethod
    async def fetch_recent_documents(self, since: datetime) -> List[Document]:
        """Fetch documents modified since a specific time"""
        pass
    
    @abstractmethod
    async def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """Fetch a specific document by ID"""
        pass
    
    async def health_check(self) -> bool:
        """Check if the connector is healthy and can connect"""
        try:
            return await self.connect()
        except Exception as e:
            logger.error(f"Health check failed for {self.name}: {e}")
            return False
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get information about the data source"""
        return {
            "name": self.name,
            "enabled": self.config.get("enabled", False),
            "sync_interval": self.config.get("sync_interval", 60)
        } 