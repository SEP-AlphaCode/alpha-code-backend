# Alpha Mini RAG Chatbot

Hệ thống chatbot thông minh cho robot Alpha Mini sử dụng **RAG (Retrieval-Augmented Generation)**.

## 🚀 Tính năng

- ✅ Trả lời câu hỏi về tính năng Alpha Mini
- ✅ Hướng dẫn sử dụng chi tiết
- ✅ FAQ và troubleshooting
- ✅ Tìm kiếm ngữ nghĩa (semantic search)
- ✅ Trích dẫn nguồn thông tin
- ✅ Không bịa thông tin (grounded in context)

## 📋 Yêu cầu

```bash
# Cài đặt dependencies
pip install -r requirements.txt
```

## ⚙️ Cấu hình

### 1. Tạo file `.env` từ `.env.example`

```bash
cp .env.example .env
```

### 2. Cấu hình trong `.env`

```bash
# RAG Chatbot Settings
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=alpha_mini_knowledge

# LLM Configuration
LLM_PROVIDER=openai  # hoặc anthropic
LLM_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=your-api-key-here
```

## 🔧 Khởi tạo Knowledge Base

### Lần đầu tiên:

```bash
python scripts/init_knowledge_base.py
```

Script sẽ:
1. Load dữ liệu từ `data/alpha_mini_knowledge/*.json`
2. Tạo embeddings cho tất cả documents
3. Lưu vào ChromaDB

### Cập nhật sau này:

```bash
# Interactive mode
python scripts/update_knowledge_base.py

# Hoặc command line
python scripts/update_knowledge_base.py add data/new_data.json
python scripts/update_knowledge_base.py stats
```

## 🚀 Chạy Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

### 1. Hỏi chatbot

```bash
POST /chatbot/ask
Content-Type: application/json

{
  "question": "Alpha Mini có thể nhảy múa không?",
  "top_k": 5
}
```

**Response:**
```json
{
  "question": "Alpha Mini có thể nhảy múa không?",
  "answer": "Có, Alpha Mini có khả năng nhảy múa theo nhạc...",
  "has_answer": true,
  "documents_used": 3,
  "documents": [...],
  "model": "gpt-4-turbo-preview",
  "tokens_used": {"total": 450}
}
```

### 2. Health Check

```bash
GET /chatbot/health
```

### 3. Statistics

```bash
GET /chatbot/stats
```

## 📝 Ví dụ Sử dụng

### Python

```python
import requests

response = requests.post(
    "http://localhost:8000/chatbot/ask",
    json={"question": "Làm sao để kết nối WiFi cho robot?"}
)

data = response.json()
print(data["answer"])
```

### cURL

```bash
curl -X POST "http://localhost:8000/chatbot/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Alpha Mini có những tính năng gì?"}'
```

## 📊 Cấu trúc Dữ liệu

Mỗi document trong knowledge base có cấu trúc:

```json
{
  "id": "feature_001",
  "content": "Nội dung thông tin...",
  "metadata": {
    "category": "features",
    "subcategory": "dance",
    "tags": ["dance", "music"],
    "language": "vi",
    "last_updated": "2025-01-01",
    "source": "official_docs"
  }
}
```

## 🔄 Quy trình RAG

```
User Question
    ↓
Embedding (sentence-transformers)
    ↓
ChromaDB Search (semantic)
    ↓
Top-K Documents Retrieved
    ↓
Context Preparation
    ↓
LLM Generation (GPT-4/Claude)
    ↓
Answer + Citations
```

## 🎯 Thêm Dữ liệu Mới

### 1. Tạo file JSON

```json
[
  {
    "id": "new_001",
    "content": "Thông tin mới...",
    "metadata": {
      "category": "features",
      "tags": ["new"],
      "language": "vi"
    }
  }
]
```

### 2. Thêm vào ChromaDB

```bash
python scripts/update_knowledge_base.py add data/new_data.json
```

## 🛠️ Troubleshooting

### Lỗi: "No module named 'sentence_transformers'"

```bash
pip install sentence-transformers
```

### Lỗi: "OPENAI_API_KEY not found"

Kiểm tra file `.env` có chứa API key:
```bash
OPENAI_API_KEY=sk-...
```

### ChromaDB bị lỗi

Reset collection:
```python
from app.services.rag.vector_store_service import get_vector_store_service
vector_store = get_vector_store_service()
vector_store.reset_collection()
```

## 📈 Performance Tips

- Sử dụng GPU nếu có: Tự động phát hiện CUDA
- Cache embeddings: Embeddings được cache trong ChromaDB
- Điều chỉnh `top_k`: Giảm nếu response quá chậm
- Sử dụng `gpt-3.5-turbo` cho response nhanh hơn

## 🔐 Security

- ⚠️ Không commit file `.env` vào git
- ⚠️ Giữ API keys bí mật
- ⚠️ Rate limit cho production
- ⚠️ Sanitize user input

## 📚 Tài liệu thêm

- [ChromaDB Docs](https://docs.trychroma.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [OpenAI API](https://platform.openai.com/docs)
- [FastAPI](https://fastapi.tiangolo.com/)

---

**Version**: 1.0  
**Last Updated**: 2025-11-05
