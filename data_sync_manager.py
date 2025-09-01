import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from data_connectors import (
    ConfluenceConnector, 
    TableauConnector, 
    SharePointConnector,
    Document
)
from vector_store import VectorStore
from config import settings, DATA_SOURCES
from loguru import logger

class DataSyncManager:
    """Manages synchronization of data from multiple sources to the vector store"""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.connectors = {}
        self.scheduler = AsyncIOScheduler()
        self.sync_history = {}
        self.initialized = False
    
    async def initialize(self):
        """Initialize the sync manager and all connectors"""
        try:
            # Initialize vector store
            await self.vector_store.initialize()
            
            # Initialize connectors
            await self._initialize_connectors()
            
            # Load sync history
            await self._load_sync_history()
            
            self.initialized = True
            logger.info("Data sync manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize data sync manager: {e}")
            raise
    
    async def _initialize_connectors(self):
        """Initialize all enabled data source connectors"""
        try:
            # Initialize Confluence connector
            if DATA_SOURCES["confluence"]["enabled"]:
                self.connectors["confluence"] = ConfluenceConnector(DATA_SOURCES["confluence"])
                if await self.connectors["confluence"].connect():
                    logger.info("Confluence connector initialized successfully")
                else:
                    logger.warning("Failed to connect to Confluence")
            
            # Initialize Tableau connector
            if DATA_SOURCES["tableau"]["enabled"]:
                self.connectors["tableau"] = TableauConnector(DATA_SOURCES["tableau"])
                if await self.connectors["tableau"].connect():
                    logger.info("Tableau connector initialized successfully")
                else:
                    logger.warning("Failed to connect to Tableau")
            
            # Initialize SharePoint connector
            if DATA_SOURCES["sharepoint"]["enabled"]:
                self.connectors["sharepoint"] = SharePointConnector(DATA_SOURCES["sharepoint"])
                if await self.connectors["sharepoint"].connect():
                    logger.info("SharePoint connector initialized successfully")
                else:
                    logger.warning("Failed to connect to SharePoint")
            
            logger.info(f"Initialized {len(self.connectors)} connectors")
            
        except Exception as e:
            logger.error(f"Error initializing connectors: {e}")
    
    async def _load_sync_history(self):
        """Load sync history from file"""
        try:
            history_file = "sync_history.json"
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    self.sync_history = json.load(f)
            else:
                self.sync_history = {}
        except Exception as e:
            logger.error(f"Error loading sync history: {e}")
            self.sync_history = {}
    
    async def _save_sync_history(self):
        """Save sync history to file"""
        try:
            history_file = "sync_history.json"
            with open(history_file, 'w') as f:
                json.dump(self.sync_history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving sync history: {e}")
    
    async def sync_all_sources(self, force_full_sync: bool = False) -> Dict[str, Any]:
        """Sync all data sources"""
        if not self.initialized:
            await self.initialize()
        
        sync_results = {
            "timestamp": datetime.now().isoformat(),
            "sources": {},
            "total_documents": 0,
            "errors": []
        }
        
        try:
            for source_name, connector in self.connectors.items():
                try:
                    source_result = await self._sync_source(source_name, connector, force_full_sync)
                    sync_results["sources"][source_name] = source_result
                    sync_results["total_documents"] += source_result.get("documents_processed", 0)
                except Exception as e:
                    error_msg = f"Error syncing {source_name}: {e}"
                    logger.error(error_msg)
                    sync_results["errors"].append(error_msg)
                    sync_results["sources"][source_name] = {
                        "status": "error",
                        "error": str(e),
                        "documents_processed": 0
                    }
            
            # Save sync history
            await self._save_sync_history()
            
            logger.info(f"Sync completed: {sync_results['total_documents']} documents processed")
            return sync_results
            
        except Exception as e:
            logger.error(f"Error during sync: {e}")
            sync_results["errors"].append(str(e))
            return sync_results
    
    async def _sync_source(self, source_name: str, connector, force_full_sync: bool = False) -> Dict[str, Any]:
        """Sync a specific data source"""
        sync_result = {
            "status": "success",
            "documents_processed": 0,
            "documents_added": 0,
            "documents_updated": 0,
            "documents_deleted": 0,
            "start_time": datetime.now().isoformat(),
            "end_time": None
        }
        
        try:
            # Check if we should do a full sync or incremental sync
            last_sync = self.sync_history.get(source_name, {}).get("last_sync")
            
            if force_full_sync or not last_sync:
                # Full sync
                documents = await connector.fetch_documents()
                sync_result["sync_type"] = "full"
            else:
                # Incremental sync
                last_sync_time = datetime.fromisoformat(last_sync)
                documents = await connector.fetch_recent_documents(last_sync_time)
                sync_result["sync_type"] = "incremental"
            
            if documents:
                # Add documents to vector store
                success = await self.vector_store.add_documents(documents)
                if success:
                    sync_result["documents_processed"] = len(documents)
                    sync_result["documents_added"] = len(documents)
                else:
                    sync_result["status"] = "error"
                    sync_result["error"] = "Failed to add documents to vector store"
            
            # Update sync history
            self.sync_history[source_name] = {
                "last_sync": datetime.now().isoformat(),
                "documents_processed": sync_result["documents_processed"],
                "sync_type": sync_result["sync_type"]
            }
            
            sync_result["end_time"] = datetime.now().isoformat()
            logger.info(f"Synced {source_name}: {sync_result['documents_processed']} documents")
            
        except Exception as e:
            sync_result["status"] = "error"
            sync_result["error"] = str(e)
            sync_result["end_time"] = datetime.now().isoformat()
            logger.error(f"Error syncing {source_name}: {e}")
        
        return sync_result
    
    async def sync_single_source(self, source_name: str, force_full_sync: bool = False) -> Dict[str, Any]:
        """Sync a single data source"""
        if not self.initialized:
            await self.initialize()
        
        if source_name not in self.connectors:
            return {
                "status": "error",
                "error": f"Source {source_name} not found or not enabled"
            }
        
        connector = self.connectors[source_name]
        return await self._sync_source(source_name, connector, force_full_sync)
    
    def start_scheduled_sync(self):
        """Start the scheduled sync process"""
        if not self.initialized:
            logger.error("Data sync manager not initialized")
            return
        
        try:
            # Schedule sync for each source based on their individual intervals
            for source_name, connector in self.connectors.items():
                interval_minutes = DATA_SOURCES[source_name]["sync_interval"]
                
                self.scheduler.add_job(
                    func=self.sync_single_source,
                    trigger=IntervalTrigger(minutes=interval_minutes),
                    args=[source_name, False],
                    id=f"sync_{source_name}",
                    name=f"Sync {source_name}",
                    replace_existing=True
                )
                
                logger.info(f"Scheduled sync for {source_name} every {interval_minutes} minutes")
            
            # Start the scheduler
            self.scheduler.start()
            logger.info("Scheduled sync started")
            
        except Exception as e:
            logger.error(f"Error starting scheduled sync: {e}")
    
    def stop_scheduled_sync(self):
        """Stop the scheduled sync process"""
        try:
            self.scheduler.shutdown()
            logger.info("Scheduled sync stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduled sync: {e}")
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get the current sync status"""
        status = {
            "initialized": self.initialized,
            "connectors": {},
            "scheduler_running": self.scheduler.running,
            "sync_history": self.sync_history,
            "vector_store_stats": {}
        }
        
        # Get connector status
        for source_name, connector in self.connectors.items():
            status["connectors"][source_name] = {
                "enabled": True,
                "connected": await connector.health_check(),
                "config": connector.get_source_info()
            }
        
        # Get vector store stats
        if self.initialized:
            status["vector_store_stats"] = await self.vector_store.get_collection_stats()
        
        return status
    
    async def health_check(self) -> bool:
        """Perform a health check on all components"""
        try:
            if not self.initialized:
                return False
            
            # Check vector store
            stats = await self.vector_store.get_collection_stats()
            if not stats:
                return False
            
            # Check connectors
            for source_name, connector in self.connectors.items():
                if not await connector.health_check():
                    logger.warning(f"Health check failed for {source_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            self.stop_scheduled_sync()
            await self._save_sync_history()
            logger.info("Data sync manager cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}") 