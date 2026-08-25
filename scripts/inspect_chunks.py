from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import retriever
from src import config

q = "How long does a regular customer have to return an unused backpack?"
res = retriever.search(q, top_k=config.TOP_K)
for r in res:
    text = r['text'].lower()
    print('FILE:', r['source_file'], 'HEADING:', r['heading'])
    print(' contains "label"?', 'label' in text)
    print(' contains "free" and "return"?', ('free' in text) and ('return' in text))
    print('--- snippet ---')
    print(text[:400])
    print('\n')
