"""Full end-to-end batch test: all 50 test PDFs through the LIVE backend.

Flow per file (mirrors the UI exactly):
  login -> POST /cases/ (with PDF + category) -> GET /analysis/case/{id}/stream (SSE)
        -> wait for all_done -> GET /analysis/case/{id} -> validate payload

Usage:
    .venv/bin/python scripts/e2e_test_50.py            # run all
    .venv/bin/python scripts/e2e_test_50.py --limit 5  # smoke run
"""
import glob
import json
import os
import re
import sys
import time

import requests

BASE = "http://localhost:8000/api/v1"
TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test_data")
EMAIL = "e2e-batch@lexorch-testing.com"
PASSWORD = "E2eBatch!2026"

CASE_TIMEOUT = 300          # seconds per document
SSE_READ_TIMEOUT = 120      # max gap between SSE events


def categorize(filename: str) -> str:
    n = filename.lower()
    if "arbitration" in n:
        return "Commercial Arbitration"
    if "writ" in n or "constitutional" in n:
        return "Constitutional Law"
    if "civil" in n:
        return "Civil Dispute"
    return "Criminal Defense"


def get_token(session: requests.Session) -> str:
    r = session.post(f"{BASE}/auth/register", json={
        "email": EMAIL, "password": PASSWORD,
        "full_name": "E2E Batch Runner", "role": "advocate",
    })
    if r.status_code not in (200, 201):
        pass  # likely already registered
    r = session.post(f"{BASE}/auth/login", data={
        "username": EMAIL, "password": PASSWORD,
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})
    r.raise_for_status()
    return r.json()["access_token"]


def run_case(session: requests.Session, token: str, pdf_path: str) -> dict:
    fname = os.path.basename(pdf_path)
    out = {"file": fname, "ok": False, "errors": []}
    t0 = time.time()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create case with the PDF attached
    with open(pdf_path, "rb") as fh:
        r = session.post(
            f"{BASE}/cases/",
            files={"file": (fname, fh, "application/pdf")},
            data={
                "title": re.sub(r"^\d+_", "", fname).rsplit(".", 1)[0].replace("_", " "),
                "case_type": categorize(fname),
                "description": "[E2E-BATCH] automated overnight verification run",
            },
            headers=headers,
            timeout=60,
        )
    if r.status_code != 201:
        out["errors"].append(f"create_case {r.status_code}: {r.text[:160]}")
        return out
    case_id = r.json()["id"]
    out["case_id"] = case_id

    # 2. Stream analysis over SSE until all_done
    done = False
    try:
        with session.get(
            f"{BASE}/analysis/case/{case_id}/stream",
            headers={**headers, "Accept": "text/event-stream"},
            stream=True, timeout=(30, SSE_READ_TIMEOUT),
        ) as resp:
            resp.raise_for_status()
            stages_seen = set()
            last = time.time()
            for raw in resp.iter_lines(decode_unicode=True):
                if time.time() - t0 > CASE_TIMEOUT:
                    out["errors"].append("overall timeout")
                    break
                if not raw or not raw.startswith("data:"):
                    continue
                try:
                    evt = json.loads(raw[5:].strip())
                except json.JSONDecodeError:
                    continue
                stages_seen.add(evt.get("stage"))
                last = time.time()
                if evt.get("stage") == "all_done":
                    done = True
                    break
            out["stages"] = len(stages_seen)
    except requests.exceptions.RequestException as exc:
        out["errors"].append(f"sse: {exc}")
    if not done:
        return out

    # 3. Fetch compiled analysis and validate payload
    r = session.get(f"{BASE}/analysis/case/{case_id}", headers=headers, timeout=30)
    if r.status_code != 200:
        out["errors"].append(f"analysis fetch {r.status_code}")
        return out
    a = r.json()

    md = a.get("metadata", {})
    def mval(key):
        v = md.get(key, {})
        return v.get("value") if isinstance(v, dict) else v

    checks = {
        "summary": bool(a.get("summary")),
        "court": bool(mval("court")) and mval("court") != "High Court of Judicature",
        "parties": bool(mval("petitioner")) and bool(mval("respondent")),
        "sections": len(a.get("sections", [])) > 0,
        "precedents": len(a.get("precedents", [])) > 0,
        "evidence": len(a.get("evidence", [])) > 0,
        "risk": bool(a.get("risk_analysis")),
        "kg_nodes": len((a.get("kg_data") or {}).get("nodes", [])) > 0,
        "trust_score": bool(a.get("confidence", {}).get("score")),
    }
    out["checks"] = checks
    out["trust"] = a.get("confidence", {}).get("score")
    out["secs"] = round(time.time() - t0, 1)
    out["ok"] = all(checks.values())
    failed = [k for k, v in checks.items() if not v]
    if failed:
        out["errors"].append(f"failed checks: {failed}")
    return out


def main() -> int:
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    pdfs = sorted(glob.glob(os.path.join(TEST_DIR, "*.pdf")))
    if limit:
        pdfs = pdfs[:limit]

    session = requests.Session()
    token = get_token(session)
    print(f"[auth] OK — testing {len(pdfs)} documents", flush=True)

    results = []
    for i, p in enumerate(pdfs, 1):
        res = run_case(session, token, p)
        res["idx"] = i
        results.append(res)
        mark = "✅" if res["ok"] else "❌"
        extra = f" trust={res.get('trust')}% {res.get('secs')}s" if res["ok"] else f" ERRORS: {res['errors']}"
        print(f"{mark} [{i:>2}/{len(pdfs)}] {os.path.basename(p)[:52]:<52}{extra}", flush=True)

    ok_count = sum(1 for r in results if r["ok"])
    secs = [r["secs"] for r in results if "secs" in r]
    trusts = [r["trust"] for r in results if isinstance(r.get("trust"), (int, float))]
    print("=" * 80, flush=True)
    print(f"E2E RESULT: {ok_count}/{len(results)} passed"
          + (f" | avg {sum(secs)/len(secs):.1f}s/doc" if secs else "")
          + (f" | trust avg {sum(trusts)/len(trusts):.0f}%" if trusts else ""), flush=True)

    with open(os.path.join(TEST_DIR, "e2e_report.json"), "w") as fh:
        json.dump(results, fh, indent=2)
    print("Report saved: test_data/e2e_report.json", flush=True)
    return 0 if ok_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
