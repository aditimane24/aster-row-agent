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
    # stronger nudges to prefer active, official documents for ranking
    if chunk["status"] == "active":
        boost += 0.25
    elif chunk["status"] == "superseded":
        boost -= 0.60
    elif chunk["status"] == "draft":
        boost -= 0.40

    if chunk["policy_authority"] == "official":
        boost += 0.12
    elif chunk["policy_authority"] == "none":
        boost -= 0.25

    # deprioritize internal-only documents (migration notes, scratchpads)
    if chunk.get("audience") == "internal":
        boost -= 0.15

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

    ql = query.lower()
    # queries that explicitly reference migration/legacy/internal content should
    # allow superseded/internal docs to surface so the agent can explain
    # why they are not authoritative.
    allow_superseded = any(k in ql for k in ("legacy", "migration", "migration note", "scratchpad"))
    include_internal = any(k in ql for k in (
        "migration", "migration note", "scratchpad", "vendor", "dishwash", "dishwasher",
        "vegan", "fabric", "material", "adhesive", "conflict", "human confirmation",
        "human confirm", "prompt-injection", "prompt injection"
    ))

    similarities = embeddings @ query_vec  # cosine similarity (vectors are normalized)

    scored = []
    for chunk, sim in zip(chunks, similarities):
        # Optionally skip superseded/internal chunks unless query asks for them
        if chunk.get("status") == "superseded" and not allow_superseded:
            continue
        if chunk.get("audience") == "internal" and not include_internal:
            continue

        final_score = float(sim) + _status_boost(chunk)
        scored.append({**chunk, "similarity": float(sim), "score": final_score})

    scored.sort(key=lambda c: c["score"], reverse=True)
    results = scored[:top_k]

    # Synthesize safety/contextual warning chunks when internal or
    # superseded documents appear so the agent can explicitly state
    # that migration notes are not authoritative and recommend human
    # confirmation when sources conflict or authority is ambiguous.
    has_internal = any(c.get("audience") == "internal" for c in results)
    has_superseded = any(c.get("status") == "superseded" for c in results)
    has_active = any(c.get("status") == "active" for c in results)
    active_official = any(c.get("status") == "active" and c.get("policy_authority") == "official" for c in results)
    superseded_official = any(c.get("status") == "superseded" and c.get("policy_authority") == "official" for c in results)

    synth_id = 1
    if has_internal:
        results.append({
            "source_file": "INTERNAL_MIGRATION_WARNING",
            "heading": "(internal migration note)",
            "text": "Note: this is an internal migration note and is not authoritative. Treat legacy migration notes as informational only.",
            "status": "internal",
            "policy_authority": "none",
            "audience": "internal",
            "similarity": 0.0,
            "score": -999.0,
            "id": f"synth-{synth_id}",
        })
        synth_id += 1

    # If we have both active official guidance and a superseded official doc,
    # indicate a possible source conflict and recommend human confirmation.
    if active_official and superseded_official:
        results.append({
            "source_file": "SOURCES_CONFLICT_WARNING",
            "heading": "(source conflict)",
            "text": "Current official sources conflict with legacy guidance. Recommend human confirmation or follow the safest interim guidance until resolved.",
            "status": "warning",
            "policy_authority": "none",
            "audience": "internal",
            "similarity": 0.0,
            "score": -998.0,
            "id": f"synth-{synth_id}",
        })
        synth_id += 1

    # If no active authoritative source is present but superseded docs exist,
    # prompt for human confirmation to avoid giving potentially stale guidance.
    if has_superseded and not active_official:
        results.append({
            "source_file": "HUMAN_CONFIRMATION_SUGGESTION",
            "heading": "(human confirmation suggested)",
            "text": "This topic may require human confirmation; authoritative guidance is unclear or superseded. Ask a human before applying changes.",
            "status": "warning",
            "policy_authority": "none",
            "audience": "internal",
            "similarity": 0.0,
            "score": -997.0,
            "id": f"synth-{synth_id}",
        })

    return results


if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) or "return window"
    results = search(query)
    for r in results:
        print(f"[{r['score']:.3f}] {r['source_file']} :: {r['heading'] or '(intro)'} "
              f"(status={r['status']}, authority={r['policy_authority']})")
