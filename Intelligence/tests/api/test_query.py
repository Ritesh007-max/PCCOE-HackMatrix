"""
FIN Query Understanding and Chat Personalization API Endpoint Tests.
Validates POST /v1/query/understand and POST /v1/chat personalization.
"""

import os
import shutil
import tempfile
import unittest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.context.service import ApplicantContextService
from unittest.mock import MagicMock
from src.extraction.models import FactSourceType, FactVerificationStatus
from src.persistence.repository import FactPersistenceRepository
from src.query.service import QueryUnderstandingService
from src.api.dependencies import (
    get_persistence_repository,
    get_applicant_context_service,
    get_query_understanding_service,
    get_hybrid_retriever,
)


class TestQueryUnderstandingAPI(unittest.TestCase):
    """API integration tests for /v1/query/understand and personalized /v1/chat."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_api_query.db")
        self.repo = FactPersistenceRepository(db_path=self.db_path)
        self.context_service = ApplicantContextService(repository=self.repo)
        self.query_service = QueryUnderstandingService(applicant_context_service=self.context_service)

        self.mock_retriever = MagicMock()
        self.mock_retriever.retrieve.return_value = []
        self.mock_retriever.retrieve_schemes.return_value = []

        # Override dependencies
        app.dependency_overrides[get_persistence_repository] = lambda: self.repo
        app.dependency_overrides[get_applicant_context_service] = lambda: self.context_service
        app.dependency_overrides[get_query_understanding_service] = lambda: self.query_service
        app.dependency_overrides[get_hybrid_retriever] = lambda: self.mock_retriever

        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_query_understand_endpoint(self):
        # 1. Setup applicant context
        self.context_service.record_user_fact(
            "api_applicant", "annual_family_income", "Rs. 4,20,000",
            source_type=FactSourceType.DOCUMENT
        )
        self.context_service.record_user_fact(
            "api_applicant", "state", "Gujarat",
            source_type=FactSourceType.DOCUMENT
        )

        # 2. Call /v1/query/understand
        resp = self.client.post(
            "/v1/query/understand",
            json={
                "applicant_id": "api_applicant",
                "message": "I am 19 and my income is 21 lakh. Suggest schemes.",
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["applicant_id"], "api_applicant")

        und = data["understanding"]
        self.assertEqual(und["intent"], "SCHEME_RECOMMENDATION")
        self.assertEqual(und["route"], "SCHEME_RECOMMENDATION_PIPELINE")
        self.assertTrue(und["applicant_context_available"])
        self.assertTrue(len(und["candidate_facts"]) >= 1)

    def test_personalized_chat_personal_fact_fast_path(self):
        # 1. Record verified fact
        self.context_service.record_user_fact(
            "chat_applicant", "annual_family_income", "Rs. 4,20,000",
            source_type=FactSourceType.DOCUMENT
        )
        # 2. Call /v1/chat with applicant_id and personal fact lookup query
        resp = self.client.post(
            "/v1/chat",
            json={
                "applicant_id": "chat_applicant",
                "query": "What is my income?",
            },
            headers={"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent"], "PERSONAL_FACT_LOOKUP")
        self.assertIn("4,20,000", data["answer"])
        self.assertIsNotNone(data.get("query_understanding"))


if __name__ == "__main__":
    unittest.main()
