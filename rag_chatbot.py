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
            # Rewrite the query for better retrieval
            rewritten_query = await self._rewrite_query(user_message)
            logger.info(f"Original query: '{user_message}' -> Rewritten: '{rewritten_query}'")
            
            # Search for relevant documents using rewritten query
            search_results = await self.vector_store.search(
                query=rewritten_query,
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
                "timestamp": datetime.now().isoformat(),
                "query_info": {
                    "original_query": user_message,
                    "rewritten_query": rewritten_query
                }
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
            user_prompt = f"""Based on the following context from your team's documents, 
            please answer the user's question:

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
    
    async def _rewrite_query(self, user_query: str, conversation_history: List[Dict] = None) -> str:
        """Rewrite user query to improve retrieval using Tesla energy industry knowledge and conversation context"""
        try:
            system_prompt = """You are a query rewriting assistant for documentation 
            search on a team that investigates issues with Tesla's Residential energy fleet. 
            Rewrite the user's question to maximize correct retrieval while keeping the core meaning of the original query. 
            First consider the conversation history to understand context and references, paying attention
            to pronouns and follow-up questions. Then Think about the components of Tesla's energy products, 
            use industry-specific terms, expand on ambiguous parts, and add relevant synonyms or acronyms 
            (e.g. PW3 for Powerwall 3).

            Conversation Context Examples:
            
            Example 1 - Follow-up question:
            Previous: "What are main causes of arcing in PW3 sites?"
            Current: "how about PW2?"
            Output: "What are main causes of arcing in Powerwall 2 PW2 sites? (following up on previous question about arcing in Powerwall 3 sites)"
            
            Example 2 - Pronoun reference:
            Previous: "Powerwall not charging properly"
            Current: "what about the inverter?"
            Output: "What about Powerwall inverter issues related to charging problems? (referring to inverter problems causing Powerwall charging issues)"
            
            Example 3 - Topic continuation:
            Previous: "Solar panels underperforming"
            Current: "any other causes?"
            Output: "What are other causes of solar panel underperformance beyond what was mentioned? (continuing discussion about solar panel performance issues)"
            
            Example 4 - Product comparison:
            Previous: "PW3 installation guide"
            Current: "same for PW2?"
            Output: "Powerwall 2 PW2 installation guide (asking for similar installation information for Powerwall 2 as was provided for Powerwall 3)"

            Key Tesla Energy Products and Acronyms:
            - Powerwall (PW, PW2: Powerwall 2, PW3: Powerwall 3)
            - Solar Panels (Solar Roof, Solar Panels, PV)
            - Solar Inverter (PVI PVCOM: Legacy Solar Inverter, PVI-45:Solar Inverter 45)
            - Gateway (GW, Backup Gateway, Backup Gateway 2)
            - Backup Switch (BS, Backup Switch 2)
            - Wall Connector (WC, Gen 3, Gen 4)
            - Energy Management System (EMS)
            - TOU (Time of Use) rates

            Common Issues and Terms:
            - Inverter faults, communication errors, grid disconnections
            - Battery degradation, capacity loss, cycle count
            - Solar production issues, shading, panel failures
            - Installation problems, mounting, wiring
            - Software bugs, firmware updates, app issues
            - Grid integration, utility communication, interconnection
            - Performance monitoring, data logging, analytics

            Example for adding more keywords and details to the query:
            Input: "I am seeing solar underperformance on a particular site, what could be the reason?"
            Output: "What are some causes of solar system underperformance on a residential Tesla Energy site (solar panels / PV array). 
            What factors could lead to reduced solar generation output, such as inverter efficiency issues, DC/AC conversion losses, shading, 
            soiling, wiring or connection faults, rapid shutdown device problems, degradation of PV modules, monitoring calibration errors, 
            or site-specific environmental conditions?"


            

            
            """

            # Prepare conversation context for the prompt
            conversation_context = ""
            if conversation_history and len(conversation_history) > 0:
                # Get last 3 user messages for context (excluding current query)
                recent_messages = conversation_history[-3:]  # Last 3 messages
                conversation_context = "Recent conversation context:\n"
                for i, msg in enumerate(recent_messages, 1):
                    if msg.get('user_message'):
                        conversation_context += f"{i}. User: {msg['user_message']}\n"
                        if msg.get('assistant_response'):
                            conversation_context += f"   Assistant: {msg['assistant_response'][:200]}...\n"
                conversation_context += "\n"
            
            user_prompt = f"""{conversation_context}Original query: {user_query}

Please rewrite this query considering the conversation context above. If this is a follow-up question, incorporate relevant details from the conversation.

Rewritten query:"""

            # Generate rewritten query
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await self.llm.agenerate([messages])
            rewritten_query = response.generations[0][0].text.strip()
            
            # Clean up the response (remove any extra text)
            if "\n" in rewritten_query:
                rewritten_query = rewritten_query.split("\n")[0].strip()
            
            # Fallback to original query if rewriting fails
            if not rewritten_query or len(rewritten_query) < 5:
                logger.warning(f"Query rewriting failed, using original query: {user_query}")
                return user_query
            
            return rewritten_query
            
        except Exception as e:
            logger.error(f"Error rewriting query: {e}")
            # Fallback to original query
            return user_query

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
- Always base your responses on the team's documents
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
            # Rewrite the query for better retrieval
            rewritten_query = await self._rewrite_query(query)
            logger.info(f"Search - Original query: '{query}' -> Rewritten: '{rewritten_query}'")
            
            # Prepare filter
            filter_metadata = None
            if filter_source:
                filter_metadata = {"source_type": filter_source}
            
            # Search vector store with rewritten query
            results = await self.vector_store.search(
                query=rewritten_query,
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