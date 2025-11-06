# Alpha Mini RAG Chatbot - Kiến trúc Hệ thống

## 📋 Tổng quan

Hệ thống RAG (Retrieval-Augmented Generation) cho phép Alpha Mini chatbot trả lời câu hỏi của người dùng về:
- Tính năng và khả năng của robot
- Hướng dẫn sử dụng chi tiết
- FAQ và troubleshooting
- Thông tin kỹ thuật

## 🏗️ Kiến trúc Hệ thống

```
┌─────────────────┐
│  User Question  │
└────────┬────────┘
         │
         v
┌─────────────────────────────────────────┐
│         1. Embedding Service            │
│  (sentence-transformers/all-MiniLM-L6)  │
└────────┬────────────────────────────────┘
         │ Vector embedding
         v
┌─────────────────────────────────────────┐
│      2. ChromaDB Vector Store           │
│   - Semantic search                     │
│   - Similarity matching                 │
│   - Top-k retrieval                     │
└────────┬────────────────────────────────┘
         │ Retrieved documents
         v
┌─────────────────────────────────────────┐
│      3. Context Preparation             │
│   - Rerank results                      │
│   - Format context                      │
│   - Apply filters                       │
└────────┬────────────────────────────────┘
         │ Relevant context
         v
┌─────────────────────────────────────────┐
│      4. LLM Generation                  │
│   (OpenAI GPT-4 / Anthropic Claude)     │
│   - Prompt engineering                  │
│   - Context injection                   │
│   - Response generation                 │
└────────┬────────────────────────────────┘
         │
         v
┌─────────────────┐
│     Answer      │
└─────────────────┘
```

## 📁 Cấu trúc Thư mục

```
alpha-mini-backend/
├── app/
│   ├── services/
│   │   └── rag/
│   │       ├── __init__.py
│   │       ├── embedding_service.py      # Tạo embeddings
│   │       ├── vector_store_service.py   # Quản lý ChromaDB
│   │       ├── retrieval_service.py      # Logic truy xuất
│   │       └── generation_service.py     # Sinh câu trả lời
│   ├── routers/
│   │   └── chatbot_router.py             # API endpoints
│   └── models/
│       └── chatbot_models.py             # Pydantic models
├── data/
│   └── alpha_mini_knowledge/
│       ├── features.json                 # Tính năng robot
│       ├── user_guides.json              # Hướng dẫn sử dụng
│       ├── faq.json                      # FAQ
│       └── troubleshooting.json          # Khắc phục sự cố
├── scripts/
│   ├── init_knowledge_base.py            # Khởi tạo database
│   └── update_knowledge_base.py          # Cập nhật dữ liệu
└── chroma_db/                            # ChromaDB storage
```

## 🔄 Workflow Chi tiết

### 1. **Embedding Phase**
```python
User question → Embedding model → 384-dim vector
```
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Fast, efficient, multilingual support
- Consistent với embedded documents

### 2. **Retrieval Phase**
```python
Query vector → ChromaDB.similarity_search() → Top-K docs
```
- Cosine similarity search
- Configurable top_k (default: 5)
- Similarity threshold filtering
- Metadata filtering (category, tags)

### 3. **Context Preparation**
```python
Retrieved docs → Rerank → Format → Context string
```
- Reranking by relevance score
- Chunking if context too long
- Add source attribution
- Format for LLM prompt

### 4. **Generation Phase**
```python
Context + Question + Prompt → LLM → Answer
```
- Prompt template với instructions
- Context injection
- Temperature control
- Response validation

## 🔑 Core Components

### EmbeddingService
- Tạo embeddings cho queries và documents
- Cache embeddings để tối ưu performance
- Support batch processing

### VectorStoreService
- Khởi tạo và quản lý ChromaDB collection
- Add/update/delete documents
- Persistence và backup

### RetrievalService
- Semantic search với filters
- Reranking algorithms
- Result formatting

### GenerationService
- LLM API integration
- Prompt management
- Response parsing và validation
- Hallucination prevention

## 📊 Data Schema

### Document Structure
```json
{
  "id": "feature_001",
  "content": "Alpha Mini có thể nhảy múa theo nhạc...",
  "metadata": {
    "category": "features",
    "subcategory": "dance",
    "tags": ["dance", "music", "entertainment"],
    "language": "vi",
    "last_updated": "2025-01-01",
    "source": "official_docs"
  }
}
```

## 🛡️ Chiến lược Chống Hallucination

1. **Strict Context Grounding**: Chỉ dùng thông tin từ retrieved docs
2. **Citation**: Luôn trích dẫn nguồn trong response
3. **Confidence Scoring**: Đánh giá độ tin cậy của answer
4. **Fallback Messages**: Thừa nhận khi không có thông tin
5. **Prompt Engineering**: Instructions rõ ràng về không bịa thông tin

## 🔧 Configuration

```python
RAG_CONFIG = {
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "collection_name": "alpha_mini_knowledge",
    "top_k": 5,
    "similarity_threshold": 0.7,
    "llm_model": "gpt-4-turbo",
    "temperature": 0.3,
    "max_tokens": 1000
}
```

## 🚀 Cách Mở rộng

### Thêm Data Mới
1. Tạo file JSON/Markdown trong `data/alpha_mini_knowledge/`
2. Chạy `python scripts/update_knowledge_base.py`
3. Documents tự động được embedded và indexed

### Cải thiện Retrieval
- Fine-tune embedding model với domain data
- Implement hybrid search (dense + sparse)
- Add query expansion
- Use cross-encoder reranking

### Multi-language Support
- Thêm documents bằng các ngôn ngữ khác
- Use multilingual embedding models
- Language detection và routing

### Advanced Features
- Conversation history tracking
- Multi-turn dialogue support
- User feedback loop
- A/B testing cho prompts

## 📈 Performance Optimization

1. **Caching**: Cache embeddings và frequent queries
2. **Batch Processing**: Embed multiple queries cùng lúc
3. **Async Operations**: Non-blocking retrieval
4. **Index Optimization**: Periodic ChromaDB optimization
5. **Load Balancing**: Distribute LLM calls

## 🔒 Security & Privacy

- API key management
- Rate limiting
- Query sanitization
- PII detection và filtering
- Audit logging

## 📝 Monitoring & Logging

- Query analytics
- Retrieval quality metrics
- Response quality tracking
- Error monitoring
- Performance metrics

---

**Version**: 1.0  
**Last Updated**: 2025-11-05  
**Author**: Alpha Mini Development Team
