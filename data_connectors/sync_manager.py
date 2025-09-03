"""
Data synchronization manager for RAG system
Handles syncing data from various sources to the vector store
"""

import asyncio
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from .base_connector import Document
from . import get_connector
from vector_store import VectorStore
from config import settings

class DataSyncManager:
    """Manages synchronization of data from various sources to the vector store"""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.initialized = False
        self.sync_history_file = "sync_history.json"
        
    async def initialize(self):
        """Initialize the sync manager"""
        try:
            await self.vector_store.initialize()
            self.initialized = True
            logger.info("Data sync manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize sync manager: {e}")
            raise
    
    def _load_sync_history(self) -> Dict[str, Any]:
        """Load sync history from file"""
        try:
            if os.path.exists(self.sync_history_file):
                with open(self.sync_history_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading sync history: {e}")
            return {}
    
    def _save_sync_history(self, history: Dict[str, Any]):
        """Save sync history to file"""
        try:
            with open(self.sync_history_file, 'w') as f:
                json.dump(history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving sync history: {e}")
    
    def _get_last_sync_time(self, source_name: str) -> Optional[datetime]:
        """Get the last sync time for a specific source"""
        history = self._load_sync_history()
        source_history = history.get(source_name, {})
        last_sync_str = source_history.get('last_sync')
        
        if last_sync_str:
            try:
                return datetime.fromisoformat(last_sync_str)
            except:
                pass
        
        return None
    
    def _update_sync_history(self, source_name: str, sync_result: Dict[str, Any]):
        """Update sync history for a source"""
        history = self._load_sync_history()
        
        if source_name not in history:
            history[source_name] = {}
        
        history[source_name].update({
            'last_sync': datetime.now().isoformat(),
            'last_sync_result': sync_result,
            'documents_processed': sync_result.get('documents_processed', 0),
            'documents_added': sync_result.get('documents_added', 0),
            'documents_updated': sync_result.get('documents_updated', 0),
            'documents_deleted': sync_result.get('documents_deleted', 0)
        })
        
        self._save_sync_history(history)
    
    async def sync_source(self, source_name: str, force_full_sync: bool = False) -> Dict[str, Any]:
        """Sync a specific data source with incremental logic"""
        if not self.initialized:
            await self.initialize()
        
        try:
            logger.info(f"🔄 Starting sync for {source_name}")
            
            # Get the appropriate connector
            connector = get_connector(source_name)
            
            # Connect to the data source
            if not await connector.connect():
                raise Exception(f"Failed to connect to {source_name}")
            
            # Determine sync strategy
            last_sync_time = self._get_last_sync_time(source_name)
            sync_strategy = "full" if force_full_sync else "incremental"
            
            if force_full_sync:
                logger.info(f"🔄 Force full sync requested for {source_name}")
                documents = await connector.fetch_documents()
            elif last_sync_time:
                # Check if it's been more than 7 days since last sync (fallback to full sync)
                days_since_sync = (datetime.now() - last_sync_time).days
                if days_since_sync > 7:
                    logger.info(f"🔄 Last sync was {days_since_sync} days ago, doing full sync for {source_name}")
                    documents = await connector.fetch_documents()
                    sync_strategy = "full_fallback"
                else:
                    logger.info(f"🔄 Incremental sync for {source_name} since {last_sync_time}")
                    documents = await connector.fetch_recent_documents(last_sync_time)
                    sync_strategy = "incremental"
            else:
                # First time syncing this source
                logger.info(f"🔄 First time sync for {source_name}, doing full sync")
                documents = await connector.fetch_documents()
                sync_strategy = "first_time"
            
            logger.info(f"📄 Fetched {len(documents)} documents from {source_name} using {sync_strategy} strategy")
            
            # Get existing documents from vector store for comparison
            existing_docs = await self.vector_store.get_all_documents(
                filter_metadata={"source_type": source_name}
            )
            existing_ids = {doc["id"] for doc in existing_docs}
            
            # Create set of current document IDs from source
            current_doc_ids = {doc.id for doc in documents}
            
            # Identify deleted documents (exist in vector store but not in current source)
            deleted_doc_ids = existing_ids - current_doc_ids
            
            if not documents and not deleted_doc_ids:
                result = {
                    "status": "success",
                    "result": {
                        "source": source_name,
                        "sync_strategy": sync_strategy,
                        "documents_processed": 0,
                        "documents_added": 0,
                        "documents_updated": 0,
                        "documents_deleted": 0,
                        "sync_timestamp": datetime.now().isoformat(),
                        "last_sync_time": last_sync_time.isoformat() if last_sync_time else None
                    }
                }
                self._update_sync_history(source_name, result["result"])
                return result
            
            # Process and add documents to vector store
            documents_added = 0
            documents_updated = 0
            documents_deleted = 0
            
            # For incremental sync, we need to check if documents already exist
            if sync_strategy == "incremental" and last_sync_time:
                # Separate new and existing documents
                new_docs = []
                existing_docs_to_update = []
                
                for doc in documents:
                    if doc.id in existing_ids:
                        existing_docs_to_update.append(doc)
                    else:
                        new_docs.append(doc)
                
                logger.info(f"📊 {source_name}: {len(new_docs)} new, {len(existing_docs_to_update)} existing, {len(deleted_doc_ids)} deleted")
                
                # Add new documents
                if new_docs:
                    success = await self.vector_store.add_documents(new_docs)
                    if success:
                        documents_added = len(new_docs)
                        logger.info(f"✅ Added {documents_added} new documents from {source_name}")
                    else:
                        logger.error(f"❌ Failed to add new documents from {source_name}")
                
                # Update existing documents
                if existing_docs_to_update:
                    success = await self.vector_store.update_documents(existing_docs_to_update)
                    if success:
                        documents_updated = len(existing_docs_to_update)
                        logger.info(f"✅ Updated {documents_updated} existing documents from {source_name}")
                    else:
                        logger.error(f"❌ Failed to update existing documents from {source_name}")
                
            else:
                # Full sync - add all documents
                success = await self.vector_store.add_documents(documents)
                if success:
                    documents_added = len(documents)
                    logger.info(f"✅ Successfully added {documents_added} documents from {source_name}")
                else:
                    logger.error(f"❌ Failed to add documents from {source_name}")
            
            # Remove deleted documents from vector store
            if deleted_doc_ids:
                logger.info(f"🗑️ Removing {len(deleted_doc_ids)} deleted documents from {source_name}")
                try:
                    # Convert to list of document IDs for deletion
                    deleted_doc_list = list(deleted_doc_ids)
                    success = await self.vector_store.delete_documents(deleted_doc_list)
                    if success:
                        documents_deleted = len(deleted_doc_ids)
                        logger.info(f"✅ Successfully removed {documents_deleted} deleted documents from {source_name}")
                    else:
                        logger.error(f"❌ Failed to remove deleted documents from {source_name}")
                except Exception as e:
                    logger.error(f"❌ Error removing deleted documents from {source_name}: {e}")
                    # Don't fail the entire sync if cleanup fails
                    documents_deleted = 0
            
            result = {
                "status": "success",
                "result": {
                    "source": source_name,
                    "sync_strategy": sync_strategy,
                    "documents_processed": len(documents),
                    "documents_added": documents_added,
                    "documents_updated": documents_updated,
                    "documents_deleted": documents_deleted,
                    "sync_timestamp": datetime.now().isoformat(),
                    "last_sync_time": last_sync_time.isoformat() if last_sync_time else None
                }
            }
            
            # Update sync history
            self._update_sync_history(source_name, result["result"])
            
            logger.info(f"✅ Sync for {source_name} completed: {documents_added} added, {documents_updated} updated, {documents_deleted} deleted")
            return result
            
        except Exception as e:
            logger.error(f"Error syncing {source_name}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source": source_name,
                "sync_timestamp": datetime.now().isoformat()
            }
    
    async def sync_all_sources(self, force_full_sync: bool = False) -> Dict[str, Any]:
        """Sync all configured data sources"""
        if not self.initialized:
            await self.initialize()
        
        try:
            logger.info("🔄 Starting sync of all data sources")
            
            # Get enabled sources from config
            enabled_sources = []
            if settings.confluence_url:
                enabled_sources.append("confluence")
            if settings.sharepoint_url:
                enabled_sources.append("sharepoint")
            if settings.tableau_server_url:
                enabled_sources.append("tableau")
            
            if not enabled_sources:
                return {
                    "status": "success",
                    "result": {
                        "documents_processed": 0,
                        "documents_added": 0,
                        "documents_updated": 0,
                        "documents_deleted": 0,
                        "sync_timestamp": datetime.now().isoformat(),
                        "message": "No data sources configured"
                    }
                }
            
            # Sync each source
            total_processed = 0
            total_added = 0
            total_updated = 0
            total_deleted = 0
            sync_strategies = []
            source_results = []
            
            for source in enabled_sources:
                try:
                    result = await self.sync_source(source, force_full_sync)
                    if result.get("status") == "success":
                        sync_data = result.get("result", {})
                        total_processed += sync_data.get("documents_processed", 0)
                        total_added += sync_data.get("documents_added", 0)
                        total_updated += sync_data.get("documents_updated", 0)
                        total_deleted += sync_data.get("documents_deleted", 0)
                        sync_strategies.append(sync_data.get("sync_strategy", "unknown"))
                        source_results.append({
                            "source": source,
                            "strategy": sync_data.get("sync_strategy", "unknown"),
                            "processed": sync_data.get("documents_processed", 0),
                            "added": sync_data.get("documents_added", 0),
                            "updated": sync_data.get("documents_updated", 0),
                            "deleted": sync_data.get("documents_deleted", 0)
                        })
                    else:
                        logger.error(f"Sync failed for {source}: {result.get('error')}")
                        source_results.append({
                            "source": source,
                            "status": "failed",
                            "error": result.get("error", "Unknown error")
                        })
                except Exception as e:
                    logger.error(f"Error syncing {source}: {e}")
                    source_results.append({
                        "source": source,
                        "status": "error",
                        "error": str(e)
                    })
            
            # Determine overall sync strategy
            overall_strategy = "mixed"
            if all(strategy == "incremental" for strategy in sync_strategies):
                overall_strategy = "incremental"
            elif all(strategy == "full" for strategy in sync_strategies):
                overall_strategy = "full"
            elif all(strategy in ["full", "full_fallback"] for strategy in sync_strategies):
                overall_strategy = "full"
            
            result = {
                "status": "success",
                "result": {
                    "documents_processed": total_processed,
                    "documents_added": total_added,
                    "documents_updated": total_updated,
                    "documents_deleted": total_deleted,
                    "sync_timestamp": datetime.now().isoformat(),
                    "sources_synced": enabled_sources,
                    "overall_sync_strategy": overall_strategy,
                    "source_results": source_results,
                    "sync_summary": {
                        "total_sources": len(enabled_sources),
                        "successful_syncs": len([r for r in source_results if r.get("status") != "failed"]),
                        "failed_syncs": len([r for r in source_results if r.get("status") == "failed"]),
                        "strategies_used": list(set(sync_strategies))
                    }
                }
            }
            
            logger.info(f"✅ Sync of all sources completed: {total_added} added, {total_updated} updated, {total_deleted} deleted")
            logger.info(f"📊 Overall strategy: {overall_strategy}, Sources: {enabled_sources}")
            return result
            
        except Exception as e:
            logger.error(f"Error in sync all sources: {e}")
            return {
                "status": "error",
                "error": str(e),
                "sync_timestamp": datetime.now().isoformat()
            }
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get sync status for all data sources"""
        try:
            # This would typically check last sync times, document counts, etc.
            # For now, returning basic status
            status = {
                "status": "success",
                "data": {
                    "confluence": {
                        "enabled": bool(settings.confluence_url),
                        "last_sync": self._get_last_sync_time("confluence").isoformat() if self._get_last_sync_time("confluence") else None,
                        "status": "up_to_date" if self._get_last_sync_time("confluence") else "never_synced",
                        "documents_count": 0
                    },
                    "sharepoint": {
                        "enabled": bool(settings.sharepoint_url),
                        "last_sync": self._get_last_sync_time("sharepoint").isoformat() if self._get_last_sync_time("sharepoint") else None,
                        "status": "up_to_date" if self._get_last_sync_time("sharepoint") else "never_synced",
                        "documents_count": 0
                    },
                    "tableau": {
                        "enabled": bool(settings.tableau_server_url),
                        "last_sync": self._get_last_sync_time("tableau").isoformat() if self._get_last_sync_time("tableau") else None,
                        "status": "up_to_date" if self._get_last_sync_time("tableau") else "never_synced",
                        "documents_count": 0
                    }
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_sync_statistics(self) -> Dict[str, Any]:
        """Get detailed sync statistics and history"""
        try:
            history = self._load_sync_history()
            
            # Calculate statistics for each source
            source_stats = {}
            total_syncs = 0
            total_documents_processed = 0
            total_documents_added = 0
            total_documents_updated = 0
            total_documents_deleted = 0
            
            for source_name in ["confluence", "sharepoint", "tableau"]:
                source_history = history.get(source_name, {})
                if source_history:
                    last_sync = source_history.get('last_sync')
                    last_result = source_history.get('last_sync_result', {})
                    
                    source_stats[source_name] = {
                        "enabled": bool(getattr(settings, f"{source_name}_url", None)),
                        "last_sync": last_sync,
                        "last_sync_strategy": last_result.get('sync_strategy', 'unknown'),
                        "documents_processed": last_result.get('documents_processed', 0),
                        "documents_added": last_result.get('documents_added', 0),
                        "documents_updated": last_result.get('documents_updated', 0),
                        "documents_deleted": last_result.get('documents_deleted', 0),
                        "sync_status": "up_to_date" if last_sync else "never_synced"
                    }
                    
                    total_syncs += 1
                    total_documents_processed += last_result.get('documents_processed', 0)
                    total_documents_added += last_result.get('documents_added', 0)
                    total_documents_updated += last_result.get('documents_updated', 0)
                    total_documents_deleted += last_result.get('documents_deleted', 0)
                else:
                    source_stats[source_name] = {
                        "enabled": bool(getattr(settings, f"{source_name}_url", None)),
                        "last_sync": None,
                        "last_sync_strategy": None,
                        "documents_processed": 0,
                        "documents_added": 0,
                        "documents_updated": 0,
                        "documents_deleted": 0,
                        "sync_status": "never_synced"
                    }
            
            # Calculate overall statistics
            overall_stats = {
                "total_sources_enabled": len([s for s in source_stats.values() if s["enabled"]]),
                "total_sources_synced": total_syncs,
                "total_documents_processed": total_documents_processed,
                "total_documents_added": total_documents_added,
                "total_documents_updated": total_documents_updated,
                "total_documents_deleted": total_documents_deleted,
                "sync_efficiency": {
                    "new_documents_rate": (total_documents_added / max(total_documents_processed, 1)) * 100,
                    "update_rate": (total_documents_updated / max(total_documents_processed, 1)) * 100,
                    "deletion_rate": (total_documents_deleted / max(total_documents_processed, 1)) * 100
                }
            }
            
            return {
                "status": "success",
                "data": {
                    "source_statistics": source_stats,
                    "overall_statistics": overall_stats,
                    "sync_history_file": self.sync_history_file,
                    "last_updated": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting sync statistics: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def force_full_sync(self, source_name: str = None) -> Dict[str, Any]:
        """Force a full sync for a specific source or all sources"""
        try:
            if source_name:
                logger.info(f"🔄 Force full sync requested for {source_name}")
                return await self.sync_source(source_name, force_full_sync=True)
            else:
                logger.info("🔄 Force full sync requested for all sources")
                return await self.sync_all_sources(force_full_sync=True)
        except Exception as e:
            logger.error(f"Error in force full sync: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
