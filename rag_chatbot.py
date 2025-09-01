import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import openai
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.prompts import ChatPromptTemplate
from langchain.chains import LLMChain

from vector_store import VectorStore
from config import settings
from loguru import logger

class RAGChatbot:
    """RAG-based chatbot that uses team documents for intelligent responses"""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.llm = None
        self.initialized = False
        self.conversation_history = []
        
    async def initialize(self):
        """Initialize the chatbot"""
        try:
            # Initialize vector store
            await self.vector_store.initialize()
            
            # Initialize OpenAI client
            openai.api_key = settings.openai_api_key
            
            # Initialize LangChain chat model
            self.llm = ChatOpenAI(
                model_name=settings.openai_model,
                temperature=0.7,
                max_tokens=1000
            )
            
            self.initialized = True
            logger.info("RAG chatbot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG chatbot: {e}")
            raise
    
    async def chat(self, user_message: str, conversation_id: str = None, 
                   include_sources: bool = True, max_sources: int = 3) -> Dict[str, Any]:
        """Process a user message and return a response"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Search for relevant documents
            search_results = await self.vector_store.search(
                query=user_message,
                n_results=max_sources
            )
            
            # Prepare context from search results
            context = self._prepare_context(search_results)
            
            # Generate response using LLM
            response = await self._generate_response(user_message, context, include_sources)
            
            # Prepare sources information
            sources = []
            if include_sources and search_results:
                sources = self._prepare_sources(search_results)
            
            # Store conversation history
            self.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "user_message": user_message,
                "assistant_response": response,
                "sources": sources,
                "conversation_id": conversation_id
            })
            
            return {
                "response": response,
                "sources": sources,
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            return {
                "response": "I apologize, but I encountered an error while processing your request. Please try again.",
                "sources": [],
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _prepare_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Prepare context from search results"""
        if not search_results:
            return "No relevant documents found."
        
        context_parts = []
        for i, result in enumerate(search_results, 1):
            content = result.get('content', '')
            metadata = result.get('metadata', {})
            title = metadata.get('title', 'Unknown Document')
            source_type = metadata.get('source_type', 'Unknown Source')
            source_url = metadata.get('source_url', '')
            
            context_parts.append(f"Document {i}:")
            context_parts.append(f"Title: {title}")
            context_parts.append(f"Source: {source_type}")
            context_parts.append(f"Content: {content[:1000]}...")  # Limit content length
            if source_url:
                context_parts.append(f"URL: {source_url}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _prepare_sources(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare sources information for the response"""
        sources = []
        for result in search_results:
            metadata = result.get('metadata', {})
            sources.append({
                "title": metadata.get('title', 'Unknown Document'),
                "source_type": metadata.get('source_type', 'Unknown Source'),
                "source_url": metadata.get('source_url', ''),
                "relevance_score": 1 - (result.get('distance', 0) if result.get('distance') else 0)
            })
        return sources
    
    async def _generate_response(self, user_message: str, context: str, include_sources: bool) -> str:
        """Generate response using the LLM"""
        try:
            # Create system prompt
            system_prompt = self._create_system_prompt(include_sources)
            
            # Create user prompt with context
            user_prompt = f"""Based on the following context from your team's documents, please answer the user's question:

Context:
{context}

User Question: {user_message}

Please provide a helpful and accurate response based on the context provided. If the context doesn't contain enough information to answer the question, please say so and suggest where they might find more information."""

            # Generate response
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.llm.agenerate([messages])
            return response.generations[0][0].text.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I apologize, but I encountered an error while generating a response. Please try again."
    
    def _create_system_prompt(self, include_sources: bool) -> str:
        """Create the system prompt for the chatbot"""
        base_prompt = """You are a helpful AI assistant for a team's knowledge base. You have access to documents from multiple sources including:

1. Confluence pages and blog posts
2. Tableau dashboards and workbooks
3. SharePoint documents (presentations, tables, word docs)

Your role is to:
- Provide accurate and helpful answers based on the team's documents
- Cite specific sources when possible
- Be conversational and professional
- If you don't have enough information, suggest where to find more details
- Focus on practical, actionable information

Guidelines:
- Always base your responses on the provided context
- Be concise but thorough
- Use a professional but friendly tone
- If the context doesn't contain relevant information, acknowledge this and suggest alternative sources
- When citing sources, mention the document title and source type"""

        if include_sources:
            base_prompt += "\n\nWhen providing information, you may reference specific documents and sources to support your answers."

        return base_prompt
    
    async def search_documents(self, query: str, n_results: int = 5, 
                              filter_source: str = None) -> List[Dict[str, Any]]:
        """Search documents directly"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Prepare filter
            filter_metadata = None
            if filter_source:
                filter_metadata = {"source_type": filter_source}
            
            # Search vector store
            results = await self.vector_store.search(
                query=query,
                n_results=n_results,
                filter_metadata=filter_metadata
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.get('content', ''),
                    "metadata": result.get('metadata', {}),
                    "relevance_score": 1 - (result.get('distance', 0) if result.get('distance') else 0)
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    async def get_conversation_history(self, conversation_id: str = None, 
                                      limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history"""
        if conversation_id:
            # Filter by conversation ID
            history = [
                msg for msg in self.conversation_history 
                if msg.get('conversation_id') == conversation_id
            ]
        else:
            # Get all history
            history = self.conversation_history
        
        # Return limited results
        return history[-limit:] if limit else history
    
    async def clear_conversation_history(self, conversation_id: str = None):
        """Clear conversation history"""
        if conversation_id:
            self.conversation_history = [
                msg for msg in self.conversation_history 
                if msg.get('conversation_id') != conversation_id
            ]
        else:
            self.conversation_history = []
        
        logger.info("Conversation history cleared")
    
    async def get_chatbot_stats(self) -> Dict[str, Any]:
        """Get chatbot statistics"""
        try:
            vector_stats = await self.vector_store.get_collection_stats()
            
            return {
                "total_conversations": len(set(msg.get('conversation_id') for msg in self.conversation_history if msg.get('conversation_id'))),
                "total_messages": len(self.conversation_history),
                "vector_store_stats": vector_stats,
                "model": settings.openai_model,
                "initialized": self.initialized
            }
        except Exception as e:
            logger.error(f"Error getting chatbot stats: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Perform a health check"""
        try:
            if not self.initialized:
                return False
            
            # Check vector store
            stats = await self.vector_store.get_collection_stats()
            if not stats:
                return False
            
            # Check OpenAI connection (simple test)
            try:
                test_response = await self.llm.agenerate([["Hello"]])
                return True
            except:
                return False
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False 