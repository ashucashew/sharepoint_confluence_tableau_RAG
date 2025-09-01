import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import tableauserverclient as TSC
from tableauserverclient import ServerResponseError
from bs4 import BeautifulSoup

from .base_connector import BaseConnector, Document
from config import settings
from loguru import logger

class TableauConnector(BaseConnector):
    """Connector for Tableau Server"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.tableau_auth = None
        self.server = None
        self.site_id = settings.tableau_site_id
    
    async def connect(self) -> bool:
        """Establish connection to Tableau Server"""
        try:
            # Create authentication object
            self.tableau_auth = TSC.TableauAuth(
                username=settings.tableau_username,
                password=settings.tableau_password,
                site_id=self.site_id
            )
            
            # Create server object
            self.server = TSC.Server(settings.tableau_server_url)
            
            # Sign in
            self.server.auth.sign_in(self.tableau_auth)
            logger.info(f"Successfully connected to Tableau Server at {settings.tableau_server_url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Tableau Server: {e}")
            return False
    
    async def fetch_documents(self) -> List[Document]:
        """Fetch all documents from Tableau"""
        documents = []
        
        try:
            # Fetch workbooks
            workbooks = await self._fetch_workbooks()
            documents.extend(workbooks)
            
            # Fetch views (dashboards)
            views = await self._fetch_views()
            documents.extend(views)
            
            # Fetch datasources
            datasources = await self._fetch_datasources()
            documents.extend(datasources)
            
            logger.info(f"Fetched {len(documents)} documents from Tableau")
            return documents
            
        except Exception as e:
            logger.error(f"Error fetching Tableau documents: {e}")
            return []
    
    async def _fetch_workbooks(self) -> List[Document]:
        """Fetch workbooks from Tableau"""
        documents = []
        
        try:
            all_workbooks, pagination_item = self.server.workbooks.get()
            
            for workbook in all_workbooks:
                try:
                    doc = await self._process_workbook(workbook)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    logger.error(f"Error processing workbook {workbook.id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching workbooks: {e}")
        
        return documents
    
    async def _fetch_views(self) -> List[Document]:
        """Fetch views (dashboards) from Tableau"""
        documents = []
        
        try:
            all_views, pagination_item = self.server.views.get()
            
            for view in all_views:
                try:
                    doc = await self._process_view(view)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    logger.error(f"Error processing view {view.id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching views: {e}")
        
        return documents
    
    async def _fetch_datasources(self) -> List[Document]:
        """Fetch datasources from Tableau"""
        documents = []
        
        try:
            all_datasources, pagination_item = self.server.datasources.get()
            
            for datasource in all_datasources:
                try:
                    doc = await self._process_datasource(datasource)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    logger.error(f"Error processing datasource {datasource.id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching datasources: {e}")
        
        return documents
    
    async def _process_workbook(self, workbook) -> Optional[Document]:
        """Process a Tableau workbook into a Document"""
        try:
            # Get detailed workbook information
            workbook_detail = self.server.workbooks.get_by_id(workbook.id)
            
            # Build content from workbook metadata
            content_parts = []
            
            if workbook_detail.description:
                content_parts.append(f"Description: {workbook_detail.description}")
            
            if workbook_detail.tags:
                content_parts.append(f"Tags: {', '.join(workbook_detail.tags)}")
            
            if hasattr(workbook_detail, 'views') and workbook_detail.views:
                view_names = [view.name for view in workbook_detail.views]
                content_parts.append(f"Views: {', '.join(view_names)}")
            
            content = "\n".join(content_parts) if content_parts else f"Workbook: {workbook_detail.name}"
            
            # Get metadata
            metadata = {
                'workbook_id': workbook_detail.id,
                'project_name': workbook_detail.project_name,
                'owner_name': workbook_detail.owner.name if workbook_detail.owner else None,
                'content_url': workbook_detail.content_url,
                'size': workbook_detail.size,
                'tags': workbook_detail.tags if hasattr(workbook_detail, 'tags') else []
            }
            
            return Document(
                id=f"tableau_workbook_{workbook_detail.id}",
                title=workbook_detail.name,
                content=content,
                source_type="tableau",
                source_url=f"{settings.tableau_server_url}/#/workbooks/{workbook_detail.id}",
                metadata=metadata,
                last_modified=workbook_detail.updated_at,
                created_at=workbook_detail.created_at
            )
            
        except Exception as e:
            logger.error(f"Error processing workbook {workbook.id}: {e}")
            return None
    
    async def _process_view(self, view) -> Optional[Document]:
        """Process a Tableau view (dashboard) into a Document"""
        try:
            # Get detailed view information
            view_detail = self.server.views.get_by_id(view.id)
            
            # Build content from view metadata
            content_parts = []
            
            if view_detail.description:
                content_parts.append(f"Description: {view_detail.description}")
            
            if view_detail.tags:
                content_parts.append(f"Tags: {', '.join(view_detail.tags)}")
            
            if hasattr(view_detail, 'workbook') and view_detail.workbook:
                content_parts.append(f"Workbook: {view_detail.workbook.name}")
            
            content = "\n".join(content_parts) if content_parts else f"View: {view_detail.name}"
            
            # Get metadata
            metadata = {
                'view_id': view_detail.id,
                'workbook_name': view_detail.workbook.name if hasattr(view_detail, 'workbook') else None,
                'project_name': view_detail.project_name if hasattr(view_detail, 'project_name') else None,
                'content_url': view_detail.content_url,
                'tags': view_detail.tags if hasattr(view_detail, 'tags') else []
            }
            
            return Document(
                id=f"tableau_view_{view_detail.id}",
                title=view_detail.name,
                content=content,
                source_type="tableau",
                source_url=f"{settings.tableau_server_url}/#/views/{view_detail.content_url}",
                metadata=metadata,
                last_modified=view_detail.updated_at,
                created_at=view_detail.created_at
            )
            
        except Exception as e:
            logger.error(f"Error processing view {view.id}: {e}")
            return None
    
    async def _process_datasource(self, datasource) -> Optional[Document]:
        """Process a Tableau datasource into a Document"""
        try:
            # Get detailed datasource information
            datasource_detail = self.server.datasources.get_by_id(datasource.id)
            
            # Build content from datasource metadata
            content_parts = []
            
            if datasource_detail.description:
                content_parts.append(f"Description: {datasource_detail.description}")
            
            if datasource_detail.tags:
                content_parts.append(f"Tags: {', '.join(datasource_detail.tags)}")
            
            if hasattr(datasource_detail, 'datasource_type'):
                content_parts.append(f"Type: {datasource_detail.datasource_type}")
            
            content = "\n".join(content_parts) if content_parts else f"Datasource: {datasource_detail.name}"
            
            # Get metadata
            metadata = {
                'datasource_id': datasource_detail.id,
                'project_name': datasource_detail.project_name,
                'owner_name': datasource_detail.owner.name if datasource_detail.owner else None,
                'content_url': datasource_detail.content_url,
                'datasource_type': datasource_detail.datasource_type if hasattr(datasource_detail, 'datasource_type') else None,
                'tags': datasource_detail.tags if hasattr(datasource_detail, 'tags') else []
            }
            
            return Document(
                id=f"tableau_datasource_{datasource_detail.id}",
                title=datasource_detail.name,
                content=content,
                source_type="tableau",
                source_url=f"{settings.tableau_server_url}/#/datasources/{datasource_detail.id}",
                metadata=metadata,
                last_modified=datasource_detail.updated_at,
                created_at=datasource_detail.created_at
            )
            
        except Exception as e:
            logger.error(f"Error processing datasource {datasource.id}: {e}")
            return None
    
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
            if doc_id.startswith("tableau_workbook_"):
                workbook_id = doc_id.replace("tableau_workbook_", "")
                workbook = self.server.workbooks.get_by_id(workbook_id)
                return await self._process_workbook(workbook)
            elif doc_id.startswith("tableau_view_"):
                view_id = doc_id.replace("tableau_view_", "")
                view = self.server.views.get_by_id(view_id)
                return await self._process_view(view)
            elif doc_id.startswith("tableau_datasource_"):
                datasource_id = doc_id.replace("tableau_datasource_", "")
                datasource = self.server.datasources.get_by_id(datasource_id)
                return await self._process_datasource(datasource)
        except Exception as e:
            logger.error(f"Error fetching document {doc_id}: {e}")
        return None
    
    def __del__(self):
        """Clean up Tableau connection"""
        if self.server and self.server.auth:
            try:
                self.server.auth.sign_out()
            except:
                pass 
    
    def _process_tables(self, soup):
        """Convert HTML tables to readable text format"""
        tables = soup.find_all('table')
        
        for table in tables:
            # Convert table to structured text
            table_text = self._table_to_text(table)
            
            # Replace the table with the structured text
            table.replace_with(BeautifulSoup(f"\n\n{table_text}\n\n", 'html.parser'))
    
    def _table_to_text(self, table):
        """Convert a table to readable text format"""
        try:
            rows = table.find_all('tr')
            if not rows:
                return ""
            
            table_lines = []
            
            for i, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                if not cells:
                    continue
                
                # Process each cell
                cell_texts = []
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    if cell_text:
                        cell_texts.append(cell_text)
                
                if cell_texts:
                    # Join cells with | separator
                    row_text = " | ".join(cell_texts)
                    table_lines.append(row_text)
            
            if table_lines:
                # Add table header and footer
                table_text = "\n".join(table_lines)
                return f"TABLE:\n{table_text}\nEND TABLE"
            
            return ""
            
        except Exception as e:
            logger.error(f"Error processing table: {e}")
            return table.get_text()
    
    def _table_to_structured_text(self, table):
        """Convert table to more structured format with headers"""
        try:
            rows = table.find_all('tr')
            if not rows:
                return ""
            
            table_lines = []
            headers = []
            
            for i, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                if not cells:
                    continue
                
                # Extract cell content
                cell_texts = []
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    cell_texts.append(cell_text)
                
                if not cell_texts:
                    continue
                
                # First row is typically headers
                if i == 0:
                    headers = cell_texts
                    table_lines.append(" | ".join(headers))
                    table_lines.append("-" * len(" | ".join(headers)))  # Separator line
                else:
                    # Data rows
                    row_text = " | ".join(cell_texts)
                    table_lines.append(row_text)
            
            if table_lines:
                table_text = "\n".join(table_lines)
                return f"TABLE:\n{table_text}\nEND TABLE"
            
            return ""
            
        except Exception as e:
            logger.error(f"Error processing structured table: {e}")
            return table.get_text()
    
    def _extract_tables_info(self, soup):
        """Extract information about tables in the document"""
        tables = soup.find_all('table')
        tables_info = []
        
        for i, table in enumerate(tables):
            try:
                rows = table.find_all('tr')
                headers = []
                
                # Try to get headers from first row
                if rows:
                    first_row = rows[0]
                    header_cells = first_row.find_all(['th', 'td'])
                    headers = [cell.get_text(strip=True) for cell in header_cells]
                
                table_info = {
                    "table_index": i,
                    "row_count": len(rows),
                    "headers": headers,
                    "has_headers": len(headers) > 0
                }
                tables_info.append(table_info)
                
            except Exception as e:
                logger.error(f"Error extracting table info: {e}")
        
        return tables_info