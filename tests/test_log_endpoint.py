from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "orchestrator.py"
PAGE = ROOT / "subscribe_client.html"


def test_orchestrator_exposes_recent_logs_endpoint():
    source = ORCHESTRATOR.read_text(encoding="utf-8")

    assert 'self.path.startswith("/logs")' in source
    assert "def read_recent_logs" in source
    assert "orchestrator.log" in source
    assert '"lines"' in source


def test_logs_endpoint_is_not_logged_to_itself():
    source = ORCHESTRATOR.read_text(encoding="utf-8")
    match = re.search(r"def log_message\(self, fmt, \*args\):(?P<body>.*?)(?=\ndef |\nclass |\Z)", source, re.S)

    assert match
    assert 'if self.path.startswith("/logs"):' in match.group("body")
    assert "return" in match.group("body")
    assert 'log.info("HTTP %s %s"' in match.group("body")


def test_client_polls_logs_while_request_is_running():
    source = PAGE.read_text(encoding="utf-8")

    assert "startLogPolling(apiUrl)" in source
    assert "stopLogPolling()" in source
    assert "fetch(logUrl" in source
    assert "serviceLog" in source
