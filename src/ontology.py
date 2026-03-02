from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Evidence:
    id: str
    source_type: str  # issue or comment
    source_id: str
    url: str
    snippet: str
    offsets: Tuple[int, int]
    timestamp: str


@dataclass
class Entity:
    id: str
    type: str
    name: str
    aliases: List[str] = field(default_factory=list)
    props: Dict[str, str] = field(default_factory=dict)


@dataclass
class Claim:
    id: str
    subject_id: str
    predicate: str
    object: str
    evidence_ids: List[str]
    confidence: float
    validity: str  # current | historical
    created_at: Optional[str] = None
    current: bool = True
