#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
"""
Phase 2+3: Comprehensive QA pass on the DocuSign clone.
Walks all flows, captures evidence, logs findings.
"""
import os, json, time, traceback
from playwright.sync_api import sync_playwright, expect
from auth_config import get_http_credentials

BASE = "http://13.207.185.159"
USERNAME, PASSWORD = get_http_credentials()
AUTH = {"username": USERNAME, "password": PASSWORD}
EVIDENCE = "evidence/raw"
os.makedirs(EVIDENCE, exist_ok=True)

findings = []  # {screen, finding, severity, category, details}

def ss(page, name, annotate=None):
    """Take screenshot and save."""
    path = os.path.join(EVIDENCE, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    print(f"  [SS] {path}")
    return path

def log(screen, finding, severity, category, details="", evidence=""):
    findings.append({
        "screen": screen, "finding": finding,
        "severity": severity, "category": category,
        "details": details, "evidence": evidence
    })
    print(f"  [FIND-{severity}] {screen}: {finding}")

def console_errors(page):
    errors = []
    page.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    return errors

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
        page.on("console", lambda m: errs.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))

        # ================================================================
        # 1. HOME PAGE
        # ================================================================
        print("\n[HOME PAGE]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        # Check page title
        title = page.title()
        if "Rl_Docusign" in title or "Rl" in title:
            p_path = ss(page, "home_title_bug")
            log("Home", "Page title is 'Rl_Docusign' instead of 'DocuSign' or proper branding",
                "P3", "Content / Copy",
                "title='Rl_Docusign'; meta description='Dashboard template for RL environment state management.'",
                p_path)

        # Check description meta
        desc = page.evaluate("document.querySelector('meta[name=description]')?.content")
        if desc and "RL environment state management" in desc:
            log("Home", "Meta description exposes internal 'RL environment' label",
                "P3", "Content / Copy",
                f"meta description='{desc}'",
                "evidence/raw/home_title_bug.png")

        # Check welcome message (no user name shown)
        welcome = page.locator("text=Welcome back,").first
        if welcome.is_visible():
            welcome_text = welcome.evaluate("el => el.parentElement?.innerText || el.innerText")
            print(f"  Welcome text: {welcome_text[:100]}")
            if welcome_text.strip().endswith(",") or "Welcome back," == welcome_text.strip():
                p_path = ss(page, "home_welcome_empty_name")
                log("Home", "Welcome message shows 'Welcome back,' with no user name",
                    "P2", "Data / Seeded",
                    f"Text: '{welcome_text.strip()}' — no username appended",
                    p_path)
        
        # Check Overview stats are all 0 / static
        try:
            stat_vals = page.evaluate("""() => {
                const els = document.querySelectorAll('button');
                const results = [];
                for (const el of els) {
                    const txt = el.innerText.trim();
                    if (/Waiting|Expiring|Completed/.test(txt)) results.push(txt);
                }
                return results;
            }""")
            print(f"  Overview stats: {stat_vals}")
        except: pass

        # Check nav: Reports and Admin disabled
        disabled_nav = page.evaluate("""() => {
            const spans = document.querySelectorAll('nav span');
            return [...spans].map(s => ({text: s.innerText, cursor: getComputedStyle(s).cursor}));
        }""")
        print(f"  Disabled nav: {disabled_nav}")
        for item in disabled_nav:
            if item.get('cursor') == 'not-allowed':
                log("Home -> Nav", f"Nav item '{item.get('text')}' is permanently disabled (cursor:not-allowed)",
                    "P2", "Functional",
                    f"Nav item '{item.get('text')}' uses span not a, cursor: not-allowed, no fallback or tooltip",
                    "")

        # Check footer copyright year
        footer_text = page.evaluate("document.body.innerText")
        if "2026" in footer_text:
            # Check if copyright year matches current year
            import datetime
            current_year = datetime.datetime.now().year
            if current_year != 2026:
                log("Home → Footer", f"Copyright year shows {current_year} in footer but was hardcoded",
                    "P4", "Content / Copy", "", "")
        
        # ================================================================
        # 2. NAV PIXEL PASS - check colors
        # ================================================================
        print("\n[NAV PIXEL PASS]")
        nav_styles = page.evaluate("""() => {
            const active = document.querySelector('.nav-link-active');
            const inactive = document.querySelector('.nav-link');
            const header = document.querySelector('header');
            if (!active || !inactive || !header) return null;
            const cs_a = getComputedStyle(active);
            const cs_i = getComputedStyle(inactive);
            const cs_h = getComputedStyle(header);
            return {
                active_color: cs_a.color,
                active_bg: cs_a.backgroundColor,
                inactive_color: cs_i.color,
                header_bg: cs_h.backgroundColor,
                header_border: cs_h.borderBottom,
                header_height: cs_h.height,
                nav_font_size: cs_a.fontSize,
                nav_font_weight: cs_a.fontWeight
            };
        }""")
        print(f"  Nav styles: {nav_styles}")
        if nav_styles:
            # DocuSign uses #130032 for active, check it
            if nav_styles.get('nav_font_size') != '16px':
                log("Home → Nav", f"Nav font size is {nav_styles.get('nav_font_size')} instead of expected 16px",
                    "P4", "UI / Pixel",
                    f"Computed font-size: {nav_styles.get('nav_font_size')}", "")

        # ================================================================
        # 3. AGREEMENTS / DOCUMENTS PAGE
        # ================================================================
        print("\n[AGREEMENTS PAGE]")
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        # Collect errors
        if errs:
            print(f"  Console errors: {errs[:3]}")
        
        # Check the tabs
        tabs = page.evaluate("""() => {
            const sidebar_links = document.querySelectorAll('[href*="/send/documents"]');
            return [...sidebar_links].map(a => ({href: a.href, text: a.innerText.trim()}));
        }""")
        print(f"  Sidebar tabs: {tabs}")
        
        # Check default active tab
        page_url = page.url
        print(f"  Current URL: {page_url}")
        if page_url == BASE + "/send/documents" or page_url.endswith("/send/documents"):
            # Inbox should be default
            active_tab = page.evaluate("""() => {
                const active = document.querySelector('[class*="active"], [aria-selected="true"], [class*="selected"]');
                return active ? active.innerText.trim() : 'none found';
            }""")
            print(f"  Active tab: {active_tab}")

        # Check list columns
        cols = page.evaluate("""() => {
            return [...document.querySelectorAll('button')].map(b => b.innerText.trim()).filter(t => t);
        }""")
        print(f"  Buttons: {cols[:15]}")

        # Check empty state message
        empty_state = page.evaluate("""() => {
            const body = document.body.innerText;
            const match = body.match(/is empty[\s\S]{0,200}/);
            return match ? match[0] : null;
        }""")
        if empty_state:
            print(f"  Empty state: {empty_state[:150]}")

        # Try switching tabs
        for tab_view in ['sent', 'completed', 'action-required']:
            print(f"\n  [Tab: {tab_view}]")
            page.goto(BASE + f"/send/documents?view={tab_view}", wait_until="networkidle")
            page.wait_for_timeout(1500)
            tab_url = page.url
            print(f"  URL after nav: {tab_url}")
            tab_text = page.evaluate("document.body.innerText")
            print(f"  Content preview: {tab_text[:200]}")

        # ================================================================
        # 4. START FLOW - Click "Start" button
        # ================================================================
        print("\n[START FLOW]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        
        start_btn = page.locator("button:has-text('Start')").first
        if start_btn.is_visible():
            start_btn.click()
            page.wait_for_timeout(2000)
            after_start_url = page.url
            print(f"  URL after Start click: {after_start_url}")
            
            # Check if a modal or new page appeared
            modal = page.evaluate("""() => {
                const modal = document.querySelector('[role=dialog], .modal, [class*=modal], [class*=Modal]');
                return modal ? {visible: true, text: modal.innerText.slice(0,200)} : {visible: false};
            }""")
            print(f"  Modal after Start: {modal}")
            
            if modal.get('visible'):
                p_path = ss(page, "start_modal")
                log("Home → Start", "Examining Start modal flow", "P3", "Functional",
                    f"Modal appeared: {modal.get('text')[:100]}", p_path)
            
            # Look for upload area
            upload_area = page.locator("input[type=file]").first
            if upload_area.count() > 0:
                print("  File input found!")
                p_path = ss(page, "upload_screen")
                
                # Test: upload unsupported file type
                import tempfile
                # Create test files
                test_pdf_path = os.path.join(os.getcwd(), "test_sample.pdf")
                # Create a minimal PDF
                with open(test_pdf_path, 'wb') as f:
                    f.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF')
                upload_area.set_input_files(test_pdf_path)
                page.wait_for_timeout(2000)
                p_path_upload = ss(page, "upload_pdf_result")
                print(f"  PDF upload screenshot: {p_path_upload}")
                
                # After upload - note URL
                upload_result_url = page.url
                print(f"  URL after PDF upload: {upload_result_url}")

        # ================================================================
        # 5. UPLOAD EDGE CASES
        # ================================================================
        print("\n[UPLOAD EDGE CASES]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        start_btn2 = page.locator("button:has-text('Start')").first
        if start_btn2.is_visible():
            start_btn2.click()
            page.wait_for_timeout(2000)
            
            file_input = page.locator("input[type=file]").first
            if file_input.count() > 0:
                # Test 0-byte file
                zero_path = os.path.join(os.getcwd(), "zero_byte.pdf")
                with open(zero_path, 'wb') as f: pass
                try:
                    file_input.set_input_files(zero_path)
                    page.wait_for_timeout(2000)
                    zero_result = page.evaluate("document.body.innerText")
                    p_path_zero = ss(page, "upload_zero_byte")
                    if "error" not in zero_result.lower() and "invalid" not in zero_result.lower():
                        log("Upload", "0-byte file accepted without validation error",
                            "P2", "Validation",
                            "Uploaded 0-byte PDF; no error shown; file accepted silently",
                            p_path_zero)
                    print(f"  Zero-byte result text (200): {zero_result[:200]}")
                except Exception as e:
                    print(f"  Zero-byte test error: {e}")

                # Test unsupported file type
                exe_path = os.path.join(os.getcwd(), "test_file.exe")
                with open(exe_path, 'wb') as f: f.write(b'MZ' + b'\x00' * 100)
                try:
                    page.reload(wait_until="networkidle")
                    page.wait_for_timeout(1000)
                    start_btn3 = page.locator("button:has-text('Start')").first
                    if start_btn3.is_visible():
                        start_btn3.click()
                        page.wait_for_timeout(1500)
                    file_input2 = page.locator("input[type=file]").first
                    if file_input2.count() > 0:
                        file_input2.set_input_files(exe_path)
                        page.wait_for_timeout(2000)
                        exe_result = page.evaluate("document.body.innerText")
                        p_path_exe = ss(page, "upload_unsupported_type")
                        print(f"  Exe upload result: {exe_result[:200]}")
                        if "error" not in exe_result.lower() and "not supported" not in exe_result.lower() and "invalid" not in exe_result.lower():
                            log("Upload", "Unsupported file type (.exe) accepted without validation error",
                                "P1", "Validation",
                                "Uploaded .exe binary; no type validation error displayed",
                                p_path_exe)
                except Exception as e:
                    print(f"  Exe test error: {e}")

        # ================================================================
        # 6. TEMPLATES PAGE
        # ================================================================
        print("\n[TEMPLATES PAGE]")
        page.goto(BASE + "/send/templates", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        tmpl_url = page.url
        print(f"  URL: {tmpl_url}")
        
        # Check table headers sortable
        sortable = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            return [...btns].map(b => b.innerText.trim()).filter(t => ['Last Change','Name','Owner','Created Date'].includes(t));
        }""")
        print(f"  Sortable columns: {sortable}")
        
        # Check pagination
        pagination = page.evaluate("""() => {
            const body = document.body.innerText;
            return body.includes('/ Page') ? 'found' : 'not found';
        }""")
        print(f"  Pagination: {pagination}")
        
        # Check empty state 
        tmpl_text = page.evaluate("document.body.innerText")
        if "No templates found" in tmpl_text:
            p_path_tmpl = ss(page, "templates_empty_state")
            print(f"  Templates: empty state shown")
        
        # Shared with me tab
        page.goto(BASE + "/send/templates?view=shared-with-me", wait_until="networkidle")
        page.wait_for_timeout(1500)
        shared_text = page.evaluate("document.body.innerText")
        print(f"  Shared templates text: {shared_text[:200]}")

        # ================================================================
        # 7. AUTH / SESSION tests
        # ================================================================
        print("\n[AUTH TESTS]")
        # Test accessing without auth (should get 401 or redirect)
        import urllib.request
        try:
            req = urllib.request.urlopen("http://13.207.185.159/send/home", timeout=10)
            no_auth_status = req.status
            print(f"  No-auth status: {no_auth_status} — SHOULD be 401")
            if no_auth_status == 200:
                log("Auth", "Endpoint accessible without HTTP Basic Auth credentials",
                    "P1", "Functional",
                    "GET /send/home without Authorization header returns 200",
                    "")
        except Exception as e:
            print(f"  No-auth response: {e}")  # Expected: 401

        # ================================================================
        # 8. WRONG CREDENTIALS
        # ================================================================
        ctx2 = browser.new_context(
            viewport={"width": 1280, "height": 960},
            http_credentials={"username": "wrong", "password": "wrong"},
            ignore_https_errors=True
        )
        p2 = ctx2.new_page()
        try:
            p2.goto(BASE + "/send/home", wait_until="domcontentloaded", timeout=10000)
            wrong_cred_status = p2.evaluate("document.body?.innerText?.slice(0, 200)")
            print(f"  Wrong creds content: {wrong_cred_status}")
        except Exception as e:
            print(f"  Wrong creds error: {e}")
        finally:
            p2.close()
            ctx2.close()

        # ================================================================
        # 9. DIRECT URL / BROWSER NAVIGATION
        # ================================================================
        print("\n[NAVIGATION TESTS]")
        # Test direct navigation to a mid-flow URL (without upload context)
        # (upload flow needs context, so navigate to a page that might break)
        page.goto(BASE + "/send/documents?view=action-required", wait_until="networkidle")
        page.wait_for_timeout(1500)
        action_url = page.url
        action_text = page.evaluate("document.body.innerText")
        print(f"  Action Required URL: {action_url}")
        print(f"  Action Required text: {action_text[:200]}")
        
        # Test browser back behavior
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.go_back()
        page.wait_for_timeout(1500)
        back_url = page.url
        print(f"  After back: {back_url}")

        # ================================================================
        # 10. FOOTER LINKS
        # ================================================================
        print("\n[FOOTER LINKS]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        footer_links = page.evaluate("""() => {
            const footer = document.querySelector('footer');
            if (!footer) return 'no footer element';
            const links = footer.querySelectorAll('a');
            return [...links].map(a => ({text: a.innerText.trim(), href: a.href}));
        }""")
        print(f"  Footer links: {footer_links}")
        if footer_links == 'no footer element':
            p_path_footer = ss(page, "home_no_footer_element")
            log("Home → Footer", "No semantic <footer> element; footer content is in a div",
                "P4", "UI / Pixel",
                "Footer area uses generic div instead of <footer> landmark element",
                p_path_footer)

        # ================================================================
        # 11. CONSOLE ERRORS summary
        # ================================================================
        print(f"\n[ALL CONSOLE ERRORS FOUND]: {len(errs)}")
        if errs:
            print('\n'.join(errs[:10]))
            if len(errs) > 0:
                log("Global", f"{len(errs)} console errors/warnings found during test run",
                    "P2", "Error handling",
                    '\n'.join(errs[:5]),
                    "")

        # ================================================================
        # 12. GET SIGNATURES FLOW
        # ================================================================
        print("\n[GET SIGNATURES FLOW]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        get_sig_btn = page.locator("button:has-text('Get Signatures')").first
        if get_sig_btn.count() > 0 and get_sig_btn.is_visible():
            get_sig_btn.click()
            page.wait_for_timeout(2000)
            get_sig_url = page.url
            get_sig_modal = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog], [class*=modal], [class*=Modal]');
                return m ? m.innerText.slice(0,300) : null;
            }""")
            print(f"  Get Signatures URL: {get_sig_url}")
            print(f"  Get Signatures modal: {get_sig_modal}")
            if get_sig_modal:
                p_path_gs = ss(page, "get_signatures_modal")

        # ================================================================
        # 13. SIGN A DOCUMENT FLOW
        # ================================================================
        print("\n[SIGN A DOCUMENT FLOW]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        sign_btn = page.locator("button:has-text('Sign a Document')").first
        if sign_btn.count() > 0 and sign_btn.is_visible():
            sign_btn.click()
            page.wait_for_timeout(2000)
            sign_url = page.url
            sign_modal = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog], [class*=modal], [class*=Modal]');
                return m ? m.innerText.slice(0,300) : null;
            }""")
            print(f"  Sign a Document URL: {sign_url}")
            print(f"  Sign modal: {sign_modal}")
            if sign_modal:
                p_path_sign = ss(page, "sign_document_modal")

        # ================================================================
        # 14. SEND WITH AI FLOW
        # ================================================================
        print("\n[SEND WITH AI FLOW]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        ai_btn = page.locator("button:has-text('Send with AI')").first
        if ai_btn.count() > 0 and ai_btn.is_visible():
            ai_btn.click()
            page.wait_for_timeout(2000)
            ai_url = page.url
            ai_modal = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog], [class*=modal], [class*=Modal]');
                return m ? m.innerText.slice(0,300) : null;
            }""")
            print(f"  Send with AI URL: {ai_url}")
            print(f"  AI modal: {ai_modal}")
            if ai_modal:
                p_path_ai = ss(page, "send_with_ai_modal")

        # ================================================================
        # 15. HOME OVERVIEW STATS - click to navigate
        # ================================================================
        print("\n[HOME STATS BUTTONS]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        for stat_label in ['Waiting for others', 'Expiring soon', 'Completed']:
            stat_btn = page.locator(f"button:has-text('{stat_label}')").first
            if stat_btn.count() > 0 and stat_btn.is_visible():
                # Get the number/count from the button
                stat_content = stat_btn.evaluate("el => el.innerText.trim()")
                print(f"  Stat '{stat_label}': {stat_content!r}")
                stat_btn.click()
                page.wait_for_timeout(1500)
                after_stat_url = page.url
                print(f"  After click '{stat_label}': {after_stat_url}")
                page.go_back()
                page.wait_for_timeout(1000)

        # ================================================================
        # 16. DOUBLE-CLICK PROTECTION - Start button
        # ================================================================
        print("\n[DOUBLE CLICK PROTECTION]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        start_dbl = page.locator("button:has-text('Start')").first
        if start_dbl.count() > 0:
            start_dbl.dblclick()
            page.wait_for_timeout(2000)
            dbl_url = page.url
            print(f"  After double-click Start: {dbl_url}")

        # ================================================================
        # 17. PAGE REFRESH MID-FLOW
        # ================================================================
        print("\n[PAGE REFRESH TESTS]")
        page.goto(BASE + "/send/documents?view=sent", wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1500)
        refresh_url = page.url
        print(f"  After refresh on sent view: {refresh_url}")
        if "sent" not in refresh_url:
            p_path_refresh = ss(page, "agreements_sent_after_refresh")
            log("Agreements", "Tab/view state lost after page refresh (URL param dropped)",
                "P2", "Navigation",
                f"Navigated to /send/documents?view=sent, refreshed, URL became: {refresh_url}",
                p_path_refresh)

        # ================================================================
        # 18. AGREEMENTS VIEW - check Sidebar "Show More"
        # ================================================================
        print("\n[AGREEMENTS SIDEBAR]")
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(1500)
        show_more = page.locator("button:has-text('Show More')").first
        if show_more.count() > 0 and show_more.is_visible():
            show_more.click()
            page.wait_for_timeout(1500)
            after_show_more = page.evaluate("document.body.innerText")
            print(f"  After 'Show More': {after_show_more[:300]}")
            p_path_sm = ss(page, "agreements_show_more_expanded")

        # ================================================================
        # 19. ADVANCED SEARCH
        # ================================================================
        print("\n[ADVANCED SEARCH]")
        page.goto(BASE + "/send/documents", wait_until="networkidle")
        page.wait_for_timeout(1500)
        adv_search = page.locator("button:has-text('Advanced search')").first
        if adv_search.count() > 0 and adv_search.is_visible():
            adv_search.click()
            page.wait_for_timeout(1500)
            adv_form = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog], form, [class*=search]');
                return m ? m.innerText.slice(0,300) : null;
            }""")
            print(f"  Advanced search expanded: {adv_form}")
            p_path_adv = ss(page, "agreements_advanced_search")
            
            # Try clearing 
            clear_btn = page.locator("button:has-text('Clear')").first
            if clear_btn.count() > 0 and clear_btn.is_visible():
                clear_btn.click()
                page.wait_for_timeout(1000)

        # ================================================================
        # 20. KEYBOARD / ESC in modals
        # ================================================================
        print("\n[KEYBOARD TESTS]")
        page.goto(BASE + "/send/home", wait_until="networkidle")
        page.wait_for_timeout(1500)
        start_esc = page.locator("button:has-text('Start')").first
        if start_esc.count() > 0:
            start_esc.click()
            page.wait_for_timeout(1500)
            modal_visible_before = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog], [class*=modal], [class*=Modal]');
                return !!m;
            }""")
            print(f"  Modal visible before Esc: {modal_visible_before}")
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)
            modal_visible_after = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog], [class*=modal], [class*=Modal]');
                return !!m;
            }""")
            print(f"  Modal visible after Esc: {modal_visible_after}")
            if modal_visible_before and modal_visible_after:
                p_path_esc = ss(page, "modal_esc_not_closing")
                log("Home → Modal", "Modal does not close on Escape key press",
                    "P2", "Functional",
                    "Clicked Start, modal appeared, pressed Escape, modal remained open",
                    p_path_esc)

        print("\n[DONE - Phase 2+3 exploration complete]")
        browser.close()

    # Save findings
    with open("evidence/raw/functional_findings.json", "w") as f:
        json.dump(findings, f, indent=2)
    print(f"\nTotal findings logged: {len(findings)}")
    print("Saved: evidence/raw/functional_findings.json")

if __name__ == "__main__":
    run()
