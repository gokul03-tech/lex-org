"""BROWSER-LEVEL end-to-end verification of all test PDFs through the real UI.

For every PDF this script, using headless Chromium:
  1. logs into the app like a human,
  2. clicks "New Case Dossier", fills the modal, attaches the PDF, submits,
  3. waits for redirect to /cases/:id, clicks "Run AI Ingestion",
  4. waits for the multi-agent pipeline to finish (summary card appears),
  5. visits ALL FIVE module pages and asserts rendered data,
  6. scans every page for wrong-data markers: undefined / NaN / [object Object],
  7. screenshots failures to test_data/browser_failures/.

Usage:
    .venv/bin/python scripts/browser_e2e_600.py --limit 3      # smoke
    .venv/bin/python scripts/browser_e2e_600.py                # full run (resumes)

Progress: appends one JSON line per case to test_data/browser_results.jsonl
"""
import glob
import json
import os
import re
import sys
import time

from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout

APP = "http://localhost:5173"
TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test_data")
FAIL_DIR = os.path.join(TEST_DIR, "browser_failures")
JSONL = os.path.join(TEST_DIR, "browser_results.jsonl")
EMAIL = "browser-bot@lexorch-testing.com"
PASSWORD = "BrowserBot!2026"

CASE_TIMEOUT = 260          # hard cap per document
JUNK = ["[object Object]", "NaN%", ">NaN<"]


def categorize(filename: str) -> str:
    n = filename.lower()
    if "arbitration" in n:
        return "Commercial Arbitration"
    if "writ" in n or "constitutional" in n:
        return "Constitutional Law"
    if "civil" in n:
        return "Civil Dispute"
    return "Criminal Defense"


def log_result(rec: dict):
    with open(JSONL, "a") as fh:
        fh.write(json.dumps(rec) + "\n")


def already_done() -> set[str]:
    if not os.path.exists(JSONL):
        return set()
    done = set()
    with open(JSONL) as fh:
        for line in fh:
            try:
                rec = json.loads(line)
                if rec.get("ok"):
                    done.add(rec["file"])
            except Exception:
                pass
    return done


