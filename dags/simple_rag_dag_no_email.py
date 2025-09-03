"""
Simple RAG DAG without email dependencies
This is a basic example to understand Airflow concepts
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests
import json

# Simple DAG configuration
default_args = {
    'owner': 'data-team',
    'start_date': datetime(2024, 1, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
    'email_on_failure': False
}

# Define the DAG
dag = DAG(
    'simple_rag_dag_no_email',
    default_args=default_args,
    description='Simple RAG pipeline without email dependencies',
    schedule_interval='@daily',
    catchup=False,
    tags=['rag', 'learning', 'no-email']
)

# Task 1: Check if RAG system is running
def check_rag_health():
    """Simple health check for RAG system"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            print("✅ RAG system is healthy!")
            return "healthy"
        else:
            print("❌ RAG system is not responding properly")
            return "unhealthy"
    except Exception as e:
        print(f"❌ Error checking RAG health: {e}")
        raise

# Task 2: Get system status
def get_system_status():
    """Get current system status"""
    try:
        response = requests.get("http://localhost:8000/api/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            print(f"📊 System Status: {json.dumps(status, indent=2)}")
            return status
        else:
            print("❌ Could not get system status")
            return None
    except Exception as e:
        print(f"❌ Error getting system status: {e}")
        raise

# Task 3: Sync data sources
def sync_data_sources():
    """Sync all data sources"""
    try:
        print("🔄 Starting data source synchronization")
        
        response = requests.post("http://localhost:8000/api/sync", timeout=300)
        if response.status_code == 200:
            result = response.json()
            sync_data = result.get("result", {})
            documents_processed = sync_data.get("documents_processed", 0)
            documents_added = sync_data.get("documents_added", 0)
            documents_updated = sync_data.get("documents_updated", 0)
            documents_deleted = sync_data.get("documents_deleted", 0)
            
            print(f"✅ Sync completed: {documents_processed} processed, {documents_added} added, {documents_updated} updated, {documents_deleted} deleted")
            return sync_data
        else:
            print("❌ Sync failed")
            return None
    except Exception as e:
        print(f"❌ Error during sync: {e}")
        return None

# Task 4: Log completion
def log_completion():
    """Log completion of the DAG"""
    print("✅ Simple RAG DAG completed successfully")
    return {"status": "completed", "timestamp": datetime.now().isoformat()}

# Define the tasks
health_check_task = PythonOperator(
    task_id='check_health',
    python_callable=check_rag_health,
    dag=dag
)

status_task = PythonOperator(
    task_id='get_status',
    python_callable=get_system_status,
    dag=dag
)

sync_task = PythonOperator(
    task_id='trigger_sync',
    python_callable=sync_data_sources,
    dag=dag
)

completion_task = PythonOperator(
    task_id='print_completion',
    python_callable=log_completion,
    dag=dag
)

# Define the task dependencies (workflow)
health_check_task >> status_task >> sync_task >> completion_task