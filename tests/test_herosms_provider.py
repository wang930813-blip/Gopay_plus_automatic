import importlib.util
import ssl
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_orchestrator():
    sys.modules.setdefault("grpc", types.SimpleNamespace())
    sys.modules.setdefault("payment_pb2", types.SimpleNamespace())
    sys.modules.setdefault("payment_pb2_grpc", types.SimpleNamespace())

    config_path = ROOT / "config.json"
    restore_config = None
    if not config_path.exists():
        restore_config = config_path
        config_path.write_text((ROOT / "config.example.json").read_text(encoding="utf-8"), encoding="utf-8")

    spec = importlib.util.spec_from_file_location("orchestrator_under_test", ROOT / "orchestrator.py")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        if restore_config:
            restore_config.unlink()


def test_build_sms_api_url_keeps_existing_query_and_adds_api_key():
    orch = load_orchestrator()

    url = orch._build_sms_api_url(
        "https://hero-sms.com/stubs/handler_api.php?lang=cn",
        {"action": "getStatus", "id": "123", "api_key": "KEY"},
    )

    assert url == "https://hero-sms.com/stubs/handler_api.php?lang=cn&action=getStatus&id=123&api_key=KEY"


def test_match_herosms_activation_by_full_or_suffix_phone():
    orch = load_orchestrator()
    activations = [
        {"id": "old", "phone": "628000000000"},
        {"activationId": "new", "phoneNumber": "6281947801215"},
    ]

    assert orch._find_herosms_activation_id(activations, "81947801215") == "new"
    assert orch._find_herosms_activation_id(activations, "01215") == "new"


def test_match_herosms_activation_from_active_activations_rows():
    orch = load_orchestrator()
    response = {
        "status": "success",
        "data": [],
        "activeActivations": {
            "row": [],
            "rows": [
                {"activationId": "row-id", "phoneNumber": "6281947801215"},
            ],
        },
    }

    assert orch._find_herosms_activation_id(response, "81947801215") == "row-id"


def test_parse_herosms_otp_from_status_text_or_json():
    orch = load_orchestrator()

    assert orch._extract_herosms_otp("STATUS_OK:654321") == "654321"
    assert orch._extract_herosms_otp('{"status":"STATUS_OK","sms":"Your code is 123456"}') == "123456"
    assert orch._extract_herosms_otp("STATUS_WAIT_CODE") == ""


def test_create_ssl_context_prefers_certifi(monkeypatch):
    orch = load_orchestrator()
    calls = {}

    class FakeCertifi:
        @staticmethod
        def where():
            return "/tmp/certifi-ca.pem"

    def fake_create_default_context(cafile=None):
        calls["cafile"] = cafile
        return "ssl-context"

    monkeypatch.setitem(sys.modules, "certifi", FakeCertifi)
    monkeypatch.setattr(ssl, "create_default_context", fake_create_default_context)

    assert orch._create_ssl_context() == "ssl-context"
    assert calls["cafile"] == "/tmp/certifi-ca.pem"


def test_herosms_request_headers_use_browser_user_agent():
    orch = load_orchestrator()

    headers = orch._sms_api_headers()

    assert "Mozilla/5.0" in headers["User-Agent"]
    assert headers["Accept"] == "application/json,text/plain,*/*"
