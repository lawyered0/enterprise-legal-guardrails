#!/usr/bin/env python3
"""Regression tests for guard_and_run adapter."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "guard_and_run.py"


def run(*args: str, env: dict[str, str] | None = None, input_text: str | None = None) -> tuple[int, str, str]:
    command = [sys.executable, str(SCRIPT), *args]
    proc = subprocess.run(
        command,
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


# 1) Benign text should pass and execute command.
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

# 2) REVIEW should still run by default but emit a warning to stderr.
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

# 3) Strict REVIEW should block.
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

# 4) Block threshold override can enforce a hard block.
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

# 5) Missing command should error.
code, out, err = run(
    "--app",
    "website",
    "--action",
    "post",
    "--text",
    "Hello",
)
assert code == 2, (code, out, err)
assert "Missing command." in err, (out, err)

# 6) Missing -- delimiter should error.
code, out, err = run(
    "--app",
    "website",
    "--action",
    "post",
    "--text",
    "Hello",
    "python3",
    "-c",
    "print('x')",
)
assert code == 2, (code, out, err)
assert "requires delimiter --" in err, (out, err)

# 7) Explicit allow-list blocks unexpected binaries.
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

# 8) Regex allowlist support.
code, out, err = run(
    "--allowed-command",
    "regex:python3",
    "--app",
    "website",
    "--action",
    "post",
    "--text",
    "Hello",
    "--",
    "python3",
    "-c",
    "print('regex-ok')",
)
assert code == 0, (code, out, err)
assert out.strip() == "regex-ok", (out, err)

# 9) Legacy alias allowlist variable should apply.
code, out, err = run(
    "--app",
    "website",
    "--action",
    "post",
    "--text",
    "Hello",
    "--",
    "cat",
    "/etc/hosts",
    env={**os.environ.copy(), "BABYLON_ALLOWED_COMMANDS": "python3"},
)
assert code == 1, (code, out, err)
assert "not in the allowlist" in err, (out, err)

# 10) Text file input should be honored.
with tempfile.TemporaryDirectory() as tmpdir:
    payload = Path(tmpdir) / "payload.txt"
    payload.write_text("Policy-safe text from file.", encoding="utf-8")
    code, out, err = run(
        "--app",
        "website",
        "--action",
        "post",
        "--text-file",
        str(payload),
        "--",
        "python3",
        "-c",
        "print('from-file')",
    )
    assert code == 0, (code, out, err)
    assert out.strip() == "from-file", (out, err)

# 11) Stdin should work for draft text.
code, out, err = run(
    "--app",
    "website",
    "--action",
    "post",
    "--",
    "python3",
    "-c",
    "print('from-stdin')",
    input_text="Hello from stdin",
)
assert code == 0, (code, out, err)
assert out.strip() == "from-stdin", (out, err)

# 12) Strict mode can also be sourced from env alias.
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
    "print('should-not-run-env')",
    env={**os.environ.copy(), "ENTERPRISE_LEGAL_GUARDRAILS_STRICT": "true"},
)
assert code == 2, (code, out, err)
assert "Blocked by enterprise legal guardrails" in err, err
assert "should-not-run-env" not in out and "should-not-run-env" not in err, (out, err)

# 13) Max text bytes enforcement.
code, out, err = run(
    "--app",
    "website",
    "--action",
    "post",
    "--max-text-bytes",
    "1",
    "--text",
    "too big",
    "--",
    "python3",
    "-c",
    "print('nope')",
)
assert code == 2, (code, out, err)
assert "max allowed bytes" in err, (out, err)

# 14) Sanitized environment should remove unshared variables and keep explicit prefixes.
with tempfile.TemporaryDirectory() as tmpdir:
    code, out, err = run(
        "--sanitize-env",
        "--keep-env",
        "KEEP_ME",
        "--keep-env-prefix",
        "SHARED_",
        "--app",
        "website",
        "--action",
        "post",
        "--text",
        "Hello",
        "--",
        "python3",
        "-c",
        "import os; print('KEEP_ME' in os.environ, any(k.startswith('SHARED_') for k in os.environ), 'DROP_ME' in os.environ)",
        env={
            **os.environ,
            "KEEP_ME": "1",
            "SHARED_TOKEN": "2",
            "DROP_ME": "3",
        },
    )
    assert code == 0, (code, out, err)
    assert out.strip() == "True True False", (out, err)

# 15) command-timeout blocks long-running command.
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

# 16) dry-run does not execute the wrapped command.
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

# 17) Checker timeout argument validation.
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

# 18) Command timeout argument validation.
code, out, err = run(
    "--command-timeout",
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

# 19) Command not found should return 1 with explicit message.
code, out, err = run(
    "--app",
    "website",
    "--action",
    "post",
    "--text",
    "Hello",
    "--",
    "definitely-missing-command",
)
assert code == 1, (code, out, err)
assert "Command not found" in err

# 20) Non-zero command exit code should be propagated.
code, out, err = run(
    "--app",
    "website",
    "--action",
    "post",
    "--text",
    "Hello",
    "--",
    "python3",
    "-c",
    "import sys; sys.exit(5)",
)
assert code == 5, (code, out, err)

# 21) Audit log writes JSONL and appends across runs.
with tempfile.TemporaryDirectory() as tmpdir:
    log_path = Path(tmpdir) / "guard_audit.jsonl"
    code1, out1, err1 = run(
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
    assert code1 == 0, (code1, out1, err1)

    code2, out2, err2 = run(
        "--audit-log",
        str(log_path),
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
        "print('nope')",
    )
    assert code2 == 0, (code2, out2, err2)

    lines = [line for line in log_path.read_text().splitlines() if line.strip()]
    assert len(lines) == 2, lines
    rec1 = json.loads(lines[0])
    rec2 = json.loads(lines[1])
    assert rec1["command_ran"] is True
    assert rec1["dry_run"] is False
    assert rec2["command_ran"] is False
    assert rec2["dry_run"] is True

print("ok")
