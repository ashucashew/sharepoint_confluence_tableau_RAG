import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
import hashlib
import json
import re
import uuid

from data_connectors import Document
from config import settings
from loguru import logger

class DocumentChunk:
    """Represents a chunk of a document"""
    def __init__(self, id: str, content: str, metadata: Dict[str, Any], chunk_index: int, total_chunks: int):
        self.id = id
        self.content = content
        self.metadata = metadata
        self.chunk_index = chunk_index
        self.total_chunks = total_chunks

class DocumentProcessor:
    """Handles document processing including chunking and text cleaning"""
    
    def __init__(self):
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
    
    def process_documents(self, documents: List[Document]) -> List[DocumentChunk]:
        """Process documents and return chunks"""
        chunks = []
        
        for doc in documents:
            try:
                doc_chunks = self._chunk_document(doc)
                chunks.extend(doc_chunks)
            except Exception as e:
                logger.error(f"Error processing document {doc.id}: {e}")
                continue
        
        logger.info(f"Processed {len(documents)} documents into {len(chunks)} chunks")
        return chunks
    
    def _chunk_document(self, document: Document) -> List[DocumentChunk]:
        """Chunk a single document"""
        chunks = []
        
        # Special handling for different document types
        if document.source_type == "sharepoint" and document.metadata.get('file_type') == '.pptx':
            # Chunk PowerPoint presentations by slide
            chunks = self._chunk_powerpoint_by_slide(document)
        elif document.source_type == "sharepoint" and document.metadata.get('file_type') == '.docx':
            # Chunk Word documents by sections
            chunks = self._chunk_word_by_sections(document)
        elif document.source_type == "sharepoint" and document.metadata.get('file_type') == '.xlsx':
            # Chunk Excel by worksheet
            chunks = self._chunk_excel_by_worksheet(document)
        else:
            # Default chunking for other documents
            chunks = self._chunk_by_size(document)
        
        return chunks
    
    def _chunk_powerpoint_by_slide(self, document: Document) -> List[DocumentChunk]:
        """Chunk PowerPoint presentation by individual slides"""
        chunks = []
        content = document.content
        
        # Split by slide markers
        slide_pattern = r'Slide \d+:'
        slide_matches = list(re.finditer(slide_pattern, content))
        
        if not slide_matches:
            # Fall back to size-based chunking if no slide markers found
            return self._chunk_by_size(document)
        
        for i, match in enumerate(slide_matches):
            start_pos = match.start()
            end_pos = slide_matches[i + 1].start() if i + 1 < len(slide_matches) else len(content)
            
            slide_content = content[start_pos:end_pos].strip()
            if slide_content:
                chunk_id = f"{document.id}_slide_{i + 1}"
                chunk_metadata = {
                    **document.metadata,
                    "chunk_type": "slide",
                    "slide_number": i + 1,
                    "total_slides": len(slide_matches),
                    "original_title": document.title
                }
                
                chunk = DocumentChunk(
                    id=chunk_id,
                    content=slide_content,
                    metadata=chunk_metadata,
                    chunk_index=i,
                    total_chunks=len(slide_matches)
                )
                chunks.append(chunk)
        
        return chunks
    
    def _chunk_word_by_sections(self, document: Document) -> List[DocumentChunk]:
        """Chunk Word document by sections and tables"""
        chunks = []
        content = document.content
        
        # Split by table markers first
        table_pattern = r'TABLE:\n(.*?)\nEND TABLE'
        table_matches = list(re.finditer(table_pattern, content, re.DOTALL))
        
        if table_matches:
            # Process tables as separate chunks
            last_end = 0
            for i, match in enumerate(table_matches):
                # Add text before table
                text_before = content[last_end:match.start()].strip()
                if text_before:
                    chunks.extend(self._chunk_text_segment(text_before, document, f"text_{i}", "text"))
                
                # Add table as separate chunk
                table_content = match.group(0)
                chunk_id = f"{document.id}_table_{i + 1}"
                chunk_metadata = {
                    **document.metadata,
                    "chunk_type": "table",
                    "table_number": i + 1,
                    "total_tables": len(table_matches),
                    "original_title": document.title
                }
                
                chunk = DocumentChunk(
                    id=chunk_id,
                    content=table_content,
                    metadata=chunk_metadata,
                    chunk_index=len(chunks),
                    total_chunks=len(table_matches) + len(chunks)
                )
                chunks.append(chunk)
                last_end = match.end()
            
            # Add remaining text after last table
            text_after = content[last_end:].strip()
            if text_after:
                chunks.extend(self._chunk_text_segment(text_after, document, f"text_final", "text"))
        else:
            # No tables found, use size-based chunking
            chunks = self._chunk_by_size(document)
        
        return chunks
    
    def _chunk_excel_by_worksheet(self, document: Document) -> List[DocumentChunk]:
        """Chunk Excel workbook by worksheets"""
        chunks = []
        content = document.content
        
        # Split by worksheet markers
        worksheet_pattern = r'Worksheet: (.+?)(?=\n\nWorksheet:|$)'
        worksheet_matches = list(re.finditer(worksheet_pattern, content, re.DOTALL))
        
        if not worksheet_matches:
            # Fall back to size-based chunking if no worksheet markers found
            return self._chunk_by_size(document)
        
        for i, match in enumerate(worksheet_matches):
            worksheet_content = match.group(0).strip()
            if worksheet_content:
                chunk_id = f"{document.id}_worksheet_{i + 1}"
                chunk_metadata = {
                    **document.metadata,
                    "chunk_type": "worksheet",
                    "worksheet_number": i + 1,
                    "total_worksheets": len(worksheet_matches),
                    "worksheet_name": match.group(1),
                    "original_title": document.title
                }
                
                chunk = DocumentChunk(
                    id=chunk_id,
                    content=worksheet_content,
                    metadata=chunk_metadata,
                    chunk_index=i,
                    total_chunks=len(worksheet_matches)
                )
                chunks.append(chunk)
        
        return chunks
    
    def _chunk_text_segment(self, text: str, document: Document, segment_id: str, chunk_type: str) -> List[DocumentChunk]:
        """Chunk a text segment by size"""
        chunks = []
        text_chunks = self._split_text(text)
        
        for i, chunk_text in enumerate(text_chunks):
            chunk_id = f"{document.id}_{segment_id}_{i + 1}"
            chunk_metadata = {
                **document.metadata,
                "chunk_type": chunk_type,
                "segment_id": segment_id,
                "original_title": document.title
            }
            
            chunk = DocumentChunk(
                id=chunk_id,
                content=chunk_text,
                metadata=chunk_metadata,
                chunk_index=i,
                total_chunks=len(text_chunks)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _chunk_by_size(self, document: Document) -> List[DocumentChunk]:
        """Default chunking by text size"""
        # Clean and prepare the content
        cleaned_content = self._clean_content(document.content)
        
        # Split content into chunks
        text_chunks = self._split_text(cleaned_content)
        
        # Initialize chunks list
        chunks = []
        
        # Create chunk objects
        for i, chunk_text in enumerate(text_chunks):
            chunk_id = f"{document.id}_chunk_{i + 1}"
            
            # Prepare chunk metadata
            chunk_metadata = {
                **document.metadata,
                "chunk_type": "text",
                "original_title": document.title
            }
            
            chunk = DocumentChunk(
                id=chunk_id,
                content=chunk_text,
                metadata=chunk_metadata,
                chunk_index=i,
                total_chunks=len(text_chunks)
            )
            chunks.append(chunk)
        
        return chunks
    
    def _clean_content(self, content: str) -> str:
        """Clean and prepare content for chunking"""
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove special characters that might interfere with chunking
        content = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}]', '', content)
        
        return content.strip()
    
    def _split_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        if not text:
            return []
        
        # If text is shorter than chunk size, return as single chunk
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # If this is not the last chunk, try to break at a sentence boundary
            if end < len(text):
                # Look for sentence endings in the last 200 characters of the chunk
                search_start = max(start + self.chunk_size - 200, start)
                search_text = text[search_start:end]
                
                # Find the last sentence ending
                sentence_endings = ['.', '!', '?', '\n\n']
                last_ending = -1
                for ending in sentence_endings:
                    pos = search_text.rfind(ending)
                    if pos > last_ending:
                        last_ending = pos
                
                if last_ending > 0:
                    end = search_start + last_ending + 1
            
            # Extract the chunk
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position for next chunk (with overlap)
            start = end - self.chunk_overlap
        
        return chunks

