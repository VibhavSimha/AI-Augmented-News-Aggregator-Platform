"""
Download a large GDELT Events corpus for local RAG.
- Target size: ~2–3 GB (configurable)
- Source: http://data.gdeltproject.org/events/YYYYMMDD.export.CSV.zip (GDELT 1.0)
- Output: data/news_corpus.parquet with columns [text, source, url, year, month]

Notes:
- This script streams daily zip files and writes to Parquet incrementally.
- Stop once target size (on-disk Parquet) is reached or days exhausted.
"""
import os
import io
import sys
import math
import time
import zipfile
import argparse
import datetime as dt
from pathlib import Path

import requests
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = DATA_DIR / "news_corpus.parquet"
TMP_DIR = DATA_DIR / "gdelt_tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

GDELT_URL_TMPL = "http://data.gdeltproject.org/events/{datestr}.export.CSV.zip"

# Minimal set of columns we need from GDELT 1.0 (58 columns total)
GDELT_COLS = [
    'GLOBALEVENTID', 'SQLDATE', 'MonthYear', 'Year', 'FractionDate',
    'Actor1Code', 'Actor1Name', 'Actor1CountryCode', 'Actor1KnownGroupCode',
    'Actor1EthnicCode', 'Actor1Religion1Code', 'Actor1Religion2Code',
    'Actor1Type1Code', 'Actor1Type2Code', 'Actor1Type3Code',
    'Actor2Code', 'Actor2Name', 'Actor2CountryCode', 'Actor2KnownGroupCode',
    'Actor2EthnicCode', 'Actor2Religion1Code', 'Actor2Religion2Code',
    'Actor2Type1Code', 'Actor2Type2Code', 'Actor2Type3Code',
    'IsRootEvent', 'EventCode', 'EventBaseCode', 'EventRootCode',
    'QuadClass', 'GoldsteinScale', 'NumMentions', 'NumSources',
    'NumArticles', 'AvgTone',
    'Actor1Geo_Type', 'Actor1Geo_FullName', 'Actor1Geo_CountryCode',
    'Actor1Geo_ADM1Code', 'Actor1Geo_Lat', 'Actor1Geo_Long',
    'Actor1Geo_FeatureID',
    'Actor2Geo_Type', 'Actor2Geo_FullName', 'Actor2Geo_CountryCode',
    'Actor2Geo_ADM1Code', 'Actor2Geo_Lat', 'Actor2Geo_Long',
    'Actor2Geo_FeatureID',
    'ActionGeo_Type', 'ActionGeo_FullName', 'ActionGeo_CountryCode',
    'ActionGeo_ADM1Code', 'ActionGeo_Lat', 'ActionGeo_Long',
    'ActionGeo_FeatureID',
    'DATEADDED', 'SOURCEURL'
]

USE_COLS = [
    'SQLDATE', 'Year', 'Actor1Name', 'Actor2Name', 'ActionGeo_FullName',
    'ActionGeo_CountryCode', 'SOURCEURL'
]


def download_day(date: dt.date) -> bytes | None:
    datestr = date.strftime("%Y%m%d")
    url = GDELT_URL_TMPL.format(datestr=datestr)
    try:
        resp = requests.get(url, timeout=120)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.content
    except Exception:
        return None


def iter_days_back(days: int):
    today = dt.date.today()
    for i in range(days):
        yield today - dt.timedelta(days=i+1)


def ensure_parquet_writer(schema: pa.schema, writer_ref: dict):
    if writer_ref.get('writer') is None:
        writer_ref['writer'] = pq.ParquetWriter(str(OUTPUT_PATH), schema)
    return writer_ref['writer']


