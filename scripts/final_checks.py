#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final targeted checks and screenshot captures for evidence."""
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
    print(f"  [SS] {path}")
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
        # 1. PREPARE PAGE - Full detailed exploration
        # ==============================================================
        print("\n[PREPARE PAGE - DETAILED]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        get_sig = page.locator("button:has-text('Get Signatures')").first
        get_sig.click()
        page.wait_for_timeout(3000)
        prepare_url = page.url
        prepare_id = prepare_url.split('/prepare/')[-1].split('?')[0] if '/prepare/' in prepare_url else 'N/A'
        print(f"  Prepare URL: {prepare_url}, ID: {prepare_id}")
        p_prepare = ss(page, "prepare_page_setup_envelope")
        
        prepare_text = page.evaluate("document.body.innerText")
        
        # Check Subject field placeholder
        subject_input = page.locator("input[placeholder*='Complete with Docusign']").first
        if subject_input.count() > 0:
            ph = subject_input.evaluate("el => el.placeholder")
            val = subject_input.evaluate("el => el.value")
            char_count = page.evaluate("""() => {
                const counters = [...document.querySelectorAll('*')].filter(el => el.innerText.match(/^\\d+\\/100$/));
                return counters.map(c => c.innerText);
            }""")
            print(f"  Subject placeholder: '{ph}', value: '{val}', char counts: {char_count}")
            if 'Complete with Docusign:' in ph:
                log("Prepare -> Add message", "Subject field placeholder shows functional prefix 'Complete with Docusign:' instead of user-facing hint",
                    "P3", "Content / Copy",
                    f"Input placeholder: '{ph}'. DocuSign shows 'Please DocuSign: [document name]' format.",
                    p_prepare)

        # Check char counters for subject (100) and message (10000)
        counters = page.evaluate("""() => {
            const body = document.body.innerText;
            const matches = body.match(/\\d+\\/\\d+/g);
            return matches || [];
        }""")
        print(f"  Character counters: {counters}")
        
        # Check "Frequency of reminders" - default 0 days
        reminder_text = page.evaluate("""() => {
            const body = document.body.innerText;
            const idx = body.indexOf('Every 0 days');
            return idx >= 0 ? body.slice(idx - 50, idx + 100) : 'not found';
        }""")
        print(f"  Reminder section: {reminder_text}")
        if "Every 0 days" in str(reminder_text):
            log("Prepare -> Add message", "'Every 0 days' is shown as default reminder frequency",
                "P3", "Functional",
                "Default reminder frequency shows 'Every 0 days' -- 0 means no reminders; DocuSign defaults to 'Every 3 days'.",
                p_prepare)
        
        # Check "Name *" and "Email *" placeholder text
        name_input = page.locator("input[type=text]").first
        email_input = page.locator("input[type=text]").nth(1)
        if name_input.count() > 0:
            name_ph = name_input.evaluate("el => el.placeholder")
            print(f"  Name input placeholder: '{name_ph}'")
            if not name_ph:
                log("Prepare -> Recipients", "Name field has no placeholder text",
                    "P3", "Content / Copy",
                    "Recipient Name input has no placeholder text. DocuSign shows 'Full Name'.",
                    p_prepare)
        if email_input.count() > 0:
            email_ph = email_input.evaluate("el => el.placeholder")
            print(f"  Email input placeholder: '{email_ph}'")
            if not email_ph:
                log("Prepare -> Recipients", "Email field has no placeholder text",
                    "P3", "Content / Copy",
                    "Recipient Email input has no placeholder text. DocuSign shows 'Email Address'.",
                    p_prepare)

        # Test: Click "Next: Add Fields" without adding any document
        print("\n[NEXT WITHOUT DOCUMENT]")
        next_btn = page.locator("button:has-text('Next: Add Fields')").first
        if next_btn.is_visible():
            next_btn.click()
            page.wait_for_timeout(2000)
            after_next_url = page.url
            validation = page.evaluate("""() => {
                const alerts = document.querySelectorAll('[role=alert], [class*=error], [class*=Error], [class*=toast], [class*=Toast]');
                return [...alerts].map(a => a.innerText.trim()).filter(t => t);
            }""")
            print(f"  After Next without doc: URL={after_next_url}, validation={validation}")
            p_no_doc = ss(page, "prepare_next_no_document")
            if '/add-fields' in after_next_url or after_next_url != prepare_url:
                log("Prepare -> Send", "'Next: Add Fields' proceeds without document attached",
                    "P1", "Validation",
                    f"Clicked Next without attaching any document. URL changed to: {after_next_url}. No blocking validation.",
                    p_no_doc)
            elif not validation:
                log("Prepare -> Send", "'Next: Add Fields' shows no validation when no document attached",
                    "P1", "Validation",
                    f"Clicked Next without document. Stayed at: {after_next_url} but no error message shown.",
                    p_no_doc)

        # Test: Click "Next: Add Fields" without adding a recipient
        print("\n[NEXT WITHOUT RECIPIENT]")
        # Upload a PDF first
        import tempfile
        pdf_path = os.path.join(os.getcwd(), "test_sample.pdf")
        if not os.path.exists(pdf_path):
            with open(pdf_path, 'wb') as f:
                f.write(b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF')
        
        # Go back to prepare page fresh
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        get_sig2 = page.locator("button:has-text('Get Signatures')").first
        get_sig2.click()
        page.wait_for_timeout(3000)
        
        # Upload the PDF
        file_input = page.locator("input[type=file]").first
        if file_input.count() > 0:
            file_input.set_input_files(pdf_path)
            page.wait_for_timeout(3000)
            after_upload = page.evaluate("document.body.innerText")
            print(f"  After PDF upload: {after_upload[:300]}")
            p_after_upload = ss(page, "prepare_after_pdf_upload")
        
        # Check if recipient name/email are still empty after upload
        name_val = page.evaluate("""() => {
            const inputs = [...document.querySelectorAll('input[type=text]')];
            return inputs.map(i => ({placeholder: i.placeholder, value: i.value, id: i.id}));
        }""")
        print(f"  Input values after upload: {name_val}")
        
        # Now click Next without filling recipient
        next_btn2 = page.locator("button:has-text('Next: Add Fields')").first
        if next_btn2.is_visible():
            next_btn2.click()
            page.wait_for_timeout(2000)
            after_next2_url = page.url
            validation2 = page.evaluate("""() => {
                const alerts = document.querySelectorAll('[role=alert], [class*=error], [class*=Error], [class*=toast], [class*=Toast]');
                return [...alerts].map(a => a.innerText.trim()).filter(t => t);
            }""")
            p_no_recip = ss(page, "prepare_next_no_recipient")
            print(f"  After Next without recipient: URL={after_next2_url}, validation={validation2}")
            if '/add-fields' in after_next2_url:
                log("Prepare -> Recipients", "'Next: Add Fields' proceeds without any recipient",
                    "P1", "Validation",
                    f"PDF uploaded but no recipient entered. Clicked Next. URL: {after_next2_url}. No blocking validation.",
                    p_no_recip)
            elif not validation2:
                log("Prepare -> Recipients", "No validation error shown when Next clicked without recipient",
                    "P1", "Validation",
                    f"No recipient added, clicked Next, validation message missing.",
                    p_no_recip)

        # ==============================================================
        # 2. RECIPIENT VALIDATION
        # ==============================================================
        print("\n[RECIPIENT VALIDATION]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        get_sig3 = page.locator("button:has-text('Get Signatures')").first
        get_sig3.click()
        page.wait_for_timeout(3000)
        
        # Find name and email inputs
        name_inputs = page.locator("input[type=text]").all()
        if len(name_inputs) >= 2:
            name_inp = name_inputs[0]
            email_inp = name_inputs[1]
            
            # Test: Invalid email
            name_inp.fill("Test User")
            email_inp.fill("notanemail")
            page.wait_for_timeout(500)
            next_btn3 = page.locator("button:has-text('Next: Add Fields')").first
            if next_btn3.is_visible():
                next_btn3.click()
                page.wait_for_timeout(1500)
                inv_email_validation = page.evaluate("""() => {
                    const alerts = document.querySelectorAll('[role=alert], [class*=error], [class*=Error]');
                    const inputs = document.querySelectorAll('input');
                    const invInputs = [...inputs].filter(i => i.validity && !i.validity.valid).map(i => ({id: i.id, validationMsg: i.validationMessage}));
                    return {alerts: [...alerts].map(a => a.innerText.trim()), invalidInputs: invInputs};
                }""")
                p_inv_email = ss(page, "prepare_invalid_email")
                print(f"  Invalid email validation: {inv_email_validation}")
                if not inv_email_validation.get('alerts') and not inv_email_validation.get('invalidInputs'):
                    log("Prepare -> Recipients", "Invalid email address accepted without validation",
                        "P1", "Validation",
                        "Entered 'notanemail' as recipient email, clicked Next. No validation error shown.",
                        p_inv_email)
            
            # Test: Duplicate email
            email_inp.fill("test@test.com")
            name_inp.fill("First User")
            # Add another recipient
            add_recip_btn = page.locator("button:has-text('Add Recipient')").first
            if add_recip_btn.is_visible():
                add_recip_btn.click()
                page.wait_for_timeout(1000)
                new_name_inputs = page.locator("input[type=text]").all()
                if len(new_name_inputs) >= 4:
                    new_name_inputs[2].fill("Second User")
                    new_name_inputs[3].fill("test@test.com")  # duplicate email
                    page.wait_for_timeout(500)
                    next_btn4 = page.locator("button:has-text('Next: Add Fields')").first
                    if next_btn4.is_visible():
                        next_btn4.click()
                        page.wait_for_timeout(1500)
                        dup_validation = page.evaluate("""() => {
                            const alerts = document.querySelectorAll('[role=alert], [class*=error], [class*=Error]');
                            return [...alerts].map(a => a.innerText.trim()).filter(t => t);
                        }""")
                        p_dup = ss(page, "prepare_duplicate_email")
                        print(f"  Duplicate email validation: {dup_validation}")
                        if not dup_validation:
                            log("Prepare -> Recipients", "Duplicate email address accepted without validation",
                                "P2", "Validation",
                                "Added two recipients with same email 'test@test.com'. No duplicate validation error.",
                                p_dup)
            
            # Test: Whitespace-only name
            page.goto(BASE + "/send/home", wait_until="networkidle")
            page.wait_for_timeout(1500)
            get_sig4 = page.locator("button:has-text('Get Signatures')").first
            get_sig4.click()
            page.wait_for_timeout(3000)
            ws_name_inputs = page.locator("input[type=text]").all()
            if len(ws_name_inputs) >= 2:
                ws_name_inputs[0].fill("   ")  # whitespace only
                ws_name_inputs[1].fill("test@example.com")
                next_btn5 = page.locator("button:has-text('Next: Add Fields')").first
                if next_btn5.is_visible():
                    next_btn5.click()
                    page.wait_for_timeout(1500)
                    ws_validation = page.evaluate("""() => {
                        const alerts = document.querySelectorAll('[role=alert], [class*=error], [class*=Error]');
                        return [...alerts].map(a => a.innerText.trim()).filter(t => t);
                    }""")
                    p_ws = ss(page, "prepare_whitespace_name")
                    print(f"  Whitespace name validation: {ws_validation}")
                    if not ws_validation:
                        log("Prepare -> Recipients", "Whitespace-only recipient name accepted without validation",
                            "P2", "Validation",
                            "Entered '   ' (3 spaces) as recipient name, valid email. No validation error.",
                            p_ws)

        # ==============================================================
        # 3. "Add Fields" / PREPARE step 2
        # ==============================================================
        print("\n[FIELD PLACEMENT SCREEN]")
        # Go to Add Fields
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        get_sig5 = page.locator("button:has-text('Get Signatures')").first
        get_sig5.click()
        page.wait_for_timeout(3000)
        
        # Fill recipient name+email
        text_inputs = page.locator("input[type=text]").all()
        if len(text_inputs) >= 2:
            text_inputs[0].fill("Test Signer")
            text_inputs[1].fill("signer@example.com")
        
        # Upload PDF
        file_input2 = page.locator("input[type=file]").first
        if file_input2.count() > 0:
            file_input2.set_input_files(pdf_path)
            page.wait_for_timeout(2000)
        
        # Click Next
        next_btn6 = page.locator("button:has-text('Next: Add Fields')").first
        if next_btn6.is_visible():
            next_btn6.click()
            page.wait_for_timeout(3000)
            fields_url = page.url
            print(f"  Fields URL: {fields_url}")
            p_fields = ss(page, "prepare_add_fields")
            
            fields_text = page.evaluate("document.body.innerText")
            print(f"  Fields page text: {fields_text[:500]}")
            
            fields_elements = page.evaluate("""() => {
                return {
                    buttons: [...document.querySelectorAll('button')].map(b => b.innerText.trim()).filter(t => t),
                    fieldTypes: [...document.querySelectorAll('[draggable=true], [class*=field], [class*=Field]')].slice(0, 10).map(el => ({
                        text: el.innerText.trim().slice(0, 30),
                        draggable: el.draggable,
                        cls: el.className.slice(0, 50)
                    }))
                };
            }""")
            print(f"  Fields elements: {fields_elements}")
            
            if '/add-fields' in fields_url or '/fields' in fields_url:
                # Look for Send button
                send_btn = page.locator("button:has-text('Send'), button:has-text('Send Envelope')").first
                if send_btn.count() > 0:
                    print(f"  Send button found!")
                    p_send_screen = ss(page, "prepare_send_screen")
                    # Click Send without adding any fields
                    send_btn.click()
                    page.wait_for_timeout(3000)
                    after_send_url = page.url
                    send_validation = page.evaluate("""() => {
                        const alerts = document.querySelectorAll('[role=alert], [class*=error], [class*=toast]');
                        return [...alerts].map(a => a.innerText.trim()).filter(t => t);
                    }""")
                    p_after_send = ss(page, "prepare_after_send")
                    print(f"  After Send: URL={after_send_url}, validation={send_validation}")
                    if 'manage' in after_send_url or 'documents' in after_send_url:
                        log("Prepare -> Send", "Envelope sent without any signature fields placed",
                            "P2", "Validation",
                            "Navigated to Add Fields step, clicked Send without placing any fields. Envelope was sent.",
                            p_after_send)

        # ==============================================================
        # 4. AGREEMENTS - Status badge colors check
        # ==============================================================
        print("\n[STATUS BADGE COLORS]")
        page.goto(BASE + "/send/documents?view=sent", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        badge_styles = page.evaluate("""() => {
            const body = document.body.innerText;
            const lines = body.split('\\n').filter(l => ['Waiting', 'Completed', 'Voided', 'Declined', 'Draft', 'Sent'].some(s => l.trim() === s));
            
            // Also check computed styles of status-like elements
            const statusEls = [...document.querySelectorAll('[class*=status],[class*=Status],[class*=badge],[class*=Badge]')];
            return {
                statusLines: lines.slice(0, 10),
                badgeCount: statusEls.length,
                badges: statusEls.slice(0, 5).map(el => ({
                    text: el.innerText.trim(),
                    bg: getComputedStyle(el).backgroundColor,
                    color: getComputedStyle(el).color,
                    cls: el.className.slice(0, 50)
                }))
            };
        }""")
        print(f"  Badge styles: {badge_styles}")
        p_badges = ss(page, "agreements_sent_with_badges")

        # ==============================================================
        # 5. TEMPLATES - Verify "Template Gallery" NEW label
        # ==============================================================
        print("\n[TEMPLATE GALLERY NEW LABEL]")
        page.goto(BASE + "/send/templates", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        new_badge_info = page.evaluate("""() => {
            const btns = [...document.querySelectorAll('button')];
            const workflowBtn = btns.find(b => b.innerText.includes('Workflow Templates'));
            const galleryBtn = btns.find(b => b.innerText.includes('Template Gallery'));
            return {
                workflow: workflowBtn ? {text: workflowBtn.innerText.trim(), disabled: workflowBtn.disabled, cursor: getComputedStyle(workflowBtn).cursor} : null,
                gallery: galleryBtn ? {text: galleryBtn.innerText.trim(), disabled: galleryBtn.disabled, cursor: getComputedStyle(galleryBtn).cursor} : null
            };
        }""")
        print(f"  New badge info: {new_badge_info}")
        p_tmpl = ss(page, "templates_new_badges")
        
        # Click "Workflow Templates" to see what happens
        wf_btn = page.locator("button:has-text('Workflow Templates')").first
        if wf_btn.count() > 0:
            wf_btn.click()
            page.wait_for_timeout(2000)
            wf_url = page.url
            wf_modal = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog]');
                return m ? m.innerText.slice(0, 200) : null;
            }""")
            print(f"  Workflow Templates: URL={wf_url}, modal={wf_modal}")
            if wf_url == BASE + "/send/templates" and not wf_modal:
                log("Templates -> Workflow Templates", "Workflow Templates button (NEW) produces no action",
                    "P2", "Functional",
                    "Clicked 'Workflow Templates' (labeled NEW). URL stayed at /send/templates, no navigation or modal.",
                    p_tmpl)

        # ==============================================================
        # 6. HOME - "Start an agreement" CTA link
        # ==============================================================
        print("\n[HOME - START AN AGREEMENT]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        start_ag = page.locator("button:has-text('Start an agreement'), a:has-text('Start an agreement')").first
        if start_ag.count() > 0:
            tag = start_ag.evaluate("el => el.tagName")
            href = start_ag.evaluate("el => el.href || 'button'")
            print(f"  'Start an agreement' tag={tag}, href={href}")
            start_ag.click()
            page.wait_for_timeout(2000)
            sa_url = page.url
            sa_modal = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog]');
                return m ? m.innerText.slice(0, 200) : null;
            }""")
            print(f"  After 'Start an agreement': URL={sa_url}, modal={sa_modal}")
            if sa_url == BASE + "/send/home" and not sa_modal:
                p_sa = ss(page, "home_start_an_agreement_no_action")
                log("Home", "'Start an agreement' button produces no action",
                    "P1", "Functional",
                    "Clicked 'Start an agreement' CTA in Agreement activity widget. URL stayed at /send/home, no modal.",
                    p_sa)

        # ==============================================================
        # 7. AGREEMENTS - Check Inbox vs default tab
        # ==============================================================
        print("\n[AGREEMENTS - DEFAULT VIEW]")
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        # Check which sidebar tab is visually highlighted
        active_sidebar = page.evaluate("""() => {
            const links = [...document.querySelectorAll('[href*="/send/documents"]')];
            const active = links.filter(l => {
                const cs = getComputedStyle(l);
                return cs.fontWeight === '700' || cs.fontWeight === 'bold' || 
                       cs.color.includes('19, 0, 50') ||
                       l.className.includes('active') || l.className.includes('selected');
            });
            return active.map(a => ({text: a.innerText.trim(), href: a.href, cls: a.className}));
        }""")
        print(f"  Active sidebar items: {active_sidebar}")
        p_agreements_default = ss(page, "agreements_default_view")
        
        # Check that default is Inbox, not some other tab
        current_view = page.evaluate("""() => {
            const params = new URLSearchParams(window.location.search);
            return params.get('view') || 'none (default)';
        }""")
        print(f"  Current view param: {current_view}")
        
        # Check content of default view
        default_content_title = page.evaluate("""() => {
            const h1 = document.querySelector('h1');
            return h1 ? h1.innerText.trim() : 'no h1';
        }""")
        print(f"  Default view h1: {default_content_title}")

        # ==============================================================
        # 8. VERIFY "COMPLETED" tab shows agreements with status
        # ==============================================================
        print("\n[COMPLETED TAB DETAIL]")
        page.goto(BASE + "/send/documents?view=completed", wait_until="networkidle")
        page.wait_for_timeout(2000)
        p_completed = ss(page, "agreements_completed_detail")
        
        completed_text = page.evaluate("document.body.innerText")
        print(f"  Completed tab text: {completed_text[:800]}")
        
        # Look for status badges in completed tab
        comp_badges = page.evaluate("""() => {
            const body = document.body.innerText;
            // Check if "Completed" status appears correctly
            const lines = body.split('\\n').map(l => l.trim()).filter(l => l);
            return lines.slice(0, 50);
        }""")
        print(f"  Completed rows: {comp_badges[:20]}")

        # ==============================================================
        # 9. Get Signatures multiple clicks - seeded envelope ID check
        # ==============================================================
        print("\n[GET SIGNATURES - MULTIPLE CLICKS]")
        ids = []
        for i in range(2):
            page.goto(BASE + "/send/home", wait_until="networkidle")
            page.wait_for_timeout(1500)
            btn = page.locator("button:has-text('Get Signatures')").first
            btn.click()
            page.wait_for_timeout(3000)
            url = page.url
            if '/prepare/' in url:
                env_id = url.split('/prepare/')[-1].split('?')[0]
                ids.append(env_id)
                print(f"  Click {i+1} -> envelope ID: {env_id}")
            
        if len(ids) == 2 and ids[0] != ids[1]:
            log("Home -> Get Signatures", "Each click creates a new pre-seeded envelope with different ID",
                "P0", "Data / Seeded",
                f"Click 1: /prepare/{ids[0]}, Click 2: /prepare/{ids[1]}. Each creates a fresh seeded envelope polluting the DB.",
                "evidence/raw/prepare_page_setup_envelope.png")
        
        # ==============================================================
        # 10. SIGN MODAL - Validate Sign button behavior
        # ==============================================================
        print("\n[SIGN MODAL - SIGN BUTTON]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        sign_btn = page.locator("button:has-text('Sign a Document')").first
        sign_btn.click()
        page.wait_for_timeout(2000)
        
        modal_sign_btn = page.locator("[role=dialog] button:has-text('Sign')").first
        if modal_sign_btn.count() > 0:
            is_disabled = modal_sign_btn.evaluate("el => el.disabled")
            opacity = modal_sign_btn.evaluate("el => getComputedStyle(el).opacity")
            cursor = modal_sign_btn.evaluate("el => getComputedStyle(el).cursor")
            print(f"  Sign button: disabled={is_disabled}, opacity={opacity}, cursor={cursor}")
            p_sign_modal = ss(page, "sign_modal_sign_button_state")
            if not is_disabled:
                # Try clicking it (without file)
                page.evaluate("document.querySelector('[role=dialog] button:last-child').click()")
                page.wait_for_timeout(2000)
                sign_after = page.url
                error_after = page.evaluate("""() => {
                    const alerts = document.querySelectorAll('[role=alert], [class*=error]');
                    return [...alerts].map(a => a.innerText.trim()).filter(t => t);
                }""")
                print(f"  After Sign click (no file): URL={sign_after}, errors={error_after}")
                if not error_after:
                    log("Home -> Sign modal", "Sign button clickable without file; no validation when clicked",
                        "P1", "Validation",
                        f"Sign button not disabled (opacity={opacity}). Clicked without uploading file. No error shown.",
                        p_sign_modal)

        # ==============================================================
        # 11. AGREEMENTS VIEW - check 'Sender' vs 'To' column
        # ==============================================================
        print("\n[AGREEMENTS - COLUMN NAMES]")
        # Check what column headers appear in different views
        for view, expected_col in [('sent', 'Recipient'), ('inbox', 'Sender')]:
            page.goto(BASE + f"/send/documents?view={view}", wait_until="networkidle")
            page.wait_for_timeout(2000)
            headers = page.evaluate("""() => {
                const ths = document.querySelectorAll('th, [class*=header], [role=columnheader]');
                return [...ths].map(t => t.innerText.trim()).filter(t => t);
            }""")
            btns = page.evaluate("""() => {
                const body = document.body.innerText;
                return ['NAME', 'STATUS', 'LAST CHANGE', 'TO', 'SENDER', 'DATE', 'RECIPIENT', 'FROM'].filter(w => body.includes(w));
            }""")
            print(f"  {view} view column headers: {headers}, visible: {btns}")
            p_view = ss(page, f"agreements_{view}_columns")

        # ==============================================================
        # 12. AGREEMENTS - Sort by column
        # ==============================================================
        print("\n[AGREEMENTS - SORT]")
        page.goto(BASE + "/send/documents?view=sent", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        date_sort_btn = page.locator("button:has-text('Date')").first
        if date_sort_btn.count() > 0 and date_sort_btn.is_visible():
            date_sort_btn.click()
            page.wait_for_timeout(1500)
            after_sort_url = page.url
            print(f"  After Date sort click: {after_sort_url}")
            p_sort = ss(page, "agreements_date_sort")

        # ==============================================================
        # 13. CHECK "Shared Access" TAB
        # ==============================================================
        print("\n[SHARED ACCESS TAB]")
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(1500)
        shared_access = page.locator("button:has-text('Shared Access')").first
        if shared_access.is_visible():
            shared_access.click()
            page.wait_for_timeout(2000)
            sa_text = page.evaluate("document.body.innerText")
            print(f"  Shared Access content: {sa_text[:400]}")
            p_shared = ss(page, "agreements_shared_access")
            # Check if it shows any meaningful content
            if "no one" in sa_text.lower() or len(sa_text.strip()) < 100:
                log("Agreements -> Shared Access", "Shared Access tab shows empty/minimal content",
                    "P3", "Functional",
                    "Clicked Shared Access tab. Content: '{}'".format(sa_text[:100]),
                    p_shared)

        # ==============================================================
        # 14. CHECK AGREEMENTS INCOMPLETE/SEEDED ROWS
        # ==============================================================
        print("\n[AGREEMENTS - SEEDED ROWS DETAIL]")
        page.goto(BASE + "/send/documents?view=inbox", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        inbox_data = page.evaluate("""() => {
            const body = document.body.innerText;
            return body;
        }""")
        print(f"  Inbox content: {inbox_data[:800]}")
        p_inbox = ss(page, "agreements_inbox_detail")
        
        # Check for [Untitled] documents
        if '[Untitled]' in inbox_data:
            log("Agreements -> Inbox", "Agreement with '[Untitled]' name visible in Inbox",
                "P2", "Data / Seeded",
                "An agreement titled '[Untitled]' appears in Inbox. DocuSign requires subject.",
                p_inbox)
        
        # Check for internal email or test data
        import re
        emails_found = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', inbox_data)
        print(f"  Emails in inbox: {emails_found[:5]}")
        names_found = re.findall(r'(?:John Doe|SDSD|fakkih|Adithya|Mohammed)', inbox_data)
        print(f"  Seeded names: {names_found}")
        if names_found:
            log("Agreements -> Inbox", f"Seeded/test user names visible: {list(set(names_found))}",
                "P3", "Data / Seeded",
                f"Test names visible: {names_found}. These should be test@test.com style or not seeded.",
                p_inbox)

        # ==============================================================
        # 15. TEMPLATES - Click on a template (if any)
        # ==============================================================
        print("\n[TEMPLATES - CLICK TEMPLATE ROW]")
        page.goto(BASE + "/send/templates", wait_until="networkidle")
        page.wait_for_timeout(1500)
        tmpl_rows = page.locator("tbody tr, [role=row]").all()
        print(f"  Template rows: {len(tmpl_rows)}")
        # Templates seem empty - no rows expected
        tmpl_text = page.evaluate("document.body.innerText")
        if "No templates found" in tmpl_text:
            print("  Templates empty state confirmed")
            log("Templates", "Templates page shows 'No templates found' with no default or example templates",
                "P3", "Data / Seeded",
                "Templates page empty state shows 'No templates found'. DocuSign shows at least example or recent templates.",
                ss(page, "templates_empty"))

        print("\n[DONE - Final targeted checks complete]")
        browser.close()

    with open("evidence/raw/final_findings.json", "w") as f:
        json.dump(findings, f, indent=2)
    print(f"Total findings: {len(findings)}")

if __name__ == "__main__":
    run()
