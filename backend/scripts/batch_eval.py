"""Batch-validation harness for LexOrch-KG over large legal-document corpora.

Runs the production ingest + deterministic analysis pipeline
(DocumentParser -> build_analysis) over every PDF/TXT/HTML file in a
directory, then validates each analysis report against ten grounding
rules (V01-V10). Results are aggregated into JSON + CSV reports under
--out, with per-file checkpoints under .cache/eval/ so long runs can be
resumed. An optional LLM spot-check mode (--with-llm --sample N) runs a
stratified sample of documents per category through the full
presentation layer and adds grounding checks L01-L03.

Usage (from backend/):
    python -m scripts.batch_eval --dir ./test_data --out ./reports --workers 8
    python -m scripts.batch_eval --dir ./test_data --out ./reports \
        --workers 8 --with-llm --sample 5

Exit code is 0 iff pass_rate >= 0.95 and there are zero V02/V03/V08
violations across the whole batch.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - tqdm is optional
    tqdm = None

from app.agents.presentation_universal import LABELS, build_analysis
from app.document_pipeline.parser import DocumentParser

CACHE_VERSION = 3
PASS_RATE_THRESHOLD = 0.95
HARD_CODES = frozenset({"V02", "V03", "V08"})
ALLOWED_CATEGORIES = frozenset(
    {"criminal_bail", "criminal_trial", "civil", "arbitration", "writ", "other"}
)
VALID_STATUSES = frozenset({"extracted", "inferred", "not_found"})
BANNED_STRINGS = (
    "Not found in document",
    "Mock summary",
    "keyword",
    "vector",
    "Applicable Statutes",
    "{'num'",
    "Bail App.",
    "— —",
    "IN THE HIGH COURT OF IN THE",
)
JUNK_NAMES = frozenset({"keyword", "vector", ""})
OPERATIVE_VERB_RE = re.compile(r"\b(?:allowed|dismissed|disposed|set aside)\b", re.IGNORECASE)
SUPPORTED_SUFFIXES = {".pdf", ".txt", ".html", ".htm"}
MIME_BY_SUFFIX = {".pdf": "application/pdf", ".txt": "text/plain"}

_norm_ws = lambda s: re.sub(r"\s+", " ", str(s or "")).strip()
_nows = lambda s: re.sub(r"[^a-z0-9]", "", str(s or "").lower())
EM_DASH = "\u2014"


# --------------------------------------------------------------------------- #
# Result containers
# --------------------------------------------------------------------------- #
@dataclass
class Violation:
    """A single rule violation attached to one evaluated file."""

    code: str
    message: str


@dataclass
class FileResult:
    """Outcome of evaluating exactly one input document."""

    file: str
    parsed: bool
    engine: str = ""
    pages: int = 0
    category: str | None = None
    trust_score: float | None = None
    coverage: float | None = None
    status_counts: dict[str, int] = field(default_factory=dict)
    violations: list[Violation] = field(default_factory=list)
    error: str | None = None
    duration_ms: int = 0
    llm_checked: bool = False

    @property
    def passed(self) -> bool:
        return self.parsed and not self.violations

    def violation_codes(self) -> list[str]:
        return [v.code for v in self.violations]


@dataclass
class BatchSummary:
    """Aggregated statistics for the whole batch run."""

    total: int = 0
    parsed: int = 0
    parse_fail: int = 0
    passed: int = 0
    pass_rate: float = 0.0
    categories: dict[str, int] = field(default_factory=dict)
    avg_coverage: float | None = None
    avg_trust: float | None = None
    top_violations: list[tuple[str, int]] = field(default_factory=list)
    hard_violations: dict[str, int] = field(default_factory=dict)
    llm_checked: int = 0
    failed_files: list[dict[str, str]] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Generic helpers
# --------------------------------------------------------------------------- #
def iter_strings(node: Any) -> Iterator[str]:
    """Yield every string leaf value inside an arbitrarily nested structure."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from iter_strings(value)
    elif isinstance(node, (list, tuple, set)):
        for item in node:
            yield from iter_strings(item)


