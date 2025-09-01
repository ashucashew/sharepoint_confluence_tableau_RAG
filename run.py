#!/usr/bin/env python3
"""
Team RAG Chatbot - Main Application Runner

This script starts the RAG chatbot application with proper initialization
and error handling.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from web_app import app
from config import settings

def setup_logging():
    """Configure logging for the application"""
    # Remove default logger
    logger.remove()
    
    # Add console logger with colors
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # Add file logger
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG"
    )

def check_environment():
    """Check if required environment variables are set"""
    required_vars = [
        "OPENAI_API_KEY",
        "CHROMA_PERSIST_DIRECTORY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var.lower(), None):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file and ensure all required variables are set.")
        return False
    
    return True

def create_directories():
    """Create necessary directories"""
    directories = [
        "logs",
        settings.chroma_persist_directory,
        "static",
        "templates"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

async def main():
    """Main application entry point"""
    try:
        # Setup logging
        setup_logging()
        
        # Create necessary directories
        create_directories()
        
        logger.info("Starting Team RAG Chatbot...")
        
        # Check environment
        if not check_environment():
            logger.error("Environment check failed. Exiting.")
            sys.exit(1)
        
        # Log configuration summary
        logger.info(f"Configuration loaded:")
        logger.info(f"  - Host: {settings.host}")
        logger.info(f"  - Port: {settings.port}")
        logger.info(f"  - Debug: {settings.debug}")
        logger.info(f"  - OpenAI Model: {settings.openai_model}")
        logger.info(f"  - Embedding Model: {settings.embedding_model}")
        
        # Check data source configurations
        enabled_sources = []
        if settings.confluence_url:
            enabled_sources.append("Confluence")
        if settings.tableau_server_url:
            enabled_sources.append("Tableau")
        if settings.sharepoint_url:
            enabled_sources.append("SharePoint")
        
        if enabled_sources:
            logger.info(f"Enabled data sources: {', '.join(enabled_sources)}")
        else:
            logger.warning("No data sources configured. The chatbot will work with existing data only.")
        
        # Import and run the FastAPI application
        import uvicorn
        
        logger.info(f"Starting web server on {settings.host}:{settings.port}")
        
        uvicorn.run(
            "web_app:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level="info" if not settings.debug else "debug"
        )
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main()) 