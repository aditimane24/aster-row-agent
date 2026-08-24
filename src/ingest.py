"""
Turns the markdown files in knowledge-base/ into a searchable index.

Design choices (so you can explain these in an interview):
- Chunking is by ## heading, not fixed character count. Policy docs are
  organized in short, self-contained sections ("Return window",
  "Return shipping and refunds", ...) — splitting on headings keeps each
  chunk semantically whole and lets us cite "filename + heading" exactly
  as the assignment asks for.
- Front matter (status, policy_authority, effective_date, supersedes...)
  is parsed and attached to EVERY chunk from that file, not thrown away.
  This is what lets the retriever later prefer active/official docs over
  superseded or draft ones.
- Embeddings are computed locally with sentence-transformers — free,
  no extra API key, fine for a knowledge base this small.
"""
import json
import pickle
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from src import config


@dataclass
class Chunk:
    chunk_id: str          # e.g. "01-returns-policy-current.md::Standard return window"
    source_file: str       # "01-returns-policy-current.md"
    document_id: str       # from front matter, e.g. "RET-2026-01"
    title: str             # document title from front matter
    heading: str           # the ## heading this chunk falls under (or "" for intro text)
    text: str              # the actual chunk content the model will read
    status: str            # active / superseded / draft
    policy_authority: str  # official / none
    audience: str          # customer / internal
    effective_date: str
    supersedes: str
    superseded_by: str


def parse_front_matter(raw_text: str) -> tuple[dict, str]:
    """
    Splits a markdown file into (front_matter_dict, body_text).
    Front matter here is simple flat "key: value" pairs between --- lines,
    so we parse it by hand instead of pulling in a YAML library.
    """
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw_text, re.DOTALL)
    if not match:
        return {}, raw_text

    fm_block, body = match.groups()
    meta = {}
    for line in fm_block.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, body


def chunk_body(body: str) -> list[tuple[str, str]]:
    """
    Splits body text on '## Heading' lines.
    Returns a list of (heading, text) tuples. Any text before the first
    '##' (usually the '# Title' line and a short intro) becomes one
    chunk with heading="" so it isn't lost.
    """
    parts = re.split(r"\n(?=## )", body.strip())
    chunks = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        heading_match = re.match(r"^## (.+)", part)
        heading = heading_match.group(1).strip() if heading_match else ""
        chunks.append((heading, part))
    return chunks


def build_chunks_for_file(path: Path) -> list[Chunk]:
    raw = path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(raw)

    chunks = []
    for heading, text in chunk_body(body):
        chunk_id = f"{path.name}::{heading or 'intro'}"
        chunks.append(Chunk(
            chunk_id=chunk_id,
            source_file=path.name,
            document_id=meta.get("document_id", ""),
            title=meta.get("title", ""),
            heading=heading,
            text=text,
            status=meta.get("status", "unknown"),
            policy_authority=meta.get("policy_authority", "unknown"),
            audience=meta.get("audience", "unknown"),
            effective_date=meta.get("effective_date", ""),
            supersedes=meta.get("supersedes", ""),
            superseded_by=meta.get("superseded_by", ""),
        ))
    return chunks


def build_index():
    all_chunks: list[Chunk] = []
    for path in sorted(config.KNOWLEDGE_BASE_DIR.glob("*.md")):
        all_chunks.extend(build_chunks_for_file(path))

    print(f"Parsed {len(all_chunks)} chunks from "
          f"{len(list(config.KNOWLEDGE_BASE_DIR.glob('*.md')))} files.")

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(config.EMBEDDING_MODEL)
    texts = [c.text for c in all_chunks]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    with open(config.INDEX_FILE, "wb") as f:
        pickle.dump({
            "chunks": [asdict(c) for c in all_chunks],
            "embeddings": embeddings,
        }, f)

    print(f"Saved index with {len(all_chunks)} chunks to {config.INDEX_FILE}")


if __name__ == "__main__":
    build_index()
