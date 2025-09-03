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

# Task 3: Manual sync trigger
def trigger_sync():
    """Trigger a manual sync of all sources"""
    try:
        response = requests.post("http://localhost:8000/api/sync", timeout=60)
        if response.status_code == 200:
            result = response.json()
            print(f"🔄 Sync triggered: {json.dumps(result, indent=2)}")
            return result
        else:
            print("❌ Sync trigger failed")
            return None
    except Exception as e:
        print(f"❌ Error triggering sync: {e}")
        raise

# Task 4: Cleanup orphaned documents
def cleanup_orphaned_documents():
    """Clean up orphaned documents from vector store"""
    try:
        print("🧹 Starting orphaned document cleanup")
        
        response = requests.post("http://localhost:8000/api/cleanup", timeout=300)
        if response.status_code == 200:
            result = response.json()
            cleanup_data = result.get("result", {})
            documents_cleaned = cleanup_data.get("documents_cleaned", 0)
            
            print(f"✅ Cleanup completed: {documents_cleaned} documents cleaned")
            return cleanup_data
        else:
            print("❌ Cleanup failed")
            return None
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        raise

# Task 5: Print completion message
def print_completion():
    """Print completion message"""
    print("🎉 RAG pipeline completed successfully!")
    print("📅 Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return "completed"

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
    python_callable=trigger_sync,
    dag=dag
)

cleanup_task = PythonOperator(
    task_id='cleanup_orphaned',
    python_callable=cleanup_orphaned_documents,
    dag=dag
)

completion_task = PythonOperator(
    task_id='print_completion',
    python_callable=print_completion,
    dag=dag
)

# Define the task dependencies (workflow)
health_check_task >> status_task >> sync_task >> cleanup_task >> completion_task