"""
Unit tests for Incremental RAG Updates and FAISS/Index Purging.
Explicitly verifies:
- ADD creates fresh chunks and embeddings.
- UPDATE purges old chunks and indexes new chunks.
- DELETE deactivates chunks so removed schemes CANNOT appear in active retrieval.
- Unchanged chunks retain stable IDs and pre-computed embeddings.
"""

from pathlib import Path
import sys
import unittest
import numpy as np

_AI_DIR = Path(__file__).resolve().parents[2]
if str(_AI_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_DIR))

from src.data_pipeline.incremental_rag import IncrementalRAGUpdater
from src.data_pipeline.models import RecordDiff, ChangeType
from src.rag.store import NumpyVectorStore


class TestIncrementalRAG(unittest.TestCase):

    def setUp(self):
        # Mock embedding generator (deterministic 4D vector)
        def mock_emb(texts):
            return np.array([[len(t), len(t) * 2, 1.0, 0.5] for t in texts], dtype=np.float32)

        self.updater = IncrementalRAGUpdater(embedding_fn=mock_emb)

        # Baseline chunks
        self.existing_chunks = [
            {"chunk_id": "chunk_pm_kisan_01", "scheme_slug": "pm-kisan", "text": "PM Kisan benefit is 6000"},
            {"chunk_id": "chunk_pm_kisan_02", "scheme_slug": "pm-kisan", "text": "PM Kisan eligibility is farmers"},
            {"chunk_id": "chunk_old_grant_01", "scheme_slug": "old-grant", "text": "Old Grant deleted scheme"},
            {"chunk_id": "chunk_post_matric_01", "scheme_slug": "post-matric-sc", "text": "Post matric scholarship tuition"},
        ]

    def test_incremental_add_update_delete(self):
        """
        Scenario:
        - pm-kisan: MODIFIED (UPDATE) -> old chunks purged, new chunk generated
        - old-grant: REMOVED (DELETE) -> chunks purged completely
        - solar-yojana: ADDED (ADD) -> new chunk added
        - post-matric-sc: UNCHANGED -> retained as-is
        """
        diffs = [
            RecordDiff(scheme_slug="pm-kisan", change_type=ChangeType.MODIFIED),
            RecordDiff(scheme_slug="old-grant", change_type=ChangeType.REMOVED),
            RecordDiff(scheme_slug="solar-yojana", change_type=ChangeType.ADDED),
        ]

        all_records = [
            {"slug": "pm-kisan", "scheme_name": "PM Kisan Updated", "benefits": "Enhanced 8000"},
            {"slug": "solar-yojana", "scheme_name": "PM Surya Ghar", "benefits": "300 free units"},
            {"slug": "post-matric-sc", "scheme_name": "Post Matric SC", "benefits": "Tuition"},
        ]

        def mock_chunker(rec):
            slug = rec["slug"]
            clean_slug = slug.replace("-", "_")
            return [
                {"chunk_id": f"chunk_{clean_slug}_new_01", "scheme_slug": slug, "text": f"Fresh text for {rec['scheme_name']}"}
            ]

        final_chunks, purged_ids, new_ids = self.updater.compute_incremental_chunks(
            existing_chunks=self.existing_chunks,
            diffs=diffs,
            all_canonical_records=all_records,
            chunk_fn=mock_chunker
        )

        final_slugs = [c["scheme_slug"] for c in final_chunks]
        final_ids = [c["chunk_id"] for c in final_chunks]

        # 1. DELETE check: old-grant MUST NOT exist in final chunks
        self.assertNotIn("old-grant", final_slugs)
        self.assertIn("chunk_old_grant_01", purged_ids)

        # 2. UPDATE check: old pm-kisan chunk IDs purged; new pm-kisan chunk added
        self.assertIn("chunk_pm_kisan_01", purged_ids)
        self.assertIn("chunk_pm_kisan_02", purged_ids)
        self.assertNotIn("chunk_pm_kisan_01", final_ids)
        self.assertIn("chunk_pm_kisan_new_01", final_ids)

        # 3. ADD check: solar-yojana chunk added
        self.assertIn("solar-yojana", final_slugs)
        self.assertIn("chunk_solar_yojana_new_01", final_ids)

        # 4. UNCHANGED check: post-matric-sc retained intact
        self.assertIn("chunk_post_matric_01", final_ids)

    def test_faiss_vector_store_purge_and_retrieval(self):
        """
        Verify that purged/deleted scheme chunks cannot continue appearing in active retrieval.
        """
        vector_store = NumpyVectorStore(dimension=4)

        # Initial cache
        cached_embs = {
            "chunk_pm_kisan_01": np.array([10.0, 20.0, 1.0, 0.5], dtype=np.float32),
            "chunk_old_grant_01": np.array([15.0, 30.0, 1.0, 0.5], dtype=np.float32),
            "chunk_post_matric_01": np.array([8.0, 16.0, 1.0, 0.5], dtype=np.float32),
        }

        # Active chunks: old_grant is deleted; pm-kisan is updated with new chunk
        active_chunks = [
            {"chunk_id": "chunk_pm_kisan_new_01", "scheme_slug": "pm-kisan", "text": "PM Kisan 8000"},
            {"chunk_id": "chunk_post_matric_01", "scheme_slug": "post-matric-sc", "text": "Post matric"},
        ]
        new_ids = {"chunk_pm_kisan_new_01"}

        updated_cache = self.updater.update_vector_index(
            active_chunks=active_chunks,
            cached_embeddings=cached_embs,
            new_chunk_ids=new_ids,
            vector_store=vector_store,
        )

        # Stale chunk must be removed from cache
        self.assertNotIn("chunk_old_grant_01", updated_cache)
        self.assertNotIn("chunk_pm_kisan_01", updated_cache)

        # Search the updated vector store: old_grant MUST NEVER appear
        query_vec = np.array([15.0, 30.0, 1.0, 0.5], dtype=np.float32)
        results = vector_store.search(query_vector=query_vec, top_k=5)
        retrieved_ids = [r[0] for r in results]

        self.assertNotIn("chunk_old_grant_01", retrieved_ids)
        self.assertNotIn("chunk_pm_kisan_01", retrieved_ids)
        self.assertIn("chunk_pm_kisan_new_01", retrieved_ids)


if __name__ == "__main__":
    unittest.main()
