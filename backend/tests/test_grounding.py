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

    # Test Section bindings
    assert map_section_to_act('482', binds, 'criminal') == 'Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023'
    assert map_section_to_act('111', binds, 'criminal') == 'Bharatiya Nyaya Sanhita (BNS), 2023'
    assert map_section_to_act('66D', binds, 'criminal') == 'Information Technology Act, 2000'
    assert map_section_to_act('63', binds, 'criminal') == 'Bharatiya Sakshya Adhiniyam (BSA), 2023'

    # Test dynamic evidence & risk
    ev_items = extract_evidence_items(VIKRAM_TEXT)
    assert not any('contraband' in str(it).lower() for it in ev_items)
    risk = build_risk_strategy(VIKRAM_TEXT, report)
    assert 'Bail application allowed' in risk['conclusion']


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

    issues = render_issues(r_ctx)
    assert any('Section 482' in iss for iss in issues)
    assert any('Section 111' in iss for iss in issues)

    conclusion = render_conclusion(r_ctx, VIKRAM_TEXT)
    assert 'Bail application allowed' in conclusion

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
