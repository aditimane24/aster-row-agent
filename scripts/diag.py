from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import retriever, order_tool
import json

def diag(q):
    print('Query:', q)
    res = retriever.search(q, top_k=6)
    for r in res:
        print(f" {r['score']:.4f} | {r['source_file']} :: {r['heading'] or '(intro)'} (status={r['status']})")
    print()

# standard-return-window
diag('How long does a regular customer have to return an unused backpack?')
# order data privacy lookup
print('ORD-1007 lookup:')
print(json.dumps(order_tool.lookup_order('ORD-1007'), indent=2))
