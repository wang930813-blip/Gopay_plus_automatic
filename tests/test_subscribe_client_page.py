from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "subscribe_client.html"


def test_standalone_page_exists_with_remote_url_input():
    source = PAGE.read_text(encoding="utf-8")

    assert 'id="apiUrl"' in source
    assert "https://plusapi.3737.cc.cd/subscribe" in source
    assert 'id="authToken"' in source
    assert 'value="shengzhi6666"' in source
    assert 'value="930813"' in source


def test_page_posts_subscribe_payload_and_shows_result():
    source = PAGE.read_text(encoding="utf-8")

    assert "fetch(apiUrl" in source
    assert "Authorization: `Bearer ${authToken}`" in source
    assert "session_token: sessionToken" in source
    assert "phone_number: phoneNumber" in source
    assert "pin" in source
    assert 'id="resultBody"' in source
    assert 'id="elapsed"' in source
