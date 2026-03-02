import json
import os
import time
from pathlib import Path
from typing import Dict, Iterable, List

import requests

from .config import DEFAULT_REPO, MAX_ISSUES, RAW_DIR, REQUEST_TIMEOUT


def _write_jsonl(path: Path, records: Iterable[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _github_headers() -> Dict[str, str]:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_issues(repo: str = DEFAULT_REPO, max_issues: int = MAX_ISSUES) -> List[Dict]:
    issues: List[Dict] = []
    page = 1
    per_page = min(100, max_issues)
    headers = _github_headers()
    while len(issues) < max_issues:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/issues",
            params={"state": "all", "per_page": per_page, "page": page, "direction": "desc"},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        batch = resp.json()
        # filter out PRs
        batch = [item for item in batch if "pull_request" not in item]
        if not batch:
            break
        issues.extend(batch)
        page += 1
        time.sleep(0.2)  # gentle on API
    return issues[:max_issues]


def fetch_comments(issues: List[Dict]) -> List[Dict]:
    comments: List[Dict] = []
    headers = _github_headers()
    for issue in issues:
        comment_count = issue.get("comments", 0)
        if not comment_count:
            continue
        url = issue.get("comments_url")
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        items = resp.json()
        # add issue metadata to comment for easier downstream joins
        for item in items:
            item["issue_number"] = issue.get("number")
        comments.extend(items)
        time.sleep(0.15)
    return comments


def run(repo: str = DEFAULT_REPO, max_issues: int = MAX_ISSUES) -> None:
    issues = fetch_issues(repo, max_issues)
    comments = fetch_comments(issues)
    _write_jsonl(RAW_DIR / "issues.jsonl", issues)
    _write_jsonl(RAW_DIR / "comments.jsonl", comments)
    meta = {
        "repo": repo,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "issue_count": len(issues),
        "comment_count": len(comments),
    }
    (RAW_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Fetched {len(issues)} issues and {len(comments)} comments from {repo}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Download GitHub issues + comments as corpus")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="owner/repo to download")
    parser.add_argument("--max", type=int, default=MAX_ISSUES, help="max issues to fetch")
    args = parser.parse_args()
    run(args.repo, args.max)
