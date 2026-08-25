"""Batch-verify every PDF in backend/test_data through the real pipeline.

Stages per file:
  1. DocumentParser.parse          -> text + page count
  2. extract_metadata              -> parties, court, date, judges, category
  3. build_analysis (universal)    -> sections, precedents, evidence, kg, trust

Exit code 0 only if every file passes every stage.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.document_pipeline.parser import DocumentParser
from app.agents.metadata_extractor import extract_metadata
from app.agents.presentation_universal import build_analysis

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test_data")


def meta_val(meta: dict, key: str):
    v = meta.get(key)
    if isinstance(v, dict):
        return v.get("value")
    return v


def run_one(path: str, parser: DocumentParser) -> dict:
    res = {"file": os.path.basename(path), "checks": {}, "errors": []}

    # Stage 1 — parse
    try:
        parsed = parser.parse(path, mime_type="application/pdf")
        text = parsed.get("text", "")
        res["checks"]["parsed"] = len(text) > 300 and "[Error parsing" not in text
        res["pages"] = parsed.get("page_count", 0)
    except Exception as exc:
        res["errors"].append(f"parse: {exc}")
        res["checks"]["parsed"] = False
        return res

    # Stage 2 — deterministic metadata
    try:
        meta = extract_metadata(text)
        ok_pet = bool(meta_val(meta, "petitioner"))
        ok_res = bool(meta_val(meta, "respondent"))
        ok_date = meta.get("decision_date", {}).get("status") == "extracted"
        ok_court = bool(meta_val(meta, "court"))
        ok_judges = bool(meta_val(meta, "presiding_judges"))
        res["checks"].update({
            "petitioner": ok_pet, "respondent": ok_res,
            "decision_date": ok_date, "court": ok_court, "judges": ok_judges,
        })
        res["category"] = meta.get("case_category")
    except Exception as exc:
        res["errors"].append(f"metadata: {exc}")
        res["checks"].update({"petitioner": False, "respondent": False,
                              "decision_date": False, "court": False, "judges": False})

    # Stage 3 — deep universal analysis builder
    try:
        analysis = build_analysis(text)
        res["checks"]["sections"] = len(analysis.get("sections", [])) > 0 or len(analysis.get("statutes", [])) > 0
        res["checks"]["kg"] = len((analysis.get("kg") or {}).get("nodes", [])) > 0
        res["trust"] = analysis.get("trust_score")
    except Exception as exc:
        res["errors"].append(f"build_analysis: {exc}")
        res["checks"]["sections"] = False
        res["checks"]["kg"] = False

    return res


def main() -> int:
    pdfs = sorted(glob.glob(os.path.join(TEST_DIR, "*.pdf")))
    if not pdfs:
        print("No PDFs found.")
        return 2

    parser = DocumentParser()
    results = []
    for p in pdfs:
        results.append(run_one(p, parser))

    required = ["parsed", "petitioner", "respondent", "decision_date",
                "court", "judges", "sections", "kg"]
    failures = [r for r in results if not all(r["checks"].get(k) for k in required)]

    print("=" * 78)
    print(f"{'FILE':<58} {'PG':>3}  RESULT")
    print("=" * 78)
    for r in results:
        failed = [k for k in required if not r["checks"].get(k)]
        status = "PASS" if not failed else f"FAIL: {','.join(failed)}"
        mark = "✅" if not failed else "❌"
        print(f"{mark} {r['file'][:55]:<56} {r.get('pages', '?'):>3}  {status}")
        for err in r["errors"]:
            print(f"     ⚠ {err}")

    print("=" * 78)
    total_checks = len(results) * len(required)
    passed_checks = sum(1 for r in results for k in required if r["checks"].get(k))
    cats: dict[str, int] = {}
    for r in results:
        cats[r.get("category") or "?"] = cats.get(r.get("category") or "?", 0) + 1
    trusts = [r["trust"] for r in results if isinstance(r.get("trust"), (int, float))]
    print(f"FILES: {len(results)}   CHECKS PASSED: {passed_checks}/{total_checks}"
          f" ({100 * passed_checks / total_checks:.1f}%)")
    print(f"CATEGORIES: {json.dumps(cats)}")
    if trusts:
        print(f"TRUST SCORES: min={min(trusts):.0f} max={max(trusts):.0f} avg={sum(trusts)/len(trusts):.0f}")
    print(f"RESULT: {'ALL PASS ✅' if not failures else f'{len(failures)} FILES FAILED ❌'}")

    with open(os.path.join(TEST_DIR, "batch_test_report.json"), "w") as fh:
        json.dump(results, fh, indent=2)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
