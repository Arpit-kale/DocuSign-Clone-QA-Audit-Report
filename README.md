# DocuSign Clone — QA Audit Report

![Status](https://img.shields.io/badge/QA%20pass-complete-2E7D32)
![Defects](https://img.shields.io/badge/defects-45-1F3864)
![P0](https://img.shields.io/badge/P0-2-C00000)
![P1](https://img.shields.io/badge/P1-8-E65100)
![P2](https://img.shields.io/badge/P2-20-F9A825)
![Env](https://img.shields.io/badge/Chrome%20·%20Windows%2011-1280×960-607D8B)

A side-by-side quality audit of the **Scaler AI Labs DocuSign clone** against production **DocuSign**, covering visual fidelity, end-to-end functional flows and the realism of seeded data.

> **Verdict in one line:** the clone looks convincing at a glance, but the main entry point to sending a document is broken, and the Prepare step silently writes junk records on every visit. Fix those two and most of what remains is polish.

---

## At a glance

| | |
|---|---|
| **Tester** | QA Team |
| **Build under test** | `http://13.207.185.159/` (behind HTTP basic auth) |
| **Reference** | DocuSign web app, free-trial account |
| **Environment** | Chrome 153.0.8010.12 · Windows 11 (build 26300) · 1280 × 960 · 100% zoom |
| **Date** | 03 Oct 2026 |
| **Defects logged** | 45, each with screenshot evidence and repro steps |

### Severity profile

| Tag | Level | Count | What it means here |
|:---:|---|:---:|---|
| **P0** | Blocker | 2 | Stops the core send flow or corrupts stored data |
| **P1** | Critical | 8 | Core feature broken, or severe UI failure on a main screen |
| **P2** | Major | 20 | Wrong behaviour on a common path, or visible pixel drift on a primary screen |
| **P3** | Minor | 11 | Edge cases, secondary screens, subtle visual mismatches |
| **P4** | Trivial | 4 | Copy, branding and 1px-level cosmetics |
| | **Total** | **45** | |

A per-category breakdown is calculated live on the **Summary** tab of the tracker.

---

## What to fix first

| # | Bug | Severity | Why it comes first |
|:---:|---|:---:|---|
| 1 | **BUG-003** — Home: the primary **Start** button does nothing on click | P0 | It is the front door to the product. No new envelope can be started from the dashboard, so every downstream flow is unreachable from its natural entry point. |
| 2 | **BUG-029** — Prepare: each click on **Get Signatures** creates a new, empty envelope record | P0 | Data corruption without any user action to confirm it. Every visit leaves an orphaned envelope behind, which pollutes lists, counters and any model trained on this state. |
| 3 | **BUG-031** — Prepare: **Next: Add Fields** proceeds with no document uploaded | P1 | Missing validation lets an envelope reach field placement with nothing to place fields on, producing invalid states further down the flow. |
| 4 | **BUG-0XX** — *[next-highest P1]* | P1 | *[one line on user impact]* |
| 5 | **BUG-0XX** — *[next-highest P1 / P2]* | P1 | *[one line on user impact]* |

---

## Where the clone diverges from DocuSign

**Interaction and flow.** The most serious problems sit at the start of the journey: the Start CTA, envelope creation on the Prepare screen, and the absence of guards before moving on to field placement. Once a user gets past those, the remaining issues are mostly validation gaps and navigation inconsistencies rather than dead ends.

**Seeded data.** Several records do not hold up to a close read: placeholder names, timestamps that never move, and statuses that contradict the rest of the row. The page title and meta description also expose internal environment naming (`Rl_Docusign`) in every browser tab.

**Visual fidelity.** Measured from computed styles, not by eye:

| Element | Clone | DocuSign | Impact |
|---|---|---|---|
| Top navigation height | 64px, `0 16px` padding | 60px | Nav items sit lower than the original |
| Table header text | Uppercase, heavier weight (`NAME`, `STATUS`) | Title case, lighter (`Subject`, `Status`) | Table reads louder than the original |
| Primary button | `#CAC2FF` background, `#130032` text | *[value from original's computed style]* | *[match / mismatch]* |
| Dashboard heading | No `<h1>` present | Page has a top-level heading | Structure and accessibility drift |

---

## Repository contents

| Path | Contents |
|---|---|
| [`bug_tracker_QA.xlsx`](bug_tracker_QA.xlsx) | The tracker: all 14 required columns, severity and category dropdowns, colour-coded severity, live summary counts |
| [`summary_note.pdf`](summary_note.pdf) | Half-page summary note ([source](summary_note.md)) |
| [`evidence/`](evidence/) | One screenshot per defect, named `BUG-00X_<module>_<slug>.png` to match the tracker |
| [`bugs.json`](bugs.json) | Single source of truth; the spreadsheet and PDF are generated from it |
| [`notes/checklist.md`](notes/checklist.md) | Module-by-module coverage checklist |
| [`notes/blocked.md`](notes/blocked.md) | Flows that could not be tested past a certain point, and why |
| [`RUNNING_GUIDE.md`](RUNNING_GUIDE.md) | Full setup and reproduction guide |

### Testing that was blocked

- **Dashboard → Start:** the button is unresponsive (logged as BUG-003), so the upload flow had to be reached through **Get Signatures** instead.

---

## Scope

**Covered**
- **Shell and navigation:** login redirect, session persistence across refresh, active nav states, avatar menu, footer links.
- **Dashboard:** hero banner, Start, Send with AI, Get Signatures, the Sign a Document modal, overview status cards.
- **Agreements:** list rendering, search and advanced search, filename handling, seeded-data audit.
- **Prepare and send:** envelope creation, recipient validation, email format checks, reminder settings.
- **Global behaviour:** modal dismissal (Esc and backdrop click), 404 handling, design-token comparison against the original.

**Excluded, per the brief**
- Export and download (CSV, PDF, image, and document download).
- Third-party integrations (Drive, Notion, Slack, Salesforce).
- Load and performance benchmarking.
- Security testing (XSS, SQL injection, brute force, sign-ups).

**Excluded by assumption**
- Paid-plan features and billing flows, since the free-trial reference account cannot show them.

---

## Rebuilding the deliverables

```bash
pip install -r requirements.txt
playwright install chromium

# Re-capture screens, computed styles and console errors
python scripts/comprehensive_bug_collector.py

# Regenerate the tracker and summary PDF from bugs.json
python scripts/build_deliverables.py --name "QA" \
  --evidence-base https://github.com/<GITHUB_USER>/<REPO>/blob/main/
```

The build stops with a clear message if any row is missing a required field, uses an invalid severity, repeats an ID, or points to an evidence file that does not exist.