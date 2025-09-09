import json, subprocess, sys, os, pathlib

HERE = pathlib.Path(__file__).parent
PROJECT_ROOT = HERE.parent
SAMPLE = PROJECT_ROOT / "tests" / "fixtures" / "sample_whiteboard_session.json"
SCRIPT = PROJECT_ROOT / "scripts" / "validate_whiteboard_session.py"
SCHEMA = PROJECT_ROOT / "docs" / "schemas" / "whiteboard_session.schema.json"


def test_sample_session_valid():
    assert SAMPLE.is_file(), "Sample session fixture missing"
    cmd = [sys.executable, str(SCRIPT), str(SAMPLE), "--schema", str(SCHEMA)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print("STDOUT:", proc.stdout)
        print("STDERR:", proc.stderr)
    assert proc.returncode == 0, f"Validation failed: {proc.stderr}"
    data = json.loads(proc.stdout)
    assert data["status"] == "ok"
    assert data["event_count"] > 0


def test_monotonic_timestamps_enforced(tmp_path):
    payload = json.loads(SAMPLE.read_text())
    payload["events"][2]["t"] = 1  # violate monotonic order
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload))
    cmd = [sys.executable, str(SCRIPT), str(bad), "--schema", str(SCHEMA)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode != 0
    assert "monotonic" in proc.stderr.lower()
