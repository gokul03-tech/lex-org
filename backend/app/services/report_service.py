"""Legal advisory report generation service.

Assembles the 16-section report from all agent outputs,
generates PDF via WeasyPrint, and manages report storage.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import settings


class ReportGenerator:
    """Assemble and generate legal advisory reports.

    Combines outputs from all 12 agents into a structured
    16-section report with explainability graphs.
    """

    REPORT_SECTIONS = [
        (1, "Executive Summary"),
        (2, "Case Facts"),
        (3, "Legal Issues Identified"),
        (4, "Applicable Acts"),
        (5, "Applicable Sections"),
        (6, "Supporting Judgments"),
        (7, "Evidence Analysis"),
        (8, "Contradiction Analysis"),
        (9, "Risk Assessment"),
        (10, "Procedural Compliance"),
        (11, "Strategy Recommendation"),
        (12, "Trust Score"),
        (13, "Confidence Scores"),
        (14, "Explainability Graph"),
        (15, "Knowledge Graph Snapshot"),
        (16, "References & Human Review Note"),
    ]

    def __init__(self) -> None:
        self.output_dir = Path("outputs/reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def assemble_report(
        self,
        agent_state: dict[str, Any],
        case_id: str = "",
        case_title: str = "",
    ) -> dict[str, Any]:
        """Assemble the 16-section report from agent outputs.

        Args:
            agent_state: The final AgentState from the analysis pipeline.
            case_id: The database case ID.
            case_title: The case title.

        Returns:
            Complete report dict with all sections.
        """
        report = {
            "meta": {
                "case_id": case_id,
                "case_title": case_title,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "version": settings.APP_VERSION,
                "llm_backend": settings.LLM_BACKEND,
            },
            "sections": [],
        }

        sections_data = {
            "Executive Summary": self._section_1_executive_summary(agent_state),
            "Case Facts": self._section_2_case_facts(agent_state),
            "Legal Issues Identified": self._section_3_legal_issues(agent_state),
            "Applicable Acts": self._section_4_applicable_acts(agent_state),
            "Applicable Sections": self._section_5_applicable_sections(agent_state),
            "Supporting Judgments": self._section_6_judgments(agent_state),
            "Evidence Analysis": self._section_7_evidence(agent_state),
            "Contradiction Analysis": self._section_8_contradictions(agent_state),
            "Risk Assessment": self._section_9_risk(agent_state),
            "Procedural Compliance": self._section_10_procedure(agent_state),
            "Strategy Recommendation": self._section_11_strategy(agent_state),
            "Trust Score": self._section_12_trust(agent_state),
            "Confidence Scores": self._section_13_confidence(agent_state),
            "Explainability Graph": self._section_14_explainability(agent_state),
            "Knowledge Graph Snapshot": self._section_15_kg(agent_state),
            "References & Human Review Note": self._section_16_references(agent_state),
        }

        for order, title in self.REPORT_SECTIONS:
            report["sections"].append({
                "order": order,
                "title": title,
                "content": sections_data.get(title, {}),
            })

        return report

    def _section_1_executive_summary(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "summary": state.get("case_summary", "No summary available"),
            "trust_score": state.get("trust_score", 0.0),
            "key_findings": state.get("legal_issues", [])[:5],
        }

    def _section_2_case_facts(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "summary": state.get("case_summary", ""),
            "facts": state.get("case_facts", {}),
            "timeline": state.get("timeline", []),
            "entities": state.get("entities", {}),
        }

    def _section_3_legal_issues(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "issues": state.get("legal_issues", []),
        }

    def _section_4_applicable_acts(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "acts": state.get("applicable_acts", []),
        }

    def _section_5_applicable_sections(self, state: dict[str, Any]) -> dict[str, Any]:
        sections = state.get("applicable_sections", [])
        return {
            "sections": [
                {
                    "section_number": s.get("section_number", ""),
                    "act": s.get("act", ""),
                    "title": s.get("title", ""),
                    "text_excerpt": s.get("text", "")[:300],
                    "relevance": s.get("relevance_score", 0.0),
                }
                for s in sections[:15]
            ],
        }

    def _section_6_judgments(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "precedents": state.get("precedents", [])[:10],
        }

    def _section_7_evidence(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "assessment": state.get("evidence_assessment", {}),
        }

    def _section_8_contradictions(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "contradictions": state.get("contradictions", []),
        }

    def _section_9_risk(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "assessment": state.get("risk_assessment", {}),
        }

    def _section_10_procedure(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": state.get("procedural_status", {}),
        }

    def _section_11_strategy(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "options": state.get("strategy_options", []),
            "reasoning": state.get("legal_reasoning", ""),
            "irac": state.get("irac_analysis", {}),
        }

    def _section_12_trust(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "trust_score": state.get("trust_score", 0.0),
            "interpretation": self._interpret_trust(state.get("trust_score", 0.0)),
        }

    def _section_13_confidence(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "per_agent": state.get("agent_confidence", {}),
        }

    def _section_14_explainability(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "graph": state.get("explanation_graph", {}),
        }

    def _section_15_kg(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "graph_data": state.get("kg_data", {}),
        }

    def _section_16_references(self, state: dict[str, Any]) -> dict[str, Any]:
        sections = state.get("applicable_sections", [])
        return {
            "section_references": [
                f"Section {s.get('section_number')} of {s.get('act')}"
                for s in sections[:10]
            ],
            "disclaimer": (
                "IMPORTANT DISCLAIMER: This report is an AI-assisted advisory output "
                "generated by LexOrch-KG for research and reference purposes only. "
                "It does NOT constitute legal advice. The analysis and recommendations "
                "should be reviewed by a qualified legal professional before use in "
                "any legal proceedings. The confidence scores and trust metrics are "
                "automated estimates and should not be solely relied upon."
            ),
            "generation_note": (
                f"Generated on {datetime.now(timezone.utc).strftime('%B %d, %Y')} "
                f"using LexOrch-KG v{settings.APP_VERSION} "
                f"(LLM backend: {settings.LLM_BACKEND})."
            ),
        }

    @staticmethod
    def _interpret_trust(score: float) -> str:
        """Provide human-readable interpretation of trust score."""
        if score >= 0.8:
            return "HIGH: Multiple agents agree with high confidence. Recommendations are reliable."
        elif score >= 0.6:
            return "MODERATE: Reasonable agreement among agents. Review key findings before relying."
        elif score >= 0.4:
            return "LOW: Significant disagreement or low confidence. Further analysis recommended."
        else:
            return "VERY LOW: Insufficient or conflicting information. Do not rely without expert review."

    def generate_pdf(self, report: dict[str, Any], output_path: str | None = None) -> str:
        """Generate a PDF version of the report.

        Args:
            report: The assembled report dict.
            output_path: Optional output file path.

        Returns:
            Path to the generated PDF.
        """
        if output_path is None:
            case_id = report.get("meta", {}).get("case_id", "unknown")
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_path = str(self.output_dir / f"report_{case_id}_{timestamp}.pdf")

        try:
            html = self._render_html(report)
            self._write_pdf(html, output_path)
            logger.info(f"PDF report generated: {output_path}")
            return output_path
        except ImportError:
            logger.warning("WeasyPrint not installed. Saving as HTML instead.")
            html_path = output_path.replace(".pdf", ".html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self._render_html(report))
            return html_path
        except Exception as exc:
            logger.error(f"PDF generation failed: {exc}")
            # Save as JSON fallback
            json_path = output_path.replace(".pdf", ".json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
            return json_path

    def _render_html(self, report: dict[str, Any]) -> str:
        """Render report as HTML."""
        sections_html = ""
        for section in report.get("sections", []):
            title = section.get("title", "")
            content = section.get("content", {})

            if isinstance(content, dict):
                content_str = json.dumps(content, indent=2, default=str)
            else:
                content_str = str(content)

            sections_html += f"""
            <div class="section">
                <h2>{title}</h2>
                <pre>{content_str}</pre>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LexOrch-KG Legal Advisory Report</title>
    <style>
        body {{ font-family: 'Georgia', serif; max-width: 800px; margin: 40px auto; padding: 20px; color: #1a1a1a; }}
        h1 {{ color: #1B2A4A; border-bottom: 2px solid #C9A84C; padding-bottom: 10px; }}
        h2 {{ color: #2563EB; margin-top: 30px; }}
        .section {{ margin-bottom: 30px; page-break-inside: avoid; }}
        pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; white-space: pre-wrap; font-size: 13px; line-height: 1.5; }}
        .meta {{ color: #666; font-size: 12px; margin-bottom: 30px; }}
        .disclaimer {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin-top: 40px; }}
    </style>
</head>
<body>
    <h1>LexOrch-KG Legal Advisory Report</h1>
    <div class="meta">
        <p>Case ID: {report.get('meta', {}).get('case_id', 'N/A')}</p>
        <p>Generated: {report.get('meta', {}).get('generated_at', 'N/A')}</p>
    </div>
    {sections_html}
    <div class="disclaimer">
        <strong>IMPORTANT:</strong> This is an AI-assisted legal analysis report. 
        It does not constitute legal advice. Please consult a qualified legal professional.
    </div>
</body>
</html>"""

    @staticmethod
    def _write_pdf(html: str, output_path: str) -> None:
        """Write HTML to PDF using WeasyPrint."""
        from weasyprint import HTML
        HTML(string=html).write_pdf(output_path)

    def save_report_json(self, report: dict[str, Any], output_path: str | None = None) -> str:
        """Save report as JSON file.

        Args:
            report: The assembled report.
            output_path: Optional output path.

        Returns:
            Path to the saved file.
        """
        if output_path is None:
            case_id = report.get("meta", {}).get("case_id", "unknown")
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            output_path = str(self.output_dir / f"report_{case_id}_{timestamp}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Report JSON saved: {output_path}")
        return output_path
