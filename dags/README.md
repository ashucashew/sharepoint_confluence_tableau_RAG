# Airflow DAGs for RAG System

This directory contains Airflow DAGs for automating the RAG (Retrieval-Augmented Generation) system.

## DAG Files

### 1. `simple_rag_dag.py`
A simple DAG for learning Airflow concepts and testing the RAG system.

**Features:**
- Health check of RAG system
- Get system status
- Trigger manual sync
- Print completion message

**Schedule:** Daily (`@daily`)

**Task Flow:**
```
check_health → get_status → trigger_sync → print_completion
```

### 2. `rag_embedding_pipeline.py`
A comprehensive DAG for production RAG embedding updates.

**Features:**
- Health check before starting
- Parallel sync of all data sources (Confluence, SharePoint, Tableau)
- Cleanup of orphaned documents
- Refresh of old embeddings
- Generate daily reports

**Schedule:** Daily at 2 AM (`0 2 * * *`)

**Task Flow:**
```
health_check → get_sync_status → [sync_confluence, sync_sharepoint, sync_tableau] → cleanup_orphaned → refresh_old_embeddings → get_embedding_stats → generate_daily_report
```

## Understanding the Code

### DAG Structure
```python
# 1. Import Airflow components
from airflow import DAG
from airflow.operators.python import PythonOperator

# 2. Define default arguments
default_args = {
    'owner': 'data-team',
    'start_date': datetime(2024, 1, 1),
    'retries': 3,
    'retry_delay': timedelta(minutes=5)
}

# 3. Create DAG object
dag = DAG(
    'my_dag_name',
    default_args=default_args,
    schedule_interval='@daily'
)

# 4. Define tasks
def my_task_function():
    # Your task logic here
    pass

my_task = PythonOperator(
    task_id='my_task',
    python_callable=my_task_function,
    dag=dag
)

# 5. Define dependencies
task1 >> task2 >> task3
```

### Key Concepts

**DAG (Directed Acyclic Graph):**
- A workflow with tasks and dependencies
- Tasks run in a specific order
- No circular dependencies allowed

**Operators:**
- `PythonOperator`: Runs Python functions
- `BashOperator`: Runs shell commands
- `EmailOperator`: Sends emails

**Scheduling:**
- `@daily`: Run once per day
- `@hourly`: Run every hour
- `0 2 * * *`: Cron format (daily at 2 AM)

**XCom:**
- Way to pass data between tasks
- Used for sharing results and status

## Setup Instructions

1. **Install Airflow:**
   ```bash
   pip install -r requirements-airflow.txt
   ```

2. **Run setup script:**
   ```bash
   python scripts/setup_airflow.py
   ```

3. **Start Airflow:**
   ```bash
   # Terminal 1
   airflow webserver --port 8080
   
   # Terminal 2
   airflow scheduler
   ```

4. **Access Airflow UI:**
   - Open http://localhost:8080
   - Login: admin / admin

## Testing DAGs

### Manual Trigger
```bash
# Trigger simple DAG
airflow dags trigger simple_rag_dag

# Trigger with specific date
airflow dags trigger rag_embedding_pipeline --conf '{"execution_date": "2024-01-15"}'
```

### Check DAG Status
```bash
# List all DAGs
airflow dags list

# Check DAG state
airflow dags state simple_rag_dag

# View task logs
airflow tasks logs simple_rag_dag check_health 2024-01-15
```

## Custom Operators

See `plugins/rag_operators.py` for custom operators:
- `RAGHealthCheckOperator`: Check RAG system health
- `RAGSyncOperator`: Sync specific data sources
- `RAGCleanupOperator`: Clean up orphaned documents
- `RAGStatsOperator`: Get system statistics

## Configuration

Airflow variables can be set in the UI or via command line:
```bash
airflow variables set rag_api_base_url "http://localhost:8000"
airflow variables set rag_email_recipients "team@company.com"
```

## Monitoring

- **Web UI:** http://localhost:8080
- **Task Logs:** Available in UI for each task
- **Email Alerts:** Configured for failures
- **XCom:** View data passed between tasks

## Troubleshooting

1. **DAG not appearing:** Check DAGs folder path in Airflow config
2. **Tasks failing:** Check logs in Airflow UI
3. **RAG API errors:** Verify RAG system is running on correct port
4. **Permission issues:** Check file permissions in DAGs folder
