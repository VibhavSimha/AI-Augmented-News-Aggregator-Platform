from flask import Flask, jsonify, request, render_template
from collections import Counter
import re
import os
import json
import time
import sqlite3
import hashlib
from datetime import datetime
import nltk
from nltk.corpus import stopwords
from groq import Groq, GroqError
import requests
from dotenv import load_dotenv
from pathlib import Path
from flask_cors import CORS

# RAG imports (required for embedding and search)
try:
    import pandas as pd
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("⚠ RAG dependencies not installed. Install requirements.txt for full functionality.")

app = Flask(__name__)

# Robust .env loading: try CWD, script dir, project root, and server subdir
def _load_env_files():
    candidates = [
        Path.cwd() / '.env',
        Path(__file__).parent / '.env',
        (Path(__file__).parent / 'server' / '.env'),
        Path(__file__).parent.parent / '.env',
    ]
    for p in candidates:
        try:
            if p.exists():
                load_dotenv(p, override=False)
        except Exception:
            # Ignore malformed env files silently
            pass

_load_env_files()
CORS(app, resources={r"/*": {"origins": os.getenv("CORS_ORIGIN", "*")}})


# Initialize Groq API client and config
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "15"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Use a supported Groq model; allow override via env
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
client = Groq(api_key=GROQ_API_KEY)

# Ensure stopwords are available without repeated downloads
try:
    _ = stopwords.words("english")
except LookupError:
    nltk.download('stopwords')

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
CACHE_DB = os.path.join(DATA_DIR, "http_cache.sqlite")

# RAG Worker configuration
RAG_WORKER_URL = os.getenv("RAG_WORKER_URL", "http://127.0.0.1:5001")
RAG_WORKER_TIMEOUT = float(os.getenv("RAG_WORKER_TIMEOUT", "10"))

# Legacy RAG setup (no longer used - moved to worker)
_rag_worker_available = None  # Cache worker availability

def _check_rag_worker():
    """Check if RAG worker is available"""
    global _rag_worker_available
    
    if _rag_worker_available is not None:
        return _rag_worker_available
    
    try:
        resp = requests.get(
            f"{RAG_WORKER_URL}/health",
            timeout=2
        )
        if resp.status_code == 200:
            data = resp.json()
            _rag_worker_available = data.get('rag_ready', False)
            if _rag_worker_available:
                print(f"✓ RAG worker available at {RAG_WORKER_URL}")
            return _rag_worker_available
    except Exception as e:
        print(f"⚠ RAG worker not available: {e}")
    
    _rag_worker_available = False
    return False

def rag_search(query, k=10):
    """
    Search RAG index via worker service
    
    Args:
        query: search string
        k: number of results
    
    Returns:
        List of article dicts (empty list if worker unavailable)
    """
    if not _check_rag_worker():
        print("⚠ RAG worker not available - returning empty results")
        return []
    
    try:
        resp = requests.post(
            f"{RAG_WORKER_URL}/search",
            json={"query": query, "k": k},
            timeout=RAG_WORKER_TIMEOUT
        )
        
        if resp.status_code == 200:
            data = resp.json()
            return data.get('results', [])
        else:
            print(f"⚠ RAG worker search failed: {resp.status_code}")
            return []
    
    except Exception as e:
        print(f"⚠ RAG worker request failed: {e}")
        return []


def _db():
    conn = sqlite3.connect(CACHE_DB)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS http_cache (k TEXT PRIMARY KEY, ts REAL, body TEXT)"
    )
    return conn


