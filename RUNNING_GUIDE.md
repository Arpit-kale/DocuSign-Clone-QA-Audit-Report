# QA Reproduction & Running Guide — DocuSign Clone

This guide provides step-by-step instructions to reproduce tests, capture automated evidence, validate the bug dataset, and rebuild the deliverables (`.xlsx` bug tracker and `.pdf` executive summary).

---

## 1. Environment & Prerequisites

- **Operating System:** Windows 11 (Build 26300) / macOS / Linux
- **Python:** Python 3.10+ (tested on Python 3.14)
- **Browser:** Chromium 153+ via Playwright
- **Viewport:** 1280 × 960 (100% zoom)
- **Target Application:** `http://13.207.185.159/`
- **Authentication:** HTTP Basic Auth; provide credentials locally using `DOCUSIGN_QA_USERNAME` and `DOCUSIGN_QA_PASSWORD`.

### Setup Environment
```bash
# Clone the repository
git clone https://github.com/<GITHUB_USER>/<REPO>.git
cd QA-DocuSign-Clone-Bug-Hunt

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright Chromium browser binary
playwright install chromium

# Set these in your local shell; do not commit credentials
export DOCUSIGN_QA_USERNAME="<your username>"
export DOCUSIGN_QA_PASSWORD="<your password>"
```

---

## 2. Running Automated Test Passes & Evidence Collection

### Comprehensive Bug Collector (`scripts/comprehensive_bug_collector.py`)
Executes end-to-end user journeys across all application screens (Dashboard, Agreements, Templates, Prepare flow, Modals, Error boundaries, and Pixel/CSS audits). Captures screenshots directly into `evidence/`:
```bash
python scripts/comprehensive_bug_collector.py
```

### Headless Pixel Capture (`scripts/capture.py`)
Performs batch navigation across all documented routes in `routes.txt`, capturing full-page screenshots, computed CSS styling tokens (`styles.json`), and browser console logs (`console.json`):
```bash
python scripts/capture.py --routes routes.txt --selectors selectors.txt --out evidence/raw/clone
```

### Screenshot Annotation Tool (`scripts/annotate.py`)
Adds a highlighted red rectangular callout box with a label directly onto an evidence screenshot:
```bash
python scripts/annotate.py evidence/BUG-003_home_start_button_unresponsive.png 184 120 120 40 "Unresponsive button"
```

---

## 3. Validating & Rebuilding Deliverables

### Validate Bug Dataset (`bugs.json`)
The script `scripts/compile_bugs.py` validates the schema integrity of all 45 logged bugs:
```bash
python scripts/compile_bugs.py
```
Validation checks performed by `build_deliverables.py`:
- All 9 required fields present (`id`, `title`, `category`, `severity`, `module`, `steps`, `expected`, `actual`, `evidence`).
- Severity must be one of `P0`, `P1`, `P2`, `P3`, `P4`.
- Unique IDs with no duplicates.
- Every evidence path resolves to an existing file on disk.

### Rebuilding Spreadsheets & PDFs (`scripts/build_deliverables.py`)
To build the local Excel tracker (`bug_tracker_QA.xlsx`) and PDF summary (`summary_note.pdf`):
```bash
python scripts/build_deliverables.py --name "QA"
```

To build with public GitHub evidence URLs embedded in every row:
```bash
python scripts/build_deliverables.py --name "QA" --evidence-base https://github.com/<GITHUB_USER>/<REPO>/blob/main/
```

---

## 4. Key Manual Test Repro Recipes

### BUG-003: Primary 'Start' Action Button Unresponsive (P0)
1. Open `http://13.207.185.159/` and authenticate using your locally configured credentials.
2. On `/send/home`, locate the primary 'Start' CTA button in the hero card.
3. Click 'Start'.
4. **Expected:** File upload modal or workflow initiation.
5. **Actual:** Zero response; no DOM change, no network call.

### BUG-029: 'Get Signatures' Envelope ID Auto-Mutation & DB Bloat (P0)
1. Navigate to `/send/home`.
2. Click 'Get Signatures' — observe URL: `/send/prepare/<ID>?isNew=true` (e.g. ID `16039`).
3. Click 'Home' to return to dashboard.
4. Click 'Get Signatures' again — observe new ID `16040`.
5. Repeat — observe monotonic ID auto-increment creating orphaned ghost records without user confirmation.

### BUG-019: Agreements Table Download Button Non-Functional (P1)
1. Navigate to `/send/documents`.
2. Locate any agreement row and click the 'Download' button.
3. **Expected:** Browser initiates download of combined/separate document PDF.
4. **Actual:** No download event fires; action fails silently.

### BUG-011: Modal Escape Key Dismiss Ignored (P2)
1. On `/send/home`, click 'Sign a Document' to open the dialog.
2. Press `Escape` on the physical keyboard.
3. **Expected:** Dialog immediately dismisses.
4. **Actual:** Dialog remains trapped on screen.
