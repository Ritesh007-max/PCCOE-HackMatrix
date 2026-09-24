"""
Tests for API Authorization & Role Semantics.
Verifies role mapping, privilege hierarchy, and access denial for policy mutation endpoints.
"""

import unittest
from fastapi import HTTPException
from src.api.authorization import (
    Role,
    get_current_role,
    require_admin,
    require_role,
)


class TestAuthorizationModel(unittest.TestCase):
    def test_role_from_header(self):
        self.assertEqual(Role.from_header("admin"), Role.ADMIN)
        self.assertEqual(Role.from_header("reviewer"), Role.REVIEWER)
        self.assertEqual(Role.from_header("citizen"), Role.CITIZEN)
        self.assertEqual(Role.from_header("service"), Role.SERVICE)
        # Unknown falls back to citizen
        self.assertEqual(Role.from_header("attacker_role"), Role.CITIZEN)

    def test_admin_has_all_privileges(self):
        checker = require_role(Role.ADMIN)
        # Admin can access admin endpoints
        res = checker(current_role=Role.ADMIN)
        self.assertEqual(res, Role.ADMIN)

    def test_citizen_forbidden_on_admin_endpoint(self):
        checker = require_role(Role.ADMIN)
        with self.assertRaises(HTTPException) as ctx:
            checker(current_role=Role.CITIZEN)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Forbidden", ctx.exception.detail)

    def test_reviewer_forbidden_on_admin_endpoint(self):
        checker = require_role(Role.ADMIN)
        with self.assertRaises(HTTPException) as ctx:
            checker(current_role=Role.REVIEWER)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_reviewer_allowed_on_reviewer_endpoint(self):
        checker = require_role(Role.REVIEWER, Role.ADMIN)
        res = checker(current_role=Role.REVIEWER)
        self.assertEqual(res, Role.REVIEWER)

    def test_admin_allowed_on_reviewer_endpoint(self):
        checker = require_role(Role.REVIEWER, Role.ADMIN)
        res = checker(current_role=Role.ADMIN)
        self.assertEqual(res, Role.ADMIN)


if __name__ == "__main__":
    unittest.main()
