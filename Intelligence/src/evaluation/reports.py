"""
FIN Evaluation Report Generator.
Serializes evaluation runs into structured JSON and GitHub Flavored Markdown artifacts
under Intelligence/data/evaluation/reports/. Enforces strict sanitization of API keys and citizen PII.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, Optional

import sys
_INTELLIGENCE_DIR = Path(__file__).resolve().parents[2]
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))

from src.evaluation.metrics import MetricAggregator


class ReportManager:
    """Manages persistence and sanitization of evaluation reports."""

    def __init__(self, reports_dir: Optional[Path] = None):
        self.reports_dir = reports_dir or _INTELLIGENCE_DIR / "data" / "evaluation" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def persist_run(
        self,
        run_data: Dict[str, Any],
        suite_name: str = "full"
    ) -> Dict[str, Path]:
        """
        Saves both JSON and Markdown reports to the reports directory.
        Returns dictionary of saved file paths.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        sanitized_run = self.sanitize_report_data(run_data)

        # 1. JSON Report
        json_path = self.reports_dir / f"phase13_{timestamp}_{suite_name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(sanitized_run, f, indent=2, ensure_ascii=False)

        # 2. Markdown Report
        md_content = MetricAggregator.format_markdown_report(sanitized_run)
        md_path = self.reports_dir / f"phase13_{timestamp}_{suite_name}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return {"json": json_path, "markdown": md_path}

    @staticmethod
    def sanitize_report_data(data: Any) -> Any:
        """Recursively scrubs API keys, auth tokens, and Aadhaar/PAN formats from reports."""
        if isinstance(data, dict):
            return {k: ReportManager.sanitize_report_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [ReportManager.sanitize_report_data(item) for item in data]
        elif isinstance(data, str):
            # Scrub API key patterns
            scrubbed = re.sub(r"AIzaSy[A-Za-z0-9_-]{33}", "[SCRUBBED_GEMINI_KEY]", data)
            scrubbed = re.sub(r"sk-or-v1-[a-f0-9]{64}", "[SCRUBBED_OPENROUTER_KEY]", scrubbed)
            scrubbed = re.sub(r"ps_live_[a-zA-Z0-9_-]{16,}", "[SCRUBBED_SERVICE_KEY]", scrubbed)
            # Scrub Aadhaar / PAN
            scrubbed = re.sub(r"\b[2-9]{1}[0-9]{3}\s[0-9]{4}\s[0-9]{4}\b", "[SCRUBBED_AADHAAR]", scrubbed)
            scrubbed = re.sub(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", "[SCRUBBED_PAN]", scrubbed)
            return scrubbed
        return data
