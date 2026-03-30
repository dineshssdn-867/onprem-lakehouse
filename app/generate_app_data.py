"""
Generate pickle files and TF-IDF matrix for the Streamlit app
from the current bronze layer data in Trino.

Usage:
    python generate_app_data.py
    # Or from host: docker exec recommender_app python generate_app_data.py
"""
import os
import pickle

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import scipy.sparse

# -- Config --
TRINO_HOST = os.environ.get("TRINO_HOST", "trino")
TRINO_PORT = int(os.environ.get("TRINO_PORT", "8080"))
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def get_trino_connection():
    from trino.dbapi import connect
    return connect(host=TRINO_HOST, port=TRINO_PORT, user="trino", catalog="lakehouse")


def fetch_restaurants():
    conn = get_trino_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            business_id,
            businessid,
            name,
            categories,
            address,
            city,
            state,
            stars,
            review_count,
            is_open
        FROM bronze.restaurant_transform
    """)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    conn.close()
    return pd.DataFrame(rows, columns=columns)


def compute_weighted_score(df):
    """Compute IMDB-style weighted rating."""
    C = df['stars'].mean()
    m = df['review_count'].quantile(0.70)
    qualified = df[df['review_count'] >= m].copy()
    qualified['score'] = qualified.apply(
        lambda x: (x['review_count'] / (x['review_count'] + m)) * x['stars'] +
                  (m / (x['review_count'] + m)) * C,
        axis=1
    )
    return qualified.sort_values('score', ascending=False).reset_index(drop=True)


def build_tfidf_matrix(df):
    """Build TF-IDF matrix from available text columns."""
    text_cols = ['categories', 'city', 'name']
    parts = [df[c].fillna('') for c in text_cols if c in df.columns]
    df['text_features'] = parts[0]
    for p in parts[1:]:
        df['text_features'] = df['text_features'] + ' ' + p
    vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
    tfidf_matrix = vectorizer.fit_transform(df['text_features'])
    return tfidf_matrix


def main():
    print("Fetching restaurant data from Trino...")
    df = fetch_restaurants()
    print(f"  Got {len(df)} restaurants")

    # res_df.pickle — used for content-based recommendation lookups
    res_df = df[['business_id', 'name', 'categories']].copy()
    with open(os.path.join(DATA_DIR, 'res_df.pickle'), 'wb') as f:
        pickle.dump(res_df, f)
    print(f"  Saved res_df.pickle ({len(res_df)} rows)")

    # res_scores.pickle — used for score-based recommendations and detail view
    scored_df = compute_weighted_score(df)
    with open(os.path.join(DATA_DIR, 'res_scores.pickle'), 'wb') as f:
        pickle.dump(scored_df, f)
    print(f"  Saved res_scores.pickle ({len(scored_df)} rows)")

    # res_matrix.npz — TF-IDF sparse matrix for content-based recommendations
    tfidf_matrix = build_tfidf_matrix(res_df)
    scipy.sparse.save_npz(os.path.join(DATA_DIR, 'res_matrix.npz'), tfidf_matrix)
    dense_size_mb = tfidf_matrix.shape[0] * tfidf_matrix.shape[0] * 8 / 1024 / 1024
    print(f"  Saved res_matrix.npz (shape={tfidf_matrix.shape}, full cosine sim would be {dense_size_mb:.0f} MB)")
    print(f"  With lazy computation, only {tfidf_matrix.shape[1] * 8 / 1024:.0f} KB per query row")

    print("Done!")


if __name__ == "__main__":
    main()
