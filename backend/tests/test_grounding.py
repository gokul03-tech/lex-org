"""LexOrch-KG Universal Grounding Regression Test Suite.
Verifies all 8 Universal Rules across all 5 known judgment domains.
"""
import pytest
from app.agents.universal_grounding import analyze, gate, map_section_to_act, bind_sections
from app.agents.analysis_fixes_v2 import extract_submissions, extract_evidence_items, build_risk_strategy

# ── Sample Judgments Corpus ──
MAKWANA_TEXT = """Ramji Duda Makwana vs The State Of Maharashtra on 12 August, 1993
(1994) 96 BOMLR 808, 1994 Cri LJ 1987
Bench: Saldanha, J. and S.P. Kurdukar, J.
JUDGMENT
Saldanha, J.
1. Special Case No. 280 of 1991. The accused was charged under Section 8(c) read with Section 21 of the NDPS Act, 1985.
2. The panchanama was drawn under Section 114(e) of the Indian Evidence Act, 1872.
3. reported in 1991 Cri LJ 232 in the case of Usman Haidarkhan Shaikh v. State of Maharashtra.
4. On 6-1-1991 the raid occurred. On 8-1-1991 sample reached C.A.
5. Appeal dismissed.
S.P. Kurdukar, J. - I agree."""

SETTY_TEXT = """V.K. Srinivasa Setty vs Premier Life And General Insurance Co. on 9 October, 1957
AIR 1958 KANT 53, AIR 1958 MYS 53
Bench: Somnath Iyer, J. and Sadasivayya, J.
JUDGMENT
Somnath Iyer, J.
1. Regular Appeal No. 12 of 1950. The plaintiff filed a suit on the policy of insurance.
2. The contract of insurance is governed by the Insurance Act, 1938.
3. Decree for plaintiff.
Sadasivayya, J. - I agree."""

VIKRAM_TEXT = """IN THE HIGH COURT OF JUDICATURE AT BOMBAY
Vikram Dev vs The State Of Maharashtra ... on 14 March, 2024
(2024) 2 Bom CR 412, 2024 Cri LJ 1580
Bench: Revati Mohite Dere, J. and Gauri Godse, J.
JUDGMENT
Revati Mohite Dere, J.
1. The applicant has approached under Section 482 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023 for bail in C.R. No. 102 of 2024.
2. Charges under Section 111 of the Bharatiya Nyaya Sanhita (BNS), 2023 and Section 66D of the Information Technology Act, 2000.
3. Electronic evidence lacks certificate under Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023.
4. reported in (2011) 1 SCC 694 in the case of Sanjay Chandra v. Central Bureau of Investigation.
5. On 15-01-2024 incident occurred. On 05-03-2024 charge sheet filed.
6. Bail application is allowed on P.R. Bond of Rs. 50,000/-.
Gauri Godse, J. - I agree."""

APEX_TEXT = """IN THE HIGH COURT OF DELHI AT NEW DELHI
Apex Infrastructure Pvt. Ltd. vs National Highways Authority of India ... on 18 January, 2023
AIR 2023 DEL 145, (2023) 1 DLT 89
Bench: Prathiba M. Singh, J.
JUDGMENT
Prathiba M. Singh, J.
1. Petition under Section 34 of the Arbitration and Conciliation Act, 1996 challenging the Arbitral Award.
2. Breach of contract under Section 73 of the Indian Contract Act, 1872.
3. reported in (2015) 3 SCC 49 in the case of Associate Builders v. Delhi Development Authority.
4. Petition is partly allowed."""

ANANYA_TEXT = """IN THE SUPREME COURT OF INDIA
Dr. Ananya Sharma vs Union Of India & Ors. ... on 5 May, 2023
[2023] 4 SCR 710, (2023) 6 SCC 301
Bench: D.Y. Chandrachud, CJI and P.S. Narasimha, J.
JUDGMENT
D.Y. Chandrachud, CJI
1. Writ petition under Article 32 of the Constitution of India for violation of Article 21 and Article 19(1)(a).
2. reported in (2017) 10 SCC 1 in the case of Justice K.S. Puttaswamy v. Union of India.
3. Writ petition is disposed of.
P.S. Narasimha, J. - I agree."""


def test_universal_grounding_makwana():
    report, binds, precs, timeline = analyze(MAKWANA_TEXT)
    assert report['petitioner']['value'] == 'Ramji Duda Makwana'
    assert report['decision_date']['value'] == '12 August 1993'
    assert report['court']['value'] == 'Bombay High Court'
    assert 'Special Case No. 280 of 1991' in (report['court_matter']['value'] or '')
    assert any('Usman Haidarkhan' in p['case_name'] for p in precs)


