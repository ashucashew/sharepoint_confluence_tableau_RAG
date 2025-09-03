import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
import json

from rag_chatbot import RAGChatbot
from vector_store import VectorStore
from config import settings
from loguru import logger
from config import DATA_SOURCES
from data_connectors import get_connector

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Team RAG Chatbot",
    description="A RAG-based chatbot for team knowledge management",
    version="1.0.0"
)

# Initialize components
chatbot = RAGChatbot()
vector_store = VectorStore()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    include_sources: bool = True
    max_sources: int = 3

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    conversation_id: str
    timestamp: str

class SearchRequest(BaseModel):
    query: str
    n_results: int = 5
    filter_source: Optional[str] = None

class SyncRequest(BaseModel):
    force_full_sync: bool = False

class EmbeddingRefreshRequest(BaseModel):
    embedding_created_at: Dict[str, str]

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    try:
        await chatbot.initialize()
        await vector_store.initialize()
        logger.info("Web application started successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        logger.info("Web application shutdown successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()

# Routes
@app.get("/", response_class=HTMLResponse)
async def chat_interface(request: Request):
    """Serve the main chat interface"""
    return templates.TemplateResponse("chat.html", {"request": request})

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Chat API endpoint"""
    try:
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        # Process chat message
        result = await chatbot.chat(
            user_message=request.message,
            conversation_id=conversation_id,
            include_sources=request.include_sources,
            max_sources=request.max_sources
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search")
async def search_endpoint(request: SearchRequest):
    """Search documents endpoint"""
    try:
        # Get rewritten query for logging with conversation context
        rewritten_query = await chatbot._rewrite_query(request.query, chatbot.conversation_history)
        
        results = await chatbot.search_documents(
            query=request.query,
            n_results=request.n_results,
            filter_source=request.filter_source
        )
        
        return {
            "results": results,
            "original_query": request.query,
            "rewritten_query": rewritten_query,
            "total_results": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rewrite-query")
async def rewrite_query_endpoint(request: dict):
    """Rewrite a query for better retrieval"""
    try:
        query = request.get("query", "")
        conversation_history = request.get("conversation_history", [])
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Use conversation history if provided, otherwise use chatbot's history
        history_to_use = conversation_history if conversation_history else chatbot.conversation_history
        rewritten_query = await chatbot._rewrite_query(query, history_to_use)
        
        return {
            "original_query": query,
            "rewritten_query": rewritten_query,
            "conversation_context_used": len(history_to_use) > 0,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in query rewriting endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# NEW: Sync endpoints for DAGs
@app.post("/api/sync")
async def sync_all_sources(request: SyncRequest = SyncRequest()):
    """Sync all data sources"""
    try:
        logger.info("🔄 Starting sync of all data sources")
        
        # Use the sync manager
        from data_connectors import DataSyncManager
        sync_manager = DataSyncManager()
        await sync_manager.initialize()
        
        result = await sync_manager.sync_all_sources(request.force_full_sync)
        
        logger.info("✅ Sync of all sources completed")
        return result
        
    except Exception as e:
        logger.error(f"Error in sync all sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync/{source_name}")
async def sync_source(source_name: str, request: SyncRequest = SyncRequest()):
    """Sync a specific data source"""
    try:
        logger.info(f"🔄 Starting sync for {source_name}")
        
        # Use the sync manager
        from data_connectors import DataSyncManager
        sync_manager = DataSyncManager()
        await sync_manager.initialize()
        
        result = await sync_manager.sync_source(source_name, request.force_full_sync)
        
        logger.info(f"✅ Sync for {source_name} completed")
        return result
        
    except Exception as e:
        logger.error(f"Error syncing {source_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sync-status")
async def get_sync_status():
    """Get sync status for all data sources"""
    try:
        logger.info("📊 Getting sync status")
        
        # Use the sync manager
        from data_connectors import DataSyncManager
        sync_manager = DataSyncManager()
        await sync_manager.initialize()
        
        status = await sync_manager.get_sync_status()
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/embeddings/refresh")
async def refresh_embeddings(request: EmbeddingRefreshRequest):
    """Refresh old embeddings"""
    try:
        logger.info("🔄 Starting embedding refresh")
        
        # This would call your vector store refresh method
        # For now, returning mock data
        result = {
            "status": "success",
            "data": {
                "documents_to_refresh": 0,
                "refresh_timestamp": datetime.now().isoformat(),
                "criteria": request.embedding_created_at
            }
        }
        
        logger.info("✅ Embedding refresh analysis completed")
        return result
        
    except Exception as e:
        logger.error(f"Error during embedding refresh: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/embedding-stats")
async def get_embedding_stats():
    """Get embedding statistics"""
    try:
        logger.info("📊 Getting embedding statistics")
        
        # This would call your vector store stats method
        # For now, returning mock data
        stats = {
            "status": "success",
            "data": {
                "total_embeddings": 0,
                "embedding_models": {},
                "chunk_types": {},
                "embedding_age_stats": {}
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting embedding stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/collection-stats")
async def get_collection_stats():
    """Get collection statistics"""
    try:
        logger.info("📊 Getting collection statistics")
        
        # This would call your vector store collection stats method
        # For now, returning mock data
        stats = {
            "status": "success",
            "data": {
                "total_documents": 0,
                "total_chunks": 0,
                "collection_size_mb": 0,
                "last_updated": datetime.now().isoformat()
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_system_status():
    """Get overall system status"""
    try:
        logger.info("📊 Getting system status")
        
        # Check various system components
        chatbot_healthy = await chatbot.health_check()
        vector_store_healthy = True  # You might want to add a health check method
        
        status = {
            "status": "healthy" if chatbot_healthy and vector_store_healthy else "unhealthy",
            "components": {
                "chatbot": "healthy" if chatbot_healthy else "unhealthy",
                "vector_store": "healthy" if vector_store_healthy else "unhealthy"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/sync-statistics")
async def get_sync_statistics():
    """Get detailed sync statistics and history"""
    try:
        from data_connectors import DataSyncManager
        sync_manager = DataSyncManager()
        await sync_manager.initialize()
        
        stats = await sync_manager.get_sync_statistics()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting sync statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/force-full-sync")
async def force_full_sync(source_name: str = None):
    """Force a full sync for a specific source or all sources"""
    try:
        from data_connectors import DataSyncManager
        sync_manager = DataSyncManager()
        await sync_manager.initialize()
        
        result = await sync_manager.force_full_sync(source_name)
        return result
        
    except Exception as e:
        logger.error(f"Error in force full sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time chat
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process chat message
            result = await chatbot.chat(
                user_message=message_data.get("message", ""),
                conversation_id=message_data.get("conversation_id"),
                include_sources=message_data.get("include_sources", True),
                max_sources=message_data.get("max_sources", 3)
            )
            
            # Send response back to client
            await manager.send_personal_message(
                json.dumps(result),
                websocket
            )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        chatbot_healthy = await chatbot.health_check()
        
        return {
            "status": "healthy" if chatbot_healthy else "unhealthy",
            "chatbot": chatbot_healthy,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "web_app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    ) 