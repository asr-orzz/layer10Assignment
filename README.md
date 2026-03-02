# Layer10 Take-Home: Grounded Memory Graph for GitHub Issues

This repo builds a grounded long-term memory from a public corpus (GitHub issues + comments for `psf/requests`). It downloads a small slice, extracts structured entities/claims with spaCy, deduplicates, stores them in SQLite, serves retrieval for questions, and emits an explorable graph HTML.

## Quickstart
1) Install deps (installs spaCy + en_core_web_sm model on first run):
   ```bash
   pip install --user -r requirements.txt
   ```
2) Run end-to-end (downloads 30 issues by default):
   ```bash
   python -m src.run_pipeline --repo psf/requests --max 30
   ```
   Optionally set `GITHUB_TOKEN` to avoid rate limits.
3) Retrieve grounded context packs:
   ```bash
   python -m src.retrieve "Which issues mention proxies?" --top 5
   ```
4) Visualize the memory graph (writes `outputs/graph.html`):
   ```bash
   python -m src.viz
   ```
   Open the HTML in a browser to click through nodes and edges.

Generated artifacts land in `data/raw/` (corpus), `outputs/memory.db` (SQLite graph), `outputs/graph.html` (visual), and `outputs/sample_context_packs.json` (example retrievals).

## Ontology (compact)
- **Entity**: `person`, `issue`, `component`, `concept` with aliases + props (stable ids for issues, GitHub login for people).
- **Evidence**: source_type (`issue|comment`), source_id, URL, snippet, char offsets, timestamp.
- **Claim**: `(subject_id, predicate, object, evidence_ids, confidence, validity, created_at, current)`.
- Core predicates: `created_by`, `status`, `assigned_to`, `has_label`, `mentions`, `comment_by`, `summary`.

## Pipeline
- **Ingestion** (`src/ingest.py`): pulls issues/comments via GitHub REST (`state=all`, PRs filtered) with light rate limiting; writes JSONL + metadata.
- **Extraction** (`src/extract.py`): spaCy NER + heuristics to ground claims; every claim links to evidence snippet + timestamp. Stable issue ids (`issue-{number}`) keep history safe.
- **Dedup/Canonicalize** (`src/dedupe.py`):
  - Entities: merge by login (people) and label (components); track alias map.
  - Claims: fuzzy text merge (SequenceMatcher) with confidence max + unioned evidences.
- **Store** (`src/graph_store.py`): SQLite tables for entities/evidence/claims; idempotent writes and full reset each pipeline run.
- **Retrieval** (`src/retrieve.py`): BM25 over claim text + evidence snippets ? ranked context packs with citations.
- **Visualization** (`src/viz.py`): networkx ? pyvis HTML; literal objects rendered as boxes; color-coded by entity type.

## How to adapt for Layer10 (email/Slack/Jira)
- **Ontology tweaks**: add `message`, `thread`, `channel`, `ticket`, `decision`, `owner` predicates; distinguish event time vs validity time; store redaction tombstones.
- **Extraction contract**: require offsets + message ids; validate schema with Pydantic; retry/repair on missing evidence; version prompts/models; backfill when schema changes.
- **Dedup strategy**: identity resolution via email + directory lookup; thread-level near-duplicate hashing (quote/forward handling); reversible merges with audit log.
- **Grounding & safety**: store source ACLs; retrieval filters by user permissions; keep deletion markers so memory can decay when sources vanish.
- **Ops & LTM**: incremental ingestion cursors, idempotent upserts, regression suites on sampled threads/issues; promote claims to durable memory only with multi-evidence support or human review hooks.

## Reproducibility
- Deterministic defaults (`psf/requests`, 30 issues). Change corpus with `--repo owner/name` and `--max N`.
- All outputs are file-based; reruns are safe (DB cleared then repopulated). No paid API dependencies.

## Example outputs
- `outputs/sample_context_packs.json` – two example questions with grounded snippets.
- `outputs/graph.html` – interactive graph; filters can be added by editing `src/viz.py`.