def file_sha1(path: Path) -> str:
    """Stable content hash used as the per-file checkpoint key."""
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# --------------------------------------------------------------------------- #
# Ingest stage
# --------------------------------------------------------------------------- #
class IngestError(RuntimeError):
    """Raised when a file cannot be converted to non-empty text."""


def _fallback_pdf_text(path: Path) -> str:
    """Extract PDF text with pdfplumber, then pypdf, without OCR."""
    try:
        import pdfplumber

        with pdfplumber.open(str(path)) as pdf:
            return "\n\n".join(page.extract_text() or "" for page in pdf.pages)
    except ImportError:
        pass
    except Exception:
        pass
    try:
        from pypdf import PdfReader

        return "\n\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)
    except Exception as exc:
        raise IngestError(f"pdf fallback failed: {exc}") from exc


def _fallback_plain_text(path: Path) -> str:
    """Read .txt/.html as utf-8; strip tags for html."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise IngestError(f"read failed: {exc}") from exc
    if path.suffix.lower() in {".html", ".htm"}:
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
        text = re.sub(r"<[^>]+>", " ", text)
    return text


def ingest_document(path: Path) -> tuple[str, str, int]:
    """Ingest one file via the production parser, with graceful fallbacks.

    Returns:
        Tuple of (text, engine_label, page_count).

    Raises:
        IngestError: If no strategy yields non-empty text.
    """
    suffix = path.suffix.lower()
    try:
        parsed = DocumentParser().parse(path, mime_type=MIME_BY_SUFFIX.get(suffix))
        text = parsed.get("text") or ""
        if text.strip():
            fmt = parsed.get("format", suffix.lstrip("."))
            return text, f"DocumentParser/{fmt}", int(parsed.get("page_count") or 0)
    except IngestError:
        raise
    except Exception:
        logger.opt(exception=False).debug(f"primary parser failed for {path.name}; falling back")

    if suffix == ".pdf":
        text = _fallback_pdf_text(path)
        if text.strip():
            return text, "fallback/pdfplumber+pypdf", 0
        raise IngestError("empty text extracted from pdf")
    text = _fallback_plain_text(path)
    if text.strip():
        return text, "fallback/utf8", 1
    raise IngestError("empty or unreadable file")


# --------------------------------------------------------------------------- #
# Validators V01-V10 (each returns a list of violations)
# --------------------------------------------------------------------------- #
def check_banned_strings(report: dict[str, Any]) -> list[Violation]:
    """V02 - no banned/mock/placeholder string may appear anywhere in output."""
    banned_lower = [b.lower() for b in BANNED_STRINGS]
    found: dict[str, str] = {}
    for text in iter_strings(report):
        low = text.lower()
        for banned, banned_l in zip(BANNED_STRINGS, banned_lower):
            if banned_l in low and banned not in found:
                found[banned] = text[:100]
    return [
        Violation("V02", f"banned string {b!r} leaked in output: {snip!r}")
        for b, snip in found.items()
    ]


def check_case_title(report: dict[str, Any], stem: str, filename: str) -> list[Violation]:
    """V03 - case_title must be non-empty and never echo the filename."""
    meta = report.get("metadata") or {}
    title_field = meta.get("case_title")
    value = title_field.get("value") if isinstance(title_field, dict) else title_field
    if not isinstance(value, str) or not value.strip():
        return [Violation("V03", "metadata.case_title is empty")]
    leaks = {
        _norm_ws(stem).casefold(),
        _norm_ws(filename).casefold(),
    }
    if _norm_ws(value).casefold() in leaks:
        return [Violation("V03", f"case_title renders the filename stem: {value[:80]!r}")]
    return []


def check_metadata_statuses(report: dict[str, Any]) -> list[Violation]:
    """V04 - every metadata field status must be extracted/inferred/not_found."""
    violations = []
    for key, value in (report.get("metadata") or {}).items():
        status = value.get("status") if isinstance(value, dict) else None
        if status not in VALID_STATUSES:
            violations.append(Violation("V04", f"metadata.{key} has invalid status {status!r}"))
    return violations


def check_trust_score(report: dict[str, Any]) -> list[Violation]:
    """V05 - trust_score must lie in [40, 99]; it may never reach 100."""
    trust = report.get("trust_score")
    if isinstance(trust, bool) or not isinstance(trust, (int, float)):
        return [Violation("V05", f"trust_score is not numeric: {trust!r}")]
    if not 40 <= trust <= 99:
        return [Violation("V05", f"trust_score {trust} outside allowed range [40, 99]")]
    return []


def check_timeline(report: dict[str, Any]) -> list[Violation]:
    """V06 - timeline non-empty; tail event date matches extracted decision_date."""
    timeline = report.get("timeline") or []
    if not timeline:
        return [Violation("V06", "timeline is empty")]
    decision = (report.get("metadata") or {}).get("decision_date")
    if isinstance(decision, dict) and decision.get("status") == "extracted" and decision.get("value"):
        tail_date = (timeline[-1] or {}).get("date") if isinstance(timeline[-1], dict) else None
        if _norm_ws(tail_date) != _norm_ws(decision["value"]):
            return [
                Violation(
                    "V06",
                    f"tail timeline date {tail_date!r} != decision_date {decision['value']!r}",
                )
            ]
    return []


def check_statutes(report: dict[str, Any]) -> list[Violation]:
    """V07 - every statute exposes a formatted display with em-dash + act name."""
    violations = []
    for index, section in enumerate(report.get("sections") or []):
        if not isinstance(section, dict):
            violations.append(Violation("V07", f"sections[{index}] is not a structured entry"))
            continue
        display = section.get("display")
        act = section.get("act")
        if not isinstance(display, str) or EM_DASH not in display:
            violations.append(Violation("V07", f"sections[{index}] display missing '{EM_DASH}'"))
        elif not isinstance(act, str) or not act or act not in display:
            violations.append(Violation("V07", f"sections[{index}] display missing act name"))
    return violations


def check_precedents(report: dict[str, Any]) -> list[Violation]:
    """V08 - precedent names valid, no self-match, similarity sane, citations bound."""
    violations = []
    meta = report.get("metadata") or {}
    title_field = meta.get("case_title")
    title_value = title_field.get("value") if isinstance(title_field, dict) else title_field
    title_key = _nows(title_value)
    citation_owner: dict[str, str] = {}

    for index, precedent in enumerate(report.get("precedents") or []):
        label = f"precedents[{index}]"
        if not isinstance(precedent, dict):
            violations.append(Violation("V08", f"{label} is not a structured entry"))
            continue
        name = str(precedent.get("case_name") or "").strip()
        if name.lower() in JUNK_NAMES:
            violations.append(Violation("V08", f"{label} has junk case_name {name!r}"))
        elif title_key and _nows(name) == title_key:
            violations.append(Violation("V08", f"{label} case_name matches the case itself"))
        similarity = precedent.get("similarity")
        if similarity is not None and (
            isinstance(similarity, bool) or not isinstance(similarity, (int, float)) or similarity > 100
        ):
            violations.append(Violation("V08", f"{label} similarity out of range: {similarity!r}"))
        citation = str(precedent.get("citation") or "").strip()
        if citation:
            cite_key = _nows(citation)
            name_key = _nows(name)
            owner = citation_owner.setdefault(cite_key, name_key)
            if owner != name_key:
                violations.append(
                    Violation("V08", f"citation {citation!r} shared by two precedents")
                )
    return violations


def check_category(report: dict[str, Any]) -> list[Violation]:
    """V09 - detected category must be one of the known taxonomy values."""
    category = report.get("category")
    if category not in ALLOWED_CATEGORIES:
        return [Violation("V09", f"unknown category {category!r}")]
    return []


def check_category_sections(report: dict[str, Any]) -> list[Violation]:
    """V10 - submissions/evidence/risk populated; labels match LABELS[category]."""
    violations = []
    category = report.get("category")
    expected_labels = list(LABELS.get(category, ("", "")))
    labels = report.get("labels")
    labels_list = [str(x) for x in labels] if isinstance(labels, (list, tuple)) else []
    if labels_list != expected_labels:
        violations.append(
            Violation("V10", f"labels {labels_list} != LABELS[{category!r}] {expected_labels}")
        )

    submissions = report.get("submissions") or {}

    def _has_content(key: str) -> bool:
        items = submissions.get(key)
        return isinstance(items, list) and any(isinstance(x, str) and x.strip() for x in items)

    if not _has_content("a"):
        violations.append(Violation("V10", "submissions.a is empty"))
    if not _has_content("b"):
        violations.append(Violation("V10", "submissions.b is empty"))
    if not any(
        isinstance(x, dict) and str(x.get("detail") or x.get("label") or "").strip()
        for x in report.get("evidence") or []
    ):
        violations.append(Violation("V10", "evidence entries are empty"))

    risk = report.get("risk") or {}
    for key in ("strengths", "gaps", "action_plan"):
        items = risk.get(key)
        if not isinstance(items, list) or not any(
            isinstance(x, str) and x.strip() for x in items
        ):
            violations.append(Violation("V10", f"risk.{key} is empty"))
    if not str(risk.get("conclusion") or "").strip():
        violations.append(Violation("V10", "risk.conclusion is empty"))
    return violations()


def compute_coverage(report: dict[str, Any]) -> tuple[float | None, dict[str, int]]:
    """Coverage = extracted / (extracted + inferred + not_found) over metadata."""
    counts = Counter(
        value.get("status")
        for value in (report.get("metadata") or {}).values()
        if isinstance(value, dict)
    )
    status_counts = {k: counts[k] for k in sorted(counts)}
    total = sum(status_counts.get(s, 0) for s in VALID_STATUSES)
    if total == 0:
        return None, status_counts
    return status_counts.get("extracted", 0) / total, status_counts


def validate_report(report: dict[str, Any], stem: str, filename: str) -> list[Violation]:
    """Run every V-rule against one analysis report and collect all violations."""
    violations: list[Violation] = []
    violations.extend(check_banned_strings(report))
    violations.extend(check_case_title(report, stem, filename))
    violations.extend(check_metadata_statuses(report))
    violations.extend(check_trust_score(report))
    violations.extend(check_timeline(report))
    violations.extend(check_statutes(report))
    violations.extend(check_precedents(report))
    violations.extend(check_category(report))
    violations.extend(check_category_sections(report))
    return violations


# --------------------------------------------------------------------------- #
# Optional LLM-mode checks (L01-L03)
# --------------------------------------------------------------------------- #
def supporting_quotes(report: dict[str, Any]) -> list[str]:
    """Collect document-derived strings that must exist verbatim in the source."""
    quotes: list[str] = []
    for item in report.get("evidence") or []:
        if isinstance(item, dict) and item.get("detail"):
            quotes.append(str(item["detail"]))
    for item in report.get("timeline") or []:
        if isinstance(item, dict) and item.get("fact"):
            quotes.append(str(item["fact"]))
    risk = report.get("risk") or {}
    for key in ("strengths", "gaps", "action_plan"):
        for item in risk.get(key) or []:
            if isinstance(item, str) and item.strip():
                quotes.append(item)
    return [q for q in quotes if q.strip()]


def llm_extra_violations(text: str, report: dict[str, Any]) -> tuple[list[Violation], dict[str, Any]]:
    """L01-L03: issues non-empty, operative conclusion, verbatim quote grounding."""
    from app.agents.presentation_universal import render_issues

    violations: list[Violation] = []
    issues = render_issues(report)
    if not issues:
        violations.append(Violation("L01", "issues[] is empty"))

    conclusion = str((report.get("risk") or {}).get("conclusion") or "")
    if not OPERATIVE_VERB_RE.search(conclusion):
        violations.append(Violation("L02", f"conclusion lacks operative verb: {conclusion[:80]!r}"))

    source = _norm_ws(text)
    ungrounded = 0
    for quote in supporting_quotes(report):
        if _norm_ws(quote) not in source:
            ungrounded += 1
            violations.append(
                Violation("L03", f"supporting quote not verbatim in source: {_norm_ws(quote)[:90]!r}")
            )
    stats = {"issues": len(issues), "quotes": len(supporting_quotes(report)), "ungrounded_quotes": ungrounded}
    return violations, stats


# --------------------------------------------------------------------------- #
# Per-file pipeline
# --------------------------------------------------------------------------- #
def evaluate_file(path: Path, cache_dir: Path | None = None) -> FileResult:
    """Full INGEST -> ANALYZE -> VALIDATE cycle for one document (with checkpoint)."""
    started = time.perf_counter()
    digest = file_sha1(path)

    cached = _load_cache(cache_dir, digest)
    if cached is not None:
        return cached

    result = FileResult(file=path.name)
    try:
        text, result.engine, result.pages = ingest_document(path)
        report = build_analysis(text)
        result.category = report.get("category")
        result.trust_score = report.get("trust_score")
        result.coverage, result.status_counts = compute_coverage(report)
        result.parsed = True
        result.violations = validate_report(report, path.stem, path.name)
    except Exception as exc:
        result.parsed = False
        result.error = str(exc)[:300]
        result.violations = [Violation("V01", f"pipeline exception: {exc}")]

    result.duration_ms = int((time.perf_counter() - started) * 1000)
    _write_cache(cache_dir, digest, result)
    return result


def _cache_path(cache_dir: Path | None, digest: str) -> Path | None:
    return cache_dir / f"{digest}.json" if cache_dir else None


def _load_cache(cache_dir: Path | None, digest: str) -> FileResult | None:
    path = _cache_path(cache_dir, digest)
    if not path or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("cache_version") != CACHE_VERSION:
            return None
        return FileResult(**payload["result"])
    except Exception:
        logger.debug(f"ignoring corrupt checkpoint {path.name}")
        return None


def _write_cache(cache_dir: Path | None, digest: str, result: FileResult) -> None:
    path = _cache_path(cache_dir, digest)
    if not path:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"cache_version": CACHE_VERSION, "result": asdict(result)}
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception:
        logger.debug(f"failed writing checkpoint {path.name}")


def _worker(payload: tuple[str, str | None]) -> dict[str, Any]:
    """ProcessPool entry point: evaluate one file and return its serializable form."""
    path_str, cache_str = payload
    cache_dir = Path(cache_str) if cache_str else None
    return asdict(evaluate_file(Path(path_str), cache_dir))


# --------------------------------------------------------------------------- #
# Aggregation, reports, exit policy
# --------------------------------------------------------------------------- #
def aggregate_results(results: list[dict[str, Any]]) -> BatchSummary:
    """Fold per-file results into the batch-level summary."""
    summary = BatchSummary(total=len(results))
    code_counter: Counter[str] = Counter()
    coverages: list[float] = []
    trusts: list[float] = []

    for result in results:
        codes = result["violation_codes"] if "violation_codes" in result else _codes_of(result)
        if result["parsed"]:
            summary.parsed += 1
        else:
            summary.parse_fail += 1
        if result["parsed"] and not codes:
            summary.passed += 1
        if result.get("category"):
            summary.categories[result["category"]] = summary.categories.get(result["category"], 0) + 1
        if isinstance(result.get("coverage"), (int, float)):
            coverages.append(float(result["coverage"]))
        if isinstance(result.get("trust_score"), (int, float)):
            trusts.append(float(result["trust_score"]))
        for violation in result["violations"]:
            code_counter[violation["code"]] += 1
        if codes:
            reasons = "; ".join(f"{v['code']}: {v['message']}" for v in result["violations"][:4])
            summary.failed_files.append({"file": result["file"], "reasons": reasons})

    summary.pass_rate = (summary.passed / summary.parsed) if summary.parsed else 0.0
    summary.avg_coverage = round(sum(coverages) / len(coverages), 4) if coverages else None
    summary.avg_trust = round(sum(trusts) / len(trusts), 2) if trusts else None
    summary.top_violations = code_counter.most_common()
    summary.hard_violations = {c: n for c, n in code_counter.items() if c in HARD_CODES}
    summary.llm_checked = sum(1 for r in results if r.get("llm_checked"))
    summary.failed_files.sort(key=lambda f: f["file"])
    return summary


def _codes_of(result: dict[str, Any]) -> list[str]:
    return [v["code"] for v in result["violations"]]


def exit_code_for(summary: BatchSummary) -> int:
    """0 iff pass_rate >= threshold and zero hard (V02/V03/V08) violations."""
    if summary.pass_rate < PASS_RATE_THRESHOLD:
        return 1
    if summary.hard_violations:
        return 1
    return 0


def write_reports(
    results: list[dict[str, Any]], summary: BatchSummary, out_dir: Path, ts: str
) -> tuple[Path, Path]:
    """Persist eval_<ts>.json (full detail) and eval_<ts>.csv (one row/file)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"eval_{ts}.json"
    csv_path = out_dir / f"eval_{ts}.csv"

    json_path.write_text(
        json.dumps({"summary": asdict(summary), "files": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["name", "category", "trust", "coverage", "violations"])
        for result in results:
            joined = "; ".join(f"{v['code']}: {v['message']}" for v in result["violations"])
            writer.writerow(
                [
                    result["file"],
                    result.get("category") or "",
                    result.get("trust_score") if result.get("trust_score") is not None else "",
                    result.get("coverage") if result.get("coverage") is not None else "",
                    joined,
                ]
            )
    return json_path, csv_path


def print_summary(summary: BatchSummary, json_path: Path, csv_path: Path) -> None:
    """Render the human-readable console summary table (the only stdout)."""
    bar = "=" * 86
    print(bar)
    print(" BATCH EVALUATION SUMMARY")
    print(bar)
    print(
        f" files={summary.total}  parsed={summary.parsed}  parse_fail={summary.parse_fail}"
        f"  passed={summary.passed}  pass_rate={summary.pass_rate:.1%}  "
        f"(threshold {PASS_RATE_THRESHOLD:.0%})"
    )
    cats = ", ".join(f"{k}={v}" for k, v in sorted(summary.categories.items())) or "-"
    print(f" categories : {cats}")
    cov = f"{summary.avg_coverage:.3f}" if summary.avg_coverage is not None else "-"
    trst = f"{summary.avg_trust:.1f}" if summary.avg_trust is not None else "-"
    print(f" avg coverage={cov}  avg trust={trst}  llm_spot_checked={summary.llm_checked}")
    top = ", ".join(f"{c}x{n}" for c, n in summary.top_violations[:10]) or "none"
    print(f" violations : {top}")
    hard = ", ".join(f"{c}={n}" for c, n in summary.hard_violations.items()) or "none"
    print(f" hard(V02/V03/V08): {hard}")
    if summary.failed_files:
        print(f" failed files ({len(summary.failed_files)}):")
        for failure in summary.failed_files[:15]:
            print(f"   - {failure['file']}: {failure['reasons'][:150]}")
        if len(summary.failed_files) > 15:
            print(f"   ... and {len(summary.failed_files) - 15} more (see CSV/JSON)")
    print(f" reports    : {json_path}")
    print(f"              {csv_path}")
    verdict = "PASS" if exit_code_for(summary) == 0 else "FAIL"
    print(f" RESULT     : {verdict}")
    print(bar)


# --------------------------------------------------------------------------- #
# LLM stratified sampling driver
# --------------------------------------------------------------------------- #
def run_llm_spot_checks(results: list[dict[str, Any]], sample_per_category: int) -> None:
    """Re-run sampled docs per category through presentation layer with L03 checks.

    Mutates ``results`` in place, attaching L-code violations to the sampled
    files so they flow into aggregation and the written reports.
    """
    by_category: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        if result["parsed"]:
            by_category.setdefault(result.get("category") or "other", []).append(result)

    picked: list[tuple[dict[str, Any], Path]] = []
    for category in sorted(by_category):
        for result in sorted(by_category[category], key=lambda r: r["file"])[:sample_per_category]:
            picked.append((result, Path(result["_path"])))

    logger.info(f"LLM spot-check: {len(picked)} documents selected (stratified)")
    for result, path in picked:
        try:
            text, _, _ = ingest_document(path)
            report = build_analysis(text)
            violations, stats = llm_extra_violations(text, report)
            result["llm_checked"] = True
            result["llm_stats"] = stats
            existing_codes = {v["code"] for v in result["violations"]}
            result["violations"].extend(
                asdict(v) for v in violations if v.code not in existing_codes
            )
        except Exception as exc:
            result["llm_checked"] = True
            result["violations"].append(asdict(Violation("L00", f"llm spot-check failed: {exc}")))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """CLI definition for the batch evaluator."""
    parser = argparse.ArgumentParser(
        prog="python -m scripts.batch_eval",
        description="Batch-validate LexOrch-KG analysis over a corpus of legal documents.",
    )
    parser.add_argument("--dir", default="./test_data", help="corpus directory to scan")
    parser.add_argument("--out", default="./reports", help="directory for JSON/CSV reports")
    parser.add_argument("--workers", type=int, default=8, help="parallel worker processes")
    parser.add_argument(
        "--with-llm", action="store_true", help="run stratified LLM-layer spot checks"
    )
    parser.add_argument(
        "--sample", type=int, default=5, help="docs per category for --with-llm sampling"
    )
    return parser.parse_args(argv)


def discover_files(root: Path) -> list[Path]:
    """Recursively collect supported documents under ``root`` (sorted)."""
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES)


def main(argv: list[str] | None = None) -> int:
    """Entry point: orchestrate discovery, parallel evaluation, reporting."""
    args = parse_args(argv)
    root = Path(args.dir).resolve()
    out_dir = Path(args.out).resolve()
    cache_dir = Path(os.environ.get("EVAL_CACHE_DIR", ".cache/eval"))

    files = discover_files(root)
    if not files:
        logger.error(f"no supported documents found under {root}")
        return 2
    logger.info(f"discovered {len(files)} documents under {root}")

    payloads: list[tuple[str, str | None]] = []
    cached_results: list[dict[str, Any]] = []
    for path in files:
        cached = _load_cache(cache_dir, file_sha1(path))
        if cached is not None:
            cached_results.append(_attach_path(asdict(cached), path))
        else:
            payloads.append((str(path), str(cache_dir)))

    computed: list[dict[str, Any]] = []
    progress = tqdm(total=len(files), desc="batch-eval", unit="doc") if tqdm else None
    try:
        if payloads:
            with ProcessPoolExecutor(max_workers=max(1, args.workers)) as pool:
                futures = [pool.submit(_worker, payload) for payload in payloads]
                for future in as_completed(futures):
                    result = future.result()
                    computed.append(_attach_path(result, Path(result["file"])))
                    if progress:
                        progress.update(1)
                    elif int(len(computed) % 25) == 0:
                        logger.info(f"progress {len(computed)}/{len(payloads)}")
        if progress:
            progress.close()
    finally:
        if progress and not progress.disable:
            progress.close()

    results = sorted(cached_results + computed, key=lambda r: r["file"])

    if args.with_llm:
        run_llm_spot_checks(results, max(1, args.sample))

    summary = aggregate_results(results)
    ts = time.strftime("%Y%m%d-%H%M%S")
    json_path, csv_path = write_reports(results, summary, out_dir, ts)
    print_summary(summary, json_path, csv_path)
    return exit_code_for(summary)


def _attach_path(result: dict[str, Any], path: Path) -> dict[str, Any]:
    """Keep the absolute source path inside the dict for LLM resampling."""
    result["_path"] = str(path)
    return result


if __name__ == "__main__":
    import os

    sys.exit(main())
