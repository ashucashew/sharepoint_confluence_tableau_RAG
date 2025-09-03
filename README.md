# Team RAG Chatbot

A comprehensive RAG (Retrieval-Augmented Generation) chatbot system that automatically syncs and indexes documents from multiple sources including Confluence, Tableau, and SharePoint, providing intelligent responses based on your team's knowledge base.

## Features

- **Multi-Source Integration**: Automatically syncs documents from:
  - **Confluence**: Pages, blog posts, and attachments
  - **Tableau**: Dashboards, workbooks, and datasources
  - **SharePoint**: Documents, presentations, and files

- **Intelligent RAG System**: 
  - Vector-based document search using ChromaDB
  - OpenAI GPT-4 integration for natural language responses
  - Context-aware responses with source citations
  - **Query Rewriting**: Automatically expands queries with Tesla energy industry terms and synonyms for better retrieval
  - **Conversation-Aware**: Understands context from previous messages for follow-up questions

- **Automated Data Pipeline**:
  - **Apache Airflow Integration**: Production-grade scheduling and monitoring
  - **Daily Automated Syncs**: Runs at 2 AM daily with comprehensive error handling
  - **Parallel Processing**: Syncs all data sources simultaneously
  - **Health Monitoring**: Built-in health checks and failure notifications
  - **Cleanup Operations**: Automatic removal of orphaned documents

- **Modern Web Interface**:
  - Real-time chat interface with WebSocket support
  - Document search functionality
  - Query rewriting display
  - Responsive design for all devices

- **Enterprise Features**:
  - Conversation history management
  - Source filtering and relevance scoring
  - Health monitoring and error handling
  - Production-ready deployment options

## Query Rewriting System

The RAG system includes an intelligent query rewriting component specifically designed for Tesla's residential energy fleet documentation. This feature automatically expands user queries with relevant industry terms, synonyms, and acronyms to improve document retrieval.

### How It Works

1. **User Input**: User asks a question like "Powerwall not charging"
2. **Query Rewriting**: System expands the query to include:
   - Product synonyms: "Powerwall PW PW2 PW3 Powerwall 2 Powerwall 3"
   - Related terms: "battery charging issue inverter communication fault"
   - Industry terminology: "residential energy storage backup power"
   - **Conversation Context**: Incorporates relevant details from previous messages
3. **Enhanced Retrieval**: Expanded query finds more relevant documents
4. **Better Results**: Users get more comprehensive and accurate responses

### Tesla Energy Terms Covered

- **Energy Storage**: Powerwall (PW, PW2, PW3), Powerpack, Megapack
- **Solar**: Solar Panels, Solar Roof, PV systems
- **Charging**: Wall Connector, Mobile Connector, Supercharger
- **Control Systems**: Gateway, Backup Switch, Energy Management System
- **Grid Services**: VPP, TOU rates, Demand Response, Frequency Regulation
- **Common Issues**: Inverter faults, communication errors, grid disconnections

### Example Transformations

| Original Query | Rewritten Query |
|----------------|-----------------|
| "Powerwall not charging" | "Powerwall PW PW2 PW3 Powerwall 2 Powerwall 3 not charging battery charging issue inverter communication fault" |
| "Solar panels not working" | "Solar panels Solar Roof PV not working solar production issue panel failure inverter fault shading problem" |
| "Gateway error" | "Gateway GW Backup Gateway Backup Gateway 2 error communication fault network issue backup power problem" |

### Conversation-Aware Rewriting

The system now understands conversation context and can handle follow-up questions intelligently:

| Conversation Context | User Query | Rewritten Query |
|---------------------|-------------|-----------------|
| "What are main causes of arcing in PW3 sites?" | "how about PW2?" | "What are main causes of arcing in Powerwall 2 PW2 sites? (following up on previous question about arcing in Powerwall 3 sites)" |
| "Powerwall not charging properly" | "what about the inverter?" | "What about Powerwall inverter issues related to charging problems? (referring to inverter problems causing Powerwall charging issues)" |
| "Solar panels underperforming" | "any other causes?" | "What are other causes of solar panel underperformance beyond what was mentioned? (continuing discussion about solar panel performance issues)" |

## Airflow Integration

The system uses Apache Airflow for production-grade orchestration of data pipelines and automated maintenance tasks.

### **Automated DAGs:**

#### **1. Daily RAG Pipeline (`rag_embedding_pipeline`)**
- **Schedule**: Daily at 2 AM
- **Tasks**:
  - Health check of RAG system
  - Parallel sync of all data sources (Confluence, SharePoint, Tableau)
  - Cleanup of orphaned documents
  - Refresh of old embeddings
  - Generation of daily reports
  - Email notifications on failures

#### **2. Simple RAG DAG (`simple_rag_dag_no_email`)**
- **Schedule**: Daily
- **Tasks**:
  - Health check
  - System status check
  - Manual sync trigger
  - Completion logging

### **Custom Airflow Operators:**

- **`RAGHealthCheckOperator`**: Checks RAG system health
- **`RAGSyncOperator`**: Syncs specific data sources
- **`RAGCleanupOperator`**: Cleans up orphaned documents
- **`RAGStatsOperator`**: Collects system statistics

### **Benefits of Airflow Integration:**

- **Production Reliability**: Enterprise-grade scheduling and monitoring
- **Parallel Processing**: Syncs multiple sources simultaneously
- **Error Handling**: Automatic retries and failure notifications
- **Monitoring**: Web UI for pipeline visualization and debugging
- **Scalability**: Easy to add new tasks and data sources
- **Maintenance**: Automated cleanup and health checks

### **Deployment Options:**

