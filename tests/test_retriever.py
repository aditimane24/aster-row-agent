from src import retriever


def test_prefer_active_official_document():
    results = retriever.search("return window for a regular customer", top_k=5)
    files = [r['source_file'] for r in results]
    assert "01-returns-policy-current.md" in files
