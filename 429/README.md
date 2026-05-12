# Midtrans 429 Bypass Browser
该脚本可过gopay的429限流，和跳过账单 直到手机号支付 ，适合个人使用
## What it does
1. Takes a Stripe checkout URL (`https://pay.openai.com/c/pay/cs_live_...`)
2. Automatically extracts `snap_token` from Stripe (no browser needed)
3. Opens **your system Chrome** with a persistent profile (`./chrome_profile`)
   - Extensions are **enabled** — install them normally, they persist between runs
4. **Intercepts all `/linking` POST requests and removes the `Authorization` header**
   - This bypasses Midtrans Envoy's 429 rate limiting
5. Logs all API traffic for debugging

## How to use

### Method 1: Double-click
1. Double-click `START.bat`
2. Paste the checkout URL when prompted
3. Browser opens, do your thing

### Method 2: Command line
```
python bypass_429.py <checkout_url>
```

### Method 3: Drag & drop
Drag a text file containing the URL onto `START.bat`

## Requirements
```
pip install curl_cffi playwright
playwright install chromium
```

## How the bypass works
Midtrans uses Envoy proxy with `X-Envoy-Ratelimited: true` to block
repeated `/linking` requests. The rate limit is triggered by the
`Authorization: Basic ...` header (which contains the Midtrans Client ID).

By removing this header and relying on session cookies set during
`load_transaction()`, we authenticate via cookies instead — Envoy's
rate limiter doesn't see the client ID and lets the request through.