def cache_get(key: str, max_age: int = 1800):
    conn = _db()
    cur = conn.execute("SELECT ts, body FROM http_cache WHERE k=?", (key,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    ts, body = row
    if time.time() - ts > max_age:
        return None
    try:
        return json.loads(body)
    except Exception:
        return None


def cache_set(key: str, obj: dict):
    conn = _db()
    conn.execute(
        "REPLACE INTO http_cache (k, ts, body) VALUES (?,?,?)",
        (key, time.time(), json.dumps(obj)),
    )
    conn.commit()
    conn.close()


def extract_keywords(text):
    words = re.findall(r'\b\w+\b', text.lower())
    stop_words = set(stopwords.words("english"))
    keywords = [w for w in words if w not in stop_words and len(w) > 2 and not w.isdigit()]
    common_words = Counter(keywords).most_common(6)
    return [word for word, _ in common_words]

def get_historical_events(headline):
    prompt = (
        "Return exactly a JSON array with 5 objects. Each object has: \n"
        ' - "event": brief description (string)\n'
        ' - "year": 4-digit year or null\n'
        "Events must be ordered from oldest to most recent.\n\n"
        f"Topic: {headline}"
    )
    messages = [
        {"role": "system", "content": "You are a precise analyst. Respond in strict JSON only."},
        {"role": "user", "content": prompt},
    ]
    chat_completion = client.chat.completions.create(
        messages=messages,
        model=GROQ_MODEL,
        temperature=0.2,
    )
    content = chat_completion.choices[0].message.content
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list) and len(parsed) == 5:
            return parsed
    except Exception:
        pass
    # Fallback to line-split
    lines = [l.strip("- ").strip() for l in content.split("\n") if l.strip()]
    return [{"event": l, "year": None} for l in lines[:5]]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_headline', methods=['POST'])
def process_headline():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        headline = (payload.get('headline') or '').strip()
        if not headline:
            return jsonify({"error": "headline is required"}), 400

        events = get_historical_events(headline)
        timeline_data = []
        for e in events:
            event_text = (e["event"] if isinstance(e, dict) else str(e)).strip()
            if not event_text:
                continue
            keywords = extract_keywords(event_text)
            query = " ".join(keywords) or event_text
            
            # Use RAG for article search
            articles = rag_search(query, k=5) or []
            
            # Filter articles by relevance score (keep only if score > 0.5)
            RELEVANCE_THRESHOLD = 0.5
            relevant_articles = [a for a in articles if a.get('score', 0) > RELEVANCE_THRESHOLD]
            
            # If no relevant articles found, create a placeholder with the event as context
            if not relevant_articles:
                event_year = e.get("year") if isinstance(e, dict) else None
                if event_year:
                    excerpt = f"No recent news coverage found for this {event_year} event. Our database contains current news articles from 2025."
                else:
                    excerpt = f"No recent news coverage found for this historical event. Our database contains current news articles from 2025."
                
                relevant_articles = [{
                    "title": "Historical Context",
                    "excerpt": excerpt,
                    "snippet": event_text,
                    "source": "Historical Record",
                    "link": "",
                    "date": None,
                    "score": 0.0
                }]
            
            timeline_data.append({
                "event": event_text,
                "year": (e.get("year") if isinstance(e, dict) else None),
                "articles": relevant_articles[:3] if relevant_articles else []
            })

        return jsonify(timeline_data)
    except GroqError as e:
        # Surface model issues (e.g., decommissioned) as 400 to the client
        return jsonify({"error": str(e)}), 400
    except requests.Timeout:
        return jsonify({"error": "Upstream timeout"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/ask', methods=['POST'])
def ask():
    # Grounded Q&A over recent news for a headline/question
    try:
        payload = request.get_json(force=True, silent=True) or {}
        headline = (payload.get('headline') or '').strip()
        question = (payload.get('question') or '').strip()
        if not question:
            return jsonify({"error": "question is required"}), 400
        combo = " ".join([w for w in [headline, question] if w])
        
        # Use RAG for context articles
        ctx_articles = rag_search(combo, k=5) or []
        
        context = "\n\n".join(
            f"Title: {a.get('title')}\nSource: {a.get('source')}\nDate: {a.get('date')}\nURL: {a.get('link')}\nSnippet: {a.get('snippet')}"
            for a in ctx_articles if a
        ) or "No relevant articles found."
        messages = [
            {"role": "system", "content": "Answer using only the provided news context. If insufficient, say you are unsure."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ]
        chat = client.chat.completions.create(
            messages=messages,
            model=GROQ_MODEL,
            temperature=0.1,
        )
        answer = chat.choices[0].message.content
        return jsonify({"answer": answer, "sources": ctx_articles})
    except GroqError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health')
def health():
    """Health check - reports RAG worker availability"""
    rag_ready = _check_rag_worker()
    
    # Use timezone-aware datetime
    from datetime import timezone
    current_time = datetime.now(timezone.utc).isoformat()
    
    # Get worker info if available
    worker_info = {}
    if rag_ready:
        try:
            resp = requests.get(f"{RAG_WORKER_URL}/health", timeout=2)
            if resp.status_code == 200:
                worker_info = resp.json()
        except:
            pass
    
    return jsonify({
        "ok": True,
        "time": current_time,
        "groq": bool(GROQ_API_KEY),
        "model": GROQ_MODEL,
        "rag_available": RAG_AVAILABLE,
        "rag_ready": rag_ready,
        "rag_worker_url": RAG_WORKER_URL,
        "rag_index_size": worker_info.get('index_size', 0),
        "rag_backend": worker_info.get('backend', None)
    })

if __name__ == '__main__':
    if not GROQ_API_KEY:
        print("Warning: Missing GROQ_API_KEY in environment (.env). LLM features will fail.")
    print("🚀 Starting with RAG-only mode (no SerpAPI)")
    # To avoid multiple process reloading which may race when loading large native models,
    # default to running without the Flask reloader. Control debug via FLASK_DEBUG env.
    flask_debug = str(os.getenv("FLASK_DEBUG", "")).lower() in ("1", "true", "yes")
    app.run(debug=flask_debug, use_reloader=False)