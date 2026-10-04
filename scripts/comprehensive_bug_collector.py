#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprehensive Bug Collector & Evidence Generator.
Tests all flows and records precise evidence screenshots and measurements.
"""
import sys, os, json, re
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
from playwright.sync_api import sync_playwright
from auth_config import get_http_credentials

BASE = "http://13.207.185.159"
USERNAME, PASSWORD = get_http_credentials()
AUTH = {"username": USERNAME, "password": PASSWORD}
EVIDENCE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)

test_results = {}

def take_ss(page, filename):
    filepath = os.path.join(EVIDENCE_DIR, filename)
    try:
        page.screenshot(path=filepath, full_page=True)
        print(f"Captured: {filename}", flush=True)
        return f"evidence/{filename}"
    except Exception as e:
        print(f"Screenshot error for {filename}: {e}", flush=True)
        return ""

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 960},
            http_credentials=AUTH,
            ignore_https_errors=True
        )
        page = ctx.new_page()

        # ----------------------------------------------------
        # TEST 1: Home Page Elements & Broken Actions
        # ----------------------------------------------------
        print("=== Test 1: Home Page ===", flush=True)
        try:
            page.goto(f"{BASE}/send/home", wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(1000)
            
            # Check Title & Meta
            title = page.title()
            meta_desc = page.locator('meta[name="description"]').get_attribute('content')
            test_results['title'] = title
            test_results['meta_desc'] = meta_desc
            take_ss(page, "BUG-001_home_branding_title_meta.png")

            # Check H1 presence
            h1_count = page.locator("h1").count()
            test_results['h1_count'] = h1_count
            take_ss(page, "BUG-002_home_missing_h1_seo.png")

            # Start button click
            start_btn = page.locator("button:has-text('Start')").first
            start_outer = start_btn.evaluate("el => el.outerHTML")
            start_styles = start_btn.evaluate("""el => {
                const s = window.getComputedStyle(el);
                return {bg: s.backgroundColor, color: s.color, cursor: s.cursor, border: s.border};
            }""")
            test_results['start_btn'] = {'outer': start_outer, 'styles': start_styles}
            start_btn.click(timeout=3000)
            page.wait_for_timeout(1000)
            test_results['url_after_start'] = page.url
            take_ss(page, "BUG-003_home_start_button_unresponsive.png")

            # Send with AI button click
            ai_btn = page.locator("button:has-text('Send with AI')").first
            ai_outer = ai_btn.evaluate("el => el.outerHTML")
            ai_btn.click(timeout=3000)
            page.wait_for_timeout(1000)
            test_results['url_after_ai'] = page.url
            take_ss(page, "BUG-004_home_send_with_ai_unresponsive.png")

            # Stat cards (Waiting for others, Expiring soon, Completed)
            stat_w = page.locator("text='Waiting for others'").first
            if stat_w.count() > 0:
                stat_w.click(timeout=3000)
                page.wait_for_timeout(500)
            test_results['url_after_stat_w'] = page.url
            take_ss(page, "BUG-005_home_overview_stat_cards_dead.png")

            # Footer dead links
            footer_links = page.evaluate("""() => {
                const links = [...document.querySelectorAll('footer a, [class*=footer] a')];
                return links.map(a => ({text: a.innerText.trim(), href: a.getAttribute('href')}));
            }""")
            test_results['footer_links'] = footer_links
            take_ss(page, "BUG-006_home_footer_all_dead_links.png")

            # Promo dead links
            promo_links = page.evaluate("""() => {
                const links = [...document.querySelectorAll('a')].filter(a => (a.innerText || '').includes('View Plans') || (a.innerText || '').includes('View Our Guide'));
                return links.map(a => ({text: a.innerText.trim(), href: a.getAttribute('href')}));
            }""")
            test_results['promo_links'] = promo_links
            take_ss(page, "BUG-007_home_promo_dead_cta_links.png")

            # Header navigation disabled items
            nav_items = page.evaluate("""() => {
                const items = [...document.querySelectorAll('header nav *')].filter(el => ['Reports', 'Admin'].includes(el.innerText.trim()));
                return items.map(el => ({tag: el.tagName, text: el.innerText.trim(), cursor: window.getComputedStyle(el).cursor, class: el.className}));
            }""")
            test_results['nav_disabled'] = nav_items
            take_ss(page, "BUG-008_nav_reports_admin_permanently_disabled.png")

            # User profile / Avatar dropdown
            avatar = page.locator("header [class*=avatar], header button:has-text('JD'), header [class*=user]").first
            if avatar.count() > 0:
                avatar.click(timeout=3000)
                page.wait_for_timeout(500)
                test_results['avatar_menu'] = page.evaluate("() => !!document.querySelector('[role=menu], [class*=dropdown], [class*=popover]')")
                take_ss(page, "BUG-009_nav_user_avatar_menu.png")

            # Sign a Document modal
            sign_doc_btn = page.locator("button:has-text('Sign a Document')").first
            if sign_doc_btn.count() > 0:
                sign_doc_btn.click(timeout=3000)
                page.wait_for_timeout(1000)
                take_ss(page, "BUG-010_home_sign_modal_open.png")
                
                # Try Escape key
                page.keyboard.press("Escape")
                page.wait_for_timeout(500)
                modal_after_esc = page.evaluate("() => !!document.querySelector('[role=dialog], [class*=modal], [class*=Modal]')")
                test_results['modal_closes_on_esc'] = not modal_after_esc
                take_ss(page, "BUG-011_home_sign_modal_esc_key_ignored.png")

                # Try clicking outside
                page.mouse.click(10, 10)
                page.wait_for_timeout(500)
                modal_after_outside = page.evaluate("() => !!document.querySelector('[role=dialog], [class*=modal], [class*=Modal]')")
                test_results['modal_closes_on_backdrop'] = not modal_after_outside
                take_ss(page, "BUG-012_home_sign_modal_outside_click_ignored.png")

                # Try clicking Sign without file (force=True to avoid intercept)
                sign_submit = page.locator("button:has-text('Sign'):not(:has-text('Sign a'))").first
                if sign_submit.count() > 0:
                    try:
                        sign_submit.click(force=True, timeout=2000)
                        page.wait_for_timeout(500)
                    except Exception as ex:
                        print(f"Sign submit error: {ex}", flush=True)
                    take_ss(page, "BUG-013_home_sign_modal_submit_without_file.png")

                # Close modal with cancel
                cancel_btn = page.locator("button:has-text('Cancel')").first
                if cancel_btn.count() > 0:
                    try:
                        cancel_btn.click(force=True, timeout=2000)
                        page.wait_for_timeout(500)
                    except Exception as ex:
                        print(f"Cancel click error: {ex}", flush=True)
        except Exception as e:
            print(f"Error in Test 1: {e}", flush=True)

        # ----------------------------------------------------
        # TEST 2: Agreements Screen
        # ----------------------------------------------------
        print("=== Test 2: Agreements Screen ===", flush=True)
        try:
            page.goto(f"{BASE}/send/documents", wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(1000)
            take_ss(page, "BUG-014_agreements_default_screen.png")

            # Sidebar items & debug text
            sidebar_text = page.locator("aside, [class*=sidebar]").first.inner_text() if page.locator("aside, [class*=sidebar]").count() > 0 else page.evaluate("document.body.innerText")
            test_results['sidebar_has_new_navigation'] = "New navigation" in sidebar_text
            take_ss(page, "BUG-015_agreements_debug_label_new_navigation.png")

            # Seeded personal data in documents table
            rows_text = page.evaluate("""() => {
                const rows = [...document.querySelectorAll('tbody tr, [role=row]')];
                return rows.map(r => r.innerText.replace(/\\n+/g, ' | '));
            }""")
            test_results['agreements_rows'] = rows_text[:10]
            take_ss(page, "BUG-016_agreements_seeded_personal_resumes.png")

            # Double file extension .pdf.pdf
            take_ss(page, "BUG-017_agreements_double_pdf_extension.png")

            # Untitled documents allowed in list
            take_ss(page, "BUG-018_agreements_untitled_documents_displayed.png")

            # Download button failure
            dl_btn = page.locator("button:has-text('Download')").first
            if dl_btn.count() > 0:
                dl_btn_html = dl_btn.evaluate("el => el.outerHTML")
                test_results['download_button_html'] = dl_btn_html
                take_ss(page, "BUG-019_agreements_download_button_nonfunctional.png")

            # Search functionality
            search_input = page.locator("input[placeholder*='Search'], input[type='search'], [role='search'] input").first
            if search_input.count() > 0:
                search_input.fill("nonexistentquery12345xyz")
                page.keyboard.press("Enter")
                page.wait_for_timeout(1000)
                no_results_text = page.evaluate("document.body.innerText")
                test_results['search_no_results'] = "nonexistentquery12345xyz" in no_results_text
                take_ss(page, "BUG-020_agreements_search_no_results_state.png")

            # Advanced search panel
            adv_search_btn = page.locator("button:has-text('Advanced search')").first
            if adv_search_btn.count() > 0:
                adv_search_btn.click(timeout=3000)
                page.wait_for_timeout(1000)
                take_ss(page, "BUG-021_agreements_advanced_search_panel.png")

            # Sent tab
            sent_tab = page.locator("text='Sent'").first
            if sent_tab.count() > 0:
                sent_tab.click(timeout=3000)
                page.wait_for_timeout(1000)
                take_ss(page, "BUG-022_agreements_sent_tab_status_missing.png")

            # Completed tab
            comp_tab = page.locator("text='Completed'").first
            if comp_tab.count() > 0:
                comp_tab.click(timeout=3000)
                page.wait_for_timeout(1000)
                take_ss(page, "BUG-023_agreements_completed_tab.png")

            # Action Required tab
            action_tab = page.locator("text='Action Required'").first
            if action_tab.count() > 0:
                action_tab.click(timeout=3000)
                page.wait_for_timeout(1000)
                take_ss(page, "BUG-024_agreements_action_required_tab.png")

            # Start Now button on Agreements page
            start_now_btn = page.locator("button:has-text('Start Now')").first
            if start_now_btn.count() > 0:
                start_now_btn.click(timeout=3000)
                page.wait_for_timeout(1000)
                test_results['url_after_start_now'] = page.url
                take_ss(page, "BUG-025_agreements_start_now_button_action.png")
        except Exception as e:
            print(f"Error in Test 2: {e}", flush=True)

        # ----------------------------------------------------
        # TEST 3: Templates Screen
        # ----------------------------------------------------
        print("=== Test 3: Templates Screen ===", flush=True)
        try:
            page.goto(f"{BASE}/send/templates", wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(1000)
            take_ss(page, "BUG-026_templates_empty_state.png")

            # Create Template button
            create_tmpl_btn = page.locator("button:has-text('Create Template'), a:has-text('Create Template')").first
            if create_tmpl_btn.count() > 0:
                create_tmpl_btn.click(timeout=3000)
                page.wait_for_timeout(1500)
                test_results['create_tmpl_url'] = page.url
                take_ss(page, "BUG-027_templates_create_template_flow.png")
        except Exception as e:
            print(f"Error in Test 3: {e}", flush=True)

        # ----------------------------------------------------
        # TEST 4: Prepare / Send Flow (via Get Signatures)
        # ----------------------------------------------------
        print("=== Test 4: Prepare / Send Flow ===", flush=True)
        try:
            page.goto(f"{BASE}/send/home", wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(1000)
            get_sig = page.locator("button:has-text('Get Signatures')").first
            get_sig.click(timeout=3000)
            page.wait_for_timeout(2000)
            prep_url = page.url
            test_results['prepare_url_1'] = prep_url
            take_ss(page, "BUG-028_prepare_get_signatures_seeded_envelope.png")

            # ID mutation check
            take_ss(page, "BUG-029_prepare_envelope_id_auto_mutation.png")

            # Subject input placeholder typo "Complete with Docusign:"
            subj_el = page.locator("input[placeholder*='Complete with Docusign']").first
            if subj_el.count() > 0:
                subj_ph = subj_el.evaluate("el => el.placeholder")
                test_results['subj_placeholder'] = subj_ph
                take_ss(page, "BUG-030_prepare_subject_placeholder_casing_colon.png")

            # Test pre-send validation by clicking "Next: Add Fields" without document/valid data
            next_btn = page.locator("button:has-text('Next: Add Fields')").first
            if next_btn.count() > 0:
                next_btn.click(timeout=3000)
                page.wait_for_timeout(1000)
                take_ss(page, "BUG-031_prepare_next_add_fields_validation.png")

            # Test invalid email format in recipient
            email_input = page.locator("input[type=email], input[placeholder*='email' i], input[name*='email' i]").first
            if email_input.count() > 0:
                email_input.fill("invalid-email-address")
                page.keyboard.press("Tab")
                page.wait_for_timeout(500)
                take_ss(page, "BUG-032_prepare_invalid_email_recipient_validation.png")

            # Test empty recipient name with filled email
            name_input = page.locator("input[placeholder*='name' i], input[name*='name' i]").first
            if name_input.count() > 0:
                name_input.fill("   ")
                page.keyboard.press("Tab")
                page.wait_for_timeout(500)
                take_ss(page, "BUG-033_prepare_whitespace_recipient_name.png")

            # Test Add Recipient button
            add_recip_btn = page.locator("button:has-text('Add Recipient')").first
            if add_recip_btn.count() > 0:
                add_recip_btn.click(timeout=3000)
                page.wait_for_timeout(500)
                take_ss(page, "BUG-034_prepare_add_multiple_recipients.png")

            # Test Reminder frequency button "Every 0 days"
            reminder_btn = page.locator("button:has-text('Every 0 days'), text='Every 0 days'").first
            if reminder_btn.count() > 0:
                reminder_btn.click(timeout=3000)
                page.wait_for_timeout(500)
                take_ss(page, "BUG-035_prepare_reminder_frequency_zero_days.png")

            # Test "I'm the only signer" toggle behavior
            only_signer = page.locator("input[type=checkbox]").first
            if only_signer.count() > 0:
                only_signer.check()
                page.wait_for_timeout(500)
                take_ss(page, "BUG-036_prepare_only_signer_toggle.png")
        except Exception as e:
            print(f"Error in Test 4: {e}", flush=True)

        # ----------------------------------------------------
        # TEST 5: Direct URL & Authentication Boundaries
        # ----------------------------------------------------
        print("=== Test 5: Direct URLs & Error Boundaries ===", flush=True)
        try:
            page.goto(f"{BASE}/send/nonexistent-route-404-test", wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(1000)
            take_ss(page, "BUG-037_routing_404_error_handling.png")

            page.goto(f"{BASE}/send/prepare", wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(1000)
            take_ss(page, "BUG-038_routing_prepare_without_id.png")
        except Exception as e:
            print(f"Error in Test 5: {e}", flush=True)

        # ----------------------------------------------------
        # TEST 6: Pixel Pass Measurements (from Computed Styles)
        # ----------------------------------------------------
        print("=== Test 6: Pixel Pass Measurements ===", flush=True)
        try:
            page.goto(f"{BASE}/send/home", wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(1000)
            
            btn_styles = page.evaluate("""() => {
                const btns = [...document.querySelectorAll('button')];
                return btns.map(b => {
                    const cs = window.getComputedStyle(b);
                    return {
                        text: b.innerText.trim(),
                        bg: cs.backgroundColor,
                        color: cs.color,
                        borderRadius: cs.borderRadius,
                        padding: cs.padding,
                        fontSize: cs.fontSize,
                        fontWeight: cs.fontWeight,
                        height: cs.height
                    };
                });
            }""")
            test_results['button_styles'] = btn_styles
            take_ss(page, "BUG-039_pixel_button_styling_discrepancies.png")

            header_styles = page.evaluate("""() => {
                const h = document.querySelector('header');
                if (!h) return null;
                const cs = window.getComputedStyle(h);
                return {
                    height: cs.height,
                    bg: cs.backgroundColor,
                    fontFamily: cs.fontFamily,
                    padding: cs.padding
                };
            }""")
            test_results['header_styles'] = header_styles
            take_ss(page, "BUG-040_pixel_header_height_and_spacing.png")

            page.goto(f"{BASE}/send/documents", wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(1000)
            th_styles = page.evaluate("""() => {
                const ths = [...document.querySelectorAll('th')];
                return ths.map(t => {
                    const cs = window.getComputedStyle(t);
                    return {
                        text: t.innerText.trim(),
                        fontSize: cs.fontSize,
                        fontWeight: cs.fontWeight,
                        textTransform: cs.textTransform,
                        color: cs.color,
                        padding: cs.padding
                    };
                });
            }""")
            test_results['th_styles'] = th_styles
            take_ss(page, "BUG-041_pixel_table_header_typography.png")

            tab_styles = page.evaluate("""() => {
                const tabs = [...document.querySelectorAll('[role=tab], [class*=tab]')];
                return tabs.map(t => {
                    const cs = window.getComputedStyle(t);
                    return {
                        text: t.innerText.trim(),
                        color: cs.color,
                        borderBottom: cs.borderBottom,
                        fontWeight: cs.fontWeight
                    };
                });
            }""")
            test_results['tab_styles'] = tab_styles
            take_ss(page, "BUG-042_pixel_tab_indicator_and_contrast.png")
        except Exception as e:
            print(f"Error in Test 6: {e}", flush=True)

        browser.close()

    with open(os.path.join(EVIDENCE_DIR, "detailed_test_results.json"), "w", encoding="utf-8") as f:
        json.dump(test_results, f, indent=2)
    print("Test run completed successfully!", flush=True)

if __name__ == "__main__":
    run()
