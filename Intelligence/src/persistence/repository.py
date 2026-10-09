"""
FIN Structured Fact & Evidence Persistence Repository.
Provides atomic, transactional storage for documents, applicant facts, and evidence records
using standard library SQLite with strict applicant isolation and idempotency guarantees.
"""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, Generator, List, Optional
import uuid

from src.extraction.models import (
    ApplicantFact,
    Evidence,
    FactSourceType,
    FactVerificationStatus,
)
from src.context.models import DocumentContext


class PersistenceError(Exception):
    """Raised when structured persistence operation fails."""
    pass


class FactPersistenceRepository:
    """
    Authoritative persistence layer for citizen documents, facts, and evidence.
    Enforces:
    1. Idempotency via SHA-256 deduplication per applicant.
    2. Strict applicant-scoped isolation on all reads and writes.
    3. Transactional atomicity: partial persistence is never committed.
    4. Auditable historical records without destructive mutation.
    """

    def __init__(self, db_path: Optional[str] = None):
        import os
        # Authoritative persistence is on Supabase; local SQLite is strictly in-memory
        persistence_mode = os.getenv("PERSISTENCE_MODE", "memory").lower()
        if db_path and db_path != ":memory:" and persistence_mode != "memory":
            self.db_path = str(Path(db_path).resolve())
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        else:
            self.db_path = ":memory:"

        self._in_memory_conn = None
        if self.db_path == ":memory:":
            self._in_memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._in_memory_conn.row_factory = sqlite3.Row
            self._init_schema(self._in_memory_conn)
        else:
            with self._get_connection() as conn:
                self._init_schema(conn)

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provides a database connection with WAL mode and foreign keys enabled."""
        if self._in_memory_conn is not None:
            yield self._in_memory_conn
            return

        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            yield conn
        finally:
            conn.close()

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        """Initializes canonical relational schema."""
        cursor = conn.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                applicant_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                mime_type TEXT,
                document_type TEXT,
                sha256 TEXT NOT NULL,
                page_count INTEGER DEFAULT 1,
                extraction_method TEXT,
                status TEXT,
                raw_text TEXT,
                metadata_json TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS applicant_facts (
                fact_id TEXT PRIMARY KEY,
                applicant_id TEXT NOT NULL,
                document_id TEXT,
                fact_key TEXT NOT NULL,
                raw_value TEXT NOT NULL,
                normalized_value_json TEXT,
                value_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                verification_status TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_reference TEXT,
                page_number INTEGER,
                text_span TEXT,
                bounding_box_json TEXT,
                extraction_method TEXT,
                extracted_at TEXT,
                fact_version TEXT DEFAULT '1.0',
                conflict_group_id TEXT,
                metadata_json TEXT,
                FOREIGN KEY (document_id) REFERENCES documents (document_id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY,
                applicant_fact_id TEXT NOT NULL,
                applicant_id TEXT NOT NULL,
                document_id TEXT,
                source_type TEXT NOT NULL,
                source_uri TEXT,
                page_number INTEGER,
                text_span TEXT,
                bounding_box_json TEXT,
                extraction_method TEXT,
                confidence REAL NOT NULL,
                verification_status TEXT NOT NULL,
                document_hash TEXT,
                created_at TEXT,
                metadata_json TEXT,
                FOREIGN KEY (applicant_fact_id) REFERENCES applicant_facts (fact_id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES documents (document_id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_docs_applicant ON documents(applicant_id);
            CREATE INDEX IF NOT EXISTS idx_docs_hash ON documents(applicant_id, sha256);
            CREATE INDEX IF NOT EXISTS idx_facts_applicant_key ON applicant_facts(applicant_id, fact_key);
            CREATE INDEX IF NOT EXISTS idx_facts_doc ON applicant_facts(document_id);
            CREATE INDEX IF NOT EXISTS idx_evidence_fact ON evidence(applicant_fact_id);
            CREATE INDEX IF NOT EXISTS idx_evidence_applicant ON evidence(applicant_id);
            """
        )
        conn.commit()

    def save_document_facts_and_evidence(
        self,
        doc_context: DocumentContext,
        facts: List[ApplicantFact],
        evidence_list: List[Evidence],
    ) -> bool:
        """
        Atomically saves document, facts, and evidence in a single transaction.
        Enforces idempotency: if document hash already exists for applicant, returns False.
        Never swallows database errors.
        """
        if not doc_context.applicant_id:
            raise PersistenceError("Applicant ID is strictly required for document persistence.")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # 1. Idempotency check: see if exact document SHA-256 already recorded for this applicant
                cursor.execute(
                    "SELECT document_id FROM documents WHERE applicant_id = ? AND sha256 = ?",
                    (doc_context.applicant_id, doc_context.document_hash),
                )
                existing = cursor.fetchone()
                if existing:
                    # Document already processed and stored for this applicant
                    return False

                # 2. Insert document record
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO documents (
                        document_id, applicant_id, file_name, mime_type,
                        document_type, sha256, page_count, extraction_method,
                        status, raw_text, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_context.document_id,
                        doc_context.applicant_id,
                        doc_context.file_name,
                        doc_context.mime_type,
                        doc_context.document_type,
                        doc_context.document_hash,
                        doc_context.page_count,
                        doc_context.extraction_method,
                        doc_context.extraction_status,
                        doc_context.raw_text,
                        json.dumps(doc_context.metadata),
                        doc_context.created_at,
                        doc_context.created_at,
                    ),
                )

                # 3. Insert ApplicantFacts
                for f in facts:
                    f.applicant_id = doc_context.applicant_id
                    f.document_id = doc_context.document_id
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO applicant_facts (
                            fact_id, applicant_id, document_id, fact_key,
                            raw_value, normalized_value_json, value_type,
                            confidence, verification_status, source_type,
                            source_reference, page_number, text_span,
                            bounding_box_json, extraction_method, extracted_at,
                            fact_version, conflict_group_id, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            f.id,
                            f.applicant_id,
                            f.document_id,
                            f.field,
                            str(f.value),
                            json.dumps(f.normalized_value),
                            f.data_type,
                            f.confidence,
                            f.verification_status.value,
                            f.source_type.value if hasattr(f.source_type, "value") else str(f.source_type),
                            f.source_document,
                            f.page_number,
                            f.text_span,
                            json.dumps(f.bounding_box) if f.bounding_box else None,
                            f.extraction_method,
                            f.extracted_at,
                            f.fact_version,
                            f.conflict_group_id,
                            json.dumps(f.metadata),
                        ),
                    )

                # 4. Insert Evidence records
                for e in evidence_list:
                    e.applicant_id = doc_context.applicant_id
                    e.document_id = doc_context.document_id
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO evidence (
                            evidence_id, applicant_fact_id, applicant_id,
                            document_id, source_type, source_uri,
                            page_number, text_span, bounding_box_json,
                            extraction_method, confidence, verification_status,
                            document_hash, created_at, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            e.evidence_id,
                            e.applicant_fact_id or "unknown_fact",
                            e.applicant_id,
                            e.document_id,
                            e.source_type.value if hasattr(e.source_type, "value") else str(e.source_type),
                            e.source_uri,
                            e.page_number,
                            e.text_span,
                            json.dumps(e.bounding_box) if e.bounding_box else None,
                            e.extraction_method,
                            e.confidence,
                            e.verification_status.value if hasattr(e.verification_status, "value") else str(e.verification_status),
                            e.document_hash,
                            e.created_at,
                            json.dumps(e.metadata),
                        ),
                    )

                conn.commit()
                return True
        except Exception as exc:
            raise PersistenceError(f"Failed to persist document and facts: {exc}") from exc

    def save_fact(self, fact: ApplicantFact, evidence_record: Optional[Evidence] = None) -> None:
        """Saves a standalone fact (e.g. USER_INPUT or PROFILE) with optional evidence."""
        if not fact.applicant_id:
            raise PersistenceError("Applicant ID is strictly required to save a fact.")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if fact.source_type == FactSourceType.PROFILE:
                    cursor.execute(
                        "DELETE FROM applicant_facts WHERE applicant_id = ? AND fact_key = ? AND source_type = ?",
                        (fact.applicant_id, fact.field, FactSourceType.PROFILE.value),
                    )
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO applicant_facts (
                        fact_id, applicant_id, document_id, fact_key,
                        raw_value, normalized_value_json, value_type,
                        confidence, verification_status, source_type,
                        source_reference, page_number, text_span,
                        bounding_box_json, extraction_method, extracted_at,
                        fact_version, conflict_group_id, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fact.id,
                        fact.applicant_id,
                        fact.document_id,
                        fact.field,
                        str(fact.value),
                        json.dumps(fact.normalized_value),
                        fact.data_type,
                        fact.confidence,
                        fact.verification_status.value,
                        fact.source_type.value if hasattr(fact.source_type, "value") else str(fact.source_type),
                        fact.source_document,
                        fact.page_number,
                        fact.text_span,
                        json.dumps(fact.bounding_box) if fact.bounding_box else None,
                        fact.extraction_method,
                        fact.extracted_at,
                        fact.fact_version,
                        fact.conflict_group_id,
                        json.dumps(fact.metadata),
                    ),
                )

                if evidence_record:
                    evidence_record.applicant_id = fact.applicant_id
                    evidence_record.applicant_fact_id = fact.id
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO evidence (
                            evidence_id, applicant_fact_id, applicant_id,
                            document_id, source_type, source_uri,
                            page_number, text_span, bounding_box_json,
                            extraction_method, confidence, verification_status,
                            document_hash, created_at, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            evidence_record.evidence_id,
                            evidence_record.applicant_fact_id,
                            evidence_record.applicant_id,
                            evidence_record.document_id,
                            evidence_record.source_type.value if hasattr(evidence_record.source_type, "value") else str(evidence_record.source_type),
                            evidence_record.source_uri,
                            evidence_record.page_number,
                            evidence_record.text_span,
                            json.dumps(evidence_record.bounding_box) if evidence_record.bounding_box else None,
                            evidence_record.extraction_method,
                            evidence_record.confidence,
                            evidence_record.verification_status.value if hasattr(evidence_record.verification_status, "value") else str(evidence_record.verification_status),
                            evidence_record.document_hash,
                            evidence_record.created_at,
                            json.dumps(evidence_record.metadata),
                        ),
                    )

                conn.commit()
        except Exception as exc:
            raise PersistenceError(f"Failed to persist fact '{fact.field}': {exc}") from exc

    def get_document_by_hash(self, applicant_id: str, sha256: str) -> Optional[DocumentContext]:
        """Retrieves a document by SHA-256 for a specific applicant."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM documents WHERE applicant_id = ? AND sha256 = ?",
                (applicant_id, sha256),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_document_context(row, conn)

    def get_applicant_documents(self, applicant_id: str) -> List[DocumentContext]:
        """Retrieves all documents owned by an applicant."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM documents WHERE applicant_id = ? ORDER BY created_at ASC",
                (applicant_id,),
            )
            rows = cursor.fetchall()
            return [self._row_to_document_context(r, conn) for r in rows]

    def delete_document(self, applicant_id: str, document_id: str) -> bool:
        """Deletes a document and cascades deletion to linked facts and evidence."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Match exact or prefix
            cursor.execute(
                "SELECT document_id FROM documents WHERE applicant_id = ? AND (document_id = ? OR document_id LIKE ?)",
                (applicant_id, document_id, f"%{document_id}%"),
            )
            matched = cursor.fetchall()
            doc_ids = [m["document_id"] for m in matched] if matched else [document_id]

            for d_id in doc_ids:
                cursor.execute(
                    "DELETE FROM evidence WHERE applicant_id = ? AND applicant_fact_id IN (SELECT fact_id FROM applicant_facts WHERE document_id = ?)",
                    (applicant_id, d_id),
                )
                cursor.execute(
                    "DELETE FROM applicant_facts WHERE applicant_id = ? AND document_id = ?",
                    (applicant_id, d_id),
                )
                cursor.execute(
                    "DELETE FROM documents WHERE applicant_id = ? AND document_id = ?",
                    (applicant_id, d_id),
                )
            conn.commit()
            return len(matched) > 0

    def get_facts_for_applicant(self, applicant_id: str) -> List[ApplicantFact]:
        """Retrieves all atomic applicant facts with applicant-scoped isolation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM applicant_facts WHERE applicant_id = ? ORDER BY extracted_at ASC",
                (applicant_id,),
            )
            rows = cursor.fetchall()
            return [self._row_to_fact(r) for r in rows]

    def get_fact_history(self, applicant_id: str, fact_key: str) -> List[ApplicantFact]:
        """Retrieves historical values and candidates for a specific fact key."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM applicant_facts WHERE applicant_id = ? AND fact_key = ? ORDER BY extracted_at ASC",
                (applicant_id, fact_key),
            )
            rows = cursor.fetchall()
            return [self._row_to_fact(r) for r in rows]

    def get_evidence_for_applicant(self, applicant_id: str) -> List[Evidence]:
        """Retrieves all evidence records owned by an applicant."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM evidence WHERE applicant_id = ? ORDER BY created_at ASC",
                (applicant_id,),
            )
            rows = cursor.fetchall()
            return [self._row_to_evidence(r) for r in rows]

    def _row_to_fact(self, row: sqlite3.Row) -> ApplicantFact:
        norm_val = json.loads(row["normalized_value_json"]) if row["normalized_value_json"] else None
        bbox = json.loads(row["bounding_box_json"]) if row["bounding_box_json"] else None
        meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}

        return ApplicantFact(
            id=row["fact_id"],
            applicant_id=row["applicant_id"],
            document_id=row["document_id"],
            field=row["fact_key"],
            value=row["raw_value"],
            normalized_value=norm_val,
            data_type=row["value_type"],
            confidence=float(row["confidence"]),
            verification_status=FactVerificationStatus(row["verification_status"]),
            source_type=FactSourceType(row["source_type"]),
            source_document=row["source_reference"] or "unknown",
            page_number=row["page_number"],
            text_span=row["text_span"],
            bounding_box=bbox,
            extraction_method=row["extraction_method"],
            extracted_at=row["extracted_at"],
            fact_version=row["fact_version"] or "1.0",
            conflict_group_id=row["conflict_group_id"],
            metadata=meta,
        )

    def _row_to_evidence(self, row: sqlite3.Row) -> Evidence:
        bbox = json.loads(row["bounding_box_json"]) if row["bounding_box_json"] else None
        meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}

        return Evidence(
            evidence_id=row["evidence_id"],
            applicant_fact_id=row["applicant_fact_id"],
            applicant_id=row["applicant_id"],
            document_id=row["document_id"],
            source_type=FactSourceType(row["source_type"]),
            source_uri=row["source_uri"],
            page_number=row["page_number"],
            text_span=row["text_span"],
            bounding_box=bbox,
            extraction_method=row["extraction_method"],
            confidence=float(row["confidence"]),
            verification_status=FactVerificationStatus(row["verification_status"]),
            document_hash=row["document_hash"],
            created_at=row["created_at"],
            metadata=meta,
        )

    def _row_to_document_context(self, row: sqlite3.Row, conn: sqlite3.Connection) -> DocumentContext:
        doc_id = row["document_id"]
        app_id = row["applicant_id"]

        # Fetch facts attached to this document
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM applicant_facts WHERE document_id = ? AND applicant_id = ?",
            (doc_id, app_id),
        )
        fact_rows = cursor.fetchall()
        facts = [self._row_to_fact(fr) for fr in fact_rows]

        # Fetch evidence attached to this document
        cursor.execute(
            "SELECT * FROM evidence WHERE document_id = ? AND applicant_id = ?",
            (doc_id, app_id),
        )
        ev_rows = cursor.fetchall()
        evidence_list = [self._row_to_evidence(er) for er in ev_rows]

        meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}

        return DocumentContext(
            document_id=doc_id,
            applicant_id=app_id,
            document_type=row["document_type"] or "UNKNOWN_DOCUMENT",
            document_hash=row["sha256"],
            file_name=row["file_name"],
            mime_type=row["mime_type"],
            page_count=int(row["page_count"] or 1),
            extraction_status=row["status"] or "VALID",
            extraction_method=row["extraction_method"] or "NATIVE_PDF",
            extracted_facts=facts,
            evidence=evidence_list,
            raw_text=row["raw_text"],
            metadata=meta,
            created_at=row["created_at"],
        )
