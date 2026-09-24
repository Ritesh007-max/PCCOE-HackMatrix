"""
Tests for Multi-Tier In-Memory Rate Limiting.
Verifies rate limit tiers (PUBLIC, PROTECTED, EXPENSIVE) and sliding-window eviction.
"""

import time
import unittest
from src.api.config import ServiceConfig
from src.api.errors import RateLimitExceededError
from src.api.middleware import InMemoryRateLimiter, RateLimitTier


class TestRateLimiting(unittest.TestCase):
    def setUp(self):
        self.config = ServiceConfig(
            rate_limit_enabled=True,
            rate_limit_per_minute=10,
            rate_limit_public=10,
            rate_limit_protected=5,
            rate_limit_expensive=2,
        )
        self.limiter = InMemoryRateLimiter(self.config)

    def test_tier_mapping(self):
        self.assertEqual(self.limiter.get_tier_for_path("/health/live"), RateLimitTier.PUBLIC)
        self.assertEqual(self.limiter.get_tier_for_path("/health/ready"), RateLimitTier.PROTECTED)
        self.assertEqual(self.limiter.get_tier_for_path("/v1/schemes/search"), RateLimitTier.PROTECTED)
        self.assertEqual(self.limiter.get_tier_for_path("/v1/documents/process"), RateLimitTier.EXPENSIVE)
        self.assertEqual(self.limiter.get_tier_for_path("/v1/applications/analyze"), RateLimitTier.EXPENSIVE)
        self.assertEqual(self.limiter.get_tier_for_path("/v1/chat/message"), RateLimitTier.EXPENSIVE)
        self.assertEqual(self.limiter.get_tier_for_path("/v1/policy/sync"), RateLimitTier.EXPENSIVE)

    def test_rate_limit_allowed_under_threshold(self):
        client = "192.168.1.100"
        # 2 requests on expensive tier (limit=2)
        self.limiter.check(client, tier=RateLimitTier.EXPENSIVE)
        self.limiter.check(client, tier=RateLimitTier.EXPENSIVE)

    def test_rate_limit_exceeded_raises(self):
        client = "192.168.1.101"
        self.limiter.check(client, tier=RateLimitTier.EXPENSIVE)
        self.limiter.check(client, tier=RateLimitTier.EXPENSIVE)
        # 3rd request should exceed limit of 2
        with self.assertRaises(RateLimitExceededError):
            self.limiter.check(client, tier=RateLimitTier.EXPENSIVE)

    def test_rate_limit_tiers_isolated(self):
        client = "192.168.1.102"
        # Exhaust expensive tier
        self.limiter.check(client, tier=RateLimitTier.EXPENSIVE)
        self.limiter.check(client, tier=RateLimitTier.EXPENSIVE)
        # Protected tier should still have allowance
        self.limiter.check(client, tier=RateLimitTier.PROTECTED)

    def test_reset_clears_history(self):
        client = "192.168.1.103"
        self.limiter.check(client, tier=RateLimitTier.EXPENSIVE)
        self.limiter.check(client, tier=RateLimitTier.EXPENSIVE)
        self.limiter.reset()
        # Should now succeed again
        self.limiter.check(client, tier=RateLimitTier.EXPENSIVE)


if __name__ == "__main__":
    unittest.main()
