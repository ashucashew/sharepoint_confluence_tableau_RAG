import os
from typing import Dict, Any
from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # OpenAI Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # Vector Database Configuration
    chroma_persist_directory: str = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    
    # Confluence Configuration
    confluence_url: str = os.getenv("CONFLUENCE_URL", "")
    confluence_username: str = os.getenv("CONFLUENCE_USERNAME", "")
    confluence_api_token: str = os.getenv("CONFLUENCE_API_TOKEN", "")
    confluence_space_keys: str = os.getenv("CONFLUENCE_SPACE_KEYS", "")
    
    # Tableau Configuration
    tableau_server_url: str = os.getenv("TABLEAU_SERVER_URL", "")
    tableau_username: str = os.getenv("TABLEAU_USERNAME", "")
    tableau_password: str = os.getenv("TABLEAU_PASSWORD", "")
    tableau_site_id: str = os.getenv("TABLEAU_SITE_ID", "")
    
    # SharePoint Configuration
    sharepoint_url: str = os.getenv("SHAREPOINT_URL", "")
    sharepoint_username: str = os.getenv("SHAREPOINT_USERNAME", "")
    sharepoint_password: str = os.getenv("SHAREPOINT_PASSWORD", "")
    sharepoint_site_url: str = os.getenv("SHAREPOINT_SITE_URL", "")
    
    # Web Application Configuration
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Scheduling Configuration
    sync_interval_minutes: int = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))
    
    # File Processing Configuration
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    supported_file_types: list = [
        ".pdf", ".docx", ".doc", ".pptx", ".ppt", 
        ".xlsx", ".xls", ".txt", ".md", ".html"
    ]
    
    # RAG Configuration - Optimized for BGE-M3
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "2000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "400"))
    max_results: int = int(os.getenv("MAX_RESULTS", "8"))
    
    class Config:
        env_file = ".env"

settings = Settings()

# Data source configurations
DATA_SOURCES = {
    "confluence": {
        "enabled": bool(settings.confluence_url),
        "sync_interval": settings.sync_interval_minutes,
        "max_pages": 1000,
        "include_attachments": True
    },
    "tableau": {
        "enabled": bool(settings.tableau_server_url),
        "sync_interval": settings.sync_interval_minutes,
        "include_descriptions": True,
        "include_metadata": True
    },
    "sharepoint": {
        "enabled": bool(settings.sharepoint_url),
        "sync_interval": settings.sync_interval_minutes,
        "include_metadata": True,
        "recursive_search": True
    }
} 