import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import aiohttp
from atlassian import Confluence
from bs4 import BeautifulSoup
import re
from dataclasses import dataclass

from .base_connector import BaseConnector, Document
from config import settings
from loguru import logger

from document_processor import DocumentProcessor, DocumentChunk

class ConfluenceConnector(BaseConnector):
    """Connector for Atlassian Confluence"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.confluence = None
        self.space_keys = settings.confluence_space_keys.split(',') if settings.confluence_space_keys else []
    
    async def connect(self) -> bool:
        """Establish connection to Confluence"""
        try:
            self.confluence = Confluence(
                url=settings.confluence_url,
                username=settings.confluence_username,
                password=settings.confluence_api_token,
                cloud=True
            )
            # Test connection
            self.confluence.get_all_spaces()
            logger.info(f"Successfully connected to Confluence at {settings.confluence_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Confluence: {e}")
            return False
    
    async def fetch_documents(self) -> List[Document]:
        """Fetch all documents from Confluence"""
        documents = []
        
        try:
            # Get all spaces if not specified
            if not self.space_keys:
                spaces = self.confluence.get_all_spaces()
                self.space_keys = [space['key'] for space in spaces['results']]
            
            for space_key in self.space_keys:
                try:
                    space_docs = await self._fetch_space_documents(space_key)
                    documents.extend(space_docs)
                except Exception as e:
                    logger.error(f"Error fetching documents from space {space_key}: {e}")
                    continue
            
            logger.info(f"Fetched {len(documents)} documents from Confluence")
            return documents
            
        except Exception as e:
            logger.error(f"Error fetching Confluence documents: {e}")
            return []
    
    async def _fetch_space_documents(self, space_key: str) -> List[Document]:
        """Fetch documents from a specific space"""
        documents = []
        
        try:
            # Get all pages in the space
            pages = self.confluence.get_all_pages_from_space(space_key, start=0, limit=1000)
            
            for page in pages:
                try:
                    doc = await self._process_page(page, space_key)
                    if doc:
                        documents.extend(doc)
                except Exception as e:
                    logger.error(f"Error processing page {page.get('id')}: {e}")
                    continue
            
            # Get all blog posts in the space
            blogs = self.confluence.get_all_blogs_from_space(space_key, start=0, limit=1000)
            
            for blog in blogs:
                try:
                    doc = await self._process_blog(blog, space_key)
                    if doc:
                        documents.extend(doc)
                except Exception as e:
                    logger.error(f"Error processing blog {blog.get('id')}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching documents from space {space_key}: {e}")
        
        return documents
    
    async def _process_page(self, page: Dict[str, Any], space_key: str) -> List[Document]:
        """Process a Confluence page into multiple Documents (text + tables)"""
        try:
            page_id = page['id']
            page_content = self.confluence.get_page_by_id(page_id, expand='body.storage')
            
            # Extract content with table separation
            content_html = page_content['body']['storage']['value']
            extracted_content = self._extract_text_with_table_chunks(content_html)
            
            documents = []
            
            # Create main text document
            if extracted_content["text"].strip():
                text_doc = Document(
                    id=f"confluence_page_{page_id}_text",
                    title=f"{page_content['title']} - Text Content",
                    content=extracted_content["text"],
                    source_type="confluence",
                    source_url=f"{settings.confluence_url}/wiki{page_content['_links']['webui']}",
                    metadata={
                        'space_key': space_key,
                        'page_type': 'page',
                        'content_type': 'text',
                        'version': page_content.get('version', {}).get('number'),
                        'status': page_content.get('status'),
                        'ancestors': [ancestor.get('title') for ancestor in page_content.get('ancestors', [])]
                    },
                    last_modified=datetime.fromisoformat(page_content['version']['when'].replace('Z', '+00:00')),
                    created_at=datetime.fromisoformat(page_content['created'].replace('Z', '+00:00'))
                )
                documents.append(text_doc)
            
            # Create separate documents for each table
            for table_chunk in extracted_content["table_chunks"]:
                table_doc = Document(
                    id=f"confluence_page_{page_id}_{table_chunk['id']}",
                    title=f"{page_content['title']} - Table {table_chunk['table_index'] + 1}",
                    content=table_chunk["content"],
                    source_type="confluence",
                    source_url=f"{settings.confluence_url}/wiki{page_content['_links']['webui']}",
                    metadata={
                        'space_key': space_key,
                        'page_type': 'page',
                        'content_type': 'table',
                        'table_index': table_chunk['table_index'],
                        'version': page_content.get('version', {}).get('number'),
                        'status': page_content.get('status'),
                        'ancestors': [ancestor.get('title') for ancestor in page_content.get('ancestors', [])]
                    },
                    last_modified=datetime.fromisoformat(page_content['version']['when'].replace('Z', '+00:00')),
                    created_at=datetime.fromisoformat(page_content['created'].replace('Z', '+00:00'))
                )
                documents.append(table_doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Error processing page {page.get('id')}: {e}")
            return []
    
    async def _process_blog(self, blog: Dict[str, Any], space_key: str) -> Optional[Document]:
        """Process a Confluence blog post into a Document"""
        try:
            blog_id = blog['id']
            blog_content = self.confluence.get_page_by_id(blog_id, expand='body.storage')
            
            # Extract content
            content_html = blog_content['body']['storage']['value']
            content_text = self._extract_text_from_html(content_html)
            
            # Get metadata
            metadata = {
                'space_key': space_key,
                'page_type': 'blog',
                'version': blog_content.get('version', {}).get('number'),
                'status': blog_content.get('status')
            }
            
            return Document(
                id=f"confluence_blog_{blog_id}",
                title=blog_content['title'],
                content=content_text,
                source_type="confluence",
                source_url=f"{settings.confluence_url}/wiki{blog_content['_links']['webui']}",
                metadata=metadata,
                last_modified=datetime.fromisoformat(blog_content['version']['when'].replace('Z', '+00:00')),
                created_at=datetime.fromisoformat(blog_content['created'].replace('Z', '+00:00'))
            )
            
        except Exception as e:
            logger.error(f"Error processing blog {blog.get('id')}: {e}")
            return None
    
    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract clean text from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it up
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.error(f"Error extracting text from HTML: {e}")
            return html_content
    
    def _extract_text_with_table_chunks(self, html_content: str) -> Dict[str, Any]:
        """Extract text and separate table chunks"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract tables first
            tables = soup.find_all('table')
            table_chunks = []
            
            for i, table in enumerate(tables):
                table_text = self._table_to_text(table)
                if table_text:
                    table_chunks.append({
                        "id": f"table_{i}",
                        "content": table_text,
                        "type": "table",
                        "table_index": i
                    })
            
            # Remove tables from soup for text processing
            for table in tables:
                table.decompose()
            
            # Get remaining text
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return {
                "text": text,
                "table_chunks": table_chunks,
                "has_tables": len(table_chunks) > 0
            }
            
        except Exception as e:
            logger.error(f"Error extracting text with table chunks: {e}")
            return {"text": html_content, "table_chunks": [], "has_tables": False}
    
    def _table_to_text(self, table: BeautifulSoup) -> str:
        """Convert a BeautifulSoup table element to a string"""
        try:
            # Extract table header and rows
            header_row = table.find('tr')
            if not header_row:
                return ""
            
            header_cells = header_row.find_all('th')
            header_text = " | ".join([cell.get_text(strip=True) for cell in header_cells])
            
            # Extract data rows
            data_rows = table.find_all('tr')[1:] # Skip header row
            data_text = []
            for row in data_rows:
                cells = row.find_all('td')
                row_text = " | ".join([cell.get_text(strip=True) for cell in cells])
                data_text.append(row_text)
            
            # Combine header and data
            if header_text:
                return f"TABLE: {header_text}\n" + "\n".join(data_text) + " END TABLE"
            else:
                return "\n".join(data_text) + " END TABLE"
        except Exception as e:
            logger.error(f"Error converting table to text: {e}")
            return ""
    
    async def fetch_recent_documents(self, since: datetime) -> List[Document]:
        """Fetch documents modified since a specific time"""
        all_docs = await self.fetch_documents()
        recent_docs = [
            doc for doc in all_docs 
            if doc.last_modified and doc.last_modified > since
        ]
        logger.info(f"Found {len(recent_docs)} recent documents since {since}")
        return recent_docs
    
    async def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """Fetch a specific document by ID"""
        try:
            # Extract the actual Confluence ID from our document ID
            if doc_id.startswith("confluence_page_"):
                page_id = doc_id.replace("confluence_page_", "")
                page_content = self.confluence.get_page_by_id(page_id, expand='body.storage')
                return await self._process_page({'id': page_id}, page_content.get('space', {}).get('key', ''))
            elif doc_id.startswith("confluence_blog_"):
                blog_id = doc_id.replace("confluence_blog_", "")
                blog_content = self.confluence.get_page_by_id(blog_id, expand='body.storage')
                return await self._process_blog({'id': blog_id}, blog_content.get('space', {}).get('key', ''))
        except Exception as e:
            logger.error(f"Error fetching document {doc_id}: {e}")
        return None 

