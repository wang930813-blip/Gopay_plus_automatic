from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOPAY = ROOT / "plus_gopay_links" / "gopay.py"


def test_sms_switch_uses_resend_otp_endpoint_and_reference_payload():
    source = GOPAY.read_text(encoding="utf-8")

    assert "https://gwa.gopayapi.com/v1/linking/resend-otp" in source
    assert 'body = {"reference_id": reference_id}' in source
    assert 'body = {"reference_id": reference_id, "otp_channel": "sms"}' not in source
