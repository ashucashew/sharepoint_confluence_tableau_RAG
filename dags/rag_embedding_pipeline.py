"""
Airflow DAG for RAG Embedding Pipeline
Automated daily updates of embeddings for the RAG system
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
# from airflow.operators.email import EmailOperator
from airflow.models import Variable
import requests
import json
import logging

# Default arguments for the DAG
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}

# DAG definition
dag = DAG(
    'rag_embedding_pipeline',
    default_args=default_args,
    description='Daily RAG embedding updates and maintenance',
    schedule_interval='0 2 * * *',  # Run daily at 2 AM
    max_active_runs=1,
    tags=['rag', 'embeddings', 'nlp']
)

# Configuration - you can set these in Airflow Variables
RAG_API_BASE_URL = Variable.get("rag_api_base_url", "http://localhost:8000")
EMAIL_RECIPIENTS = Variable.get("rag_email_recipients", "data-team@company.com")

def check_rag_system_health():
    """Check if the RAG system is healthy before starting updates"""
    try:
        response = requests.get(f"{RAG_API_BASE_URL}/health", timeout=30)
        response.raise_for_status()
        
        health_data = response.json()
        if health_data.get("status") == "healthy":
            logging.info("✅ RAG system is healthy")
            return True
        else:
            raise Exception(f"❌ RAG system unhealthy: {health_data}")
            
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        raise

def get_sync_status():
    """Get current sync status from all data sources"""
    try:
        response = requests.get(f"{RAG_API_BASE_URL}/api/sync-status", timeout=30)
        response.raise_for_status()
        
        status_data = response.json()
        logging.info(f"📊 Sync status: {json.dumps(status_data, indent=2)}")
        
        return status_data
        
    except Exception as e:
        logging.error(f"Failed to get sync status: {e}")
        raise

def sync_data_source(source_name: str):
    """Sync a specific data source"""
    def _sync_source():
        try:
            logging.info(f"🔄 Starting sync for {source_name}")
            
            response = requests.post(
                f"{RAG_API_BASE_URL}/api/sync/{source_name}",
                timeout=300  # 5 minutes timeout for sync
            )
            response.raise_for_status()
            
            result = response.json()
            logging.info(f"📄 Sync result for {source_name}: {json.dumps(result, indent=2)}")
            
            # Check if sync was successful
            if result.get("status") == "success":
                sync_data = result.get("result", {})
                documents_processed = sync_data.get("documents_processed", 0)
                documents_added = sync_data.get("documents_added", 0)
                documents_updated = sync_data.get("documents_updated", 0)
                documents_deleted = sync_data.get("documents_deleted", 0)
                
                logging.info(f"✅ {source_name} sync completed: {documents_processed} processed, "
                           f"{documents_added} added, {documents_updated} updated, {documents_deleted} deleted")
                
                return {
                    "source": source_name,
                    "status": "success",
                    "documents_processed": documents_processed,
                    "documents_added": documents_added,
                    "documents_updated": documents_updated,
                    "documents_deleted": documents_deleted
                }
            else:
                raise Exception(f"❌ Sync failed for {source_name}: {result.get('error')}")
                
        except Exception as e:
            logging.error(f"Error syncing {source_name}: {e}")
            raise
    
    return _sync_source

def refresh_old_embeddings():
    """Refresh old embeddings"""
    try:
        logging.info("🔄 Starting embedding refresh")
        
        response = requests.post(f"{RAG_API_BASE_URL}/api/embeddings/refresh", 
                               json={"embedding_created_at": {}}, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            logging.info(f"🔄 Embedding refresh result: {json.dumps(result, indent=2)}")
            
            refresh_data = result.get("data", {})
            documents_to_refresh = refresh_data.get("documents_to_refresh", 0)
            
            logging.info(f"✅ Embedding refresh completed: {documents_to_refresh} documents to refresh")
            return refresh_data
        else:
            logging.error(f"❌ Embedding refresh failed with status {response.status_code}")
            return None
            
    except Exception as e:
        logging.error(f"Error during embedding refresh: {e}")
        return None

def get_embedding_stats():
    """Get embedding statistics for monitoring"""
    try:
        logging.info("📊 Getting embedding statistics")
        
        response = requests.get(f"{RAG_API_BASE_URL}/api/embedding-stats", timeout=30)
        response.raise_for_status()
        
        result = response.json()
        logging.info(f"📊 Embedding stats: {json.dumps(result, indent=2)}")
        
        stats_data = result.get("data", {})
        
        return {
            "status": "success",
            "total_embeddings": stats_data.get("total_embeddings", 0),
            "embedding_models": stats_data.get("embedding_models", {}),
            "chunk_types": stats_data.get("chunk_types", {}),
            "age_stats": stats_data.get("embedding_age_stats", {})
        }
        
    except Exception as e:
        logging.error(f"Error getting embedding stats: {e}")
        raise

def generate_daily_report(**context):
    """Generate daily report of the embedding pipeline"""
    try:
        # Get task results from XCom
        ti = context['task_instance']
        
        # Collect results from all tasks
        sync_results = []
        for source in ['confluence', 'sharepoint', 'tableau']:
            try:
                result = ti.xcom_pull(task_ids=f'sync_{source}')
                if result:
                    sync_results.append(result)
            except:
                pass
        
        refresh_result = ti.xcom_pull(task_ids='refresh_old_embeddings')
        stats_result = ti.xcom_pull(task_ids='get_embedding_stats')
        
        # Generate report
        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "pipeline_status": "completed",
            "sync_results": sync_results,
            "refresh": refresh_result,
            "stats": stats_result
        }
        
        # Store report in XCom
        ti.xcom_push(key="daily_report", value=report)
        
        logging.info(f"📋 Daily report generated: {json.dumps(report, indent=2)}")
        
        return report
        
    except Exception as e:
        logging.error(f"Error generating daily report: {e}")
        raise

# Task definitions

# Health check task
health_check = PythonOperator(
    task_id='health_check',
    python_callable=check_rag_system_health,
    dag=dag
)

# Get initial sync status
get_sync_status_task = PythonOperator(
    task_id='get_sync_status',
    python_callable=get_sync_status,
    dag=dag
)

# Sync tasks for each data source
sync_confluence = PythonOperator(
    task_id='sync_confluence',
    python_callable=sync_data_source('confluence'),
    dag=dag
)

sync_sharepoint = PythonOperator(
    task_id='sync_sharepoint',
    python_callable=sync_data_source('sharepoint'),
    dag=dag
)

sync_tableau = PythonOperator(
    task_id='sync_tableau',
    python_callable=sync_data_source('tableau'),
    dag=dag
)

# Refresh old embeddings
refresh_old_embeddings_task = PythonOperator(
    task_id='refresh_old_embeddings',
    python_callable=refresh_old_embeddings,
    dag=dag
)

# Get final statistics
get_embedding_stats_task = PythonOperator(
    task_id='get_embedding_stats',
    python_callable=get_embedding_stats,
    dag=dag
)

# Generate daily report
generate_report = PythonOperator(
    task_id='generate_daily_report',
    python_callable=generate_daily_report,
    dag=dag
)

# Task dependencies
health_check >> get_sync_status_task

# Parallel sync tasks
get_sync_status_task >> [sync_confluence, sync_sharepoint, sync_tableau]

# Sequential maintenance tasks
[sync_confluence, sync_sharepoint, sync_tableau] >> refresh_old_embeddings_task
refresh_old_embeddings_task >> get_embedding_stats_task

# Reporting
get_embedding_stats_task >> generate_report
