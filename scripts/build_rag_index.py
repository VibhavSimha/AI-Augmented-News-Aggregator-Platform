"""
Build FAISS index from the downloaded news corpus
"""
import os
import argparse
import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pathlib import Path
from tqdm import tqdm
import pyarrow.parquet as pq

DATA_DIR = Path(__file__).parent.parent / "data"
CORPUS_PATH = DATA_DIR / "news_corpus.parquet"
INDEX_PATH = DATA_DIR / "news.index"
META_PATH = DATA_DIR / "news_meta.parquet"

def read_corpus_limited(parquet_path: Path, max_rows: int | None) -> pd.DataFrame:
    """Read up to max_rows from a Parquet file efficiently using row groups."""
    pf = pq.ParquetFile(parquet_path)
    dfs = []
    total = 0
    for i in range(pf.num_row_groups):
        tbl = pf.read_row_group(i)
        df = tbl.to_pandas()
        dfs.append(df)
        total += len(df)
        if max_rows and total >= max_rows:
            break
    if not dfs:
        return pd.DataFrame(columns=["text","year","month","source","url"])
    out = pd.concat(dfs, ignore_index=True)
    if max_rows and len(out) > max_rows:
        out = out.head(max_rows)
    return out


def build_index():
    print("=" * 60)
    print("Building RAG Index")
    print("=" * 60)
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--max_rows", type=int, default=150000, help="Max documents to index (controls time/memory)")
    args, _ = parser.parse_known_args()

    # 1. Load dataset
    print("\n1. Loading corpus...")
    if not CORPUS_PATH.exists():
        print(f"❌ Corpus not found: {CORPUS_PATH}")
        print("   Run one of:\n   - python scripts/download_gdelt_dataset.py\n   - python scripts/download_dataset.py")
        return
    
    df = read_corpus_limited(CORPUS_PATH, args.max_rows)
    print(f"✓ Loaded {len(df)} documents (limited)")
    
    # 2. Load embedding model
    print("\n2. Loading embedding model (all-MiniLM-L6-v2)...")
    print("   (First time will download ~90MB model)")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✓ Model loaded")
    
    # 3. Generate embeddings
    print("\n3. Generating embeddings...")
    texts = df['text'].fillna('').astype(str).tolist()
    
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    
    print(f"✓ Generated embeddings: {embeddings.shape}")
    
    # 4. Build FAISS index
    print("\n4. Building FAISS index...")
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product = cosine similarity (normalized)
    index.add(embeddings.astype('float32'))
    
    print(f"✓ Index contains {index.ntotal} vectors")
    
    # 5. Save index
    print("\n5. Saving index...")
    faiss.write_index(index, str(INDEX_PATH))
    print(f"✓ Saved: {INDEX_PATH}")
    
    # 6. Save metadata
    print("\n6. Saving metadata...")
    meta = df[['text', 'year', 'month', 'source', 'url']].copy()
    meta.to_parquet(META_PATH, index=False)
    print(f"✓ Saved: {META_PATH}")
    
    # 7. Summary
    print(f"\n✅ RAG index ready!")
    print(f"   Index: {INDEX_PATH.stat().st_size / (1024*1024):.1f} MB")
    print(f"   Metadata: {META_PATH.stat().st_size / (1024*1024):.1f} MB")
    print(f"   Total vectors: {index.ntotal}")
    print(f"\n   Next step: Restart Flask app to load RAG system")

if __name__ == "__main__":
    build_index()
