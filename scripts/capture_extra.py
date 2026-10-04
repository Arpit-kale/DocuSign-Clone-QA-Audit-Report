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

    # BUG-043: Agreements status filter dropdown
    page.goto(f'{BASE}/send/documents', wait_until='networkidle')
    page.wait_for_timeout(1000)
    status_filter = page.locator("button:has-text('Status'), [role=button]:has-text('Status')").first
    if status_filter.count() > 0:
        status_filter.click(force=True)
        page.wait_for_timeout(500)
    page.screenshot(path=os.path.join(EVIDENCE_DIR, 'BUG-043_agreements_status_filter_options.png'), full_page=True)
    print('Captured BUG-043')

    # BUG-044: Header Logo accessibility / alt tag
    page.goto(f'{BASE}/send/home', wait_until='networkidle')
    page.wait_for_timeout(1000)
    page.screenshot(path=os.path.join(EVIDENCE_DIR, 'BUG-044_nav_brand_logo_accessibility.png'), full_page=True)
    print('Captured BUG-044')

    # BUG-045: Prepare message character counter
    page.locator("button:has-text('Get Signatures')").first.click()
    page.wait_for_timeout(2000)
    page.screenshot(path=os.path.join(EVIDENCE_DIR, 'BUG-045_prepare_character_counter_message.png'), full_page=True)
    print('Captured BUG-045')

    browser.close()
