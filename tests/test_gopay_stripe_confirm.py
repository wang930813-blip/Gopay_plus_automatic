import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plus_gopay_links"))

from gopay import GoPayCharger


class FakeResponse:
    def __init__(self, payload, status_code=200, text=""):
        self.payload = payload
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.text or f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeExternalSession:
    def __init__(self, init_payload):
        self.headers = {}
        self.init_payload = init_payload
        self.posts = []

    def post(self, url, data=None, timeout=None):
        self.posts.append((url, dict(data or {})))
        if url.endswith("/init"):
            return FakeResponse(self.init_payload)
        if url.endswith("/confirm"):
            return FakeResponse({"setup_intent": {"status": "requires_action"}})
        raise AssertionError(f"unexpected URL {url}")


class FakeChatGPTSession:
    def __init__(self):
        self.headers = {"User-Agent": "pytest"}


def make_charger(init_payload):
    charger = GoPayCharger(
        FakeChatGPTSession(),
        {"country_code": "62", "phone_number": "81234567890", "pin": "123456"},
        otp_provider=lambda: "000000",
        log=lambda _message: None,
    )
    charger.ext = FakeExternalSession(init_payload)
    return charger


def confirm_expected_amount(init_payload):
    charger = make_charger(init_payload)

    charger._stripe_confirm("cs_test_123", "pm_test_123", "pk_test_123")

    confirm_posts = [
        data for url, data in charger.ext.posts
        if url.endswith("/confirm")
    ]
    assert confirm_posts
    return confirm_posts[-1]["expected_amount"]


def test_stripe_confirm_uses_payment_page_amount_total_from_init():
    amount = confirm_expected_amount({
        "init_checksum": "checksum",
        "payment_method_types": ["card", "gopay"],
        "currency": "idr",
        "payment_page": {"amount_total": 319000},
        "invoice": {"amount_due": 0},
    })

    assert amount == "319000"


def test_stripe_confirm_falls_back_to_invoice_amount_due():
    amount = confirm_expected_amount({
        "init_checksum": "checksum",
        "payment_method_types": ["gopay"],
        "currency": "idr",
        "payment_page": {},
        "invoice": {"amount_due": 319000},
    })

    assert amount == "319000"
