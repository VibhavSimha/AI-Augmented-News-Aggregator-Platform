# AI-Augmented News Aggregator Platform

A modern news aggregation platform featuring AI-powered contextual timeline generation and intelligent chat assistance. Built with React + Vite frontend and Flask backend with **local RAG (Retrieval-Augmented Generation)** using FAISS vector search over a 250k+ GDELT news corpus.

## ✨ Features

- **📰 Multi-Source News**: Aggregates headlines from various countries and sources
- **🤖 AI Timeline Generator**: Creates historical context timelines for any news headline using local RAG
- **💬 Intelligent Chat**: Ask questions about news with AI-powered responses grounded in real articles
- **🔍 Local RAG System**: Fast semantic search over 250k+ historical GDELT events (no external API calls after setup)
- **📊 Smart Search**: Keyword extraction and semantic similarity matching
- **🌍 Country Filters**: Browse news by country
- **⚡ Modern Stack**: React 18 + Vite 4 + Flask + FAISS + sentence-transformers

## 🏗️ Architecture

### Frontend
- **React 18** with Vite for lightning-fast dev experience
- **Tailwind CSS** 
- **Framer Motion** for smooth animations
- Responsive horizontal article cards with image thumbnails

### Backend
- **Flask** REST API with CORS support
- **RAG System**:
  - **FAISS** IndexFlatIP for cosine similarity search
  - **sentence-transformers** (all-MiniLM-L6-v2) for embeddings
  - **GDELT** dataset (8.4M+ events, 250k indexed)
  - **pandas + pyarrow** for efficient parquet I/O
- **Groq API** for LLM-powered timeline generation and Q&A
- **SerpAPI** fallback for real-time news when RAG unavailable
- **SQLite** HTTP response caching (15min TTL)

## 📋 Prerequisites

### System Requirements
- **Python 3.12** (⚠️ Python 3.13 has PyTorch compatibility issues)
- **Node.js 18+** and npm
- **macOS** (tested on M4 Mac) or Linux
- **16GB RAM** recommended for RAG system
- **5GB disk space** for GDELT dataset + FAISS index

