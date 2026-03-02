import hashlib
import re
from typing import Dict, List, Tuple

import spacy
from spacy.cli import download as spacy_download

from .config import SNIPPET_CHARS
from .ontology import Claim, Entity, Evidence


_DEF_MODEL = "en_core_web_sm"


def load_nlp():
    try:
        return spacy.load(_DEF_MODEL)
    except OSError:
        spacy_download(_DEF_MODEL)
        return spacy.load(_DEF_MODEL)


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def _snippet(text: str) -> Tuple[str, Tuple[int, int]]:
    normalized = (text or "").strip().replace("\n", " ")
    snippet = normalized[:SNIPPET_CHARS]
    return snippet, (0, min(len(snippet), len(normalized)))


def _entity_id(kind: str, name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_\-]+", "-", name.strip().lower())
    return f"{kind}-{safe}"[:80]


def extract(issues: List[Dict], comments: List[Dict]):
    nlp = load_nlp()
    entities: Dict[str, Entity] = {}
    evidences: Dict[str, Evidence] = {}
    claims: Dict[str, Claim] = {}

    def ensure_entity(kind: str, name: str, props=None, eid=None):
        entity_id = eid or _entity_id(kind, name)
        if entity_id not in entities:
            entities[entity_id] = Entity(id=entity_id, type=kind, name=name, props=props or {})
        else:
            if props:
                entities[entity_id].props.update(props)
        return entity_id

    def add_claim(subject_id: str, predicate: str, obj: str, evidence_id: str, confidence=0.75, validity="current", created_at=None):
        key = _hash(f"{subject_id}|{predicate}|{obj}")
        if key in claims:
            claim = claims[key]
            if evidence_id not in claim.evidence_ids:
                claim.evidence_ids.append(evidence_id)
            claim.confidence = max(claim.confidence, confidence)
        else:
            claims[key] = Claim(
                id=key,
                subject_id=subject_id,
                predicate=predicate,
                object=obj,
                evidence_ids=[evidence_id],
                confidence=confidence,
                validity=validity,
                created_at=created_at,
                current=True,
            )
        return key

    # Process issues
    for issue in issues:
        num = issue.get("number")
        title = issue.get("title") or "(no title)"
        body = issue.get("body") or ""
        issue_id = f"issue-{num}"
        ensure_entity("issue", f"#{num}: {title[:60]}", props={"url": issue.get("html_url"), "number": num, "stable_id": issue_id}, eid=issue_id)

        # author
        user = issue.get("user", {})
        login = user.get("login", "unknown")
        person_id = ensure_entity("person", login, props={"user_id": user.get("id")})

        snippet, offsets = _snippet(body or title)
        ev_id = f"ev-issue-{num}"
        evidences[ev_id] = Evidence(
            id=ev_id,
            source_type="issue",
            source_id=str(num),
            url=issue.get("html_url", ""),
            snippet=snippet,
            offsets=offsets,
            timestamp=issue.get("created_at", ""),
        )

        add_claim(issue_id, "created_by", person_id, ev_id, confidence=0.7, created_at=issue.get("created_at"))
        add_claim(issue_id, "status", issue.get("state", "unknown"), ev_id, confidence=0.8)
        add_claim(issue_id, "summary", title, ev_id, confidence=0.9)

        if issue.get("assignee"):
            assignee = issue["assignee"].get("login", "")
            if assignee:
                assignee_id = ensure_entity("person", assignee)
                add_claim(issue_id, "assigned_to", assignee_id, ev_id, confidence=0.78)

        for label in issue.get("labels", []):
            label_name = label.get("name")
            if not label_name:
                continue
            component_id = ensure_entity("component", label_name)
            add_claim(issue_id, "has_label", component_id, ev_id, confidence=0.72)

        # Named entity hints from body
        if body:
            doc = nlp(body)
            for ent in doc.ents:
                if ent.label_ in {"ORG", "PRODUCT", "GPE"}:
                    concept_id = ensure_entity("concept", ent.text)
                    add_claim(issue_id, "mentions", concept_id, ev_id, confidence=0.6)

    # Process comments
    for comment in comments:
        issue_number = comment.get("issue_number")
        if issue_number is None:
            continue
        issue_entity_id = f"issue-{issue_number}"
        if issue_entity_id not in entities:
            issue_entity_id = ensure_entity("issue", f"#{issue_number}", eid=issue_entity_id)

        user = comment.get("user", {})
        login = user.get("login", "unknown")
        person_id = ensure_entity("person", login, props={"user_id": user.get("id")})

        body = comment.get("body") or ""
        snippet, offsets = _snippet(body)
        ev_id = f"ev-comment-{comment.get('id')}"
        evidences[ev_id] = Evidence(
            id=ev_id,
            source_type="comment",
            source_id=str(comment.get("id")),
            url=comment.get("html_url", ""),
            snippet=snippet,
            offsets=offsets,
            timestamp=comment.get("created_at", ""),
        )

        add_claim(issue_entity_id, "comment_by", person_id, ev_id, confidence=0.7, created_at=comment.get("created_at"))

        doc = nlp(body)
        for ent in doc.ents:
            if ent.label_ in {"ORG", "PRODUCT", "GPE"}:
                concept_id = ensure_entity("concept", ent.text)
                add_claim(issue_entity_id, "mentions", concept_id, ev_id, confidence=0.55)

    return list(entities.values()), list(evidences.values()), list(claims.values())


if __name__ == "__main__":
    import json
    from pathlib import Path

    from .config import RAW_DIR

    issues_path = RAW_DIR / "issues.jsonl"
    comments_path = RAW_DIR / "comments.jsonl"
    issues = [json.loads(line) for line in issues_path.open("r", encoding="utf-8")]
    comments = [json.loads(line) for line in comments_path.open("r", encoding="utf-8")]
    ents, evs, claims = extract(issues, comments)
    print(f"entities={len(ents)}, evidences={len(evs)}, claims={len(claims)}")
