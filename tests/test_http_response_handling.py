from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "orchestrator.py"


def test_json_response_handles_disconnected_client():
    source = ORCHESTRATOR.read_text(encoding="utf-8")

    assert "except (BrokenPipeError, ConnectionResetError):" in source
    assert "client disconnected before response was sent" in source
