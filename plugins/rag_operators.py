"""
Custom Airflow operators for RAG operations
These operators provide reusable components for RAG workflows
"""

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
import requests
import json
import logging
from datetime import datetime

class RAGHealthCheckOperator(BaseOperator):
    """Custom operator to check RAG system health"""
    
    @apply_defaults
    def __init__(self, api_base_url: str = "http://localhost:8000", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_base_url = api_base_url
    
    def execute(self, context):
        try:
            self.log.info("🔍 Checking RAG system health...")
            
            response = requests.get(f"{self.api_base_url}/health", timeout=30)
            response.raise_for_status()
            
            health_data = response.json()
            if health_data.get("status") == "healthy":
                self.log.info("✅ RAG system is healthy")
                return True
            else:
                raise Exception(f"❌ RAG system unhealthy: {health_data}")
                
        except Exception as e:
            self.log.error(f"Health check failed: {e}")
            raise

class RAGSyncOperator(BaseOperator):
    """Custom operator for RAG data source synchronization"""
    
    @apply_defaults
    def __init__(self, source_name: str, api_base_url: str = "http://localhost:8000", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_name = source_name
        self.api_base_url = api_base_url
    
    def execute(self, context):
        try:
            self.log.info(f"🔄 Starting sync for {self.source_name}")
            
            response = requests.post(
                f"{self.api_base_url}/api/sync/{self.source_name}",
                timeout=300  # 5 minutes timeout
            )
            response.raise_for_status()
            
            result = response.json()
            self.log.info(f"📄 Sync result for {self.source_name}: {json.dumps(result, indent=2)}")
            
            if result.get("status") == "success":
                sync_data = result.get("result", {})
                documents_processed = sync_data.get("documents_processed", 0)
                documents_added = sync_data.get("documents_added", 0)
                documents_updated = sync_data.get("documents_updated", 0)
                documents_deleted = sync_data.get("documents_deleted", 0)
                
                self.log.info(f"✅ {self.source_name} sync completed: {documents_processed} processed, "
                           f"{documents_added} added, {documents_updated} updated, {documents_deleted} deleted")
                
                # Push result to XCom for downstream tasks
                context['task_instance'].xcom_push(
                    key=f"{self.source_name}_sync_result",
                    value=sync_data
                )
                
                return sync_data
            else:
                raise Exception(f"❌ Sync failed for {self.source_name}: {result.get('error')}")
                
        except Exception as e:
            self.log.error(f"Error syncing {self.source_name}: {e}")
            raise

class RAGCleanupOperator(BaseOperator):
    """Custom operator for RAG cleanup operations"""
    
    @apply_defaults
    def __init__(self, api_base_url: str = "http://localhost:8000", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_base_url = api_base_url
    
    def execute(self, context):
        try:
            self.log.info("🧹 Starting orphaned document cleanup")
            
            response = requests.post(f"{self.api_base_url}/api/cleanup", timeout=300)
            response.raise_for_status()
            
            result = response.json()
            cleanup_data = result.get("result", {})
            documents_cleaned = cleanup_data.get("documents_cleaned", 0)
            
            self.log.info(f"✅ Cleanup completed: {documents_cleaned} documents cleaned")
            
            # Push result to XCom
            context['task_instance'].xcom_push(
                key="cleanup_result",
                value=cleanup_data
            )
            
            return cleanup_data
            
        except Exception as e:
            self.log.error(f"Error during cleanup: {e}")
            raise

class RAGStatsOperator(BaseOperator):
    """Custom operator to get RAG system statistics"""
    
    @apply_defaults
    def __init__(self, api_base_url: str = "http://localhost:8000", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_base_url = api_base_url
    
    def execute(self, context):
        try:
            self.log.info("📊 Getting RAG system statistics")
            
            # Get sync status
            sync_response = requests.get(f"{self.api_base_url}/api/sync-status", timeout=30)
            sync_response.raise_for_status()
            sync_stats = sync_response.json()
            
            # Get embedding stats
            embedding_response = requests.get(f"{self.api_base_url}/api/embedding-stats", timeout=30)
            embedding_response.raise_for_status()
            embedding_stats = embedding_response.json()
            
            # Get collection stats
            collection_response = requests.get(f"{self.api_base_url}/api/collection-stats", timeout=30)
            collection_response.raise_for_status()
            collection_stats = collection_response.json()
            
            # Combine all stats
            combined_stats = {
                "timestamp": datetime.now().isoformat(),
                "sync_status": sync_stats,
                "embedding_stats": embedding_stats,
                "collection_stats": collection_stats
            }
            
            self.log.info(f"📊 Combined stats: {json.dumps(combined_stats, indent=2)}")
            
            # Push to XCom
            context['task_instance'].xcom_push(
                key="rag_stats",
                value=combined_stats
            )
            
            return combined_stats
            
        except Exception as e:
            self.log.error(f"Error getting RAG stats: {e}")
            raise