def test_universal_grounding_setty():
    report, binds, precs, timeline = analyze(SETTY_TEXT)
    assert report['petitioner']['value'] == 'V.K. Srinivasa Setty'
    assert report['respondent']['value'] == 'Premier Life And General Insurance Co.'
    assert report['decision_date']['value'] == '9 October 1957'
    assert report['court']['value'] == 'High Court of Mysore (Karnataka)'


def test_universal_grounding_vikram():
    report, binds, precs, timeline = analyze(VIKRAM_TEXT)
    assert report['petitioner']['value'] == 'Vikram Dev'
    assert report['respondent']['value'] == 'The State Of Maharashtra'
    assert report['court']['value'] == 'Bombay High Court'
    assert report['court_matter']['value'] == 'C.R. No. 102 of 2024'
    assert '(2024) 2 Bom CR 412' in report['citation_numbers']['value']

    # Test Section bindings. VIKRAM_TEXT line 1 cites "Section 482 of the
    # Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023" verbatim, so the in-text
    # binding wins regardless of the document's pre-July-2024 date: this is the
    # new-law CONCORDANCE mapping check (binding beats the era default).
    assert map_section_to_act('482', binds, 'criminal') == 'Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023'
    assert map_section_to_act('111', binds, 'criminal') == 'Bharatiya Nyaya Sanhita (BNS), 2023'
    assert map_section_to_act('66D', binds, 'criminal') == 'Information Technology Act, 2000'
    assert map_section_to_act('63', binds, 'criminal') == 'Bharatiya Sakshya Adhiniyam (BSA), 2023'

    # Era rule (decision-date aware): a pre-1-July-2024 document with an UNBOUND
    # bare "Section 482" (Karnataka, 22 May 2023) must resolve to the CrPC, 1973
    # rather than an anachronistic BNSS attribution; a post-commencement date
    # keeps the BNSS default.
    assert map_section_to_act('482', {}, 'criminal', decision_date='22 May 2023') == 'Code of Criminal Procedure, 1973'
    assert map_section_to_act('483', {}, 'criminal', decision_date='22 May 2023') == 'Code of Criminal Procedure, 1973'
    assert map_section_to_act('482', {}, 'criminal', decision_date='15 August 2024') == 'Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023'
    # New-law concordance additions from STATUTE_MAP: bare "67" is IT Act, and
    # an unbound "29A"/"7" is IBC (no date dependency).
    assert map_section_to_act('67', {}, 'criminal') == 'Information Technology Act, 2000'
    assert map_section_to_act('29A', {}, 'civil') == 'Insolvency and Bankruptcy Code, 2016'
    assert map_section_to_act('7', {}, 'civil') == 'Insolvency and Bankruptcy Code, 2016'
    # FIX 4 canonical STATUTE_MAP entries: bare "100" is CrPC and bare "105" is
    # BNSS, so neither ever surfaces as the "Statute (verify)" placeholder.
    assert map_section_to_act('100', {}, 'criminal') == 'Code of Criminal Procedure, 1973'
    assert map_section_to_act('105', {}, 'criminal') == 'Bharatiya Nagarik Suraksha Sanhita, 2023'
    # FIX 5 year-drift guard: a wrong enactment year is normalized to the real
    # one by the statute post-processor, never passed through to the report.
    assert map_section_to_act('100', {'100': 'Companies Act, 2015'}, 'criminal') == 'Companies Act, 2013'
    assert map_section_to_act('105', {'105': 'Companies Act, 2014'}, 'criminal') == 'Companies Act, 2013'

    # Test dynamic evidence & risk
    ev_items = extract_evidence_items(VIKRAM_TEXT)
    assert not any('contraband' in str(it).lower() for it in ev_items)
    risk = build_risk_strategy(VIKRAM_TEXT, report)
    # The document states "Bail application is allowed." Asserting a paraphrase
    # ("allowed" without "is") tested the wording of the test, not the code.
    assert 'Bail application is allowed' in risk['conclusion']


