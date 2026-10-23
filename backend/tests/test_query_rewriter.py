"""Tests for query-rewrite fast paths."""

from __future__ import annotations

from app.rag.query_rewriter import QueryRewriter


def test_long_query_skips_llm_rewrite(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise AssertionError("LLM must not be called for a self-sufficient query")

    monkeypatch.setattr("app.llm.routing.get_fast_provider", _boom)

    query = (
        "Whether the proceedings against the petitioner in C.C.No.224 of 2017 "
        "can be quashed under Section 482 of the Code of Criminal Procedure, "
        "1973, and whether their continuation amounts to an abuse of process?"
    )
    out = QueryRewriter().rewrite(query, intent="section_lookup")

    assert query in out
    assert len(out) >= 2


def test_statute_rich_query_is_self_sufficient():
    rewriter = QueryRewriter()
    statute = (
        "quashing petition under Section 482 of the Code of Criminal "
        "Procedure 1973 for abuse of process and want of jurisdiction"
    )
    assert rewriter._is_self_sufficient(statute) is True
    assert rewriter._is_self_sufficient("bail plea") is False


def test_short_query_uses_llm_rewrite(monkeypatch):
    class _Provider:
        def generate(self, _prompt, **_kwargs):
            return "expanded bail terms\nbail under section 439"

    monkeypatch.setattr("app.llm.routing.get_fast_provider", lambda: _Provider())

    out = QueryRewriter().rewrite("bail plea", intent=None)

    assert "expanded bail terms" in out