### API Keys (Required)
1. **Groq API key**: [Get one here](https://console.groq.com/keys) - Free tier available
2. **SerpAPI key**: [Get one here](https://serpapi.com/manage-api-key) - Used as fallback
3. **NewsAPI.org key**: [Get one here](https://newsapi.org/register) - For live headlines

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/VibhavSimha/AI-Augmented-News-Aggregator-Platform.git
cd AI-Augmented-News-Aggregator-Platform
```

### 2. Backend Setup (Python 3.12)

#### Install Python 3.12
```bash
# macOS (Homebrew)
brew install python@3.12

# Verify installation
/opt/homebrew/bin/python3.12 --version
```

#### Create Virtual Environment
```bash
# Create venv with Python 3.12
/opt/homebrew/bin/python3.12 -m venv venv

# Activate venv
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows
```

#### Install Dependencies
```bash
# Core packages
pip install flask flask-cors python-dotenv nltk groq requests

# RAG system packages
pip install pandas pyarrow faiss-cpu sentence-transformers torch
```

#### Configure Environment Variables
Create a `.env` file in the project root:
```bash
# Required
GROQ_API_KEY=your_groq_api_key_here
SERPAPI_KEY=your_serpapi_key_here

# Optional (defaults shown)
GROQ_MODEL=llama-3.1-8b-instant
REQUEST_TIMEOUT=15
CORS_ORIGIN=*
```

#### Download NLTK Data
```python
python -c "import nltk; nltk.download('stopwords')"
```

### 3. RAG System Setup (Optional but Recommended)

The RAG system enables fast, local semantic search over historical news events without external API calls.

#### Download GDELT Dataset (~0.3-4 GB)
```bash
# Download 120 days of GDELT data (~0.27 GB, ~8.4M events)
python scripts/download_gdelt_dataset.py --days 120 --target-size-gb 0.3

# OR for full dataset (1700 days, ~3.8 GB)
python scripts/download_gdelt_dataset.py --days 1700 --target-size-gb 3.8
```

#### Build FAISS Index
```bash
# Index 250k events (recommended, ~5 min on M4 Mac)
python scripts/build_rag_index.py --max_rows 250000

# OR index all available events
python scripts/build_rag_index.py
```

This creates:
- `data/news.index` - FAISS vector index (~366 MB for 250k vectors)
- `data/news_meta.parquet` - Metadata (~9 MB)

### 4. Start Backend Server

#### Option A: Safe Mode (RAG Disabled - Recommended for Stability)
```bash
# Use SerpAPI fallback only, avoids model loading issues
RAG_DISABLED=1 ./venv/bin/python -u app.py

# OR with logging
RAG_DISABLED=1 ./venv/bin/python -u app.py 2>&1 | tee server.log
```

**Use this if:**
- First time running the server
- Experiencing crashes or "meta tensor" errors
- Want guaranteed stability
- Don't need local RAG (SerpAPI provides news articles)

#### Option B: Standard Mode (RAG Enabled)
```bash
# Make sure venv is activated
source venv/bin/activate

# Start with RAG system (requires FAISS index built)
./venv/bin/python -u app.py

# OR with logging
./venv/bin/python -u app.py 2>&1 | tee server.log
```

**Requirements:**
- FAISS index built (`data/news.index` exists)
- Python 3.12 (not 3.13)
- 16GB+ RAM recommended

#### Option C: Debug Mode (Development)
```bash
# Enable Flask debug mode with auto-reload
FLASK_DEBUG=1 ./venv/bin/python -u app.py
```

⚠️ **Warning**: Debug mode runs multiple processes which may cause concurrent model loading issues.

#### Server Configuration

The server will display:
```
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
```

**Check server health:**
```bash
curl http://127.0.0.1:5000/health | python3 -m json.tool
```

**Sample health response:**
```json
{
  "ok": true,
  "serpapi": true,
  "groq": true,
  "model": "llama-3.1-8b-instant",
  "rag_available": true,
  "rag_disabled": false,
  "rag_ready": true,
  "rag_index_size": 250000,
  "rag_backend": "st"
}
```

**Kill the server:**
```bash
# Find and kill process on port 5000
lsof -ti:5000 | xargs kill -9

# OR if you have the process ID
kill 73329
```

Server runs at **http://127.0.0.1:5000**

### 5. Frontend Setup

```bash
cd client
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**

## 🎯 Usage

### Browse News
1. Open http://localhost:5173
2. Browse top headlines on the homepage
3. Filter by country using the dropdown
4. Search for specific topics

### AI Timeline (RAG-Powered)
1. Click **"Show Timeline"** on any article
2. AI generates 5 historical events related to the headline
3. Each event shows relevant articles from the RAG corpus
4. Timeline orders events chronologically (oldest → newest)

### Ask AI (RAG-Powered Q&A)
1. Click **"Ask AI"** on any article
2. Type your question in the chat modal
3. AI retrieves relevant context from RAG corpus
4. Receives grounded answer with source citations

## 🛠️ Troubleshooting

### Python 3.13 Compatibility Issues

**Problem**: `Cannot copy out of meta tensor; no data!` error or server crashes

**Root Cause**: PyTorch/transformers meta-tensor handling causes native segfaults in Python 3.13

**Solution 1 - Use Python 3.12 (Recommended)**:
```bash
# Check your Python version
python --version

# If using 3.13, create new venv with 3.12
brew install python@3.12
/opt/homebrew/bin/python3.12 -m venv venv
source venv/bin/activate
pip install flask flask-cors python-dotenv nltk groq requests pandas pyarrow faiss-cpu sentence-transformers torch
```

**Solution 2 - Use Safe Mode (Keep Python 3.13)**:
```bash
# Run with RAG disabled to avoid model loading
RAG_DISABLED=1 ./venv/bin/python -u app.py
```

This uses SerpAPI fallback for all queries and completely avoids the native crash.

### Server Crashes / "Python quit unexpectedly"

**Problem**: macOS shows "Python quit unexpectedly" dialog, server stops responding

**Root Cause**: Native segfault in PyTorch/OpenMP/transformers during model initialization or inference

**Solution 1 - Safe Mode (Immediate Fix)**:
```bash
# Disable local RAG entirely
RAG_DISABLED=1 ./venv/bin/python -u app.py
```

**Solution 2 - Single Process Mode**:
```bash
# Disable Flask reloader (already default in app.py)
# This prevents concurrent model loads
./venv/bin/python -u app.py
```

**Check crash reports**:
```bash
# View recent Python crashes
ls -lt ~/Library/Logs/DiagnosticReports/Python-*.ips | head -5
```

### Model Won't Load / StopIteration Error

**Problem**: Model loads initially but crashes on second use

**Solution**: The `app.py` includes patches for transformers `low_cpu_mem_usage` parameter. If issues persist:

```bash
# Clear model cache
rm -rf ~/.cache/torch/sentence_transformers/

# Restart Flask
lsof -ti:5000 | xargs kill -9
RAG_DISABLED=1 ./venv/bin/python -u app.py  # Use safe mode first
```

### Missing pyarrow / Parquet Errors

**Problem**: `Missing optional dependency 'pyarrow'`

**Solution**:
```bash
pip install pyarrow
```

### Port 5000 Already in Use

**Problem**: Flask won't start

**Solution**:
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# OR use different port
# Edit app.py: app.run(debug=True, port=5001)
```

### RAG System Disabled / Fallback to SerpAPI

**Problem**: See `⚠ RAG disabled, will use SerpAPI fallback for all queries`

**This is NORMAL and SAFE behavior when:**
- Running with `RAG_DISABLED=1` environment variable
- FAISS index not built yet
- Model loading encountered errors
- Running in safe mode to avoid crashes

**Causes & Solutions**:

1. **Intentionally disabled** (Safe Mode):
   - ✅ This is correct - server is stable
   - Timeline and Chat AI work via SerpAPI
   - No action needed

2. **FAISS index missing**:
   ```bash
   # Build the index (takes ~5 min)
   python scripts/build_rag_index.py --max_rows 250000
   ```

3. **Model won't load** (crashes/errors):
   ```bash
   # Option A: Use Python 3.12
   brew install python@3.12
   /opt/homebrew/bin/python3.12 -m venv venv
   source venv/bin/activate
   pip install -r requirements-rag.txt
   
   # Option B: Keep using safe mode
   RAG_DISABLED=1 ./venv/bin/python -u app.py
   ```

4. **Missing dependencies**:
   ```bash
   pip install sentence-transformers faiss-cpu torch pandas pyarrow
   ```

**When to use each mode:**

| Mode | Use When | Command |
|------|----------|---------|
| **Safe Mode** | First run, stability issues, crashes | `RAG_DISABLED=1 ./venv/bin/python -u app.py` |
| **RAG Mode** | FAISS built, Python 3.12, stable system | `./venv/bin/python -u app.py` |
| **Debug Mode** | Development, testing | `FLASK_DEBUG=1 ./venv/bin/python -u app.py` |

### Client Build Errors

**Problem**: Vite build fails

**Solution**:
```bash
cd client
rm -rf node_modules package-lock.json
npm install
npm run dev
```

## 📁 Project Structure

```
AI-Augmented-News-Aggregator-Platform/
├── app.py                      # Flask backend with RAG integration
├── .env                        # API keys (create this)
├── README.md                   # This file
├── data/                       # RAG system data
│   ├── news.index             # FAISS vector index
│   ├── news_meta.parquet      # Event metadata
│   ├── news_corpus.parquet    # GDELT raw data
│   └── http_cache.sqlite      # HTTP response cache
├── scripts/
│   ├── download_gdelt_dataset.py  # GDELT downloader
│   └── build_rag_index.py         # FAISS index builder
├── client/                    # React frontend
│   ├── src/
│   │   ├── App.jsx           # Main app component
│   │   ├── components/
│   │   │   ├── Header.jsx    
│   │   │   ├── AllNews.jsx   # Horizontal article cards
│   │   │   ├── TopHeadlines.jsx
│   │   │   ├── CountryNews.jsx
│   │   │   └── EverythingCard.jsx  # Timeline + Chat modals
│   │   └── assets/
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.cjs
└── venv/                      # Python 3.12 virtual environment
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Required API Keys
GROQ_API_KEY=your_groq_api_key_here
SERPAPI_KEY=your_serpapi_key_here

# Optional - Server Configuration
GROQ_MODEL=llama-3.1-8b-instant    # LLM model for timeline/chat
REQUEST_TIMEOUT=15                  # HTTP request timeout (seconds)
CORS_ORIGIN=*                       # CORS allowed origins

# Optional - RAG Control
RAG_DISABLED=0                      # Set to 1/true/yes to disable local RAG
FLASK_DEBUG=0                       # Set to 1/true/yes to enable debug mode
```

**Environment Variable Reference:**

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | *Required* | API key from console.groq.com |
| `SERPAPI_KEY` | *Required* | API key from serpapi.com |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Groq LLM model to use |
| `REQUEST_TIMEOUT` | `15` | Timeout for external API calls (seconds) |
| `CORS_ORIGIN` | `*` | CORS allowed origins |
| `RAG_DISABLED` | `0` | Disable local RAG (1/true/yes = disabled) |
| `FLASK_DEBUG` | `0` | Enable Flask debug mode (1/true/yes = enabled) |

**Running with environment variables (inline):**

```bash
# Safe mode with RAG disabled
RAG_DISABLED=1 ./venv/bin/python -u app.py

# Debug mode
FLASK_DEBUG=1 ./venv/bin/python -u app.py

# Multiple variables
RAG_DISABLED=1 FLASK_DEBUG=1 ./venv/bin/python -u app.py
```

### Backend (`app.py`)
- **RAG_INDEX_PATH**: `data/news.index` - FAISS index location
- **EMBED_MODEL_NAME**: `all-MiniLM-L6-v2` - Embedding model
- **GROQ_MODEL**: `llama-3.1-8b-instant` - LLM for timeline/chat
- **REQUEST_TIMEOUT**: `15` seconds
- **Cache TTL**: 15 minutes for news, 10 minutes for Q&A

### Dataset (`scripts/download_gdelt_dataset.py`)
- **--days**: Number of days to download (default: 120)
- **--target-size-gb**: Stop when reaching size (default: 0.3 GB)
- **Output**: `data/news_corpus.parquet`

### Index Builder (`scripts/build_rag_index.py`)
- **--max_rows**: Limit vectors to index (default: all)
- **Output**: `data/news.index` + `data/news_meta.parquet`

## 🧪 Testing

### Health Check
```bash
curl http://127.0.0.1:5000/health | python3 -m json.tool
```

Expected response:
```json
{
  "ok": true,
  "serpapi": true,
  "groq": true,
  "model": "llama-3.1-8b-instant",
  "rag_available": true,
  "rag_ready": true,
  "rag_index_size": 250000,
  "rag_backend": "st"
}
```

### Timeline Endpoint
```bash
curl -X POST http://127.0.0.1:5000/process_headline \
  -H "Content-Type: application/json" \
  -d '{"headline": "AI technology breakthrough"}' | python3 -m json.tool
```

### Chat Endpoint
```bash
curl -X POST http://127.0.0.1:5000/ask \
  -H "Content-Type: application/json" \
  -d '{"headline": "Climate change", "question": "What are the latest developments?"}' | python3 -m json.tool
```

## 🚀 Production Deployment

### Backend
```bash
# Use production WSGI server
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Frontend
```bash
cd client
npm run build
# Deploy dist/ folder to static hosting (Vercel, Netlify, etc.)
```

## 📊 Performance

- **RAG Query**: ~200-500ms (250k index, M4 Mac)
- **Timeline Generation**: ~2-5s (5 events + RAG retrieval + LLM)
- **Chat Response**: ~1-3s (RAG retrieval + LLM)
- **Cold Start**: ~10-15s (model loading on first request)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- **GDELT Project** for the global event database
- **sentence-transformers** for the embedding models
- **FAISS** for efficient vector search
- **Groq** for fast LLM inference
- **SerpAPI** for real-time news fallback
- **BBC News** for design inspiration

#### Client Setup

8. Navigate to the client directory and run:
   ```
   npm install
   ```
9. Start the client by running:
   ```
   npm run dev
   ```

## Usage

Once the project is set up and running, you can view news articles from various sources on the client side.

### Features

- **News Timeline/Contextualizer:**  
  Uses Groq API and SerpAPI to generate a timeline of key historical events and related news articles for a given headline.

- **Chatbot (Ask AI):**  
  Uses Groq API to answer user questions about a news article.

### API Keys Required

- **NewsAPI.org:** For fetching news articles.
- **Groq API:** For AI-powered chatbot and contextual timeline.
- **SerpAPI:** For fetching related news articles for timeline events.
