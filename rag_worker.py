#!/usr/bin/env python3
"""
RAG Worker - Isolated process for embedding and FAISS search
Runs separately from main Flask app to prevent crashes from affecting main server
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from pathlib import Path
import signal

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

app = Flask(__name__)
CORS(app)

# Global state
_model = None
_faiss_index = None
_meta_df = None
_backend = None

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RAG_INDEX_PATH = os.path.join(DATA_DIR, "news.index")
RAG_META_PATH = os.path.join(DATA_DIR, "news_meta.parquet")
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"


def load_rag_components():
    """Load RAG components on startup"""
    global _model, _faiss_index, _meta_df, _backend
    
    print("=" * 60)
    print("RAG Worker Starting...")
    print("=" * 60)
    
    try:
        # Force CPU and disable problematic features
        os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '0'
        os.environ['OMP_NUM_THREADS'] = '1'  # Single thread to avoid OpenMP issues
        
        print(f"\n1. Loading embedding model: {EMBED_MODEL_NAME}")
        from sentence_transformers import SentenceTransformer
        from transformers import AutoModel, AutoConfig
        import torch
        
        # Disable parallel tokenizers
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        # Patch to force low_cpu_mem_usage=False
        _original_auto_from_pretrained = AutoModel.from_pretrained
        
        @classmethod
        def _patched_auto_from_pretrained(cls, *args, **kwargs):
            kwargs['low_cpu_mem_usage'] = False
            return _original_auto_from_pretrained(*args, **kwargs)
        
        AutoModel.from_pretrained = _patched_auto_from_pretrained
        
        _model = SentenceTransformer(EMBED_MODEL_NAME, device='cpu')
        _model.eval()
        
        # Verify model has parameters
        param_count = sum(p.numel() for p in _model.parameters())
        if param_count == 0:
            raise RuntimeError("Model has no parameters")
        
        _backend = 'sentence-transformers'
        print(f"   ✓ Loaded {EMBED_MODEL_NAME} ({param_count:,} parameters)")
        
        print(f"\n2. Loading FAISS index: {RAG_INDEX_PATH}")
        import faiss
        _faiss_index = faiss.read_index(RAG_INDEX_PATH)
        print(f"   ✓ Loaded FAISS index ({_faiss_index.ntotal:,} vectors)")
        
        print(f"\n3. Loading metadata: {RAG_META_PATH}")
        import pandas as pd
        _meta_df = pd.read_parquet(RAG_META_PATH)
        print(f"   ✓ Loaded metadata ({len(_meta_df):,} entries)")
        
        print("\n" + "=" * 60)
        print("✓ RAG Worker Ready")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ RAG Worker failed to start: {e}")
        import traceback
        traceback.print_exc()
        return False


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'rag_ready': _model is not None and _faiss_index is not None,
        'backend': _backend,
        'index_size': _faiss_index.ntotal if _faiss_index else 0,
        'model': EMBED_MODEL_NAME
    })


@app.route('/embed', methods=['POST'])
def embed():
    """Embed texts into vectors"""
    if _model is None:
        return jsonify({'error': 'Model not loaded'}), 503
    
    try:
        data = request.get_json()
        texts = data.get('texts', [])
        
        if not texts:
            return jsonify({'error': 'No texts provided'}), 400
        
        # Encode with forced CPU
        import numpy as np
        vectors = _model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            device='cpu',
            show_progress_bar=False
        ).astype('float32')
        
        return jsonify({
            'vectors': vectors.tolist(),
            'shape': list(vectors.shape)
        })
        
    except Exception as e:
        print(f"Encoding error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def _extract_excerpt(text, query, max_length=250):
    """
    Extract relevant excerpt from text based on query keywords.
    Returns the most relevant sentence or text snippet.
    """
    if not text or len(text.strip()) == 0:
        return "No content available for this event."
    
    text = text.strip()
    
    # If text is short enough, return as is
    if len(text) <= max_length:
        return text
    
    # Extract query keywords
    query_words = set(word.lower() for word in query.split() if len(word) > 2)
    
    # Split into sentences
    import re
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    if not sentences:
        # Fallback: return first max_length chars
        return text[:max_length].rsplit(' ', 1)[0] + "..."
    
    # Score sentences by keyword overlap
    best_sentence = sentences[0]
    best_score = 0
    
    for sentence in sentences[:15]:  # Check first 15 sentences
        words = set(word.lower() for word in sentence.split())
        # Count matching keywords
        score = len(query_words & words)
        # Bonus for position (earlier sentences slightly preferred)
        if score > best_score or (score == best_score and sentence == sentences[0]):
            best_score = score
            best_sentence = sentence
    
    # Truncate if too long
    if len(best_sentence) > max_length:
        best_sentence = best_sentence[:max_length].rsplit(' ', 1)[0] + "..."
    
    return best_sentence


@app.route('/search', methods=['POST'])
def search():
    """Search FAISS index for similar vectors"""
    if _model is None or _faiss_index is None or _meta_df is None:
        return jsonify({'error': 'RAG not ready'}), 503
    
    try:
        import pandas as pd
        import numpy as np
        
        data = request.get_json()
        query = data.get('query', '')
        k = data.get('k', 10)
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        # Embed query
        query_vec = _model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            device='cpu',
            show_progress_bar=False
        ).astype('float32')
        
        # Search FAISS
        k_search = min(k * 2, _faiss_index.ntotal)
        scores, indices = _faiss_index.search(query_vec, k_search)
        
        # Build results
        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0 or idx >= len(_meta_df):
                continue
            
            row = _meta_df.iloc[idx]
            
            # Safely extract values
            text = str(row.get('text', '')) if pd.notna(row.get('text')) else ''
            year_val = row.get('year')
            month_val = row.get('month')
            url_val = row.get('url', '')
            
            # Format date
            date_str = None
            if pd.notna(year_val) and pd.notna(month_val):
                try:
                    date_str = f"{int(year_val)}-{int(month_val):02d}"
                except (ValueError, TypeError):
                    date_str = None
            
            # Create contextual excerpt with year and month information
            if pd.notna(year_val) and text:
                # Parse the event text to extract location and entities
                parts = text.split(' in ')
                if len(parts) >= 2:
                    entities = parts[0].strip()
                    location = ' in '.join(parts[1:]).strip()
                    
                    # Format month name if available
                    month_str = ""
                    if pd.notna(month_val):
                        try:
                            month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                                         'July', 'August', 'September', 'October', 'November', 'December']
                            month_str = f"{month_names[int(month_val) - 1]} "
                        except (ValueError, TypeError, IndexError):
                            pass
                    
                    # Create natural sentence
                    excerpt = f"Event involving {entities} in {location} ({month_str}{int(year_val)})."
                else:
                    # Fallback if parsing fails - just use the text as-is
                    excerpt = f"{text} ({int(year_val)})."
            else:
                excerpt = text if text else 'No description available.'
            
            results.append({
                'title': text[:200] if text else 'Event',
                'snippet': text if text else '',
                'excerpt': excerpt,  # Enhanced contextual excerpt
                'source': str(row.get('source', 'Historical Archive')),
                'link': str(url_val) if pd.notna(url_val) else '',
                'date': date_str,
                'score': float(score),
                'year': int(year_val) if pd.notna(year_val) else None
            })
        
        # Sort by score and return top k
        results = sorted(results, key=lambda x: x['score'], reverse=True)[:k]
        
        return jsonify({
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        print(f"Search error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def handle_shutdown(signum, frame):
    """Handle graceful shutdown"""
    print("\n\nShutting down RAG worker...")
    sys.exit(0)


if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Load RAG components
    if not load_rag_components():
        print("Failed to load RAG components. Exiting.")
        sys.exit(1)
    
    # Start Flask server
    print("\nStarting Flask server on http://127.0.0.1:5001")
    print("Press CTRL+C to stop\n")
    
    app.run(
        host='127.0.0.1',
        port=5001,
        debug=False,
        use_reloader=False,
        threaded=True
    )