@dataclass
class DocumentChunk:
    """Represents a chunk of a document"""
    id: str
    content: str
    metadata: Dict[str, Any]
    chunk_index: int
    total_chunks: int

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
        
        # Clean and prepare the content
        cleaned_content = self._clean_content(document.content)
        
        # Split content into chunks
        text_chunks = self._split_text(cleaned_content)
        
        # Create chunk objects
        for i, chunk_text in enumerate(text_chunks):
            chunk_id = f"{document.id}_chunk_{i}"
            
            # Prepare chunk metadata
            chunk_metadata = {
                "original_id": document.id,
                "title": document.title,
                "source_type": document.source_type,
                "source_url": document.source_url,
                "chunk_index": i,
                "total_chunks": len(text_chunks),
                "created_at": document.created_at.isoformat() if document.created_at else "",
                "last_modified": document.last_modified.isoformat() if document.last_modified else "",
                **document.metadata
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
        """Clean and normalize content"""
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove special characters that might interfere with chunking
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', content)
        
        # Normalize line breaks
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
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
            # Calculate end position
            end = start + self.chunk_size
            
            # If this is not the last chunk, try to break at a sentence boundary
            if end < len(text):
                # Look for sentence endings within the last 200 characters
                search_start = max(start + self.chunk_size - 200, start)
                search_end = min(end + 200, len(text))
                search_text = text[search_start:search_end]
                
                # Find the last sentence boundary
                sentence_end = self._find_last_sentence_boundary(search_text)
                if sentence_end > 0:
                    end = search_start + sentence_end
            
            # Extract the chunk
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position for next chunk (with overlap)
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _find_last_sentence_boundary(self, text: str) -> int:
        """Find the last sentence boundary in the text"""
        # Common sentence endings
        sentence_endings = ['. ', '! ', '? ', '.\n', '!\n', '?\n']
        
        last_boundary = -1
        for ending in sentence_endings:
            pos = text.rfind(ending)
            if pos > last_boundary:
                last_boundary = pos + len(ending) - 1
        
        return last_boundary 