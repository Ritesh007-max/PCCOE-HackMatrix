"""
FIN Static Security AST Scanner.
Scans Python source trees for dangerous patterns:
  - eval() / exec()
  - os.system() / os.popen()
  - subprocess.*(..., shell=True)
  - unsafe pickle.load() / pickle.loads()
  - unsafe yaml.load()
  - hardcoded credentials or API keys
"""

import ast
import os
from pathlib import Path
import re
from typing import Any, Dict, List


SUSPICIOUS_KEY_REGEX = re.compile(
    r"(?:api_key|secret_key|private_key|token|password)\s*=\s*['\"][A-Za-z0-9_\-\.]{16,}['\"]",
    re.IGNORECASE,
)


class SecurityVisitor(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.findings: List[Dict[str, Any]] = []

    def visit_Call(self, node: ast.Call) -> None:
        # Check eval() / exec()
        if isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec"):
                self.findings.append({
                    "file": self.filename,
                    "line": node.lineno,
                    "severity": "CRITICAL",
                    "type": f"DANGEROUS_FUNCTION_{node.func.id.upper()}",
                    "message": f"Use of dynamic code execution function '{node.func.id}'",
                })

        # Check os.system, os.popen
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "os" and node.func.attr in ("system", "popen"):
                self.findings.append({
                    "file": self.filename,
                    "line": node.lineno,
                    "severity": "CRITICAL",
                    "type": f"DANGEROUS_OS_{node.func.attr.upper()}",
                    "message": f"Use of shell execution function 'os.{node.func.attr}'",
                })

            # Check pickle.loads / pickle.load
            if node.func.value.id == "pickle" and node.func.attr in ("load", "loads"):
                self.findings.append({
                    "file": self.filename,
                    "line": node.lineno,
                    "severity": "HIGH",
                    "type": "UNSAFE_DESERIALIZATION_PICKLE",
                    "message": f"Unsafe object deserialization 'pickle.{node.func.attr}'",
                })

            # Check subprocess shell=True
            if node.func.value.id == "subprocess":
                for kw in node.keywords:
                    if kw.arg == "shell":
                        if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            self.findings.append({
                                "file": self.filename,
                                "line": node.lineno,
                                "severity": "HIGH",
                                "type": "SUBPROCESS_SHELL_TRUE",
                                "message": "subprocess call with shell=True creates command injection risk",
                            })

            # Check yaml.load without safe loader
            if node.func.value.id == "yaml" and node.func.attr == "load":
                has_loader = any(kw.arg == "Loader" for kw in node.keywords)
                if not has_loader and len(node.args) < 2:
                    self.findings.append({
                        "file": self.filename,
                        "line": node.lineno,
                        "severity": "HIGH",
                        "type": "UNSAFE_YAML_LOAD",
                        "message": "yaml.load without explicit SafeLoader is vulnerable to arbitrary code execution",
                    })

        self.generic_visit(node)


def scan_file(file_path: Path) -> List[Dict[str, Any]]:
    """Scans a single Python file for AST and regex security risks."""
    findings: List[Dict[str, Any]] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    # AST scanning
    try:
        tree = ast.parse(content, filename=str(file_path))
        visitor = SecurityVisitor(str(file_path))
        visitor.visit(tree)
        findings.extend(visitor.findings)
    except SyntaxError:
        pass

    # Regex scanning for hardcoded secrets
    for idx, line in enumerate(content.splitlines(), start=1):
        if SUSPICIOUS_KEY_REGEX.search(line):
            # Exclude tests and examples
            if "test" not in file_path.name.lower() and "example" not in file_path.name.lower():
                findings.append({
                    "file": str(file_path),
                    "line": idx,
                    "severity": "CRITICAL",
                    "type": "POSSIBLE_HARDCODED_SECRET",
                    "message": "Possible hardcoded secret or API key credential found",
                })

    return findings


def scan_directory(dir_path: Path) -> Dict[str, Any]:
    """Scans all Python files recursively under dir_path."""
    all_findings: List[Dict[str, Any]] = []
    files_scanned = 0

    for root, _, files in os.walk(dir_path):
        for f in files:
            if f.endswith(".py"):
                p = Path(root) / f
                # Skip virtual environments and caches
                if ".venv" in str(p) or "__pycache__" in str(p):
                    continue
                findings = scan_file(p)
                all_findings.extend(findings)
                files_scanned += 1

    by_severity = {
        "CRITICAL": [f for f in all_findings if f["severity"] == "CRITICAL"],
        "HIGH": [f for f in all_findings if f["severity"] == "HIGH"],
        "MEDIUM": [f for f in all_findings if f["severity"] == "MEDIUM"],
        "LOW": [f for f in all_findings if f["severity"] == "LOW"],
    }

    return {
        "files_scanned": files_scanned,
        "total_findings": len(all_findings),
        "critical_count": len(by_severity["CRITICAL"]),
        "high_count": len(by_severity["HIGH"]),
        "findings": all_findings,
        "by_severity": by_severity,
    }


if __name__ == "__main__":
    src_dir = Path(__file__).resolve().parents[1]
    res = scan_directory(src_dir)
    print(f"Scanned {res['files_scanned']} files.")
    print(f"Total findings: {res['total_findings']} (Critical: {res['critical_count']}, High: {res['high_count']})")
    for f in res["findings"]:
        print(f"[{f['severity']}] {f['file']}:{f['line']} -> {f['message']}")
