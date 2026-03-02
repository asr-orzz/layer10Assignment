from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = BASE_DIR / "outputs"
DB_PATH = OUTPUT_DIR / "memory.db"
GRAPH_HTML = OUTPUT_DIR / "graph.html"

DEFAULT_REPO = "psf/requests"
MAX_ISSUES = 40  # small sample for fast demo
REQUEST_TIMEOUT = 15

# Evidence snippet length for storage
SNIPPET_CHARS = 280

# Dedup thresholds
CLAIM_SIMILARITY_THRESHOLD = 0.82
