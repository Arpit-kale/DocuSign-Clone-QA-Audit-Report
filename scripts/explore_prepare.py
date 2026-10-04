#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Explore the prepare page."""
import sys
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

import os, json
from playwright.sync_api import sync_playwright
from auth_config import get_http_credentials

BASE = "http://13.207.185.159"
USERNAME, PASSWORD = get_http_credentials()
AUTH = {"username": USERNAME, "password": PASSWORD}
EVIDENCE = "evidence/raw"
findings = []

def ss(page, name):
    path = os.path.join(EVIDENCE, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    return path

def log(screen, finding, severity, category, details="", evidence=""):
    findings.append({"screen": screen, "finding": finding,
                     "severity": severity, "category": category,
                     "details": details, "evidence": evidence})
    print(f"  [FIND-{severity}] {screen}: {finding[:80]}")

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 960},
            http_credentials=AUTH,
            ignore_https_errors=True
        )
        page = ctx.new_page()

        # ==============================================================
        # PREPARE PAGE - from Get Signatures
        # ==============================================================
        print("\n[PREPARE PAGE]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        get_sig = page.locator("button:has-text('Get Signatures')").first
        if get_sig.is_visible():
            get_sig.click()
            page.wait_for_timeout(3000)
            prepare_url = page.url
            print(f"  Prepare URL: {prepare_url}")
            p_prepare = ss(page, "prepare_page_full")
            
            prepare_text = page.evaluate("document.body.innerText")
            print(f"  Full prepare page text:\n{prepare_text[:2000]}")
            
            # Check for elements
            elements = page.evaluate("""() => {
                return {
                    hasFileInput: !!document.querySelector('input[type=file]'),
                    hasCanvas: !!document.querySelector('canvas'),
                    hasIframe: !!document.querySelector('iframe'),
                    iframeCount: document.querySelectorAll('iframe').length,
                    iframeSrcs: [...document.querySelectorAll('iframe')].map(f => f.src.slice(0, 100)),
                    buttons: [...document.querySelectorAll('button')].map(b => b.innerText.trim()).filter(t => t),
                    inputs: [...document.querySelectorAll('input')].map(i => ({type: i.type, placeholder: i.placeholder, name: i.name})),
                    links: [...document.querySelectorAll('a[href]')].map(a => ({text: a.innerText.trim(), href: a.href})),
                    h1: [...document.querySelectorAll('h1,h2,h3')].map(h => ({tag: h.tagName, text: h.innerText.trim()})),
                    errorMsgs: [...document.querySelectorAll('[class*=error],[class*=Error],[role=alert]')].map(e => e.innerText.trim()).filter(t => t)
                };
            }""")
            print(f"\n  Elements:")
            for k, v in elements.items():
                if v: print(f"    {k}: {v}")
            
            # Check recipients section
            recipients_section = page.evaluate("""() => {
                const body = document.body.innerText;
                const idx = body.toLowerCase().indexOf('recipient');
                return idx >= 0 ? body.slice(idx, idx + 500) : 'no recipients section';
            }""")
            print(f"\n  Recipients section: {recipients_section[:400]}")
            
            # Check if there are fields panel / sidebar
            fields_panel = page.evaluate("""() => {
                const body = document.body.innerText;
                const words = ['Signature', 'Initials', 'Date Signed', 'Text', 'Checkbox', 'Radio', 'Dropdown', 'Field'];
                return words.filter(w => body.includes(w));
            }""")
            print(f"  Field types available: {fields_panel}")
            
            # Look for specific recipients form inputs
            recipient_form = page.evaluate("""() => {
                const inputs = [...document.querySelectorAll('input')];
                return inputs.map(i => ({
                    type: i.type,
                    placeholder: i.placeholder,
                    name: i.name,
                    id: i.id,
                    value: i.value
                }));
            }""")
            print(f"  Input fields: {recipient_form}")

            # Screenshot after exploring - annotate prepare page
            p_prepare2 = ss(page, "prepare_page_annotated")
            
            # Scroll down to see more
            page.evaluate("window.scrollTo(0, 500)")
            page.wait_for_timeout(500)
            p_prepare_scrolled = ss(page, "prepare_page_scrolled")
            print(f"  Prepare page screenshots: {p_prepare}, {p_prepare2}, {p_prepare_scrolled}")

        # ==============================================================
        # PREPARE PAGE - URL directly
        # ==============================================================
        print("\n[PREPARE PAGE - DIRECT URL]")
        page.goto(BASE + "/send/prepare/16037?isNew=true", wait_until="networkidle")
        page.wait_for_timeout(3000)
        
        # Try to find a recipient form
        recipient_inputs = page.locator("input[placeholder*='Name'], input[placeholder*='Email'], input[placeholder*='name'], input[placeholder*='email']").all()
        print(f"  Recipient inputs: {len(recipient_inputs)}")
        
        if not recipient_inputs:
            # Look for any specific text area sections
            all_inputs = page.locator("input").all()
            print(f"  All inputs: {len(all_inputs)}")
            
        # Try adding a recipient
        # Look for "Add Recipient" button
        add_recipient = page.locator("button:has-text('Add'), button:has-text('Recipient'), button:has-text('Add Recipient')").first
        if add_recipient.count() > 0:
            print(f"  Add Recipient button found: '{add_recipient.evaluate('el => el.innerText.trim()')}'")
            add_recipient.click()
            page.wait_for_timeout(1500)
            after_add = page.evaluate("document.body.innerText")
            print(f"  After add recipient click: {after_add[:300]}")
        
        # Check for "Next" or "Send" buttons in prepare flow
        flow_btns = page.locator("button:has-text('Next'), button:has-text('Send'), button:has-text('Finish')").all()
        print(f"  Flow buttons: {[b.evaluate('el => el.innerText.trim()') for b in flow_btns]}")

        # ==============================================================
        # AGREEMENTS - Check "Download" buttons work
        # ==============================================================
        print("\n[DOWNLOAD BUTTON]")
        page.goto(BASE + "/send/documents?view=inbox", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        download_btns = page.locator("button:has-text('Download')").all()
        print(f"  Download buttons: {len(download_btns)}")
        
        if download_btns:
            # Set up download listener
            with page.expect_download(timeout=5000) as download_info:
                try:
                    download_btns[0].click()
                    download = download_info.value
                    print(f"  Download triggered: {download.suggested_filename}")
                except Exception as e:
                    print(f"  Download error: {e}")

        # ==============================================================
        # CHECK HOME - Welcome message is "John Doe" (hardcoded)
        # ==============================================================
        print("\n[HOME - HARDCODED USER DATA]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        welcome_text = page.evaluate("""() => {
            const els = [...document.querySelectorAll('*')];
            for (const el of els) {
                if (el.children.length === 0 && el.innerText?.includes('Welcome back,')) {
                    return el.parentElement?.innerText;
                }
            }
            return document.body.innerText.slice(0, 200);
        }""")
        print(f"  Welcome section: {welcome_text}")
        
        # Check if John Doe is the only/hardcoded user
        if "John Doe" in str(welcome_text):
            p_hardcoded = ss(page, "home_hardcoded_john_doe")
            log("Home", "Username 'John Doe' appears hardcoded in welcome message",
                "P2", "Data / Seeded",
                "Welcome back section shows 'John Doe' -- appears to be hardcoded placeholder, not dynamic from auth context.",
                p_hardcoded)

        # Check avatar initials
        avatar_text = page.evaluate("""() => {
            const btn = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'JD');
            return btn ? btn.innerText.trim() : null;
        }""")
        print(f"  Avatar initials: {avatar_text}")
        if avatar_text == 'JD':
            log("Home -> Header", "Avatar shows 'JD' (John Doe initials) - hardcoded, not derived from auth user",
                "P2", "Data / Seeded",
                "Header avatar shows 'JD' instead of the signed-in user's identity.",
                p_hardcoded if 'p_hardcoded' in dir() else "")

        # ==============================================================
        # CHECK AGREEMENTS - Timestamp formats
        # ==============================================================
        print("\n[AGREEMENTS - DATES]")
        page.goto(BASE + "/send/documents?view=sent", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        all_text = page.evaluate("document.body.innerText")
        # Find date patterns
        import re
        dates = re.findall(r'\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}', all_text)
        print(f"  Dates found: {dates}")
        
        # ==============================================================
        # CHECK TEMPLATES - "Create Template" detailed
        # ==============================================================
        print("\n[CREATE TEMPLATE - DETAILED]")
        page.goto(BASE + "/send/templates", wait_until="networkidle")
        page.wait_for_timeout(1500)
        create_tmpl = page.locator("button:has-text('Create Template')").first
        if create_tmpl.is_visible():
            create_tmpl.click()
            page.wait_for_timeout(3000)
            ct_url = page.url
            ct_modal = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog]');
                return m ? {text: m.innerText, hasFileInput: !!m.querySelector('input[type=file]')} : null;
            }""")
            print(f"  Create Template URL: {ct_url}")
            print(f"  Create Template modal: {ct_modal}")
            p_ct = ss(page, "create_template_after_click")
            if ct_url == BASE + "/send/templates" and not ct_modal:
                log("Templates", "'Create Template' button produces no visible action",
                    "P1", "Functional",
                    "Clicked 'Create Template' button. URL: /send/templates, no modal or page change.",
                    p_ct)

        # ==============================================================
        # CHECK GLOBAL - Focus ring / accessibility
        # ==============================================================
        print("\n[ACCESSIBILITY - FOCUS RING]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        # Check if focus outline is visible
        focus_styles = page.evaluate("""() => {
            const btn = document.querySelector('button');
            if (!btn) return null;
            btn.focus();
            const cs = getComputedStyle(btn);
            return {
                outline: cs.outline,
                outlineStyle: cs.outlineStyle,
                outlineColor: cs.outlineColor,
                outlineWidth: cs.outlineWidth
            };
        }""")
        print(f"  Focus styles: {focus_styles}")

        print("\n[DONE - Prepare page exploration complete]")
        browser.close()

    with open("evidence/raw/prepare_findings.json", "w") as f:
        json.dump(findings, f, indent=2)
    print(f"Total findings: {len(findings)}")
    print("Saved: evidence/raw/prepare_findings.json")

if __name__ == "__main__":
    run()