def test_sanhita_context_blocks_ndps_default():
    """A bare "52g"/"52" in a BNSS/BNS/BSA judgment must not be hijacked by the
    NDPS numeric default when the text never names the NDPS Act."""
    # No document context: the legacy NDPS default is unchanged.
    assert map_section_to_act('52g', {}, 'criminal') == 'NDPS Act, 1985'
    # Plain BNSS document with no NDPS mention: the default is suppressed, so an
    # unbound OCR-mangled provision is left as the honest "Statute (verify)"
    # placeholder rather than a fabricated NDPS attribution.
    assert map_section_to_act('52g', {}, 'criminal', doc_text=VIKRAM_TEXT) == 'Statute (verify)'
    assert map_section_to_act('2', {}, 'criminal', doc_text=VIKRAM_TEXT) == 'Statute (verify)'
    # An explicit in-text binding still wins over the guard.
    assert map_section_to_act(
        '52g', {'52g': 'Bharatiya Nagarik Suraksha Sanhita, 2023'}, 'criminal',
        doc_text=VIKRAM_TEXT,
    ) == 'Bharatiya Nagarik Suraksha Sanhita, 2023'
    # A document that names the NDPS Act keeps the NDPS default.
    assert map_section_to_act('52g', {}, 'criminal', doc_text=MAKWANA_TEXT) == 'NDPS Act, 1985'


def test_universal_grounding_apex():
    report, binds, precs, timeline = analyze(APEX_TEXT)
    assert report['petitioner']['value'] == 'Apex Infrastructure Pvt. Ltd.'
    assert report['respondent']['value'] == 'National Highways Authority of India'
    assert report['court']['value'] == 'Delhi High Court'
    assert map_section_to_act('34', binds, 'civil') == 'Arbitration and Conciliation Act, 1996'
    assert map_section_to_act('73', binds, 'civil') == 'Indian Contract Act, 1872'


def test_universal_grounding_ananya():
    report, binds, precs, timeline = analyze(ANANYA_TEXT)
    assert report['petitioner']['value'] == 'Dr. Ananya Sharma'
    assert report['respondent']['value'] == 'Union Of India & Ors.'
    assert report['court']['value'] == 'Supreme Court of India'
    assert 'D.Y. Chandrachud' in report['presiding_judges']['value']
    assert 'P.S. Narasimha' in report['presiding_judges']['value']


def test_verification_gate_demotes_hallucinations():
    fake_report = {
        'petitioner': {'value': 'Nonexistent Person Fabricated By Model', 'status': 'extracted'},
        'court': {'value': 'Supreme Court of India', 'status': 'extracted'}
    }
    gated = gate(fake_report, ANANYA_TEXT)
    # The nonexistent person should be demoted to not_found
    assert gated['petitioner']['status'] == 'not_found'
    assert gated['petitioner']['value'] is None
    # Real court present in text stays extracted
    assert gated['court']['status'] == 'extracted'


def test_presentation_universal_layer():
    from app.agents.presentation_universal import render_issues, render_conclusion, render_chips, build_kg, lint

    # 1. Vikram Context
    report, binds, precs, timeline = analyze(VIKRAM_TEXT)
    r_ctx = {
        'metadata': report,
        'sections': ['482', '111', '66D', '63'],
        'section_acts': binds,
        'articles': [],
        'precedents': precs,
        'category': 'criminal'
    }

    # render_issues reads only what the document states. Neither this judgment
    # nor VIKRAM_TEXT frames "Issue I:"-style issues, so passing no text
    # correctly yields none. The positive branch is covered below.
    assert render_issues(r_ctx) == []
    assert render_issues(r_ctx, VIKRAM_TEXT) == []

    framed = VIKRAM_TEXT + (
        "\n\nIssue I: Whether the learned APP has conduct fair proceedings in "
        "this case.\n\nIssue II: Whether the applicant has established his innocence.\n"
    )
    issues = render_issues(r_ctx, framed)
    assert any("Issue I" in iss for iss in issues)
    assert any("Issue II" in iss for iss in issues)

    conclusion = render_conclusion(r_ctx, VIKRAM_TEXT)
    assert 'Bail application is allowed' in conclusion

    chips = render_chips(r_ctx)
    assert 'Explain Section 482.' in chips

    kg = build_kg(r_ctx)
    assert len(kg['nodes']) >= 5
    assert len(kg['edges']) >= 4
    assert any(n['label'] == 'Vikram Dev' for n in kg['nodes'])

    # 2. Lint test (raises on banned strings, passes on clean strings)
    lint(conclusion, chips, kg)
    with pytest.raises(ValueError):
        lint("This is a Mock summary response with Not found in document")


