"""
Unit tests for SourceMetadataResolver.
Phase 11: Validates official URL allowlist, untrusted domain rejection, and deadline extraction.
"""

import unittest
from src.guidance.sources import SourceMetadataResolver
from src.guidance.models import ApplicationMode, DeadlineStatus


class TestSourceMetadata(unittest.TestCase):
    """Tests for SourceMetadataResolver."""

    def test_official_url_allowlist_acceptance(self):
        """Valid government domains are accepted."""
        valid_urls = [
            "https://pmkisan.gov.in/portal",
            "https://scholarships.gov.in",
            "https://myscheme.gov.in/schemes/pm-kisan",
            "https://rural.nic.in/pmayg",
            "https://digitalgujarat.gov.in",
        ]
        for u in valid_urls:
            validated = SourceMetadataResolver.validate_official_url(u)
            self.assertEqual(validated, u)

    def test_untrusted_domain_rejection(self):
        """Untrusted blogs, search engines, and commercial sites are strictly rejected."""
        bad_urls = [
            "https://www.google.com/search?q=pmkisan",
            "https://sarkariyojana.com/apply",
            "https://cleartax.in/s/pm-kisan",
            "https://timesofindia.indiatimes.com/scheme",
            "https://myblog.blogspot.com/scheme-details",
        ]
        for bad in bad_urls:
            validated = SourceMetadataResolver.validate_official_url(bad)
            self.assertIsNone(validated)

    def test_non_url_and_empty_strings(self):
        """Malformed or empty inputs return None."""
        self.assertIsNone(SourceMetadataResolver.validate_official_url(""))
        self.assertIsNone(SourceMetadataResolver.validate_official_url(None))
        self.assertIsNone(SourceMetadataResolver.validate_official_url("not_a_url"))

    def test_resolve_deadlines_unknown(self):
        """Schemes lacking explicit calendar close dates return DeadlineStatus.UNKNOWN."""
        resolver = SourceMetadataResolver()
        guidance = resolver.resolve_deadlines("unknown_scheme_id")
        self.assertEqual(guidance.status, DeadlineStatus.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
