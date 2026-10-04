#!/usr/bin/env python3
import os
from playwright.sync_api import sync_playwright
from auth_config import get_http_credentials

BASE = 'http://13.207.185.159'
USERNAME, PASSWORD = get_http_credentials()
AUTH = {'username': USERNAME, 'password': PASSWORD}
EVIDENCE_DIR = 'evidence'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={'width': 1280, 'height': 960}, http_credentials=AUTH, ignore_https_errors=True)
    page = ctx.new_page()
    page.goto(f'{BASE}/send/home', wait_until='networkidle')
    page.wait_for_timeout(1000)
    page.locator("button:has-text('Get Signatures')").first.click()
    page.wait_for_timeout(2000)

    # BUG-032: Invalid email
    email_in = page.locator("input[type=email], input[placeholder*='email' i], input[name*='email' i]").first
    if email_in.count() > 0:
        email_in.fill('invalid-email-no-at-sign')
        page.keyboard.press('Tab')
        page.wait_for_timeout(500)
    page.screenshot(path=os.path.join(EVIDENCE_DIR, 'BUG-032_prepare_invalid_email_recipient_validation.png'), full_page=True)
    print('Captured BUG-032')

    # BUG-033: Whitespace name
    name_in = page.locator("input[placeholder*='name' i], input[name*='name' i]").first
    if name_in.count() > 0:
        name_in.fill('   ')
        page.keyboard.press('Tab')
        page.wait_for_timeout(500)
    page.screenshot(path=os.path.join(EVIDENCE_DIR, 'BUG-033_prepare_whitespace_recipient_name.png'), full_page=True)
    print('Captured BUG-033')

    # BUG-035: Reminder frequency 0 days
    rem_btn = page.locator("button:has-text('Every 0 days')").first
    if rem_btn.count() > 0:
        try:
            rem_btn.click(force=True, timeout=2000)
            page.wait_for_timeout(500)
        except Exception:
            pass
    page.screenshot(path=os.path.join(EVIDENCE_DIR, 'BUG-035_prepare_reminder_frequency_zero_days.png'), full_page=True)
    print('Captured BUG-035')

    # BUG-036: Only signer checkbox
    cb = page.locator("input[type=checkbox]").first
    if cb.count() > 0:
        try:
            cb.check(force=True)
            page.wait_for_timeout(500)
        except Exception:
            pass
    page.screenshot(path=os.path.join(EVIDENCE_DIR, 'BUG-036_prepare_only_signer_toggle.png'), full_page=True)
    print('Captured BUG-036')

    browser.close()
