import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
import json

from rag_chatbot import RAGChatbot
from data_sync_manager import DataSyncManager
from config import settings
from loguru import logger

# Initialize FastAPI app
app = FastAPI(
    title="Team RAG Chatbot",
    description="A RAG-based chatbot for team knowledge management",
    version="1.0.0"
)

# Initialize components
chatbot = RAGChatbot()
sync_manager = DataSyncManager()

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
    source_name: Optional[str] = None
    force_full_sync: bool = False

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    try:
        await chatbot.initialize()
        await sync_manager.initialize()
        sync_manager.start_scheduled_sync()
        logger.info("Web application started successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        await sync_manager.cleanup()
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
        results = await chatbot.search_documents(
            query=request.query,
            n_results=request.n_results,
            filter_source=request.filter_source
        )
        
        return {
            "results": results,
            "query": request.query,
            "total_results": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sync")
async def sync_endpoint(request: SyncRequest, background_tasks: BackgroundTasks):
    """Sync data sources endpoint"""
    try:
        if request.source_name:
            # Sync specific source
            result = await sync_manager.sync_single_source(
                source_name=request.source_name,
                force_full_sync=request.force_full_sync
            )
        else:
            # Sync all sources
            result = await sync_manager.sync_all_sources(
                force_full_sync=request.force_full_sync
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in sync endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def status_endpoint():
    """Get system status"""
    try:
        chatbot_stats = await chatbot.get_chatbot_stats()
        sync_status = await sync_manager.get_sync_status()
        
        return {
            "chatbot": chatbot_stats,
            "sync_manager": sync_status,
            "system_health": await chatbot.health_check()
        }
        
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversation-history")
async def conversation_history_endpoint(conversation_id: Optional[str] = None, limit: int = 10):
    """Get conversation history"""
    try:
        history = await chatbot.get_conversation_history(
            conversation_id=conversation_id,
            limit=limit
        )
        
        return {
            "history": history,
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        logger.error(f"Error in conversation history endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/conversation-history")
async def clear_conversation_history_endpoint(conversation_id: Optional[str] = None):
    """Clear conversation history"""
    try:
        await chatbot.clear_conversation_history(conversation_id)
        return {"message": "Conversation history cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error in clear conversation history endpoint: {e}")
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
        sync_healthy = await sync_manager.health_check()
        
        return {
            "status": "healthy" if chatbot_healthy and sync_healthy else "unhealthy",
            "chatbot": chatbot_healthy,
            "sync_manager": sync_healthy,
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