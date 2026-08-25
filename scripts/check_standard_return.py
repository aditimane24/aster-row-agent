from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import retriever
import re

query = "How long does a regular customer have to return an unused backpack?"
from src import config
results = retriever.search(query, top_k=config.TOP_K)
combined_text = "\n".join(r['text'] for r in results)

def normalize(s: str) -> str:
    s2 = re.sub(r"[-_/,]", " ", s)
    s2 = re.sub(r"[^0-9a-zA-Z\s]", " ", s2)
    return re.sub(r"\s+", " ", s2).strip().lower()

combined_norm = normalize(combined_text)
print('COMBINED_NORM:\n', combined_norm[:1000])

phrase1 = '30 calendar days'
phrase2 = 'delivery'

print('\nToken match 1:', phrase1, normalize(phrase1) in combined_norm)
print('Token match 2:', phrase2, normalize(phrase2) in combined_norm)

# show top files
print('\nTop files:')
for r in results:
    print(f"{r['source_file']} :: {r['heading']} (status={r['status']}) | score={r['score']:.4f}")

# show if forbidden phrase exists and which file contains it
forbidden_phrase = 'free return label'
for r in results:
    if forbidden_phrase in r['text'].lower():
        print('\nFound forbidden phrase in:', r['source_file'], r['heading'])
