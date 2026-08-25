import shutil
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
DIST = os.path.join(ROOT, 'dist')
if not os.path.exists(DIST):
    os.makedirs(DIST)

include = [
    'README.md',
    'deliverables/reviewer_note.md',
    'evaluation/results.json',
    'evaluation/mock_live_results.json',
    'requirements.txt',
    'scripts/run_evaluation.py',
    'scripts/mock_evaluation.py',
]

# include directories
dirs = ['src', 'tests', 'knowledge-base']

zip_base = os.path.join(DIST, 'aster-row-agent-release')
shutil.make_archive(zip_base, 'zip', ROOT)
print('Created', zip_base + '.zip')