class VectorStore:
    """Manages vector storage and retrieval using ChromaDB with comprehensive tracking"""
    
    def __init__(self):
        self.client = None
        self.collection = None
        self.embedding_model = None
        self.initialized = False
        self.document_processor = DocumentProcessor()
    
    async def initialize(self):
        """Initialize the vector store"""
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer(settings.embedding_model)
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="team_documents",
                metadata={"description": "Team documents from multiple sources"}
            )
            
            self.initialized = True
            logger.info("Vector store initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    async def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to the vector store with comprehensive tracking"""
        if not self.initialized:
            await self.initialize()
        
        try:
            if not documents:
                return True
            
            # Process documents into chunks
            chunks = self.document_processor.process_documents(documents)
            
            if not chunks:
                logger.warning("No chunks generated from documents")
                return True
            
            # Prepare chunks for insertion with comprehensive metadata
            ids = []
            texts = []
            metadatas = []
            embeddings = []
            
            current_time = datetime.now().isoformat()
            embedding_model_version = self._get_embedding_model_version()
            
            for chunk in chunks:
                # Create a unique ID for the chunk
                chunk_id = self._create_chunk_id(chunk)
                ids.append(chunk_id)
                
                # Prepare text content
                text_content = f"Title: {chunk.metadata.get('original_title', 'Unknown')}\n\nContent: {chunk.content}"
                texts.append(text_content)
                
                # Generate embedding
                embedding = self.embedding_model.encode(text_content)
                embeddings.append(embedding.tolist())
                
                # Prepare comprehensive metadata
                metadata = {
                    # Document information
                    "title": chunk.metadata.get('original_title', 'Unknown'),
                    "source_type": chunk.metadata.get('source_type', 'unknown'),
                    "source_url": chunk.metadata.get('source_url', ''),
                    "original_id": chunk.metadata.get('original_id', ''),
                    
                    # Document timestamps
                    "document_created_at": chunk.metadata.get('created_at', ''),
                    "document_modified_at": chunk.metadata.get('last_modified', ''),
                    
                    # Embedding information
                    "embedding_created_at": current_time,
                    "embedding_updated_at": current_time,
                    "embedding_model": settings.embedding_model,
                    "embedding_model_version": embedding_model_version,
                    "embedding_dimensions": len(embedding),
                    
                    # Chunk information
                    "chunk_type": chunk.metadata.get('chunk_type', 'text'),
                    "chunk_index": chunk.chunk_index,
                    "total_chunks": chunk.total_chunks,
                    "chunk_size": len(chunk.content),
                    
                    # Processing information
                    "processing_id": str(uuid.uuid4()),
                    "processing_timestamp": current_time,
                    
                    # Additional metadata
                    **chunk.metadata
                }
                metadatas.append(metadata)
            
            # Add chunks to collection with embeddings
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            
            logger.info(f"Added {len(chunks)} chunks from {len(documents)} documents to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            return False
    
    async def update_documents(self, documents: List[Document]) -> bool:
        """Update existing documents in the vector store with new embeddings"""
        if not self.initialized:
            await self.initialize()
        
        try:
            if not documents:
                return True
            
            # Process documents into chunks
            chunks = self.document_processor.process_documents(documents)
            
            if not chunks:
                return True
            
            # Delete old chunks for these documents
            for doc in documents:
                await self._delete_document_chunks(doc.id)
            
            # Add new chunks with updated embeddings
            return await self.add_documents(documents)
            
        except Exception as e:
            logger.error(f"Error updating documents in vector store: {e}")
            return False
    
    async def _delete_document_chunks(self, document_id: str) -> bool:
        """Delete all chunks for a specific document"""
        try:
            # Find all chunks for this document
            results = self.collection.get(
                where={"original_id": document_id}
            )
            
            if results and results['ids']:
                # Delete all chunks for this document
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting chunks for document {document_id}: {e}")
            return False
    
    async def delete_documents(self, document_ids: List[str]) -> bool:
        """Delete documents from the vector store"""
        if not self.initialized:
            await self.initialize()
        
        try:
            if not document_ids:
                return True
            
            # Delete chunks for each document
            for doc_id in document_ids:
                await self._delete_document_chunks(doc_id)
            
            logger.info(f"Deleted {len(document_ids)} documents from vector store")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting documents from vector store: {e}")
            return False
    
    async def search(self, query: str, n_results: int = None, filter_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search for documents in the vector store"""
        if not self.initialized:
            await self.initialize()
        
        try:
            n_results = n_results or settings.max_results
            
            # Prepare where clause for filtering
            where_clause = None
            if filter_metadata:
                where_clause = filter_metadata
            
            # Search in the collection
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause,
                include=['metadatas', 'distances', 'embeddings']
            )
            
            # Format results with embedding information
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i],
                        'id': results['ids'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else None,
                        'embedding_info': {
                            'created_at': results['metadatas'][0][i].get('embedding_created_at'),
                            'updated_at': results['metadatas'][0][i].get('embedding_updated_at'),
                            'model': results['metadatas'][0][i].get('embedding_model'),
                            'dimensions': results['metadatas'][0][i].get('embedding_dimensions')
                        }
                    })
            
            logger.info(f"Found {len(formatted_results)} results for query: {query}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []
    
    async def get_embedding_stats(self) -> Dict[str, Any]:
        """Get statistics about embeddings in the vector store"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Get all documents to analyze embedding metadata
            results = self.collection.get(limit=10000)
            
            if not results['metadatas']:
                return {"error": "No documents found"}
            
            # Analyze embedding metadata
            embedding_models = {}
            embedding_versions = {}
            embedding_ages = []
            chunk_types = {}
            
            current_time = datetime.now()
            
            for metadata in results['metadatas']:
                # Count embedding models
                model = metadata.get('embedding_model', 'unknown')
                embedding_models[model] = embedding_models.get(model, 0) + 1
                
                # Count model versions
                version = metadata.get('embedding_model_version', 'unknown')
                embedding_versions[version] = embedding_versions.get(version, 0) + 1
                
                # Calculate embedding ages
                created_at = metadata.get('embedding_created_at')
                if created_at:
                    try:
                        created_time = datetime.fromisoformat(created_at)
                        age_hours = (current_time - created_time).total_seconds() / 3600
                        embedding_ages.append(age_hours)
                    except:
                        pass
                
                # Count chunk types
                chunk_type = metadata.get('chunk_type', 'unknown')
                chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
            
            return {
                'total_embeddings': len(results['metadatas']),
                'embedding_models': embedding_models,
                'embedding_versions': embedding_versions,
                'chunk_types': chunk_types,
                'embedding_age_stats': {
                    'oldest_hours': min(embedding_ages) if embedding_ages else 0,
                    'newest_hours': max(embedding_ages) if embedding_ages else 0,
                    'average_hours': sum(embedding_ages) / len(embedding_ages) if embedding_ages else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting embedding stats: {e}")
            return {"error": str(e)}
    
    def _get_embedding_model_version(self) -> str:
        """Get the version of the current embedding model"""
        try:
            # Try to get model version from sentence transformers
            model_info = self.embedding_model.get_sentence_embedding_dimension()
            return f"{settings.embedding_model}_v{model_info}"
        except:
            return f"{settings.embedding_model}_unknown"
    
    def _create_chunk_id(self, chunk: DocumentChunk) -> str:
        """Create a unique ID for a document chunk"""
        return chunk.id
    
    async def get_all_documents(self, filter_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get all documents from the vector store"""
        if not self.initialized:
            await self.initialize()
        
        try:
            # Get all documents from the collection
            results = self.collection.get(
                include=['metadatas', 'documents', 'embeddings'],
                where=filter_metadata
            )
            
            documents = []
            if results and results['ids']:
                for i, doc_id in enumerate(results['ids']):
                    document = {
                        "id": doc_id,
                        "content": results['documents'][i] if results['documents'] else "",
                        "metadata": results['metadatas'][i] if results['metadatas'] else {},
                        "embedding": results['embeddings'][i] if results['embeddings'] else None
                    }
                    documents.append(document)
            
            return documents
            
        except Exception as e:
            logger.error(f"Error getting all documents from vector store: {e}")
            return []
    