def process_zip_bytes(zbytes: bytes) -> pd.DataFrame | None:
    try:
        with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
            # Each GDELT daily zip contains one CSV file
            names = zf.namelist()
            if not names:
                return None
            with zf.open(names[0]) as fh:
                df = pd.read_csv(
                    fh,
                    sep='\t',
                    header=None,
                    names=GDELT_COLS,
                    usecols=USE_COLS,
                    dtype={'SQLDATE': str, 'Year': float},
                    encoding='latin-1',
                    on_bad_lines='skip',
                    low_memory=False,
                )
                # Basic cleaning
                df = df.dropna(subset=['Actor1Name', 'ActionGeo_FullName'])
                df['SQLDATE'] = pd.to_datetime(df['SQLDATE'], format='%Y%m%d', errors='coerce')
                df = df.dropna(subset=['SQLDATE'])
                df['year'] = df['SQLDATE'].dt.year.astype('int32')
                df['month'] = df['SQLDATE'].dt.month.astype('int16')
                # Build text field
                df['text'] = (
                    df['Actor1Name'].fillna('') +
                    ((' vs ' + df['Actor2Name']) if 'Actor2Name' in df.columns else '') +
                    ' in ' + df['ActionGeo_FullName'].fillna('')
                ).str.strip()
                # Map to final schema
                out = df[['text', 'year', 'month']].copy()
                out['source'] = 'GDELT'
                out['url'] = df['SOURCEURL'].fillna('')
                # Filter very short
                out = out[out['text'].str.len() > 20]
                return out
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description='Download GDELT Events for RAG corpus')
    parser.add_argument('--days', type=int, default=120, help='Days back to fetch (max attempts)')
    parser.add_argument('--target-size-gb', type=float, default=2.5, help='Stop when parquet reaches this size (GB)')
    parser.add_argument('--rows-per-flush', type=int, default=50000, help='Write parquet every N rows')
    args = parser.parse_args()

    print('=' * 60)
    print('Building Large-Scale RAG Dataset (GDELT)')
    print('=' * 60)

    # If existing output exists, remove to rebuild
    if OUTPUT_PATH.exists():
        print(f"Removing existing corpus: {OUTPUT_PATH}")
        OUTPUT_PATH.unlink()

    total_rows = 0
    buffer_rows: list[pd.DataFrame] = []
    writer_ref: dict = {'writer': None}

    for day in tqdm(iter_days_back(args.days), total=args.days, desc='Days'):
        zbytes = download_day(day)
        if not zbytes:
            continue
        df = process_zip_bytes(zbytes)
        if df is None or df.empty:
            continue
        buffer_rows.append(df)
        total_rows += len(df)

        # Flush
        if sum(len(x) for x in buffer_rows) >= args.rows_per_flush:
            chunk = pd.concat(buffer_rows, ignore_index=True)
            table = pa.Table.from_pandas(chunk)
            writer = ensure_parquet_writer(table.schema, writer_ref)
            writer.write_table(table)
            buffer_rows.clear()

            # Check size
            if OUTPUT_PATH.exists():
                size_gb = OUTPUT_PATH.stat().st_size / (1024**3)
                print(f"Current corpus size: {size_gb:.2f} GB, rows: {total_rows}")
                if size_gb >= args.target_size_gb:
                    break

    # Final flush
    if buffer_rows:
        chunk = pd.concat(buffer_rows, ignore_index=True)
        table = pa.Table.from_pandas(chunk)
        writer = ensure_parquet_writer(table.schema, writer_ref)
        writer.write_table(table)
        buffer_rows.clear()

    # Close writer
    if writer_ref.get('writer'):
        writer_ref['writer'].close()

    if OUTPUT_PATH.exists():
        size_gb = OUTPUT_PATH.stat().st_size / (1024**3)
        print(f"\n✅ Dataset created!")
        print(f"   Location: {OUTPUT_PATH}")
        print(f"   Approx size: {size_gb:.2f} GB")
        print(f"   Total rows (approx): {total_rows:,}")
        print("\nNext: python scripts/build_rag_index.py --max_rows 150000")
    else:
        print("\n❌ Failed to build dataset. Try increasing --days or check network.")


if __name__ == '__main__':
    main()
