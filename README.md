# Intelligent Incident Resolution Assistant (RAG)

The **Intelligent Incident Resolution Assistant** is a Retrieval-Augmented Generation (RAG) application designed to help **IT Support Engineers** resolve customer issues by retrieving relevant information from previously resolved incidents and knowledge base documents.

The application performs semantic search using vector embeddings stored in a FAISS vector database and uses Google's Gemini 2.5 Flash to generate accurate, context-aware responses based only on the retrieved information. This approach reduces manual searching and improves incident resolution efficiency.

---

## Problem Statement

IT Support Engineers often spend significant time searching through historical incident records and knowledge base documents to identify solutions for customer issues. Traditional keyword-based search may fail to retrieve semantically relevant information, increasing incident resolution time.

This project addresses the problem by implementing a Retrieval-Augmented Generation (RAG) pipeline that performs semantic search over uploaded documents and provides grounded, context-aware responses using a Large Language Model.

---

## Key Features

### Document Management

* Upload PDF, TXT and CSV documents
* SHA256 duplicate document detection
* Document registry
* List uploaded documents
* Delete documents

### Document Processing

* Text extraction
* Configurable document chunking
* Configurable chunk overlap
* Embedding generation
* Metadata generation
* FAISS index creation

### Semantic Search

* Vector similarity search
* L2 distance-based retrieval
* Configurable Top-K retrieval
* Metadata filtering
* Source attribution

### RAG Pipeline

* Context construction
* Prompt engineering
* Gemini 2.5 Flash integration
* Context-grounded response generation
* Hallucination prevention

### Chat

* Question answering API
* Chat history
* Delete chat history

### Production Features

* Logging
* Exception handling
* Configuration management
* Health monitoring
* Statistics API

---

## Architecture

### Document Processing Flow

1. Upload document
2. Extract text
3. Split text into configurable chunks
4. Generate embeddings using all-MiniLM-L6-v2
5. Store vectors in the FAISS vector database
6. Save document metadata

### Question Answering Flow

1. User submits a question
2. Generate query embedding
3. Search FAISS using L2 distance
4. Retrieve Top-K relevant chunks
5. Build prompt using retrieved context
6. Send prompt to Gemini 2.5 Flash
7. Generate grounded response
8. Return answer with source attribution and confidence score

---

## Technology Stack

| Category        | Technology                                     |
| --------------- | ---------------------------------------------- |
| Backend         | FastAPI, Python                                |
| AI Model        | Google Gemini 2.5 Flash                        |
| Embedding Model | all-MiniLM-L6-v2                               |
| Vector Database | FAISS                                          |
| Data Storage    | JSON                                           |
| Libraries       | Sentence Transformers, NumPy, Pandas, Pydantic |
| Tools           | Git, GitHub                                    |

---

## Project Structure

```
.
│── .env
│── .env.example
│── .gitignore
│── app.py
│── README.md
│── requirements.txt
│
├── backend
│   ├── routes
│   │   ├── ask.py
│   │   ├── delete_document.py
│   │   ├── delete_history.py
│   │   ├── documents.py
│   │   ├── document_details.py
│   │   ├── health.py
│   │   ├── history.py
│   │   ├── logging.py
│   │   ├── process.py
│   │   ├── search.py
│   │   ├── stats.py
│   │   └── upload.py
│   │
│   ├── services
│   │   ├── confidence_service.py
│   │   ├── document_registry.py
│   │   ├── embedding_service.py
│   │   ├── faiss_service.py
│   │   ├── hash_service.py
│   │   ├── health_service.py
│   │   ├── history_service.py
│   │   ├── llm_service.py
│   │   ├── logging_service.py
│   │   ├── reindex_service.py
│   │   ├── retrieval_service.py
│   │   ├── stats_service.py
│   │   └── vector_store.py
│   │
│   ├── config.py
│   └── logger.py
│
├── data
│   ├── document_registry.json
│   ├── history
│   │   └── chat_history.json
│   ├── raw
│   │   └── Sample_Incidents.txt
│   └── vector_store
│       ├── index.faiss
│       └── metadata.json
│
└── frontend
    ├── index.html
    ├── script.js
    └── style.css
```

## API Endpoints

| Method | Endpoint             | Description                     |
| ------ | -------------------- | ------------------------------- |
| POST   | /upload              | Upload a document               |
| POST   | /process-document    | Process uploaded document       |
| GET    | /search              | Perform semantic search         |
| GET    | /ask                 | Ask a question                  |
| GET    | /documents           | List uploaded documents         |
| GET    | /document/{filename} | Retrieve document information   |
| DELETE | /document/{filename} | Delete a document               |
| GET    | /history             | Retrieve chat history           |
| DELETE | /history             | Clear chat history              |
| GET    | /stats               | Retrieve application statistics |
| GET    | /health              | Check application health        |

---

## Configuration

Application settings are managed through a centralized configuration file.

Configurable parameters include:

* Embedding model
* Embedding dimensions
* Vector database
* Chunk size
* Chunk overlap
* Top-K retrieval
* Gemini configuration

---

## Installation

```bash
git clone <repository-url>

cd Intelligent-Incident-Resolution-Assistant

pip install -r requirements.txt

uvicorn backend.main:app --reload
```

---

## Environment Variables

Create a `.env` file and configure:

```env
GEMINI_API_KEY=your_api_key
```

---

## Future Enhancements

* React-based frontend
* Authentication
* Docker deployment
* Cloud deployment
* CI/CD pipeline
* Unit and integration testing
* Database integration
* Streaming responses

---

## License

This project is developed for educational and portfolio purposes.
