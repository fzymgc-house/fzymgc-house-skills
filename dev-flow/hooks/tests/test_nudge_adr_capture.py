"""pytest wrapper around the bash test harness for nudge-adr-capture.

The actual fixtures live in test_nudge_adr_capture.sh (lifted from
holomush PR #3833). This wrapper just runs that harness so CI's pytest
sweep picks it up.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parent / "test_nudge_adr_capture.sh"


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq not available")
@pytest.mark.skipif(shutil.which("sha256sum") is None, reason="sha256sum not available")
def test_nudge_adr_capture_bash_harness() -> None:
    """The 15-fixture bash harness must report passed=15 failed=0."""
    result = subprocess.run(
        ["bash", str(HARNESS)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"harness exit={result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "passed=15 failed=0" in result.stdout, result.stdout
