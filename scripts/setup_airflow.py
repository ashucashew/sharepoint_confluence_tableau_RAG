#!/usr/bin/env python3
"""
Setup script for Airflow with RAG integration
This script helps configure Airflow for the RAG system
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_airflow_installation():
    """Check if Airflow is installed"""
    try:
        result = subprocess.run(['airflow', 'version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Airflow is installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ Airflow is not properly installed")
            return False
    except FileNotFoundError:
        print("❌ Airflow is not installed")
        return False

def setup_airflow_environment():
    """Set up Airflow environment variables"""
    airflow_home = Path.home() / "airflow"
    airflow_home.mkdir(exist_ok=True)
    
    # Set environment variables
    os.environ['AIRFLOW_HOME'] = str(airflow_home)
    os.environ['AIRFLOW__CORE__DAGS_FOLDER'] = str(Path.cwd() / "dags")
    os.environ['AIRFLOW__CORE__PLUGINS_FOLDER'] = str(Path.cwd() / "plugins")
    
    print(f"✅ Airflow environment set up:")
    print(f"   AIRFLOW_HOME: {airflow_home}")
    print(f"   DAGS_FOLDER: {os.environ['AIRFLOW__CORE__DAGS_FOLDER']}")
    print(f"   PLUGINS_FOLDER: {os.environ['AIRFLOW__CORE__PLUGINS_FOLDER']}")

def initialize_airflow_database():
    """Initialize Airflow database"""
    try:
        print("🗄️  Initializing Airflow database...")
        result = subprocess.run(['airflow', 'db', 'init'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Airflow database initialized successfully")
            return True
        else:
            print(f"❌ Failed to initialize database: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False

def create_airflow_user():
    """Create Airflow admin user"""
    try:
        print("👤 Creating Airflow admin user...")
        result = subprocess.run([
            'airflow', 'users', 'create',
            '--username', 'admin',
            '--firstname', 'Admin',
            '--lastname', 'User',
            '--role', 'Admin',
            '--email', 'admin@company.com',
            '--password', 'admin'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Airflow admin user created")
            return True
        else:
            print(f"❌ Failed to create user: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return False

def set_airflow_variables():
    """Set Airflow variables for RAG configuration"""
    try:
        print("⚙️  Setting Airflow variables...")
        
        variables = {
            "rag_api_base_url": "http://localhost:8000",
            "rag_email_recipients": "data-team@company.com",
            "rag_health_check_timeout": "30",
            "rag_sync_timeout": "300",
            "rag_cleanup_timeout": "300",
            "rag_embedding_refresh_days": "7"
        }
        
        for key, value in variables.items():
            result = subprocess.run([
                'airflow', 'variables', 'set', key, value
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"   ✅ Set {key} = {value}")
            else:
                print(f"   ❌ Failed to set {key}: {result.stderr}")
        
        return True
    except Exception as e:
        print(f"❌ Error setting variables: {e}")
        return False

def test_dag_loading():
    """Test if DAGs can be loaded properly"""
    try:
        print("🧪 Testing DAG loading...")
        result = subprocess.run(['airflow', 'dags', 'list'], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ DAGs loaded successfully:")
            for line in result.stdout.split('\n'):
                if 'rag' in line.lower():
                    print(f"   📋 {line.strip()}")
            return True
        else:
            print(f"❌ Failed to load DAGs: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing DAG loading: {e}")
        return False

def print_startup_instructions():
    """Print instructions for starting Airflow"""
    print("\n🚀 Airflow Setup Complete!")
    print("\nTo start Airflow, run these commands in separate terminals:")
    print("\nTerminal 1 (Web Server):")
    print("  airflow webserver --port 8080")
    print("\nTerminal 2 (Scheduler):")
    print("  airflow scheduler")
    print("\nThen open your browser to: http://localhost:8080")
    print("Login with: admin / admin")
    print("\nTo trigger a DAG manually:")
    print("  airflow dags trigger simple_rag_dag")

def main():
    """Main setup function"""
    print("🔧 Setting up Airflow for RAG system...")
    
    # Check if Airflow is installed
    if not check_airflow_installation():
        print("\n📦 To install Airflow, run:")
        print("  pip install apache-airflow")
        print("  pip install apache-airflow-providers-http")
        return False
    
    # Set up environment
    setup_airflow_environment()
    
    # Initialize database
    if not initialize_airflow_database():
        return False
    
    # Create admin user
    if not create_airflow_user():
        return False
    
    # Set variables
    if not set_airflow_variables():
        return False
    
    # Test DAG loading
    if not test_dag_loading():
        return False
    
    # Print instructions
    print_startup_instructions()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
