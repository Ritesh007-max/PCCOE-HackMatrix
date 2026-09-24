"""
Tests for Static Code Safety & Supply Chain AST Checks.
Verifies that no critical vulnerabilities exist in the codebase:
  - 0 occurrences of eval() or exec()
  - 0 occurrences of os.system() or os.popen()
  - 0 occurrences of subprocess shell=True
  - 0 hardcoded secrets
"""

from pathlib import Path
import unittest
from src.utils.security_scanner import scan_directory


class TestDependencySecurity(unittest.TestCase):
    def test_zero_critical_ast_vulnerabilities(self):
        src_dir = Path(__file__).resolve().parents[2] / "src"
        results = scan_directory(src_dir)
        
        # Critical findings must be strictly zero
        criticals = results["by_severity"]["CRITICAL"]
        self.assertEqual(
            len(criticals),
            0,
            f"Expected 0 CRITICAL security findings, got {len(criticals)}: {criticals}"
        )

    def test_subprocess_shell_safety(self):
        src_dir = Path(__file__).resolve().parents[2] / "src"
        results = scan_directory(src_dir)
        shell_true_findings = [
            f for f in results["findings"]
            if f.get("type") == "SUBPROCESS_SHELL_TRUE"
        ]
        self.assertEqual(
            len(shell_true_findings),
            0,
            f"Expected 0 subprocess shell=True findings, got {len(shell_true_findings)}"
        )


if __name__ == "__main__":
    unittest.main()