def test_analogy_mention_is_not_an_applicable_section():
    """A provision cited only "by analogy" must be filtered out, while a
    genuinely applied provision in the same document survives."""
    from app.agents.analysis_fixes_v2 import (
        filter_contextual_sections,
        section_mention_is_contextual,
    )

    text = (
        "The petitioner relies on Section 482 BNSS for the relief sought. "
        "Learned counsel, by analogy, referred to Section 50 of the NDPS Act, 1985."
    )
    assert section_mention_is_contextual(text, "50") is True
    assert section_mention_is_contextual(text, "482") is False
    kept = filter_contextual_sections(
        [{"section_number": "50"}, {"section_number": "482"}], text
    )
    assert [s["section_number"] for s in kept] == ["482"]


def test_strategy_and_gaps_prompts_guard_source():
    """Fix 2 / Fix 3: strategy must forbid mining the judicial disposition, and
    gaps must be sourced from the opposing side's submissions."""
    from app.agents.analysis import POTENTIAL_GAPS_PROMPT, STRATEGY_PROMPT

    assert "OPERATIVE ORDER" in STRATEGY_PROMPT
    assert "The appeal is allowed" in STRATEGY_PROMPT

    assert "RESPONDENT'S SUBMISSIONS" in POTENTIAL_GAPS_PROMPT
    assert "PER CONTRA" in POTENTIAL_GAPS_PROMPT
    assert "flight risk" in POTENTIAL_GAPS_PROMPT.lower()

    # The counter/opposing-counsel field must be respondent-side only.
    assert "Per contra" in STRATEGY_PROMPT
    assert "Additional Public Prosecutor" in STRATEGY_PROMPT
    assert "petitioner's own arguments" in STRATEGY_PROMPT


def test_section_number_is_not_captured_as_constitutional_article():
    """A "Section N" must not be recast as a coincidental constitutional
    Article N; an explicit "Article N" still resolves to the Constitution."""
    bnss = (
        "The applicant seeks quashing of the FIR under Section 35 of the "
        "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023."
    )
    assert map_section_to_act("35", {}, "criminal", doc_text=bnss) != "Constitution of India"

    writ = "The petitioner invokes Article 21 and Article 32 of the Constitution of India."
    assert map_section_to_act("21", {}, "criminal", doc_text=writ) == "Constitution of India"


def test_ocr_section_token_is_repaired_only_in_context():
    """An OCR-misread section token is repaired when it actually occurs in the
    document text; an isolated probe is never silently fabricated."""
    doc = (
        "Quashing of the FIR under Section 52g of the Bharatiya Nagarik "
        "Suraksha Sanhita (BNSS), 2023."
    )
    assert (
        map_section_to_act("52g", {}, "criminal", doc_text=doc)
        == "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023"
    )

    # Same BNSS context but the token is absent from the text: keep the honest
    # placeholder rather than inventing Section 528.
    absent = "The applicant seeks bail under the Bharatiya Nagarik Suraksha Sanhita, 2023."
    assert map_section_to_act("52g", {}, "criminal", doc_text=absent) == "Statute (verify)"




def test_stated_question_is_surfaced_when_no_issues_framed():
    """A document that states the question for determination as a plain
    "Whether ...?" sentence, with no "ISSUES FRAMED" heading, still has its
    issues surfaced - the sentence is the document's own words, not invented."""
    from app.agents.presentation_universal import _court_framed_issues

    text = (
        "IN THE HIGH COURT OF JUDICATURE AT BOMBAY\n"
        "The applicant seeks quashing of the FIR and proceedings. "
        "Whether the allegations, taken at face value, disclose a cognizable "
        "offence, or are they civil in nature?"
    )
    issues = [i["text"] for i in _court_framed_issues(text)]
    assert any("civil in nature" in s for s in issues)


def test_no_issue_is_invented_without_a_question_or_prayer():
    """A judgment that frames no issue and states no prayer must keep an empty
    issue list - inference never manufactures one from a bare section mention."""
    from app.agents.presentation_universal import _court_framed_issues

    assert _court_framed_issues(VIKRAM_TEXT) == []


def test_relief_clause_yields_inferred_issue():
    """An explicit prayer clause is sufficient to infer the relief-based issue."""
    from app.agents.presentation_universal import _court_framed_issues

    text = (
        "IN THE HIGH COURT\nThe petitioner humbly prays that the impugned order "
        "be set aside and that bail be granted."
    )
    issues = _court_framed_issues(text)
    assert issues and issues[0]["source"] == "inferred"


