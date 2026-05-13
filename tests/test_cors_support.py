from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "orchestrator.py"


def test_orchestrator_supports_cors_preflight():
    source = ORCHESTRATOR.read_text(encoding="utf-8")

    assert "def _send_cors_headers(self):" in source
    assert "Access-Control-Allow-Origin" in source
    assert "Access-Control-Allow-Methods" in source
    assert "GET, POST, OPTIONS" in source
    assert "Access-Control-Allow-Headers" in source
    assert "Authorization, Content-Type" in source
    assert "def do_OPTIONS(self):" in source
