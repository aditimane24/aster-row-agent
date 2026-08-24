"""
Loads the saved index and answers "what are the most relevant chunks
for this query?"

Ranking logic (important, explain this in the interview):
- Base score = cosine similarity between query and chunk embeddings.
- We add a small boost/penalty based on status and policy_authority:
    active + official   -> +0.05
    superseded           -> -0.05
    draft / none          -> -0.10
  This is a NUDGE, not a hard filter. It's enough to break near-ties
  (e.g. current vs legacy returns policy both mention "return window"),
  but it does NOT hide a lower-status document if it's the most relevant
  thing found (e.g. the migration scratchpad, when the user explicitly
  asks about it) — the agent needs to see it to correctly say "this is
  not authoritative", rather than pretend it doesn't exist.
- We do NOT filter out any status/audience here. Filtering happens in
  the agent's reasoning, not by hiding data from it — this is what lets
  us reliably detect prompt-injection content instead of silently
  dropping it.
"""
import pickle

import numpy as np
from sentence_transformers import SentenceTransformer

from src import config

_model = None  # loaded lazily, once


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def _status_boost(chunk: dict) -> float:
    boost = 0.0
    if chunk["status"] == "active":
        boost += 0.05
    elif chunk["status"] == "superseded":
        boost -= 0.05
    elif chunk["status"] == "draft":
        boost -= 0.10

    if chunk["policy_authority"] == "official":
        boost += 0.02
    elif chunk["policy_authority"] == "none":
        boost -= 0.05

    return boost


def load_index():
    with open(config.INDEX_FILE, "rb") as f:
        data = pickle.load(f)
    return data["chunks"], np.array(data["embeddings"])


def search(query: str, top_k: int = None, chunks=None, embeddings=None):
    """
    Returns a list of dicts: each chunk's metadata plus a 'score' field,
    sorted best-first. Caller decides what to do with status/authority —
    this function just ranks and returns everything it found.
    """
    top_k = top_k or config.TOP_K
    if chunks is None or embeddings is None:
        chunks, embeddings = load_index()

    model = _get_model()
    query_vec = model.encode([query], normalize_embeddings=True)[0]

    similarities = embeddings @ query_vec  # cosine similarity (vectors are normalized)

    scored = []
    for chunk, sim in zip(chunks, similarities):
        final_score = float(sim) + _status_boost(chunk)
        scored.append({**chunk, "similarity": float(sim), "score": final_score})

    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored[:top_k]


if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) or "return window"
    results = search(query)
    for r in results:
        print(f"[{r['score']:.3f}] {r['source_file']} :: {r['heading'] or '(intro)'} "
              f"(status={r['status']}, authority={r['policy_authority']})")
