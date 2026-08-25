"""
Central place for all settings. Every other file imports from here
instead of reading environment variables directly — makes it easy to
see every knob in one place, and easy to test with different settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables, if present

# --- Paths ---
ROOT_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = ROOT_DIR / "knowledge-base"
ORDERS_FILE = ROOT_DIR / "data" / "orders.json"
INDEX_FILE = ROOT_DIR / "data" / "index.pkl"
LOGS_DIR = ROOT_DIR / "logs"

# --- Model settings ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")  # 'anthropic' | 'google' | 'mock'

# --- Retrieval settings ---
TOP_K = int(os.getenv("TOP_K", "15"))
CHUNK_MAX_CHARS = 900  # roughly one policy section per chunk
