# SmartCustoms Assistant

[![Python 3.12.4](https://img.shields.io/badge/python-3.12.4-blue.svg)](https://www.python.org/downloads/)
[![PyMongo 4.13.0](https://img.shields.io/badge/PyMongo-4.13.0-green.svg)](https://www.mongodb.com/)
[![Motor 3.7.1](https://img.shields.io/badge/Motor-3.7.1-green.svg)](https://motor.readthedocs.io/)
[![PyTesseract 0.3.13](https://img.shields.io/badge/PyTesseract-0.3.13-blue.svg)](https://pypi.org/project/pytesseract/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-orange.svg)](https://openai.com/)

An intelligent AI system for customs procedures consulting and goods classification using Retrieval-Augmented Generation (RAG).

## Key Features

- **Instant Response**: Consulting on import/export regulations, customs clearance procedures, and HS code classification
- **Multi-format Processing**: DOC/DOCX, Excel, PDF with intelligent OCR
- **Tool Agent**: Accurate data retrieval from MongoDB (evolved from v1.0's MySQL ToolAgent)
- **Smart Search**: Vector search combined with MongoDB using Coordinator

## System Requirements

- Python 3.12.4
- PyMongo 4.13.0 (MongoDB driver)
- Motor 3.7.1 (Async MongoDB driver)
- PyTesseract 0.3.13 (OCR processing with dual-strategy: GPT-4 primary, Tesseract fallback)
- OpenAI API Key
- Cohere API Key (for reranking)

## ⚡ Quick Installation

```bash
# Clone repository
git clone ...
cd SmartCustoms-Assistant/app-ver-1.1

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# Run application
python main.py
```

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Query    │───▶│   Coordinator   │───▶│  Search Engine  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ MongoDB Search  │    │  Vector Search  │
                       └─────────────────┘    └─────────────────┘
                                │                        │
                                └────────┬───────────────┘
                                         ▼
                                ┌─────────────────┐
                                │  LLM Response   │
                                └─────────────────┘
```

##  API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Chat with AI assistant |
| `/api/pdf_endpoint` | POST | Upload and process PDF files |
| `/api/xlsx_endpoint` | POST | Upload and process Excel files |
| `/api/doc_endpoint` | POST | Upload and process DOC/DOCX files |
| `/api/files` | GET | List uploaded files |
| `/api/delete` | DELETE | Delete PDF/DOC files and data from Qdrant |
| `/api/xlsx_delete` | DELETE | Delete Excel data from database |

##  Configuration

### Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=your_openai_key

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=smartcustoms

# Cohere
COHERE_API_KEY=your_cohere_key

# Qdrant
QDRANT_URL=http://localhost:6333
```

### Pool Configuration

```python
# config.py
VECTOR_STORE_POOL_SIZE = 3
RERANKER_POOL_SIZE = 2
TOOL_AGENT_POOL_SIZE = 2
MONGODB_POOL_SIZE = 10
```

## Version Comparison

| Feature | v1.0 | v1.1 |
|---------|------|------|
| Database | MySQL | MongoDB |
| Search | Vector + **ToolAgent** | Vector + MongoDB |
| Query Routing | **ToolAgent** decision logic | Automatic (Coordinator) |
| Pipeline Generation | Static | Dynamic (LLM-generated) |
| Connection Pooling | Basic | Advanced |
| Tool System | **MySQL ToolAgent** (HS codes, suppliers, products) | **Tool Agent** (MongoDB, OCR, HS Lookup) |

## Data Processing

### PDF Processing
- **YOLOv11**: Detection and removal of sensitive information
- **Dual OCR Strategy**: 
  - **Primary**: GPT-4 for high-quality Vietnamese text recognition
  - **Fallback**: PyTesseract when GPT-4 returns <20 words or fails
- **Smart switching**: Automatic failover for optimal results

### Excel Processing
- Data normalization and storage in MongoDB
- Full-text search with MongoDB Atlas

### DOC/DOCX Processing
- LibreOffice conversion
- Regex-based chunking

## 🔄 Major Updates in Version 1.1

### Database Migration: MySQL → MongoDB
- **Complete transition** from MySQL to **MongoDB** for better scalability
- Integration with **MongoDB Atlas Vector Search** for efficient similarity matching
- Improved structured data search performance

### AggregatePipelineGenerator
- **LLM-powered MongoDB pipeline generation** from user queries
- Support for multiple search types:
  - **Fuzzy search** with customizable parameters
  - **Regex search** for complex patterns
  - **Exact matching** for specific fields
  - **Range queries** for time periods

### Coordinator Architecture
- **Intelligent query routing** between Vector Search and MongoDB Search
- **Dynamic decision making** based on query characteristics
- **Optimized search strategy selection**

### Enhanced System Architecture
- **Advanced Connection Pooling** for MongoDB
- **Object Pool system** for heavyweight components
- **Asynchronous design** for improved concurrency
- **Reorganized module structure** with dedicated directories

### Tool Agent Evolution
- **v1.0 ToolAgent**: Specialized MySQL tools (fuzzy supplier matching, full-text product search, HS code lookup)
- **v1.1 Tool Agent**: Expanded to MongoDB integration with OCR and enhanced HS lookup capabilities
- **Improved Decision Logic**: More sophisticated routing between tool usage and RAG pipeline

##  Testing

```bash

# Test API endpoints
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the HS code for rice?"}'
```

## Monitoring

- **LangSmith**: LLM tracing and monitoring
- **Token usage**: API cost tracking
- **Latency**: Response time measurement


##  User Guide

1. **Upload documents**: Use `/api/upload` endpoint to upload PDF, DOC/DOCX, or Excel files (only for admin)
2. **Chat**: Send questions via `/api/chat` to receive consultations
3. **File management**: Use `/api/files` and `/api/delete` to manage documents (only for admin)


## 👥 Contributors

### [Vo Minh Thinh](https://github.com/finalFlash159)  
[![GitHub](https://img.shields.io/badge/GitHub-finalFlash159-181717?style=flat&logo=github)](https://github.com/finalFlash159)  [![LinkedIn](https://img.shields.io/badge/LinkedIn-ThinhVoMinh-blue?style=flat&logo=linkedin)](https://www.linkedin.com/in/vmthinh)

**Responsibilities:**
-  System Design & Architecture  
-  Data Processing Pipeline  
-  Retrieval-Augmented Generation (RAG)  
-  LLM Integration & Chatbot Development  
-  Tool Agent Design (MongoDB, OCR, HS Lookup)  

---

###  [Tran Quoc Toan](https://github.com/tqtcse)  
[![GitHub](https://img.shields.io/badge/GitHub-tqtcse-181717?style=flat&logo=github)](https://github.com/tqtcse)  [![LinkedIn](https://img.shields.io/badge/LinkedIn-TranQuocToan-blue?style=flat&logo=linkedin)](https://www.linkedin.com/in/tqtcse)

**Responsibilities:**
-  UI/UX Design  
-  User Database & Account Management  
-  QR Code Payment Integration  
-  Frontend–Backend Integration

---

<div align="center">
  Made with ❤️ by TT Team
</div> 