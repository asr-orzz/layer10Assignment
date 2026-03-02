import json
import sqlite3
from pathlib import Path
from typing import Iterable, List

from .config import DB_PATH
from .ontology import Claim, Entity, Evidence


def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            type TEXT,
            name TEXT,
            aliases TEXT,
            props TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS evidences (
            id TEXT PRIMARY KEY,
            source_type TEXT,
            source_id TEXT,
            url TEXT,
            snippet TEXT,
            offsets TEXT,
            timestamp TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS claims (
            id TEXT PRIMARY KEY,
            subject_id TEXT,
            predicate TEXT,
            object TEXT,
            evidence_ids TEXT,
            confidence REAL,
            validity TEXT,
            created_at TEXT,
            current INTEGER
        )
        """
    )
    conn.commit()
    return conn


def clear_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM entities")
    cur.execute("DELETE FROM evidences")
    cur.execute("DELETE FROM claims")
    conn.commit()


def persist_entities(conn: sqlite3.Connection, entities: Iterable[Entity]) -> None:
    cur = conn.cursor()
    cur.executemany(
        "INSERT OR REPLACE INTO entities VALUES (?, ?, ?, ?, ?)",
        [
            (
                e.id,
                e.type,
                e.name,
                json.dumps(e.aliases, ensure_ascii=False),
                json.dumps(e.props, ensure_ascii=False),
            )
            for e in entities
        ],
    )
    conn.commit()


def persist_evidences(conn: sqlite3.Connection, evidences: Iterable[Evidence]) -> None:
    cur = conn.cursor()
    cur.executemany(
        "INSERT OR REPLACE INTO evidences VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (
                ev.id,
                ev.source_type,
                ev.source_id,
                ev.url,
                ev.snippet,
                json.dumps(ev.offsets),
                ev.timestamp,
            )
            for ev in evidences
        ],
    )
    conn.commit()


def persist_claims(conn: sqlite3.Connection, claims: Iterable[Claim]) -> None:
    cur = conn.cursor()
    cur.executemany(
        "INSERT OR REPLACE INTO claims VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                c.id,
                c.subject_id,
                c.predicate,
                c.object,
                json.dumps(c.evidence_ids, ensure_ascii=False),
                c.confidence,
                c.validity,
                c.created_at,
                1 if c.current else 0,
            )
            for c in claims
        ],
    )
    conn.commit()


def load_claims(conn: sqlite3.Connection) -> List[Claim]:
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM claims").fetchall()
    claims = []
    for row in rows:
        claims.append(
            Claim(
                id=row[0],
                subject_id=row[1],
                predicate=row[2],
                object=row[3],
                evidence_ids=json.loads(row[4]),
                confidence=row[5],
                validity=row[6],
                created_at=row[7],
                current=bool(row[8]),
            )
        )
    return claims


def load_evidences(conn: sqlite3.Connection) -> List[Evidence]:
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM evidences").fetchall()
    evidences = []
    for row in rows:
        evidences.append(
            Evidence(
                id=row[0],
                source_type=row[1],
                source_id=row[2],
                url=row[3],
                snippet=row[4],
                offsets=tuple(json.loads(row[5])),
                timestamp=row[6],
            )
        )
    return evidences


def load_entities(conn: sqlite3.Connection) -> List[Entity]:
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM entities").fetchall()
    ents = []
    for row in rows:
        ents.append(
            Entity(
                id=row[0],
                type=row[1],
                name=row[2],
                aliases=json.loads(row[3]),
                props=json.loads(row[4]),
            )
        )
    return ents
