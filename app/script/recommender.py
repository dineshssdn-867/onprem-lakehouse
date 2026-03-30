import pickle

import scipy.sparse
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from constants import DEFAULT_RES_NUMBER

# Load TF-IDF matrix once at module level (sparse, memory-efficient)
_tfidf_matrix = None


def _get_tfidf_matrix():
    global _tfidf_matrix
    if _tfidf_matrix is None:
        _tfidf_matrix = scipy.sparse.load_npz('data/res_matrix.npz')
    return _tfidf_matrix


def weighted_average_based_recommendations(ress, res_number=DEFAULT_RES_NUMBER):
    """Return top restaurants sorted by weighted score."""
    ress = ress.head(res_number)
    ress = ress[["business_id", "name", "score"]]
    ress.columns = ["business_id", "name", "score"]
    return ress


def read_item(name, fullRes):
    selected_rows = fullRes.loc[fullRes["name"] == name]
    business_id = selected_rows.iloc[0]['business_id']
    return business_id, selected_rows


def contend_based_recommendations(res, titles, res_number=DEFAULT_RES_NUMBER):
    """Content-based recommendations using lazy cosine similarity.

    Computes similarity only for selected rows against all others (O(k*N))
    instead of the full N*N matrix.
    """
    tfidf_matrix = _get_tfidf_matrix()

    # Deduplicate on name (keep first), so indices[t] always returns a scalar
    indices = pd.Series(res.index, index=res['name'])
    indices = indices[~indices.index.duplicated(keep='first')]

    idx = set()
    for t in titles:
        if t in indices.index:
            idx.add(indices[t])

    if not idx:
        return pd.DataFrame(columns=["business_id", "name", "score"])

    # Compute similarity ONLY for selected rows against all rows
    selected_rows = list(idx)
    sim_scores = cosine_similarity(tfidf_matrix[selected_rows], tfidf_matrix)

    # Aggregate: take max similarity across selected items for each candidate
    if len(sim_scores) > 1:
        max_scores = sim_scores.max(axis=0)
    else:
        max_scores = sim_scores[0]

    # Build candidate list, excluding the selected items themselves
    candidates = []
    for i, score in enumerate(max_scores):
        if i not in idx:
            candidates.append((i, score))

    candidates.sort(key=lambda x: x[1], reverse=True)
    top = candidates[:res_number]

    res_indices = [i[0] for i in top]
    res_similarity = [i[1] for i in top]

    return pd.DataFrame({
        "business_id": res['business_id'].iloc[res_indices].values,
        "name": res['name'].iloc[res_indices].values,
        "score": res_similarity,
    })
