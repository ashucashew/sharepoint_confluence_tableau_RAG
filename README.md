# Team RAG Chatbot

A comprehensive RAG (Retrieval-Augmented Generation) chatbot system that automatically syncs and indexes documents from multiple sources including Confluence, Tableau, and Shareflow, providing intelligent responses based on your team's knowledge base.

## Features

- **Multi-Source Integration**: Automatically syncs documents from:
  - **Confluence**: Pages, blog posts, and attachments
  - **Tableau**: Dashboards, workbooks, and datasources
  - **SharePoint**: Documents, presentations, and files

- **Intelligent RAG System**: 
  - Vector-based document search using ChromaDB
  - OpenAI GPT-4 integration for natural language responses
  - Context-aware responses with source citations

- **Automatic Synchronization**:
  - Scheduled background sync for all data sources
  - Incremental updates to minimize processing time
  - Real-time document indexing

- **Modern Web Interface**:
  - Real-time chat interface with WebSocket support
  - Document search functionality
  - System status monitoring
  - Responsive design for all devices

- **Enterprise Features**:
  - Conversation history management
  - Source filtering and relevance scoring
  - Health monitoring and error handling
  - Configurable sync intervals

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Confluence    │    │     Tableau     │    │   SharePoint    │
│   Connector     │    │    Connector    │    │    Connector    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Data Sync       │
                    │ Manager         │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Vector Store    │
                    │ (ChromaDB)      │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │ RAG Chatbot     │
                    │ (OpenAI GPT-4)  │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Web Interface   │
                    │ (FastAPI)       │
                    └─────────────────┘
```

## Prerequisites

- Python 3.8 or higher
- OpenAI API key
- Access to your data sources (Confluence, Tableau, Shareflow)
- Required API tokens and credentials

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd multi_source_RAG
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp env.example .env
   # Edit .env with your actual configuration
   ```

5. **Configure your data sources**:
   - Add your OpenAI API key
   - Configure Confluence credentials and space keys
   - Set up Tableau server connection details
   - Add SharePoint connection information

## Configuration

### Environment Variables

Copy `env.example` to `.env` and configure the following:

#### OpenAI Configuration
```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
```

#### Vector Database
```bash
CHROMA_PERSIST_DIRECTORY=./chroma_db
EMBEDDING_MODEL=all-mpnet-base-v2
```

#### Confluence
```bash
CONFLUENCE_URL=https://your-company.atlassian.net
CONFLUENCE_USERNAME=your_email@company.com
CONFLUENCE_API_TOKEN=your_confluence_api_token
CONFLUENCE_SPACE_KEYS=TEAM,PROJECT,DOCS
```

#### Tableau
```bash
TABLEAU_SERVER_URL=https://your-tableau-server.com
TABLEAU_USERNAME=your_tableau_username
TABLEAU_PASSWORD=your_tableau_password
TABLEAU_SITE_ID=your_site_id
```

#### SharePoint
```bash
SHAREPOINT_URL=https://your-company.sharepoint.com
SHAREPOINT_USERNAME=your_email@company.com
SHAREPOINT_PASSWORD=your_sharepoint_password
SHAREPOINT_SITE_URL=https://your-company.sharepoint.com/sites/your-site
```

## Usage

### Starting the Application

1. **Start the web application**:
   ```bash
   python web_app.py
   ```

2. **Access the chat interface**:
   Open your browser and navigate to `http://localhost:8000`

### API Endpoints

The system provides several REST API endpoints:

- `POST /api/chat` - Send a chat message
- `POST /api/search` - Search documents directly
- `POST /api/sync` - Trigger data synchronization
- `GET /api/status` - Get system status
- `GET /api/conversation-history` - Get chat history
- `DELETE /api/conversation-history` - Clear chat history
- `GET /health` - Health check endpoint

### WebSocket Support

For real-time chat, the system supports WebSocket connections at `/ws/chat`.

## Data Synchronization

### Automatic Sync

The system automatically syncs data sources based on configured intervals:

- **Confluence**: Syncs pages and blog posts
- **Tableau**: Syncs dashboards, workbooks, and datasources
- **SharePoint**: Syncs documents and files

### Manual Sync

You can trigger manual synchronization:

1. **Via Web Interface**: Click the "Sync Data" button
2. **Via API**: `POST /api/sync`
3. **Via Command Line**: Use the sync manager directly

### Sync Configuration

Configure sync intervals in your `.env` file:

```bash
SYNC_INTERVAL_MINUTES=60  # Sync every hour
```

## File Structure

```
multi_source_RAG/
├── data_connectors/          # Data source connectors
│   ├── __init__.py
│   ├── base_connector.py     # Base connector interface
│   ├── confluence_connector.py
│   ├── tableau_connector.py
│   └── sharepoint_connector.py
├── templates/                # HTML templates
│   └── chat.html
├── static/                   # Static assets
│   └── styles.css
├── config.py                 # Configuration management
├── vector_store.py           # Vector database operations
├── data_sync_manager.py      # Data synchronization
├── rag_chatbot.py           # RAG chatbot logic
├── web_app.py               # FastAPI web application
├── requirements.txt         # Python dependencies
├── env.example              # Environment variables template
└── README.md               # This file
```

## Development

### Adding New Data Sources

To add a new data source:

1. Create a new connector class in `data_connectors/`
2. Inherit from `BaseConnector`
3. Implement required methods
4. Add configuration to `config.py`
5. Update the sync manager

### Customizing the Chatbot

Modify the system prompt in `rag_chatbot.py` to customize the chatbot's behavior and responses.

### Extending the Web Interface

The web interface is built with FastAPI and uses Jinja2 templates. You can customize the UI by modifying the HTML templates and CSS.

## Monitoring and Maintenance

### Health Checks

The system provides health check endpoints:

- `GET /health` - Overall system health
- `GET /api/status` - Detailed system status

### Logging

The system uses structured logging with loguru. Logs include:

- Data synchronization events
- Chat interactions
- Error handling
- System performance metrics

### Performance Optimization

- **Vector Store**: ChromaDB provides efficient similarity search
- **Caching**: Conversation history is cached in memory
- **Async Operations**: All I/O operations are asynchronous
- **Incremental Sync**: Only new/modified documents are processed

## Troubleshooting

### Common Issues

1. **Connection Errors**:
   - Verify API credentials and URLs
   - Check network connectivity
   - Ensure proper authentication

2. **Sync Failures**:
   - Check data source permissions
   - Verify API rate limits
   - Review error logs

3. **Chatbot Not Responding**:
   - Verify OpenAI API key
   - Check vector store initialization
   - Review system logs

### Debug Mode

Enable debug mode by setting `DEBUG=True` in your `.env` file for detailed logging.

## Security Considerations

- Store sensitive credentials in environment variables
- Use HTTPS in production
- Implement proper authentication for the web interface
- Regularly rotate API keys and tokens
- Monitor access logs

## Production Deployment

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "web_app.py"]
```

### Environment Setup

1. Set up production environment variables
2. Configure reverse proxy (nginx)
3. Set up SSL certificates
4. Configure monitoring and alerting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

1. Check the troubleshooting section
2. Review the logs for error messages
3. Open an issue on GitHub
4. Contact the development team

## Roadmap

- [ ] Support for additional data sources (Slack, Jira, etc.)
- [ ] Advanced document processing (PDF parsing, image OCR)
- [ ] User authentication and authorization
- [ ] Conversation analytics and insights
- [ ] Mobile application
- [ ] Integration with popular chat platforms 