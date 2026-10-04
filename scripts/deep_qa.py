#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 3 deep functional pass - focuses on all key bugs."""
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
        errs = []
        page.on("console", lambda m: errs.append(f"{m.type}: {m.text}") if m.type in ("error","warning") else None)
        page.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))

        # ==============================================================
        # A. AGREEMENTS / DOCUMENTS - detailed
        # ==============================================================
        print("\n[AGREEMENTS - DETAILED]")
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(2000)
        p_agreements = ss(page, "agreements_default")

        # Check which tab is active by default
        active_indicator = page.evaluate("""() => {
            const links = document.querySelectorAll('[href]');
            for (const l of links) {
                if (l.className && l.className.includes('active')) {
                    return {href: l.href, text: l.innerText.trim(), cls: l.className};
                }
            }
            return null;
        }""")
        print(f"  Active link: {active_indicator}")
        # Default tab should be Inbox per DocuSign
        if active_indicator and 'inbox' not in str(active_indicator.get('href','')):
            log("Agreements", "Default active tab is not Inbox on /send/documents",
                "P2", "Functional",
                f"Active link: {active_indicator}",
                p_agreements)

        # Check that filter columns exist in table
        table_headers = page.evaluate("""() => {
            const ths = document.querySelectorAll('th, [role=columnheader]');
            return [...ths].map(t => t.innerText.trim()).filter(t => t);
        }""")
        print(f"  Table headers: {table_headers}")

        # Check row count vs sidebar count
        rows = page.evaluate("""() => {
            // Find table rows (excluding header)
            const tbody = document.querySelector('tbody');
            if (tbody) return tbody.querySelectorAll('tr').length;
            // Try other row selectors
            const rows = document.querySelectorAll('[role=row]');
            return rows.length;
        }""")
        print(f"  Table row count: {rows}")

        # Check document names in seeded data
        doc_names = page.evaluate("""() => {
            const buttons = [...document.querySelectorAll('button')];
            return buttons.map(b => b.innerText.trim()).filter(t =>
                t.includes('.pdf') || t.includes('Untitled') || t.includes('lorem') || t.includes('test')
            );
        }""")
        print(f"  Seeded document names: {doc_names}")
        if doc_names:
            p_seeded = ss(page, "agreements_seeded_data")
            log("Agreements", f"Seeded data visible: {doc_names[0][:60]}",
                "P3", "Data / Seeded",
                f"Visible seeded documents: {doc_names}",
                p_seeded)

        # Check filename: "Companies Hiring - October.pdf.pdf" - double extension
        for name in doc_names:
            if '.pdf.pdf' in name:
                log("Agreements", f"Filename with double .pdf extension: '{name[:60]}'",
                    "P3", "Data / Seeded",
                    f"Filename '{name}' shows .pdf.pdf double extension",
                    p_seeded if 'p_seeded' in dir() else "")

        # Check Sent tab - what columns appear
        page.goto(BASE + "/send/documents?view=sent", wait_until="networkidle")
        page.wait_for_timeout(2000)
        p_sent = ss(page, "agreements_sent")
        sent_headers = page.evaluate("""() => {
            const ths = document.querySelectorAll('th, [role=columnheader]');
            return [...ths].map(t => t.innerText.trim()).filter(t => t);
        }""")
        print(f"  Sent tab headers: {sent_headers}")
        sent_btns = page.evaluate("""() => {
            return [...document.querySelectorAll('button')].map(b => b.innerText.trim()).filter(t => t.length > 2);
        }""")
        print(f"  Sent tab buttons: {sent_btns[:15]}")

        # Status column in sent tab - check badge colors
        sent_statuses = page.evaluate("""() => {
            const badges = document.querySelectorAll('[class*=badge], [class*=status], [class*=Status]');
            return [...badges].map(b => ({text: b.innerText.trim(), cls: b.className, color: getComputedStyle(b).color, bg: getComputedStyle(b).backgroundColor}));
        }""")
        print(f"  Sent status badges: {sent_statuses[:5]}")

        # Check if "Sender" column appears in Sent view (it shouldn't - should be "Recipients")
        if sent_headers and 'SENDER' in ' '.join(sent_headers).upper():
            log("Agreements -> Sent", "Sent tab shows 'Sender' column instead of 'Recipients'",
                "P2", "Functional",
                f"Sent tab columns: {sent_headers}. Expected Recipients column, not Sender.",
                p_sent)

        # Completed tab
        page.goto(BASE + "/send/documents?view=completed", wait_until="networkidle")
        page.wait_for_timeout(2000)
        p_completed = ss(page, "agreements_completed")
        completed_text = page.evaluate("document.body.innerText")
        completed_rows = page.evaluate("""() => {
            const body = document.body.innerText;
            const lines = body.split('\\n').map(l => l.trim()).filter(l => l);
            return lines.slice(0, 40);
        }""")
        print(f"  Completed tab content: {completed_rows[:20]}")

        # Action Required tab
        page.goto(BASE + "/send/documents?view=action-required", wait_until="networkidle")
        page.wait_for_timeout(2000)
        p_action = ss(page, "agreements_action_required")
        action_text = page.evaluate("document.body.innerText")
        print(f"  Action Required content len: {len(action_text)}")
        # Check if empty or has data
        if "no" in action_text.lower() and "action" in action_text.lower():
            print("  Action Required: empty state shown")

        # ==============================================================
        # B. START -> UPLOAD FLOW (via "Get Signatures")
        # ==============================================================
        print("\n[PREPARE/UPLOAD FLOW]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # Click "Get Signatures" which navigated to prepare page
        get_sig = page.locator("button:has-text('Get Signatures')").first
        if get_sig.is_visible():
            get_sig.click()
            page.wait_for_timeout(3000)
            prepare_url = page.url
            print(f"  Prepare URL: {prepare_url}")
            p_prepare = ss(page, "prepare_page")
            
            # Check what's on the prepare page
            prepare_text = page.evaluate("document.body.innerText")
            print(f"  Prepare page content (300): {prepare_text[:300]}")
            
            prepare_elements = page.evaluate("""() => {
                return {
                    hasFileInput: !!document.querySelector('input[type=file]'),
                    hasUploadArea: !!document.querySelector('[class*=upload], [class*=Upload], [class*=drop]'),
                    buttons: [...document.querySelectorAll('button')].map(b => b.innerText.trim()).filter(t => t),
                    inputs: [...document.querySelectorAll('input')].map(i => ({type: i.type, placeholder: i.placeholder, name: i.name})),
                    iframeCount: document.querySelectorAll('iframe').length
                };
            }""")
            print(f"  Prepare elements: {prepare_elements}")
            
            if '/prepare/' in prepare_url:
                # This navigated to an existing seeded envelope prepare page
                envelope_id = prepare_url.split('/prepare/')[-1].split('?')[0]
                print(f"  Seeded envelope ID: {envelope_id}")
                log("Home -> Prepare", f"'Get Signatures' button opens a pre-seeded existing envelope (ID:{envelope_id}) instead of a new one",
                    "P1", "Data / Seeded",
                    f"URL: {prepare_url}. Clicking 'Get Signatures' from Home should start a fresh upload, but navigates to a pre-existing seeded envelope.",
                    p_prepare)

        # ==============================================================
        # C. "Start" button flow  
        # ==============================================================
        print("\n[START BUTTON FLOW]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        start_btn = page.locator("button:has-text('Start')").first
        if start_btn.is_visible():
            # Check button styling
            start_styles = page.evaluate("""() => {
                const btn = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'Start');
                if (!btn) return null;
                const cs = getComputedStyle(btn);
                return {
                    bg: cs.backgroundColor,
                    color: cs.color,
                    border: cs.border,
                    borderRadius: cs.borderRadius,
                    padding: cs.padding,
                    fontWeight: cs.fontWeight
                };
            }""")
            print(f"  Start button styles: {start_styles}")
            
            start_btn.click()
            page.wait_for_timeout(2000)
            after_start = page.url
            modal = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog]');
                return m ? {visible: true, text: m.innerText.slice(0, 300)} : {visible: false};
            }""")
            print(f"  After Start click URL: {after_start}, modal: {modal}")
            
            if after_start == BASE + "/send/home" and not modal.get('visible'):
                p_start = ss(page, "start_button_no_action")
                log("Home", "'Start' button click produces no action (no modal, no navigation)",
                    "P0", "Functional",
                    "Clicked 'Start' button on Home page. URL stayed at /send/home, no modal appeared, no upload dialog shown.",
                    p_start)

        # ==============================================================
        # D. "Send with AI" flow
        # ==============================================================
        print("\n[SEND WITH AI FLOW]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        ai_btn = page.locator("button:has-text('Send with AI')").first
        if ai_btn.is_visible():
            ai_btn.click()
            page.wait_for_timeout(2000)
            ai_url = page.url
            ai_modal = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog]');
                return m ? m.innerText.slice(0,300) : null;
            }""")
            print(f"  After 'Send with AI': URL={ai_url}, modal={ai_modal}")
            if ai_url == BASE + "/send/home" and not ai_modal:
                p_ai = ss(page, "send_with_ai_no_action")
                log("Home", "'Send with AI' button produces no action (no modal, no navigation)",
                    "P1", "Functional",
                    "Clicked 'Send with AI'. URL: /send/home, no modal appeared.",
                    p_ai)

        # ==============================================================
        # E. Overview stats buttons
        # ==============================================================
        print("\n[OVERVIEW STATS]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        # Check stat values
        stats_info = page.evaluate("""() => {
            const btns = [...document.querySelectorAll('button')];
            return btns
                .filter(b => ['Waiting for others', 'Expiring soon', 'Completed'].some(t => b.innerText.includes(t)))
                .map(b => {
                    const cs = getComputedStyle(b);
                    return {
                        text: b.innerText.trim(),
                        clickable: b.onclick !== null || b.getAttribute('onclick') !== null,
                        cursor: cs.cursor
                    };
                });
        }""")
        print(f"  Stats info: {stats_info}")
        
        for stat_name in ['Waiting for others', 'Expiring soon', 'Completed']:
            stat_btn = page.locator(f"button:has-text('{stat_name}')").first
            if stat_btn.count() > 0:
                stat_btn.click()
                page.wait_for_timeout(1500)
                after_url = page.url
                print(f"  After '{stat_name}' click: {after_url}")
                if after_url == BASE + "/send/home":
                    log("Home -> Overview", f"'{stat_name}' stat button does not navigate (stays on Home)",
                        "P2", "Functional",
                        f"Expected to navigate to filtered agreements view. Stayed at: {after_url}",
                        "")
                page.goto(BASE + "/send/home", wait_until="networkidle")
                page.wait_for_timeout(1000)

        # ==============================================================
        # F. HOME PAGE - Missing h1 heading
        # ==============================================================
        print("\n[SEO / ACCESSIBILITY]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        h1_count = page.evaluate("document.querySelectorAll('h1').length")
        h2_count = page.evaluate("document.querySelectorAll('h2').length")
        h3_count = page.evaluate("document.querySelectorAll('h3').length")
        print(f"  Heading counts - h1:{h1_count}, h2:{h2_count}, h3:{h3_count}")
        
        if h1_count == 0:
            p_h1 = ss(page, "home_no_h1")
            log("Home", "No <h1> element on Home page (SEO and accessibility violation)",
                "P3", "Content / Copy",
                f"h1 count: {h1_count}, h2 count: {h2_count}. Page uses 'Welcome back, John Doe' as visual heading but in a div/p, not h1.",
                p_h1)

        # Check agreements page too
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(1500)
        agreements_h1 = page.evaluate("document.querySelectorAll('h1').length")
        agreements_h2 = page.evaluate("document.querySelectorAll('h2').length")
        print(f"  Agreements headings - h1:{agreements_h1}, h2:{agreements_h2}")

        # ==============================================================
        # G. FOOTER LINKS - all dead
        # ==============================================================
        print("\n[FOOTER LINKS CHECK]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        footer_links = page.evaluate("""() => {
            const links = document.querySelectorAll('a[href]');
            return [...links]
                .filter(a => ['Contact Us','Terms of Use','Privacy','Intellectual Property','Trust','Support Home','Community'].some(t => a.innerText.includes(t)))
                .map(a => ({text: a.innerText.trim(), href: a.href}));
        }""")
        print(f"  Footer links: {footer_links}")
        dead_links = [l for l in footer_links if l['href'].endswith('#') or l['href'] == BASE + '/send/home#']
        if dead_links:
            p_footer = ss(page, "footer_dead_links")
            log("Home -> Footer", f"All {len(dead_links)} footer links are dead (href='#')",
                "P2", "Functional",
                f"Links: {[l['text'] for l in dead_links]} all resolve to '#'. Should point to real DocuSign pages.",
                p_footer)

        # Also check "View Plans" and "View Our Guide" and "Support Home"
        other_links = page.evaluate("""() => {
            const links = document.querySelectorAll('a[href], button');
            return [...links]
                .filter(el => ['View Plans','View Our Guide','Support Home','Community','Trust Center'].some(t => el.innerText.includes(t)))
                .map(el => ({text: el.innerText.trim(), tag: el.tagName, href: el.href || 'button'}));
        }""")
        print(f"  Other CTA links: {other_links}")

        # ==============================================================
        # H. PAGE TITLES
        # ==============================================================
        print("\n[PAGE TITLES]")
        for route, name in [('/send/home', 'Home'), ('/send/documents', 'Agreements'), ('/send/templates', 'Templates')]:
            page.goto(BASE + route, wait_until="networkidle")
            page.wait_for_timeout(1000)
            title = page.title()
            desc = page.evaluate("document.querySelector('meta[name=description]')?.content")
            print(f"  {name}: title='{title}', desc='{desc}'")
            if 'Rl_Docusign' in title or 'Rl ' in title:
                log(name, f"Page title '{title}' uses internal/test branding instead of proper title",
                    "P3", "Content / Copy",
                    f"Title: '{title}'. Should be e.g. '{name} | DocuSign'", "")

        # ==============================================================
        # I. TEMPLATES - "Create Template" button
        # ==============================================================
        print("\n[CREATE TEMPLATE]")
        page.goto(BASE + "/send/templates", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        create_tmpl = page.locator("button:has-text('Create Template')").first
        if create_tmpl.is_visible():
            create_tmpl.click()
            page.wait_for_timeout(2000)
            create_url = page.url
            create_modal = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog]');
                return m ? m.innerText.slice(0, 300) : null;
            }""")
            print(f"  After 'Create Template': URL={create_url}, modal={create_modal}")
            if create_url == BASE + "/send/templates" and not create_modal:
                p_create = ss(page, "create_template_no_action")
                log("Templates", "'Create Template' button produces no action (no modal, no navigation)",
                    "P1", "Functional",
                    "Clicked 'Create Template'. URL stayed at /send/templates, no modal or navigation.",
                    p_create)

        # Template "NEW" badges - Workflow Templates and Template Gallery
        new_badges = page.evaluate("""() => {
            const spans = [...document.querySelectorAll('span, div')];
            return spans.filter(s => s.innerText.trim() === 'NEW')
                        .map(s => ({text: s.innerText.trim(), parent: s.parentElement?.innerText?.trim()?.slice(0,50)}));
        }""")
        print(f"  NEW badges: {new_badges}")

        # Check pagination widget
        page.goto(BASE + "/send/templates", wait_until="networkidle")
        page.wait_for_timeout(1500)
        pagination = page.evaluate("""() => {
            const selects = document.querySelectorAll('select');
            const pageParts = document.body.innerText.match(/\\d+ \\/ Page/g);
            return {selects: [...selects].map(s => s.value), pageParts};
        }""")
        print(f"  Pagination: {pagination}")

        # ==============================================================
        # J. AGREEMENTS - Action Required tab empty state
        # ==============================================================
        print("\n[ACTION REQUIRED EMPTY STATE]")
        page.goto(BASE + "/send/documents?view=action-required", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        ar_text = page.evaluate("document.body.innerText")
        # Check if it has meaningful empty state
        has_content = any(word in ar_text.lower() for word in ['agreement', 'document', 'sign', 'task'])
        print(f"  Action Required has content: {has_content}")
        print(f"  Action Required text: {ar_text[ar_text.find('Action Required'):ar_text.find('Action Required')+300]}")

        # ==============================================================
        # K. SIGN A DOCUMENT modal details
        # ==============================================================
        print("\n[SIGN A DOCUMENT MODAL]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        sign_btn = page.locator("button:has-text('Sign a Document')").first
        if sign_btn.is_visible():
            sign_btn.click()
            page.wait_for_timeout(2000)
            modal_content = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog]');
                if (!m) return null;
                return {
                    text: m.innerText,
                    hasFileInput: !!m.querySelector('input[type=file]'),
                    buttons: [...m.querySelectorAll('button')].map(b => b.innerText.trim()),
                    inputs: [...m.querySelectorAll('input')].map(i => ({type: i.type, placeholder: i.placeholder}))
                };
            }""")
            print(f"  Sign modal: {modal_content}")
            
            if modal_content:
                # Test Esc to close
                p_sign_modal = ss(page, "sign_document_modal_open")
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)
                modal_after_esc = page.evaluate("!!document.querySelector('[role=dialog]')")
                print(f"  Modal after Esc: {modal_after_esc}")
                if not modal_after_esc:
                    print("  Sign modal closes on Esc - OK")
                else:
                    log("Home -> Sign modal", "Sign a Document modal does not close on Escape key",
                        "P2", "Functional",
                        "Pressed Escape key while Sign a Document modal was open; modal remained visible.",
                        p_sign_modal)

                # Re-open and test outside click
                sign_btn2 = page.locator("button:has-text('Sign a Document')").first
                if sign_btn2.is_visible():
                    sign_btn2.click()
                    page.wait_for_timeout(1500)
                    page.mouse.click(50, 50)  # Click outside
                    page.wait_for_timeout(1000)
                    modal_after_outside = page.evaluate("!!document.querySelector('[role=dialog]')")
                    print(f"  Modal after outside click: {modal_after_outside}")
                    if modal_after_outside:
                        log("Home -> Sign modal", "Sign a Document modal does not close on outside click",
                            "P2", "Functional",
                            "Clicked outside Sign a Document modal; modal remained visible.",
                            "")

                # Test file upload in sign modal
                sign_btn3 = page.locator("button:has-text('Sign a Document')").first
                if sign_btn3.is_visible():
                    sign_btn3.click()
                    page.wait_for_timeout(1500)
                    modal_file_input = page.locator("[role=dialog] input[type=file]").first
                    if modal_file_input.count() > 0:
                        # Upload a PDF
                        import os as _os
                        pdf_path = _os.path.join(_os.getcwd(), "test_sample.pdf")
                        modal_file_input.set_input_files(pdf_path)
                        page.wait_for_timeout(3000)
                        after_upload_url = page.url
                        after_text = page.evaluate("document.body.innerText[:300]") if False else ""
                        p_sign_upload = ss(page, "sign_document_after_upload")
                        print(f"  After sign upload: URL={after_upload_url}")
                    else:
                        print("  No file input in sign modal - upload might use drop area")

        # ==============================================================
        # L. AGREEMENTS - Check "Sender" column - should it show?
        # ==============================================================
        print("\n[AGREEMENTS TABLE COLUMNS]")
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        # Get table structure
        table_info = page.evaluate("""() => {
            const table = document.querySelector('table');
            if (!table) return 'no table';
            const headers = [...table.querySelectorAll('th')].map(th => th.innerText.trim());
            const firstRow = table.querySelector('tbody tr');
            const cells = firstRow ? [...firstRow.querySelectorAll('td')].map(td => td.innerText.trim().slice(0, 60)) : [];
            return {headers, firstRow: cells};
        }""")
        print(f"  Table info: {table_info}")

        # ==============================================================
        # M. EMPTY STATE CONSISTENCY
        # ==============================================================
        print("\n[EMPTY STATE CHECK]")
        page.goto(BASE + "/send/documents?view=inbox", wait_until="networkidle")
        page.wait_for_timeout(2000)
        inbox_text = page.evaluate("document.body.innerText")
        print(f"  Inbox content: {inbox_text[inbox_text.find('Inbox'):inbox_text.find('Inbox')+400] if 'Inbox' in inbox_text else inbox_text[:400]}")
        
        # Check if inbox shows "is empty" message properly
        if 'is empty' in inbox_text:
            empty_fragment = inbox_text[inbox_text.find('is empty')-20:inbox_text.find('is empty')+200]
            print(f"  Empty state: {empty_fragment}")
        
        # ==============================================================
        # N. AGREEMENTS - Check filter buttons
        # ==============================================================
        print("\n[AGREEMENTS FILTERS]")
        page.goto(BASE + "/send/documents?view=sent", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        # Click Date filter
        date_btn = page.locator("button:has-text('Date')").first
        if date_btn.count() > 0 and date_btn.is_visible():
            date_btn.click()
            page.wait_for_timeout(1500)
            date_dropdown = page.evaluate("""() => {
                const dropdown = document.querySelector('[role=listbox], [role=menu], select');
                return dropdown ? dropdown.innerText.slice(0, 300) : 'no dropdown';
            }""")
            print(f"  Date filter dropdown: {date_dropdown}")
            p_date_filter = ss(page, "agreements_date_filter")
            # Press Esc to close
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)

        # Click Status filter
        page.goto(BASE + "/send/documents?view=sent", wait_until="networkidle")
        page.wait_for_timeout(1500)
        status_btn = page.locator("button:has-text('Status')").first
        if status_btn.count() > 0 and status_btn.is_visible():
            status_btn.click()
            page.wait_for_timeout(1500)
            status_dropdown = page.evaluate("""() => {
                const dropdown = document.querySelector('[role=listbox], [role=menu]');
                return dropdown ? dropdown.innerText.slice(0, 300) : 'no dropdown';
            }""")
            print(f"  Status filter dropdown: {status_dropdown}")
            p_status_filter = ss(page, "agreements_status_filter")
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)

        # ==============================================================
        # O. CHECK AGREEMENTS ROW ACTIONS
        # ==============================================================
        print("\n[AGREEMENTS ROW ACTIONS]")
        page.goto(BASE + "/send/documents?view=sent", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        # Look for row-level action buttons (Download, etc.)
        row_actions = page.evaluate("""() => {
            const btns = [...document.querySelectorAll('button')];
            return btns
                .filter(b => ['Download', 'Void', 'Resend', 'Delete', 'Correct'].some(t => b.innerText.includes(t)))
                .map(b => ({text: b.innerText.trim(), disabled: b.disabled}));
        }""")
        print(f"  Row actions: {row_actions}")
        
        # Click on a document row to see detail view
        rows = page.locator("tbody tr, [role=row]").all()
        print(f"  Number of rows: {len(rows)}")
        if rows:
            try:
                rows[0].click()
                page.wait_for_timeout(2000)
                detail_url = page.url
                detail_text = page.evaluate("document.body.innerText")
                print(f"  After row click URL: {detail_url}")
                print(f"  Detail content: {detail_text[:300]}")
                p_detail = ss(page, "agreements_row_detail")
                page.go_back()
                page.wait_for_timeout(1500)
            except Exception as e:
                print(f"  Row click error: {e}")

        # ==============================================================
        # P. SEARCH FUNCTIONALITY
        # ==============================================================
        print("\n[SEARCH FUNCTIONALITY]")
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        search_inputs = page.locator("input[type=text], input[type=search], input:not([type])").all()
        print(f"  Search inputs found: {len(search_inputs)}")
        
        if search_inputs:
            # Try typing in first search input
            search_inputs[0].click()
            search_inputs[0].type("test")
            page.wait_for_timeout(1500)
            search_result = page.evaluate("document.body.innerText")
            print(f"  After search 'test': {search_result[search_result.find('test'):search_result.find('test')+200] if 'test' in search_result.lower() else 'no result'}")
            p_search = ss(page, "agreements_search_results")

        # ==============================================================
        # Q. TEMPLATES - Sidebar nav items
        # ==============================================================
        print("\n[TEMPLATES SIDEBAR]")
        page.goto(BASE + "/send/templates", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        # Click Shared with Me
        shared = page.locator("a:has-text('Shared with Me')").first
        if shared.count() > 0:
            shared.click()
            page.wait_for_timeout(1500)
            shared_url = page.url
            print(f"  Shared with Me URL: {shared_url}")
        
        # Click Favorites
        favs = page.locator("a:has-text('Favorites')").first
        if favs.count() > 0:
            favs.click()
            page.wait_for_timeout(1500)
            favs_url = page.url
            print(f"  Favorites URL: {favs_url}")
        
        # Click Workflow Templates NEW
        page.goto(BASE + "/send/templates", wait_until="networkidle")
        page.wait_for_timeout(1500)
        workflow = page.locator("button:has-text('Workflow Templates')").first
        if workflow.count() > 0:
            workflow.click()
            page.wait_for_timeout(2000)
            workflow_url = page.url
            workflow_modal = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog]');
                return m ? m.innerText.slice(0, 200) : null;
            }""")
            print(f"  Workflow Templates URL: {workflow_url}, modal: {workflow_modal}")

        # ==============================================================
        # R. AGREEMENTS - "Start Now" button
        # ==============================================================
        print("\n[AGREEMENTS - START NOW]")
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(1500)
        start_now = page.locator("button:has-text('Start Now')").first
        if start_now.is_visible():
            start_now.click()
            page.wait_for_timeout(2000)
            sn_url = page.url
            sn_modal = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog]');
                return m ? m.innerText.slice(0, 200) : null;
            }""")
            print(f"  Start Now: URL={sn_url}, modal={sn_modal}")
            if sn_url == BASE + "/send/documents" and not sn_modal:
                p_sn = ss(page, "agreements_start_now_no_action")
                log("Agreements", "'Start Now' button produces no action",
                    "P1", "Functional",
                    "Clicked 'Start Now' on Agreements page. URL stayed at /send/documents, no modal.",
                    p_sn)

        # ==============================================================
        # S. Agreements "ENVELOPES" section header button
        # ==============================================================
        print("\n[ENVELOPES BUTTON]")
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(1500)
        env_btn = page.locator("button:has-text('ENVELOPES')").first
        if env_btn.is_visible():
            env_btn.click()
            page.wait_for_timeout(1500)
            env_url = page.url
            print(f"  ENVELOPES button URL: {env_url}")

        # ==============================================================
        # T. PowerForms link
        # ==============================================================
        print("\n[POWERFORMS]")
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        # Click Show More first
        show_more = page.locator("button:has-text('Show More')").first
        if show_more.count() > 0 and show_more.is_visible():
            show_more.click()
            page.wait_for_timeout(1500)
        
        powerforms = page.locator("button:has-text('PowerForms'), a:has-text('PowerForms')").first
        if powerforms.count() > 0 and powerforms.is_visible():
            powerforms.click()
            page.wait_for_timeout(2000)
            pf_url = page.url
            pf_modal = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog]');
                return m ? m.innerText.slice(0, 200) : null;
            }""")
            print(f"  PowerForms: URL={pf_url}, modal={pf_modal}")
            if pf_url == BASE + "/send/documents" and not pf_modal:
                p_pf = ss(page, "powerforms_no_action")
                log("Agreements -> PowerForms", "PowerForms link/button produces no action",
                    "P2", "Functional",
                    "Clicked PowerForms in Agreements sidebar. No navigation or modal.",
                    p_pf)

        # ==============================================================
        # U. "New navigation" section in Agreements
        # ==============================================================
        print("\n[NEW NAVIGATION SECTION]")
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(1500)
        body_text = page.evaluate("document.body.innerText")
        if "New navigation" in body_text:
            idx = body_text.find("New navigation")
            print(f"  New navigation section: {body_text[idx:idx+300]}")
            p_newnav = ss(page, "agreements_new_navigation")
            log("Agreements", "'New navigation' section visible in Agreements sidebar — appears to be leftover/debug content",
                "P2", "Content / Copy",
                f"'New navigation' section found in sidebar. Full text: '{body_text[idx:idx+100]}'",
                p_newnav)

        # ==============================================================
        # V. AGREEMENTS - Completed tab, check names
        # ==============================================================
        print("\n[COMPLETED TAB - SEEDED DATA]")
        page.goto(BASE + "/send/documents?view=completed", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        # Get all document/envelope names
        comp_text = page.evaluate("document.body.innerText")
        print(f"  Completed content: {comp_text[comp_text.find('Completed'):comp_text.find('Completed')+500] if 'Completed' in comp_text else comp_text[:500]}")
        
        # Check for real timestamps vs static
        date_check = page.evaluate("""() => {
            const body = document.body.innerText;
            const dates = body.match(/\\d{1,2}\\/\\d{1,2}\\/\\d{4}|\\d{4}-\\d{2}-\\d{2}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec/g);
            return dates ? dates.slice(0, 10) : [];
        }""")
        print(f"  Dates found: {date_check}")

        # ==============================================================
        # W. Check "Shared Access" tab behavior
        # ==============================================================
        print("\n[SHARED ACCESS TAB]")
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(1500)
        shared_access = page.locator("button:has-text('Shared Access')").first
        if shared_access.count() > 0 and shared_access.is_visible():
            shared_access.click()
            page.wait_for_timeout(1500)
            sa_content = page.evaluate("document.body.innerText")
            print(f"  Shared Access: {sa_content[:300]}")
            p_sa = ss(page, "agreements_shared_access")

        # ==============================================================
        # X. Check: Sign modal - Sign button without file
        # ==============================================================
        print("\n[SIGN MODAL - SIGN WITHOUT FILE]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        sign_btn = page.locator("button:has-text('Sign a Document')").first
        if sign_btn.is_visible():
            sign_btn.click()
            page.wait_for_timeout(1500)
            # Try to click Sign without uploading
            sign_modal_sign_btn = page.locator("[role=dialog] button:has-text('Sign')").first
            if sign_modal_sign_btn.count() > 0 and sign_modal_sign_btn.is_visible():
                is_disabled = sign_modal_sign_btn.evaluate("btn => btn.disabled")
                print(f"  Sign button in modal disabled (without file): {is_disabled}")
                if not is_disabled:
                    sign_modal_sign_btn.click()
                    page.wait_for_timeout(2000)
                    after_sign_url = page.url
                    validation_msg = page.evaluate("""() => {
                        const errors = document.querySelectorAll('[class*=error], [class*=Error], [role=alert]');
                        return [...errors].map(e => e.innerText.trim()).filter(t => t);
                    }""")
                    print(f"  After Sign without file: URL={after_sign_url}, errors={validation_msg}")
                    if not validation_msg and after_sign_url == BASE + "/send/home":
                        p_sign_no_file = ss(page, "sign_without_file_no_validation")
                        log("Home -> Sign modal", "Sign button clickable without uploading a file (no validation)",
                            "P1", "Validation",
                            "In Sign a Document modal, clicked Sign without uploading a file. No validation error shown.",
                            p_sign_no_file)
                    page.keyboard.press("Escape")

        # ==============================================================
        # Y. GLOBAL - Keyboard navigation / Tab order
        # ==============================================================
        print("\n[KEYBOARD TAB ORDER]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        # Tab through first 5 focusable elements
        tab_order = []
        for _ in range(8):
            page.keyboard.press("Tab")
            page.wait_for_timeout(200)
            focused = page.evaluate("""() => {
                const el = document.activeElement;
                return el ? {tag: el.tagName, text: el.innerText?.slice(0,30), type: el.type, role: el.getAttribute('role')} : null;
            }""")
            if focused: tab_order.append(focused)
        print(f"  Tab order: {tab_order}")

        # ==============================================================
        # Z. CHECK BROWSER TITLE ON ALL PAGES
        # ==============================================================
        print("\n[ALL PAGE TITLES CHECK]")
        pages_to_check = [
            ('/send/home', 'Home'),
            ('/send/documents', 'Agreements'),
            ('/send/documents?view=sent', 'Sent'),
            ('/send/documents?view=completed', 'Completed'),
            ('/send/templates', 'Templates'),
        ]
        for path, name in pages_to_check:
            page.goto(BASE + path, wait_until="networkidle")
            page.wait_for_timeout(800)
            t = page.title()
            print(f"  {name:20} title: '{t}'")
            if t == 'Rl_Docusign' or t == '':
                print(f"    --> SAME TITLE on all pages - no dynamic per-page title!")

        # Check if all pages share same title
        titles = set()
        for path, name in pages_to_check:
            page.goto(BASE + path, wait_until="networkidle")
            page.wait_for_timeout(500)
            titles.add(page.title())
        if len(titles) == 1:
            log("Global", "All pages share the same browser tab title ('Rl_Docusign')",
                "P2", "Content / Copy",
                f"Every page uses identical title '{list(titles)[0]}'. DocuSign uses per-page titles.",
                "")

        # ==============================================================
        # AA. DOUBLE-CLICK PROTECTION on "Get Signatures"
        # ==============================================================
        print("\n[DOUBLE-CLICK GET SIGNATURES]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        get_sig2 = page.locator("button:has-text('Get Signatures')").first
        if get_sig2.is_visible():
            get_sig2.dblclick()
            page.wait_for_timeout(3000)
            dbl_url = page.url
            print(f"  After double-click Get Signatures: {dbl_url}")
            # Check if two prepare pages were created (side effect of double-click)

        # ==============================================================
        # AB. CHECK "SEND WITH AI" - is there any hidden functionality
        # ==============================================================
        print("\n[SEND WITH AI - DETAILED]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        ai_detailed = page.evaluate("""() => {
            const btns = [...document.querySelectorAll('button')];
            const ai = btns.find(b => b.innerText.includes('Send with AI'));
            if (!ai) return 'not found';
            const cs = getComputedStyle(ai);
            return {
                disabled: ai.disabled,
                opacity: cs.opacity,
                cursor: cs.cursor,
                onclick: ai.onclick?.toString()?.slice(0, 100)
            };
        }""")
        print(f"  Send with AI button details: {ai_detailed}")
        if isinstance(ai_detailed, dict) and ai_detailed.get('disabled'):
            log("Home", "'Send with AI' button is disabled with no user-visible indicator",
                "P2", "Functional",
                f"Button disabled={ai_detailed.get('disabled')}, cursor={ai_detailed.get('cursor')}, opacity={ai_detailed.get('opacity')}",
                "")

        print("\n[DONE - Phase 3 deep pass complete]")
        print(f"Total findings: {len(findings)}")
        browser.close()

    with open("evidence/raw/deep_findings.json", "w") as f:
        json.dump(findings, f, indent=2)
    print("Saved: evidence/raw/deep_findings.json")

if __name__ == "__main__":
    run()
