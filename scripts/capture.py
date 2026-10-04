#!/usr/bin/env python3
"""Batch-capture screens for the pixel pass: screenshot + computed styles + console errors.

routes.txt    one `name|/path` per line (lines starting with # are ignored)
selectors.txt one CSS selector per line (e.g. header, nav a, .btn-primary, h1, table th)

Clone (HTTP basic auth, default):
  python scripts/capture.py --routes routes.txt --selectors selectors.txt --out evidence/raw/clone
Original DocuSign, reusing a Chrome you are already logged into
(start Chrome with --remote-debugging-port=9222 first):
  python scripts/capture.py --base https://app.docusign.com --no-auth --cdp http://localhost:9222 \
      --routes routes_original.txt --selectors selectors.txt --out evidence/raw/original
"""
import argparse, json, os
from playwright.sync_api import sync_playwright

PROPS = ["font-family", "font-size", "font-weight", "line-height", "color", "background-color",
         "padding", "margin", "border-radius", "border", "height", "width", "letter-spacing"]

JS = """([sels, props]) => {
  const rgb2hex = v => v.replace(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)(?:,\\s*([\\d.]+))?\\)/g,
    (m,r,g,b,a) => '#' + [r,g,b].map(x => (+x).toString(16).padStart(2,'0')).join('').toUpperCase() + (a && a !== '1' ? ` a=${a}` : ''));
  const out = {};
  for (const s of sels) {
    const els = [...document.querySelectorAll(s)].slice(0, 3);
    out[s] = els.map(el => {
      const cs = getComputedStyle(el), r = el.getBoundingClientRect(), o = {};
      for (const p of props) o[p] = rgb2hex(cs.getPropertyValue(p));
      o.rect = [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
      o.text = (el.innerText || '').trim().slice(0, 40);
      return o;
    });
  }
  return out;
}"""


def read_lines(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://13.207.185.159")
    ap.add_argument("--user", default=os.environ.get("DOCUSIGN_QA_USERNAME", ""))
    ap.add_argument("--password", default=os.environ.get("DOCUSIGN_QA_PASSWORD", ""))
    ap.add_argument("--no-auth", action="store_true")
    ap.add_argument("--cdp", default="", help="connect to an existing Chrome, e.g. http://localhost:9222")
    ap.add_argument("--routes", default="routes.txt")
    ap.add_argument("--selectors", default="selectors.txt")
    ap.add_argument("--out", default="evidence/raw")
    ap.add_argument("--wait", type=int, default=1500, help="ms to wait after load")
    a = ap.parse_args()
    if not a.no_auth and (not a.user or not a.password):
        ap.error("Set DOCUSIGN_QA_USERNAME and DOCUSIGN_QA_PASSWORD or pass --user and --password.")

    os.makedirs(a.out, exist_ok=True)
    routes = [l.split("|", 1) if "|" in l else [l.strip("/").replace("/", "_") or "home", l] for l in read_lines(a.routes)]
    sels = read_lines(a.selectors)
    styles, console = {}, {}

    with sync_playwright() as p:
        if a.cdp:
            browser = p.chromium.connect_over_cdp(a.cdp)
            ctx = browser.contexts[0]
        else:
            browser = p.chromium.launch()
            kw = {"viewport": {"width": 1280, "height": 960}, "device_scale_factor": 1, "ignore_https_errors": True}
            if not a.no_auth:
                kw["http_credentials"] = {"username": a.user, "password": a.password}
            ctx = browser.new_context(**kw)
        for name, path in routes:
            name = name.strip()
            msgs = []
            page = ctx.new_page()  # fresh page per route keeps console logs separate
            page.set_viewport_size({"width": 1280, "height": 960})
            page.on("console", lambda m, msgs=msgs: msgs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
            page.on("pageerror", lambda e, msgs=msgs: msgs.append(f"pageerror: {e}"))
            url = path if path.startswith("http") else a.base.rstrip("/") + "/" + path.strip().lstrip("/")
            try:
                resp = page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(a.wait)
                page.screenshot(path=os.path.join(a.out, f"{name}.png"), full_page=True)
                styles[name] = {"url": page.url, "status": resp.status if resp else None,
                                "title": page.title(), "styles": page.evaluate(JS, [sels, PROPS]) if sels else {}}
            except Exception as e:
                msgs.append(f"capture-failed: {e}")
            console[name] = msgs
            page.close()
            print(f"{name:24s} {len(msgs)} console issue(s)")
        if not a.cdp:
            browser.close()

    with open(os.path.join(a.out, "styles.json"), "w") as f:
        json.dump(styles, f, indent=1)
    with open(os.path.join(a.out, "console.json"), "w") as f:
        json.dump(console, f, indent=1)
    print("saved to", a.out)


if __name__ == "__main__":
    main()