1. **Internal Server**: Deploy on company infrastructure
2. **Cloud Deployment**: Use managed Airflow services
3. **Docker**: Containerized deployment with docker-compose
4. **Kubernetes**: Enterprise-scale orchestration

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
                                 │
                    ┌─────────────────┐
                    │ Apache Airflow  │
                    │ (Production     │
                    │  Orchestration) │
                    └─────────────────┘
```

### **Data Flow:**

1. **Data Ingestion**: Connectors fetch documents from Confluence, Tableau, and SharePoint
2. **Processing**: Documents are chunked, embedded, and stored in ChromaDB
3. **Query Processing**: User queries are rewritten with Tesla energy industry knowledge
4. **Retrieval**: Vector search finds relevant document chunks
5. **Generation**: OpenAI GPT-4 generates responses based on retrieved context
6. **Automation**: Airflow DAGs handle daily syncs, cleanup, and maintenance

### **Key Components:**

- **Data Connectors**: Handle authentication and data extraction from source systems
- **Vector Store**: ChromaDB with sentence-transformers embeddings
- **RAG Chatbot**: OpenAI integration with conversation-aware query rewriting
- **Web Interface**: FastAPI with WebSocket support for real-time chat
- **Airflow Pipeline**: Production-grade orchestration for automated operations

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

### **Health Monitoring**

The system provides comprehensive health monitoring:

- **`GET /health`**: Overall system health status
- **Airflow UI**: Monitor DAG execution and pipeline health
- **Logs**: Structured logging for all operations

### **Automated Maintenance (via Airflow)**

- **Daily Syncs**: Automatic data synchronization at 2 AM
- **Cleanup Operations**: Removal of orphaned documents
- **Health Checks**: Automated system health monitoring
- **Error Handling**: Automatic retries and notifications
- **Performance Monitoring**: Track sync times and success rates

### **Logging and Debugging**

- **Structured Logs**: All operations logged with context
- **Airflow Logs**: Detailed pipeline execution logs
- **Error Tracking**: Comprehensive error logging and reporting
- **Performance Metrics**: Monitor response times and throughput

## Troubleshooting

### **Common Issues and Solutions**

#### **1. RAG System Issues**
- **Chatbot Not Responding**: Check OpenAI API key and vector store initialization
- **Poor Search Results**: Verify document sync status and embedding quality
- **Query Rewriting Failures**: Check OpenAI API connectivity

#### **2. Airflow Pipeline Issues**
- **DAG Failures**: Check Airflow logs and system health
- **Sync Failures**: Verify data source credentials and permissions
- **Performance Issues**: Monitor resource usage and optimize DAG scheduling

#### **3. Data Source Issues**
- **Connection Errors**: Verify API credentials, URLs, and network connectivity
- **Rate Limiting**: Check API quotas and implement backoff strategies
- **Authentication Failures**: Ensure proper token management and rotation

### **Debug Mode**

Enable debug mode by setting `DEBUG=True` in your `.env` file for detailed logging.

## Security Considerations

- **Credential Management**: Store sensitive credentials in environment variables
- **Network Security**: Use HTTPS in production with proper SSL certificates
- **Access Control**: Implement authentication for web interface access
- **API Security**: Regularly rotate API keys and monitor access logs
- **Data Privacy**: Ensure compliance with company data handling policies

## Deployment

### **Production Deployment Options**

#### **Option 1: Internal Server (Recommended for Companies)**
```bash
# On your company server/VM
git clone https://github.com/ashucashew/sharepoint_confluence_tableau_RAG.git
cd sharepoint_confluence_tableau_RAG

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp env.example .env
# Edit .env with production values

# Run with production server
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 web_app:app
```

#### **Option 2: Docker Containerization**
```bash
# Build and run with Docker
docker-compose up -d

# Or build manually
docker build -t rag-system .
docker run -p 8000:8000 rag-system
```

#### **Option 3: Cloud Deployment**
- **Azure App Service**: Managed Python hosting
- **AWS ECS**: Container orchestration
- **Google Cloud Run**: Serverless containers

### **Airflow Setup**

#### **1. Install Airflow:**
```bash
pip install -r requirements-airflow.txt
```

#### **2. Configure Environment:**
```bash
export AIRFLOW_HOME=$HOME/airflow
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/dags
export AIRFLOW__CORE__PLUGINS_FOLDER=$(pwd)/plugins
```

#### **3. Initialize and Start:**
```bash
# Initialize database
airflow db init

# Create admin user
airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@company.com --password admin

# Start Airflow
airflow webserver --port 8080 &
airflow scheduler &
```

#### **4. Access Airflow UI:**
- Open http://localhost:8080
- Login: admin / admin
- View your RAG DAGs and monitor execution

### **Configuration**

#### **Environment Variables:**
```bash
# Core RAG System
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4
EMBEDDING_MODEL=all-mpnet-base-v2

# Data Sources
CONFLUENCE_URL=https://your-company.atlassian.net
CONFLUENCE_USERNAME=your_email@company.com
CONFLUENCE_API_TOKEN=your_token

SHAREPOINT_CLIENT_ID=your_client_id
SHAREPOINT_CLIENT_SECRET=your_client_secret
SHAREPOINT_TENANT_ID=your_tenant_id

TABLEAU_SERVER_URL=https://your-company.tableau.com
TABLEAU_USERNAME=your_email@company.com
TABLEAU_PASSWORD=your_password

# Production Settings
HOST=0.0.0.0
PORT=8000
DEBUG=False
```

#### **Airflow Variables:**
```bash
# Set in Airflow UI or via CLI
airflow variables set rag_api_base_url "http://localhost:8000"
airflow variables set rag_email_recipients "team@company.com"
```

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