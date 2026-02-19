#!/usr/bin/env python3
"""Basic regression tests for enterprise legal guardrails."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check_enterprise_guardrails.py"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_enterprise_guardrails import analyze_text


def run_script(args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def run_all():
    # 1) Ensure defaults still review this known risky output.
    report = analyze_text(
        "John is a scammer and this is a guaranteed 100% win.",
        action="post",
    )
    assert report["status"] == "REVIEW", report
    assert report["thresholds"]["review"] == 5, report
    assert report["thresholds"]["block"] == 9, report

    # 2) Ensure configurable review threshold can move a REVIEW case to WATCH.
    report = analyze_text(
        "John is a scammer and this is a guaranteed 100% win.",
        action="post",
        review_threshold=9,
        block_threshold=9,
    )
    assert report["status"] == "WATCH", report
    assert report["thresholds"] == {"review": 9, "block": 10}, report

    # 3) Ensure configurable block threshold still blocks when lowered.
    report = analyze_text(
        "John is a scammer and this is a guaranteed 100% win.",
        action="post",
        review_threshold=2,
        block_threshold=4,
    )
    assert report["status"] == "BLOCK", report

    # 4) Ensure scope exclude can skip checks without changing status.
    report = analyze_text(
        "John is a scammer and this is a guaranteed 100% win.",
        action="post",
        app="whatsapp",
        scope="exclude",
        app_targets=["whatsapp", "babylon"],
    )
    assert report["status"] == "PASS", report
    assert report["findings_count"] == 0, report

    # 5) Ensure disabled guardrails always PASS.
    report = analyze_text(
        "John is a scammer and this is a guaranteed 100% win.",
        action="post",
        enabled=False,
    )
    assert report["status"] == "PASS", report
    assert report["score"] == 0, report

    # 6) Missing input file should fail cleanly without traceback.
    code, _, err = run_script(["--action", "post", "--file", "/tmp/definitely_missing_foo_123456.txt"])
    assert code == 1, (code, err)
    assert "Unable to read input text" in err, err
    assert "Traceback" not in err, err


if __name__ == "__main__":
    run_all()
    print("ok")
