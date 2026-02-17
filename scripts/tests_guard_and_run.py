#!/usr/bin/env python3
"""Regression tests for guard_and_run adapter."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "guard_and_run.py"


def run(*args: str, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    command = [sys.executable, str(SCRIPT), *args]
    proc = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


# Benign text should pass and execute command.
code, out, err = run(
    "--app",
    "website",
    "--action",
    "post",
    "--text",
    "Hello colleague, we have a stable release update.",
    "--",
    "python3",
    "-c",
    "print('ok')",
)
assert code == 0, (code, out, err)
assert out.strip() == "ok", (out, err)

# REVIEW should still run by default but emit a warning to stderr.
code, out, err = run(
    "--app",
    "website",
    "--action",
    "post",
    "--text",
    "John is a scammer and this is a guaranteed 100% win",
    "--",
    "python3",
    "-c",
    "print('review-ok')",
)
assert code == 0, (code, out, err)
assert out.strip() == "review-ok", (out, err)
assert "Guardrail REVIEW" in err, err

# Strict REVIEW should block.
code, out, err = run(
    "--strict",
    "--app",
    "website",
    "--action",
    "post",
    "--text",
    "John is a scammer and this is a guaranteed 100% win",
    "--",
    "python3",
    "-c",
    "print('should-not-run')",
)
assert code == 2, (code, out, err)
assert "Blocked by enterprise legal guardrails" in err, err
assert "should-not-run" not in out and "should-not-run" not in err, (out, err)

# Block threshold override can enforce a hard block.
code, out, err = run(
    "--app",
    "website",
    "--action",
    "post",
    "--text",
    "John is a scammer and this is a guaranteed 100% win",
    "--review-threshold",
    "2",
    "--block-threshold",
    "4",
    "--",
    "python3",
    "-c",
    "print('should-not-run2')",
)
assert code == 2, (code, out, err)
assert "Blocked by enterprise legal guardrails" in err, err

# Explicit allow-list blocks unexpected binaries.
code, out, err = run(
    "--allowed-command",
    "python3",
    "--app",
    "website",
    "--action",
    "post",
    "--text",
    "Hello",
    "--",
    "cat",
    "/etc/hosts",
)
assert code == 1, (code, out, err)
assert "not in the allowlist" in err, (out, err)

# Sanitized environment should remove unshared variables.
with tempfile.TemporaryDirectory() as tmpdir:
    code, out, err = run(
        "--sanitize-env",
        "--app",
        "website",
        "--action",
        "post",
        "--text",
        "Hello",
        "--",
        "python3",
        "-c",
        "import os; print('SHADOW_TOKEN' in os.environ)",
        env={**os.environ.copy(), "SHADOW_TOKEN": "x"},
    )
    assert code == 0, (code, out, err)
    assert out.strip() == "False", (out, err)

# command-timeout blocks long-running wrapped command.
code, out, err = run(
    "--command-timeout",
    "1",
    "--app",
    "website",
    "--action",
    "post",
    "--text",
    "Hello",
    "--",
    "python3",
    "-c",
    "import time; time.sleep(2)",
)
assert code == 1, (code, out, err)
assert "timed out" in err.lower(), (out, err)

# dry-run does not execute the wrapped command.
with tempfile.TemporaryDirectory() as tmpdir:
    marker = Path(tmpdir) / "ran.txt"
    code, out, err = run(
        "--dry-run",
        "--app",
        "website",
        "--action",
        "post",
        "--text",
        "Hello",
        "--",
        "python3",
        "-c",
        f"import pathlib; pathlib.Path('{marker.as_posix()}').write_text('done')",
    )
    assert code == 0, (code, out, err)
    assert not marker.exists(), (marker, "command should not run during dry-run")

# checker timeout argument validation
code, out, err = run(
    "--checker-timeout",
    "0",
    "--app",
    "website",
    "--action",
    "post",
    "--text",
    "Hello",
    "--",
    "python3",
    "-c",
    "print('nope')",
)
assert code == 2, (code, out, err)
assert "must be a positive integer" in err

# audit log writes redacted JSON lines.
with tempfile.TemporaryDirectory() as tmpdir:
    log_path = Path(tmpdir) / "guard_audit.jsonl"
    code, out, err = run(
        "--audit-log",
        str(log_path),
        "--app",
        "website",
        "--action",
        "post",
        "--text",
        "Hello",
        "--",
        "python3",
        "-c",
        "print('ok')",
    )
    assert code == 0, (code, out, err)
    assert log_path.exists(), (out, err)
    logged = log_path.read_text().strip().splitlines()
    assert len(logged) == 1, logged
    record = logged[0]
    parsed = json.loads(record)
    assert parsed["status"] in {"PASS", "WATCH", "REVIEW", "BLOCK"}, record
    assert parsed["text_len"] > 0
    assert "SHADOW_TOKEN" not in record, record

print("ok")
