from difflib import SequenceMatcher
from typing import Dict, List, Tuple

from .config import CLAIM_SIMILARITY_THRESHOLD
from .ontology import Claim, Entity


def dedupe_entities(entities: List[Entity]) -> Tuple[List[Entity], Dict[str, str]]:
    canonical: Dict[str, Entity] = {}
    alias_map: Dict[str, str] = {}

    for ent in entities:
        if ent.type == "person":
            key = ent.name.lower()
        elif ent.type == "component":
            key = ent.name.lower()
        else:
            key = ent.id

        if key in canonical:
            alias_map[ent.id] = canonical[key].id
            # stash alias
            if ent.name not in canonical[key].aliases:
                canonical[key].aliases.append(ent.name)
        else:
            canonical[key] = ent
            alias_map[ent.id] = ent.id
    return list(canonical.values()), alias_map


def _claim_text(claim: Claim) -> str:
    return f"{claim.subject_id}|{claim.predicate}|{claim.object}".lower()


def dedupe_claims(claims: List[Claim]) -> Tuple[List[Claim], Dict[str, str]]:
    canonical: List[Claim] = []
    mapping: Dict[str, str] = {}

    for claim in claims:
        normalized = _claim_text(claim)
        found = None
        for existing in canonical:
            score = SequenceMatcher(None, normalized, _claim_text(existing)).ratio()
            if score >= CLAIM_SIMILARITY_THRESHOLD:
                found = existing
                break
        if found:
            # merge evidence and boost confidence
            for evid in claim.evidence_ids:
                if evid not in found.evidence_ids:
                    found.evidence_ids.append(evid)
            found.confidence = max(found.confidence, claim.confidence)
            mapping[claim.id] = found.id
        else:
            canonical.append(claim)
            mapping[claim.id] = claim.id

    return canonical, mapping


def canonicalize_claims(claims: List[Claim], entity_map: Dict[str, str]) -> List[Claim]:
    adjusted: List[Claim] = []
    for claim in claims:
        claim.subject_id = entity_map.get(claim.subject_id, claim.subject_id)
        adjusted.append(claim)
    return adjusted