def login(page: Page):
    # Fast path: account may already exist
    page.goto(f"{APP}/login", wait_until="domcontentloaded")
    page.wait_for_timeout(900)
    page.fill('input[type="email"]', EMAIL)
    page.fill('input[type="password"]', PASSWORD)
    page.click('button:has-text("Sign In")')
    try:
        page.wait_for_url("**/dashboard", timeout=12000)
        return
    except PWTimeout:
        pass

    # Fallback: register a fresh account, then sign in
    page.goto(f"{APP}/register", wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    page.fill('input[type="text"]', "Browser Bot")
    page.fill('input[type="email"]', EMAIL)
    page.fill('input[type="password"]', PASSWORD)
    page.click('button:has-text("Complete Registration")')
    try:
        page.wait_for_url("**/login", timeout=10000)
    except PWTimeout:
        pass
    page.wait_for_timeout(2200)  # let RegisterPage's delayed redirect settle
    page.goto(f"{APP}/login", wait_until="domcontentloaded")
    page.wait_for_timeout(900)
    page.fill('input[type="email"]', EMAIL)
    page.fill('input[type="password"]', PASSWORD)
    page.click('button:has-text("Sign In")')
    page.wait_for_url("**/dashboard", timeout=30000)


def body_text(page: Page) -> str:
    try:
        return page.locator("body").inner_text(timeout=5000)
    except Exception:
        return ""


def find_junk(page: Page) -> list[str]:
    txt = body_text(page)
    found = [j for j in ["[object Object]", "NaN%"] if j in txt]
    # bare NaN/undefined tokens surrounded by separators
    if re.search(r"(^|\s|>)(NaN|undefined)(\s|<|$|\))", txt):
        found.append("bare NaN/undefined")
    return found


def visit_module(page: Page, case_id: str, sub: str, expect_text: str | None,
                 alt_text: str | None = None) -> dict:
    res = {"page": sub or "overview", "loaded": False, "junk": [], "marker": None}
    page.goto(f"{APP}/cases/{case_id}{sub}", wait_until="domcontentloaded")
    page.wait_for_timeout(1200)
    txt = body_text(page)
    res["loaded"] = len(txt) > 100
    if expect_text and expect_text.lower() in txt.lower():
        res["marker"] = expect_text
    elif alt_text and alt_text.lower() in txt.lower():
        res["marker"] = alt_text  # legitimate empty state
    res["junk"] = find_junk(page)
    return res


def run_one(pw_browser, pdf_path: str, idx: int, total: int, state_file: str) -> dict:
    fname = os.path.basename(pdf_path)
    rec = {"idx": idx, "file": fname, "ok": False, "case_id": None,
           "errors": [], "pages": []}
    context = pw_browser.new_context(viewport={"width": 1440, "height": 900},
                                     storage_state=state_file)
    page = context.new_page()
    t0 = time.time()

    def fail(msg: str):
        rec["errors"].append(msg)
        try:
            os.makedirs(FAIL_DIR, exist_ok=True)
            page.screenshot(path=os.path.join(FAIL_DIR, f"{fname}.png"), full_page=False)
            with open(os.path.join(FAIL_DIR, f"{fname}.txt"), "w") as fh:
                fh.write(msg + "\n\n" + body_text(page)[:3000])
        except Exception:
            pass

    try:
        # ── Create case through the UI modal ────────────────────────
        page.goto(f"{APP}/dashboard", wait_until="domcontentloaded")
        page.wait_for_selector('button:has-text("New Case Dossier")', timeout=20000)
        page.click('button:has-text("New Case Dossier")')
        page.wait_for_selector('input[type="file"]', timeout=10000)
        page.set_input_files('input[type="file"]', pdf_path)
        page.wait_for_timeout(400)
        title_val = page.locator('form input[type="text"]').first.input_value()
        if not title_val.strip():
            page.locator('form input[type="text"]').first.fill(fname.rsplit(".", 1)[0])
        page.select_option('form select', categorize(fname))
        page.locator('form input[type="text"]').nth(1).fill("Browser Bot")
        page.click('button:has-text("Initialize Dossier")')

        page.wait_for_url(re.compile(r"/cases/[0-9a-f-]{36}$"), timeout=45000)
        case_id = page.url.rstrip("/").split("/")[-1]
        rec["case_id"] = case_id

        # ── Trigger ingestion ───────────────────────────────────────
        try:
            page.wait_for_selector('button:has-text("Run AI Ingestion")', timeout=6000)
            page.click('button:has-text("Run AI Ingestion")')
        except PWTimeout:
            pass  # analysis may already exist

        # Wait for pipeline completion: Executive Summary card renders
        deadline = time.time() + CASE_TIMEOUT
        analyzed = False
        while time.time() < deadline:
            txt = body_text(page)
            if "Executive Advisory Summary" in txt or "Grounded Metadata Matrix" in txt:
                analyzed = True
                break
            if "Multi-Agent Processing Engine" in txt:
                pass  # still streaming
            page.wait_for_timeout(2000)
        if not analyzed:
            fail(f"analysis did not complete within {CASE_TIMEOUT}s")
            return rec

        # ── Verify all five module pages ────────────────────────────
        overview = visit_module(page, case_id, "", None)
        otxt = body_text(page)
        otxt_l = otxt.lower()
        checks = {
            "matrix": "grounded metadata matrix" in otxt_l,
            "extracted_badge": "extracted" in otxt_l,
            "trust_ring": re.search(r"\b\d{2}\b", otxt) is not None,
        }
        overview["checks"] = checks
        rec["pages"].append(overview)

        statutes = visit_module(page, case_id, "/statutes",
                                "Sections Invoked", "No statutory provisions extracted yet")
        rec["pages"].append(statutes)
        evidence = visit_module(page, case_id, "/evidence",
                                "Evidence Integrity", "No evidentiary records extracted")
        rec["pages"].append(evidence)

        graph = visit_module(page, case_id, "/graph",
                             "Knowledge Graph Explorer", "No knowledge graph available")
        # Wait for React Flow to actually mount nodes (or accept empty state)
        try:
            page.wait_for_selector(".react-flow__node", timeout=8000)
        except PWTimeout:
            pass
        graph["nodes_rendered"] = page.locator(".react-flow__node").count()
        rec["pages"].append(graph)

        risk = visit_module(page, case_id, "/risk",
                            "IRAC Legal Opinion", None)
        risk["conclusion_block"] = page.locator("text=Operative · for the").count() > 0
        rec["pages"].append(risk)

        # ── Aggregate verdict ───────────────────────────────────────
        all_junk = []
        for p in rec["pages"]:
            all_junk += [f"{p['page']}:{j}" for j in p.get("junk", [])]
        rec["junk_found"] = all_junk
        rec["ok"] = (
            overview["loaded"] and checks["matrix"] and checks["extracted_badge"]
            and statutes["loaded"] and evidence["loaded"] and graph["loaded"]
            and risk["loaded"] and not all_junk
            and (graph["nodes_rendered"] > 0 or "No knowledge graph" in (graph.get("marker") or ""))
        )
        rec["secs"] = round(time.time() - t0, 1)
        if not rec["ok"]:
            summary = {
                "overview_checks": checks,
                "statutes_marker": statutes.get("marker"),
                "evidence_marker": evidence.get("marker"),
                "graph_nodes": graph["nodes_rendered"],
                "graph_marker": graph.get("marker"),
                "risk_conclusion_block": risk.get("conclusion_block"),
                "junk_found": all_junk,
            }
            fail("verdict failed: " + json.dumps(summary))

    except Exception as exc:
        fail(f"exception: {type(exc).__name__}: {exc}")
    finally:
        context.close()
    return rec


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    pdfs = sorted(glob.glob(os.path.join(TEST_DIR, "*.pdf")))
    done = already_done()
    todo = [p for p in pdfs if os.path.basename(p) not in done]
    if limit:
        todo = todo[:limit]

    print(f"[browser-e2e] {len(todo)} to run ({len(done)} already passed)", flush=True)
    if not todo:
        print("nothing to do", flush=True)
        return 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        state_file = "/tmp/opencode/bot_storage_state.json"
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        login(page)
        context.storage_state(path=state_file)
        print(f"[auth] logged in via UI ✅ (state saved)", flush=True)
        context.close()

        ok_count = 0
        for i, pdf in enumerate(todo, 1):
            rec = run_one(browser, pdf, i, len(todo), state_file)
            log_result(rec)
            ok_count += rec["ok"]
            mark = "✅" if rec["ok"] else "❌"
            extra = f"{rec.get('secs', '?')}s" if rec["ok"] else "; ".join(rec["errors"])[:120]
            print(f"{mark} [{i}/{len(todo)}] {os.path.basename(pdf)[:50]:<52} {extra}", flush=True)

        print("=" * 80, flush=True)
        print(f"BROWSER E2E RESULT: {ok_count}/{len(todo)} passed", flush=True)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
