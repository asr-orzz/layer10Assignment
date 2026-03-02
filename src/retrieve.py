import argparse
import json
from collections import defaultdict
from typing import Dict, List

from rank_bm25 import BM25Okapi

from .config import DB_PATH
from .graph_store import init_db, load_claims, load_evidences, load_entities


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in text.split() if t]


def build_index(claims, evidences):
    evid_map = {ev.id: ev for ev in evidences}
    docs = []
    mapping = []
    for claim in claims:
        snippets = [evid_map[eid].snippet for eid in claim.evidence_ids if eid in evid_map]
        doc = " ".join([claim.predicate, claim.object] + snippets)
        docs.append(_tokenize(doc))
        mapping.append(claim)
    bm25 = BM25Okapi(docs)
    return bm25, mapping, evid_map


def retrieve(question: str, top_k: int = 5):
    conn = init_db(DB_PATH)
    claims = load_claims(conn)
    evidences = load_evidences(conn)
    entities = {e.id: e for e in load_entities(conn)}

    bm25, mapping, evid_map = build_index(claims, evidences)
    scores = bm25.get_scores(_tokenize(question))
    ranked = sorted(zip(mapping, scores), key=lambda x: x[1], reverse=True)[:top_k]

    packs = []
    for claim, score in ranked:
        evid_items = [evid_map[eid] for eid in claim.evidence_ids if eid in evid_map]
        subject = entities.get(claim.subject_id)
        packs.append(
            {
                "claim_id": claim.id,
                "score": round(float(score), 3),
                "subject": subject.name if subject else claim.subject_id,
                "predicate": claim.predicate,
                "object": claim.object,
                "evidence": [
                    {
                        "id": ev.id,
                        "url": ev.url,
                        "snippet": ev.snippet,
                        "timestamp": ev.timestamp,
                    }
                    for ev in evid_items
                ],
            }
        )
    return packs


def main():
    parser = argparse.ArgumentParser(description="Retrieve grounded context from memory graph")
    parser.add_argument("question", help="free-form question")
    parser.add_argument("--top", type=int, default=5, help="number of results")
    args = parser.parse_args()
    results = retrieve(args.question, args.top)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