def test_bare_act_abbreviation_binds_section_to_correct_act():
    """A section followed by a bare abbreviation ("of BNSS", "under IPC") binds
    to that Act; the long-title path is unaffected."""
    from app.agents.analysis_fixes_v2 import (
        extract_section_act_bindings,
        map_section_to_act,
    )

    bnss = "Notice under Section 35(3) of BNSS was served on the petitioners."
    binds = extract_section_act_bindings(bnss)
    assert map_section_to_act("35(3)", bnss and binds, "criminal", doc_text=bnss) == (
        "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023"
    )

    ipc = "Charges were framed under Sections 469 and 509 of the IPC."
    binds2 = extract_section_act_bindings(ipc)
    assert binds2.get("469") == "Indian Penal Code, 1860"
    assert binds2.get("509") == "Indian Penal Code, 1860"


def test_action_plan_prefers_specific_direction_over_bail_bond():
    """The action plan keeps an operative direction with an authority/period and
    does not reduce to a boilerplate bond clause when a specific one exists."""
    from app.agents.analysis_fixes_v2 import _extract_procedural_directions

    text = (
        "The petition is allowed. The petitioners are directed to furnish a "
        "personal bond of Rs. 50,000/- with two sureties. "
        "The Registry is directed to list the matter before the appropriate "
        "bench within four weeks."
    )
    plan = _extract_procedural_directions(text)
    # The specific, time-bound Registry direction is ranked ahead of the bare
    # bond clause.
    assert plan.split(";")[0].strip() and "four weeks" in plan.split(";")[0]


def test_per_contra_introduces_the_respondent_side():
    """Standalone "Per contra" (no named State counsel in the same sentence) is
    the standard lead-in for the opposing side's argument and must populate the
    respondent column rather than being dropped."""
    from app.agents.presentation_universal import extract_submissions

    text = (
        "IN THE HIGH COURT\n"
        "The petitioner submitted that the FIR is an abuse of process. "
        "Per contra, the allegations disclose a cognizable offence and the "
        "investigation must continue. "
        "The State further contended that the petitioner is a flight risk."
    )
    a, b = extract_submissions(text)
    assert a
    assert b and any("cognizable" in s or "flight risk" in s for s in b)


def test_administrative_questions_are_not_legal_issues():
    """Supreme Court reporting formalities ("Whether Reporters of Local Papers
    may be allowed...") must never surface as legal issues, while a substantively
    framed question is kept."""
    from app.agents.presentation_universal import _court_framed_issues
    from app.agents.agentic_pipeline import clean_issues_deterministic

    text = (
        "IN THE SUPREME COURT OF INDIA\n"
        "Whether Reporters of Local Papers may be allowed to see the judgment? "
        "Whether the judgment should be reported in the Digest? "
        "Whether leave to appeal granted? "
        "Whether the appellant has made out a case for quashing the FIR?"
    )
    issues = [i["text"] for i in _court_framed_issues(text)]
    assert issues == ["Whether the appellant has made out a case for quashing the FIR?"]

    cleaned = clean_issues_deterministic([
        "Whether Reporters of Local Papers may be allowed to see the judgment?",
        "Whether the appellant has made out a case for quashing the FIR?",
    ])
    assert cleaned == ["Whether the appellant has made out a case for quashing the FIR?"]


def test_section_headings_do_not_crash_submission_extraction():
    """Regression: the section-anchor branch called _switch before its
    definition, so any document with a heading like "STATE'S SUBMISSIONS" raised
    UnboundLocalError and both counsel columns came back empty."""
    from app.agents.presentation_universal import extract_submissions

    text = (
        "8. DEFENCE CONTENTIONS The accused contends the FIR is an abuse of process. "
        "The State submitted that the offence is grave and custodial interrogation "
        "is needed. "
        "10. RESPONDENT'S SUBMISSIONS Per contra, the petitioner is a flight risk."
    )
    a, b = extract_submissions(text)
    assert a and b


def test_present_tense_cues_and_dispositive_directions():
    """ "The petitioner contends"/"The State submitted" (present/past) are speaker
    cues, while the court's own "The petitioners are directed to..." order must
    NOT be filed as a petitioner submission."""
    from app.agents.presentation_universal import extract_submissions

    text = (
        "The petitioner contends that the FIR is an abuse of process. "
        "Taking into consideration the facts, the petitioners are directed to "
        "appear before the Investigating Officer. "
        "The State submitted that the offence is grave."
    )
    a, b = extract_submissions(text)
    assert any("abuse of process" in s for s in a)
    assert not any("directed to appear" in s for s in a)
    assert any("offence is grave" in s for s in b)
