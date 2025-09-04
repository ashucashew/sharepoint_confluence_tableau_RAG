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

def sync_all_sources():
    """Sync all data sources using the consolidated sync endpoint"""
    try:
        logging.info("🔄 Starting sync of all data sources")
        
        response = requests.post(
            f"{RAG_API_BASE_URL}/api/sync",
            timeout=600  # 10 minutes timeout for full sync
        )
        response.raise_for_status()
        
        result = response.json()
        logging.info(f"📄 Sync result: {json.dumps(result, indent=2)}")
        
        # Check if sync was successful
        if result.get("status") == "success":
            sync_data = result.get("result", {})
            documents_processed = sync_data.get("documents_processed", 0)
            documents_added = sync_data.get("documents_added", 0)
            documents_updated = sync_data.get("documents_updated", 0)
            documents_deleted = sync_data.get("documents_deleted", 0)
            overall_strategy = sync_data.get("overall_sync_strategy", "unknown")
            
            logging.info(f"✅ All sources sync completed: {documents_processed} processed, "
                       f"{documents_added} added, {documents_updated} updated, {documents_deleted} deleted")
            logging.info(f"📊 Overall sync strategy: {overall_strategy}")
            
            return {
                "status": "success",
                "documents_processed": documents_processed,
                "documents_added": documents_added,
                "documents_updated": documents_updated,
                "documents_deleted": documents_deleted,
                "overall_strategy": overall_strategy,
                "source_results": sync_data.get("source_results", [])
            }
        else:
            raise Exception(f"❌ Sync failed: {result.get('error')}")
            
    except Exception as e:
        logging.error(f"Error syncing all sources: {e}")
        raise

def get_embedding_stats():
    """Get embedding statistics"""
    try:
        logging.info("📊 Getting embedding statistics")
        
        response = requests.get(f"{RAG_API_BASE_URL}/api/embedding-stats", timeout=60)
        response.raise_for_status()
        
        result = response.json()
        logging.info(f"📊 Stats result: {json.dumps(result, indent=2)}")
        
        stats_data = result.get("data", {})
        total_embeddings = stats_data.get("total_embeddings", 0)
        
        logging.info(f"📊 Statistics collected: {total_embeddings} total embeddings")
        
        return {
            "status": "success",
            "total_embeddings": total_embeddings,
            "stats": stats_data
        }
        
    except Exception as e:
        logging.error(f"Error getting embedding stats: {e}")
        raise

def get_sync_statistics():
    """Get detailed sync statistics and history"""
    try:
        logging.info("📊 Getting sync statistics")
        
        response = requests.get(f"{RAG_API_BASE_URL}/api/sync-statistics", timeout=60)
        response.raise_for_status()
        
        result = response.json()
        logging.info(f"📊 Sync statistics result: {json.dumps(result, indent=2)}")
        
        sync_stats_data = result.get("data", {})
        
        logging.info("📊 Sync statistics collected successfully")
        
        return {
            "status": "success",
            "sync_statistics": sync_stats_data
        }
        
    except Exception as e:
        logging.error(f"Error getting sync statistics: {e}")
        raise

def generate_daily_report(**context):
    """Generate daily report of the embedding pipeline"""
    try:
        # Get task results from XCom
        ti = context['task_instance']
        
        # Get sync results from the single sync task
        sync_result = ti.xcom_pull(task_ids='sync_all_sources')
        if sync_result:
            sync_results = [sync_result]
        else:
            sync_results = []
        
        stats_result = ti.xcom_pull(task_ids='get_embedding_stats')
        sync_stats_result = ti.xcom_pull(task_ids='get_sync_statistics')
        
        # Generate report
        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "pipeline_status": "completed",
            "sync_results": sync_results,
            "embedding_stats": stats_result,
            "sync_statistics": sync_stats_result
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
# Sync all data sources
sync_all_sources_task = PythonOperator(
    task_id='sync_all_sources',
    python_callable=sync_all_sources,
    dag=dag
)

# Get final statistics
get_embedding_stats_task = PythonOperator(
    task_id='get_embedding_stats',
    python_callable=get_embedding_stats,
    dag=dag
)

# Get sync statistics
get_sync_statistics_task = PythonOperator(
    task_id='get_sync_statistics',
    python_callable=get_sync_statistics,
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

# Sync all sources
get_sync_status_task >> sync_all_sources_task

# Get statistics after sync
sync_all_sources_task >> [get_embedding_stats_task, get_sync_statistics_task]

# Reporting
[get_embedding_stats_task, get_sync_statistics_task] >> generate_report
