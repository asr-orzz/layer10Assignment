import json
from pathlib import Path

from . import ingest
from .config import DB_PATH, MAX_ISSUES, RAW_DIR
from .dedupe import canonicalize_claims, dedupe_claims, dedupe_entities
from .extract import extract
from .graph_store import clear_db, init_db, persist_claims, persist_entities, persist_evidences


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.open("r", encoding="utf-8")]


def run(repo: str, max_issues: int = MAX_ISSUES, skip_download: bool = False):
    issues_path = RAW_DIR / "issues.jsonl"
    comments_path = RAW_DIR / "comments.jsonl"

    if not skip_download or not issues_path.exists():
        ingest.run(repo, max_issues)

    issues = _read_jsonl(issues_path)
    comments = _read_jsonl(comments_path) if comments_path.exists() else []

    entities, evidences, claims = extract(issues, comments)
    entities, entity_map = dedupe_entities(entities)
    claims = canonicalize_claims(claims, entity_map)
    claims, claim_map = dedupe_claims(claims)

    conn = init_db(DB_PATH)
    clear_db(conn)
    persist_entities(conn, entities)
    persist_evidences(conn, evidences)
    persist_claims(conn, claims)

    print(
        f"Ingested {len(issues)} issues | entities={len(entities)} evidences={len(evidences)} claims={len(claims)}"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="End-to-end pipeline: ingest -> extract -> dedupe -> persist")
    parser.add_argument("--repo", default=None, help="owner/repo (defaults to config.DEFAULT_REPO)")
    parser.add_argument("--max", type=int, default=MAX_ISSUES)
    parser.add_argument("--skip-download", action="store_true")
    args = parser.parse_args()
    repo = args.repo or ingest.DEFAULT_REPO
    run(repo=repo, max_issues=args.max, skip_download=args.skip_download)
