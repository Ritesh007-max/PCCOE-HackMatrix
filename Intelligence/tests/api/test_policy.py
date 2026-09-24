"""
Test Policy Endpoints.
Verifies GET /v1/policy/status, GET /v1/policy/sources, POST /v1/policy/sync,
POST /v1/policy/sync/dry-run, and POST /v1/policy/rollback.
"""

import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.config import DEFAULT_SERVICE_CONFIG
from src.api.routes.policy import get_orchestrator
from src.data_pipeline.models import SyncJob, SyncStatus, SourceDefinition, SourceType, AuthorityTier


class TestPolicyEndpoints(unittest.TestCase):
    def setUp(self):
        self.mock_orchestrator = MagicMock()
        self.mock_orchestrator.get_active_policy_version.return_value = "snapshot_20260921_193823"
        self.mock_orchestrator.get_rollback_versions.return_value = ["snapshot_20260921_193823"]

        sample_job = SyncJob(
            sync_id="sync_test_99",
            status=SyncStatus.SUCCEEDED,
            started_at="2026-09-24T09:00:00Z",
            completed_at="2026-09-24T09:00:02Z",
            activation_status="ACTIVATED",
            records_seen=4749,
            records_added=0,
            records_updated=0,
            records_removed=0,
            records_unchanged=4749,
        )
        self.mock_orchestrator.get_last_sync.return_value = sample_job
        self.mock_orchestrator.sync.return_value = sample_job
        self.mock_orchestrator.rollback.return_value = "snapshot_20260921_193823"

        sample_source = SourceDefinition(
            source_id="myscheme_baseline",
            source_name="MyScheme Baseline",
            source_type=SourceType.LOCAL_BASELINE,
            authority_tier=AuthorityTier.PRIMARY_CANONICALIZED,
        )
        self.mock_orchestrator.list_sources.return_value = [sample_source]
        self.mock_orchestrator.get_source_health.return_value = {
            "myscheme_baseline": {"freshness_status": "FRESH"}
        }

        app.dependency_overrides[get_orchestrator] = lambda: self.mock_orchestrator
        self.client = TestClient(app)
        self.headers = {"X-AI-Service-Key": DEFAULT_SERVICE_CONFIG.service_api_key}

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_get_policy_status(self):
        """GET /v1/policy/status returns active snapshot and last sync info."""
        res = self.client.get("/v1/policy/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["active_policy_version"], "snapshot_20260921_193823")
        self.assertTrue(data["has_active_snapshot"])
        self.assertIsNotNone(data["last_sync"])

    def test_get_policy_sources(self):
        """GET /v1/policy/sources returns registered sources list and health."""
        res = self.client.get("/v1/policy/sources")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_sources"], 1)
        self.assertIn("source_health", data)

    def test_dry_run_sync_requires_auth(self):
        """POST /v1/policy/sync/dry-run requires valid X-AI-Service-Key."""
        res = self.client.post("/v1/policy/sync/dry-run")
        self.assertEqual(res.status_code, 401)

        res_authed = self.client.post("/v1/policy/sync/dry-run", headers=self.headers, json={})
        self.assertEqual(res_authed.status_code, 200)
        data = res_authed.json()
        self.assertTrue(data["dry_run"])

    def test_trigger_live_sync(self):
        """POST /v1/policy/sync triggers live sync and returns job outcome."""
        res = self.client.post("/v1/policy/sync", headers=self.headers, json={"force_rebuild": False})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["activated"])
        self.assertEqual(data["job"]["status"], "SUCCEEDED")

    def test_rollback_policy(self):
        """POST /v1/policy/rollback performs atomic rollback."""
        res = self.client.post("/v1/policy/rollback", headers=self.headers, json={})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("snapshot_20260921_193823", data["message"])


if __name__ == "__main__":
    unittest.main()
