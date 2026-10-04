# QA Summary — DocuSign Clone (Scaler AI Labs)
<!-- Half a page max. Replace every [bracket]. Lines starting with <!-- are ignored by the PDF builder. -->
**Tester:** QA Team · **Date:** 03 Oct 2026 · **Env:** Chrome 153.0.8010.12 / Windows 11 Build 26300 · 1280x960 · 100% zoom · **Bugs logged:** 45 (P0 2 · P1 8 · P2 20 · P3 11 · P4 4)

## Overall impression
The clone reproduces DocuSign's layout structure and high-level navigation shell reasonably well across Dashboard, Agreements, and Prepare views. However, critical interactive pathways are non-functional—the primary 'Start' CTA is completely dead, 'Get Signatures' creates orphaned seeded draft envelopes on every click, and file downloads fail silently. Visually, while layout geometry approximates the desktop dashboard, key DocuSign design tokens diverge (e.g. non-standard purple buttons vs DocuSign signature blue, missing WCAG contrast ratios, and internal RL branding in page titles).

## Top 5 bugs to fix first
1. **[BUG-003]** Home: Primary 'Start' action button is completely unresponsive on click — blocks the main envelope creation flow for all new and returning users.
2. **[BUG-029]** Prepare: Every click on 'Get Signatures' creates redundant orphaned envelope ID in database — causes continuous backend database bloat and ghost record pollution on every page navigation.
3. **[BUG-019]** Agreements: Document row 'Download' button fails to trigger browser file download — breaks core post-signing document retrieval and agreement export functionality.
4. **[BUG-031]** Prepare: Clicking 'Next: Add Fields' without uploaded document does not display inline blocker — allows invalid empty envelopes to progress into field preparation.
5. **[BUG-001]** Home: Page title and meta description expose internal RL environment branding — highly visible branding defect ('Rl_Docusign') exposed on every session and browser tab.

## Tested vs. deliberately skipped
- **Tested:** Auth & session landing, dashboard metrics & quick actions, agreements list & sidebar filters, upload dropzones & prepare stepper, recipient configuration & email validation, modal interactions (Escape, backdrop click), template management views, routing 404 boundaries, console errors, and pixel/CSS token audits against DocuSign at 1280x960.
- **Skipped (out of scope per brief):** Third-party integrations (Slack/Google/Salesforce), load and performance stress testing, security vulnerability probing (SQLi, XSS, auth bypass), paid plan payment gateways.

## Suspected but not confirmed
- Status counter cards on the Dashboard ('Waiting for others', 'Expiring soon', 'Completed') appear statically computed or hardcoded to mock values rather than driven by real-time envelope status aggregates.
- Envelope signing reminders ('Every 0 days') appear to omit backend cron dispatch workers entirely.

## Assumptions
- The official DocuSign web application UI as of October 2026 serves as the definitive source of truth; enterprise features gated behind paid tiers were not penalized.
- Seeded database documents should contain clean, realistic, and anonymized business contracts rather than internal personal resumes or duplicate file extensions.
