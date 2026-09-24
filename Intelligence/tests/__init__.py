"""
Test package for FIN AI.
Ensures AI directory is on sys.path for test discovery from any working directory.
"""

import sys
from pathlib import Path

_INTELLIGENCE_DIR = Path(__file__).resolve().parent.parent
if str(_INTELLIGENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INTELLIGENCE_DIR))
