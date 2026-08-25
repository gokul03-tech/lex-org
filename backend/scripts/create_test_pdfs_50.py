"""Generate 50 realistic test PDF judgments for LexOrch-KG multi-agent verification.

Extends create_test_pdfs.py: keeps the original 5 documents and adds 45 more,
round-robin across five practice areas (bail, arbitration, writ, civil, narcotics),
with deterministic randomization of parties, courts, benches, dates, citations,
statutes, precedents, evidence and operative outcomes.
"""
import os
import random

import fitz  # PyMuPDF

TEST_DIR = "/home/gokul/Downloads/final-year-project/backend/test_data"
os.makedirs(TEST_DIR, exist_ok=True)

random.seed(42)

# ────────────────────────────── Name / court pools ──────────────────────────
PERSON_NAMES = [
    "Ramesh Kulkarni", "Suresh Iyer", "Farhan Qureshi", "Deepak Rathi",
    "Alok Banerjee", "Nitin Deshmukh", "Rahul Srivastava", "Imran Sheikh",
    "Vinod Gowda", "Prakash Nair", "Arjun Malhotra", "Sameer Kothari",
    "Yashwant Rao", "Dinesh Pal", "Karthik Subramanian", "Manoj Tiwari",
    "Rajat Bose", "Harpreet Singh", "Girish Apte", "Naveen Chandra",
    "Zoya Khan", "Meenakshi Rathore", "Priyanka Verma", "Lakshmi Menon",
    "Shalini Gupta", "Anjali Dhar", "Radhika Shetty", "Kavita Krishnan",
]
COMPANY_NAMES = [
    "Meridian Constructions Pvt. Ltd.", "Sunrise Logistics Ltd.",
    "Trident Steel Works Pvt. Ltd.", "Bluewave Telecom Infra Ltd.",
    "Granite Mines India Pvt. Ltd.", "Orbit Pharma Labs Ltd.",
    "Silverline Hospitality Pvt. Ltd.", "Vayu Renewables Energy Ltd.",
    "Cascade Textiles Mills Ltd.", "Pinnacle EdTech Solutions Pvt. Ltd.",
]
STATE_NAMES = [
    "Maharashtra", "Delhi", "Karnataka", "Tamil Nadu", "Gujarat",
    "West Bengal", "Telangana", "Rajasthan", "Uttar Pradesh", "Kerala",
]
COURTS = [
    ("IN THE HIGH COURT OF JUDICATURE AT BOMBAY", "Bombay High Court"),
    ("IN THE HIGH COURT OF DELHI AT NEW DELHI", "High Court of Delhi"),
    ("IN THE HIGH COURT OF KARNATAKA AT BENGALURU", "Karnataka High Court"),
    ("IN THE HIGH COURT OF JUDICATURE AT MADRAS", "Madras High Court"),
    ("IN THE HIGH COURT OF GUJARAT AT AHMEDABAD", "Gujarat High Court"),
    ("IN THE HIGH COURT AT CALCUTTA", "Calcutta High Court"),
    ("IN THE HIGH COURT FOR THE STATE OF TELANGANA", "Telangana High Court"),
    ("IN THE HIGH COURT OF JUDICATURE FOR RAJASTHAN", "Rajasthan High Court"),
    ("IN THE HIGH COURT OF JUDICATURE AT ALLAHABAD", "Allahabad High Court"),
    ("IN THE SUPREME COURT OF INDIA", "Supreme Court of India"),
]
JUDGES = [
    "Revati Mohite Dere", "Gauri Godse", "Prathiba M. Singh", "D.Y. Chandrachud",
    "P.S. Narasimha", "B.R. Gavai", "Vikram Nath", "Anoop Kumar Mendiratta",
    "Nagarathna", "J.B. Pardiwala", "A.S. Oka", "M.M. Sundresh",
    "S. Ravindra Bhat", "Hima Kohli", "Bela Trivedi", "Sanjay Karol",
    "Krishna Murari", "Vipul M. Pancholi", "M.G.S. Kamal", "Sunita Agarwal",
]
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

SENIOR_COUNSEL = ["Merchant", "Sethi", "Rohatgi", "Sibal", "Dave", "Salve", "Chandrachud", "Naphade", "Luthra", "Andhyarujina"]
APP_NAMES = ["Shinde", "Menon", "Khan", "Reddy", "Joshi", "Bhat"]

# Citation generators per court-reporter flavour
def mk_citation(year: int) -> str:
    reporters = [
        lambda: f"({year}) {random.randint(1, 15)} SCC {random.randint(1, 750)}",
        lambda: f"AIR {year} SC {random.randint(100, 2500)}",
        lambda: f"{year} Cri LJ {random.randint(500, 4500)}",
        lambda: f"({year}) {random.randint(1, 9)} DLT {random.randint(50, 900)}",
        lambda: f"2023 SCC OnLine SC {random.randint(100, 1900)}",
    ]
    return random.choice(reporters)()


def rand_date(y0=2021, y1=2025):
    return f"{random.randint(1, 28)} {random.choice(MONTHS)}, {random.randint(y0, y1)}"


def short_date(y0=2021, y1=2024):
    return f"{random.randint(1, 28):02d}-{random.randint(1, 12):02d}-{random.randint(y0, y1)}"


def rupees():
    magnitude = random.choice([50000, 75000, 100000, 200000, 500000, 1000000, 2400000])
    return f"Rs. {magnitude:,}/-".replace(",", ",")


# Precedent pools (name, citation, year) — landmark, real cases
PRECEDENTS_BAIL = [
    ("Sanjay Chandra v. Central Bureau of Investigation", "(2011) 1 SCC 694"),
    ("Anvar P.V. v. P.K. Basheer", "(2014) 10 SCC 473"),
    ("Arnesh Kumar v. State of Bihar", "(2014) 8 SCC 273"),
    ("Pankaj Bansal v. Union of India", "(2023) 4 SCC 676"),
    ("Satender Kumar Antil v. CBI", "(2022) 10 SCC 51"),
]
PRECEDENTS_NDPS = [
    ("Tofan Singh v. State of Tamil Nadu", "(2021) 4 SCC 1"),
    ("Mohan Lal v. State of Rajasthan", "(2015) 6 SCC 222"),
    ("Balbir Singh v. State", "1994 Supp (1) SCC 92"),
]
PRECEDENTS_ARB = [
    ("Associate Builders v. Delhi Development Authority", "(2015) 3 SCC 49"),
    ("Ssangyong Engineering & Construction Co. Ltd. v. NHAI", "(2019) 15 SCC 131"),
    ("Delhi Airport Metro Express Pvt. Ltd. v. DMRC", "(2022) 1 SCC 131"),
    ("PSU Engineering Corporation v. State of Bihar", "(2021) 16 SCC 351"),
]
PRECEDENTS_WRIT = [
    ("Justice K.S. Puttaswamy v. Union of India", "(2017) 10 SCC 1"),
    ("Anuradha Bhasin v. Union of India", "(2020) 3 SCC 637"),
    ("Maneka Gandhi v. Union of India", "(1978) 1 SCC 248"),
    ("Modern Dental College v. State of M.P.", "(2016) 7 SCC 353"),
]
PRECEDENTS_CIVIL = [
    ("Chand Rani v. Kamal Rani", "(1993) 1 SCC 519"),
    ("Sughar Singh v. Hari Singh", "(2020) 13 SCC 285"),
    ("Lourdu Mary Margaret v. Reni Chellam", "(2020) 6 SCC 298"),
    ("K.S. Vidyanadam v. Vairavan", "(1997) 3 SCC 1"),
]

# ────────────────────────────── PDF writer ──────────────────────────────────
def create_pdf(filename: str, header: str, text: str):
    doc = fitz.open()
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    pages, current, curr_len = [], [], 0
    for p in paragraphs:
        if curr_len + len(p) > 1800:
            pages.append("\n\n".join(current))
            current, curr_len = [p], len(p)
        else:
            current.append(p)
            curr_len += len(p)
    if current:
        pages.append("\n\n".join(current))

    for idx, content in enumerate(pages):
        page = doc.new_page(width=595, height=842)
        y = 50
        if idx == 0:
            page.insert_text((50, y), header, fontsize=12, fontname="helv", color=(0.1, 0.1, 0.1))
            y += 30
        page.insert_textbox(fitz.Rect(50, y, 545, 780), content, fontsize=9.5, fontname="helv", color=(0.2, 0.2, 0.2))
        page.insert_text((180, 810), f"Indian Kanoon- http://indiankanoon.org/doc/{random.randint(1000000, 9999999)}/{idx + 1}", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))

    path = os.path.join(TEST_DIR, filename)
    doc.save(path)
    doc.close()
    return len(pages)


# ─────────────────── Category builders (return title, body) ─────────────────
def build_bail(i: int):
    acc = random.choice(PERSON_NAMES).replace(" ", "_")
    state = random.choice(STATE_NAMES)
    court_header, court_name = random.choice(COURTS[:9])
    j1, j2 = random.sample(JUDGES, 2)
    date = rand_date()
    fir = random.randint(50, 400)
    amount = random.choice([3.2, 1.5, 2.7, 4.1, 0.9, 5.6])
    ps = random.choice(["Cyber Crime Police Station", "Economic Offences Wing", "Special Enquiry Cell"])
    senior = random.choice(SENIOR_COUNSEL)
    app = random.choice(APP_NAMES)
    c1 = mk_citation(random.randint(2021, 2024))
    p1name, p1cite = PRECEDENTS_BAIL[i % len(PRECEDENTS_BAIL)]
    p2name, p2cite = PRECEDENTS_BAIL[(i + 2) % len(PRECEDENTS_BAIL)]
    bond = random.choice([50000, 75000, 100000])

    title = f"{acc.replace('_', ' ')} vs The State Of {state} ... on {date}"
    cites = f"{mk_citation(random.randint(2023, 2025))}, {mk_citation(random.randint(2022, 2024))}"
    bench = f"Bench: {j1}, J." + (f" and {j2}, J." if i % 2 == 0 else "")

    body = f"""{title}
{cites}
{bench}

JUDGMENT
{j1}, J.

1. The applicant, {acc.replace('_', ' ')}, has approached this Court under Section 482 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023, seeking regular bail in connection with C.R. No. {fir} of 2024 registered with {ps}, {state}. The offences alleged are punishable under Section 111 of the Bharatiya Nyaya Sanhita (BNS), 2023 and Section 66D of the Information Technology Act, 2000.

2. The prosecution case is that a coordinated digital fraud syndicate caused wrongful loss of Rs. {amount} Crores between {short_date()} and {short_date()}. The applicant was arrested on {short_date()} for allegedly providing logistics and server infrastructure to the prime conspirators.

3. Mr. {senior}, learned Senior Counsel for the applicant, submitted that the investigation is complete and the charge sheet was filed on {short_date()}. He contends the applicant had no mens rea, and that the CDR and cell-site records relied upon by the prosecution were seized without mandatory certification under Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023.

4. Counsel placed reliance on {p1cite} in the case of {p1name}, and on {p2cite} in the case of {p2name}, on the principle that continued custody must not become punitive where trial will take time.

5. Learned APP Ms. {app} opposed, contending that bank ledger audits and the panchanama dated {short_date()} establish the applicant's proximity to the operating nodes, and that Ex. P-14 seizure memo links the leased servers to the applicant.

6. Upon consideration of the charge sheet, this Court finds custodial interrogation has concluded; no direct fund trail touches the applicant's accounts; and trial will take considerable time. Further detention would serve no purpose.

7. The applicant is directed to be released on bail on executing a P.R. Bond of Rs. {bond:,}/- with one or two local sureties. Bail application is allowed.

{j2}, J. - I agree."""
    return title, court_header, body


def build_arbitration(i: int):
    comp = random.choice(COMPANY_NAMES).replace(" ", "_")
    resp = random.choice([
        "National Highways Authority of India", "Municipal Corporation of Greater Mumbai",
        "Power Grid Corporation of India Ltd.", "Delhi Development Authority",
    ]).replace(" ", "_")
    court_header, _ = random.choice(COURTS[:9])
    j1 = random.choice(JUDGES)
    date = rand_date(2022, 2025)
    award_date = short_date()
    agm_date = short_date(2016, 2019)
    senior_p = random.choice(SENIOR_COUNSEL)
    senior_r = random.choice(SENIOR_COUNSEL)
    claim = random.choice(["price escalation and idle machinery charges", "loss of profit and prolongation costs", "unauthorized deduction of liquidated damages", "denial of final bill measurements"])
    ex_a = random.randint(10, 40)
    ex_b = ex_a + random.randint(1, 4)
    c1 = mk_citation(random.randint(2021, 2024))
    p1name, p1cite = PRECEDENTS_ARB[i % len(PRECEDENTS_ARB)]
    p2name, p2cite = PRECEDENTS_ARB[(i + 1) % len(PRECEDENTS_ARB)]
    ld_amount = random.choice([85, 120, 240]) * 100000

    title = f"{comp.replace('_', ' ')} vs {resp.replace('_', ' ')} ... on {date}"
    cites = f"AIR {random.randint(2022, 2024)} DEL {random.randint(100, 700)}, ({random.randint(2022, 2024)}) {random.randint(1, 8)} DLT {random.randint(60, 800)}"
    body = f"""{title}
{cites}
Bench: {j1}, J.

JUDGMENT
{j1}, J.

1. The petitioner, {comp.replace('_', ' ')}, has filed this petition under Section 34 of the Arbitration and Conciliation Act, 1996 challenging the Arbitral Award dated {award_date} in disputes arising out of the works contract dated {agm_date} awarded by the respondent, {resp.replace('_', ' ')}.

2. The petitioner raised claims of {claim} under Sections 73 and 74 of the Indian Contract Act, 1872, alleging that the respondent committed systemic delays in granting site access and approvals.

3. Mr. {senior_p}, learned Senior Counsel for the petitioner, contended that the award suffers from patent illegality under Section 34(2A) of the Arbitration and Conciliation Act, 1996, as the Tribunal ignored contemporaneous correspondence admitting delay attributable to the respondent.

4. Reliance was placed on {p1cite} in the case of {p1name}, and on {p2cite} in the case of {p2name}, to contend that an award ignoring vital documentary evidence is perverse and liable to be set aside.

5. Mr. {senior_r}, learned Senior Counsel for the respondent, defended the award, urging that under Section 34 of the Arbitration and Conciliation Act, 1996 this Court does not sit in appeal over the Tribunal's factual findings, and that the deductions towards liquidated damages of Rs. {ld_amount:,}/- were justified.

6. On scrutiny, the Tribunal failed to consider Ex. P-{ex_a} and Ex. P-{ex_b} which conclusively established handover defaults attributable to the respondent. However, the findings on delay compensation suffer no infirmity since no loss was proved under Section 74 of the Indian Contract Act, 1872.

7. The petition under Section 34 is partly allowed; the award to the extent of liquidated damages of Rs. {ld_amount:,}/- is set aside, and in rest it is affirmed.

{j1}."""
    return title, court_header, body


def build_writ(i: int):
    pet = random.choice(PERSON_NAMES + COMPANY_NAMES).replace(" ", "_")
    court_header, _ = random.choice(COURTS)
    article = random.choice(["226", "32"])
    j1, j2 = random.sample(JUDGES, 2)
    date = rand_date(2022, 2025)
    senior_p = random.choice(SENIOR_COUNSEL)
    topic = random.choice([
        ("digital privacy and surveillance disclosures", "Article 21 privacy and Article 19(1)(a) expression"),
        ("arbitrary demolition notices affecting residential dwellings", "right to shelter under Article 21 and equality under Article 14"),
        ("compulsory retirement of a government servant without inquiry", "procedural fairness under Article 14 and Article 311"),
        ("internet suspension orders during public agitation", "freedom of speech and trade under Article 19(1)(a) and 19(1)(g)"),
    ])
    p1name, p1cite = PRECEDENTS_WRIT[i % len(PRECEDENTS_WRIT)]
    p2name, p2cite = PRECEDENTS_WRIT[(i + 1) % len(PRECEDENTS_WRIT)]
    outcome = random.choice([
        "disposed of with directions to constitute an independent oversight committee",
        "allowed; the impugned notification is quashed and set aside",
        "disposed of with a direction to decide the representation within eight weeks",
    ])

    title = f"{pet.replace('_', ' ')} vs Union Of India & Ors. ... on {date}"
    cites = f"[{random.randint(2022, 2024)}] {random.randint(1, 12)} SCR {random.randint(100, 990)}, ({random.randint(2022, 2024)}) {random.randint(1, 12)} SCC {random.randint(100, 600)}"
    body = f"""{title}
{cites}
Bench: {j1}, {'CJI' if i % 3 == 0 else 'J'} and {j2}, J.

JUDGMENT
{j1}, {'CJI' if i % 3 == 0 else 'J'}

1. The petitioner, {pet.replace('_', ' ')}, invokes the extraordinary jurisdiction of this Court under Article {article} of the Constitution of India challenging state action concerning {topic[0]}, contending violation of {topic[1]}.

2. Mr./Ms. {senior_p}, learned Senior Counsel for the petitioner, argued that the impugned measure fails the proportionality standard — legality, legitimate aim, necessity, and balancing — recognized in Maneka Gandhi and subsequent authorities.

3. Reliance was placed on {p1cite} in the case of {p1name}, and on {p2cite} in the case of {p2name}.

4. The learned Solicitor General defended the action as falling within reasonable restrictions under Article 19(2) and Article 21 framework, citing national security and administrative exigency.

5. Upon evaluation, this Court finds that while the State has legitimate interests, the absence of procedural safeguards renders the impugned action disproportionate under Articles 14 and 21 of the Constitution of India.

6. The writ petition under Article {article} of the Constitution is accordingly {outcome}.

{j2}, J. - I agree."""
    return title, court_header, body


def build_civil(i: int):
    pl = random.choice(PERSON_NAMES + COMPANY_NAMES).replace(" ", "_")
    df = random.choice(PERSON_NAMES).replace(" ", "_")
    court_header, _ = random.choice(COURTS)
    j1, j2 = random.sample(JUDGES, 2)
    date = rand_date(2021, 2025)
    senior = random.choice(SENIOR_COUNSEL)
    consideration = random.choice([1.8, 2.4, 3.1, 4.5])
    subject = random.choice([
        ("Specific Performance of an Agreement to Sell registered under the Indian Registration Act, 1908", "execution of sale deed and permanent injunction"),
        ("specific performance of a development agreement coupled with possession", "direction to execute conveyance and mesne profits"),
        ("specific performance of a lease-cum-sale deed of a commercial unit", "execution and registration of the sale certificate"),
    ])
    p1name, p1cite = PRECEDENTS_CIVIL[i % len(PRECEDENTS_CIVIL)]
    p2name, p2cite = PRECEDENTS_CIVIL[(i + 1) % len(PRECEDENTS_CIVIL)]
    outcome = random.choice([
        "The appeal is allowed. The respondents are directed to execute the conveyance deed upon receipt of the remaining consideration within eight weeks.",
        "The appeal is allowed in part; specific performance is decreed subject to deposit of balance sale consideration within twelve weeks.",
        "The second appeal is dismissed; however, the plaintiff is granted refund of earnest money with interest at 9% per annum.",
    ])

    title = f"{pl.replace('_', ' ')} vs {df.replace('_', ' ')} & Ors. ... on {date}"
    cites = f"({random.randint(2021, 2024)}) {random.randint(1, 9)} ALD {random.randint(100, 650)}, AIR {random.randint(2022, 2025)} SC {random.randint(100, 1500)}"
    body = f"""{title}
{cites}
Bench: {j1}, J. and {j2}, J.

JUDGMENT
{j1}, J.

1. This appeal arises out of a civil suit for {subject[0]}. The plaintiff/appellant seeks {subject[1]} under Order 39 Rule 1 and 2 of the Code of Civil Procedure, 1908 (CPC) in respect of property situated in {random.choice(['Bengaluru', 'Pune', 'Hyderabad', 'Jaipur', 'Kochi'])}.

2. The respondent/vendor contended that time was of the essence and the appellant failed to tender the balance consideration of Rs. {consideration} Crores within the stipulated 90 days, invoking forfeiture under Section 74 of the Indian Contract Act, 1872.

3. Mr. {senior}, learned Senior Counsel for the appellant, argued that in contracts relating to immovable property time is not ordinarily of the essence, and demonstrated continuous readiness and willingness under Section 16(c) of the Specific Relief Act, 1963.

4. Counsel relied upon {p1cite} in the case of {p1name}, and upon {p2cite} in the case of {p2name}, holding readiness and willingness must be gathered from contemporaneous conduct.

5. Having examined the bank statements and escrow deposits, this Court holds the appellant satisfied the test of readiness and willingness under Section 16(c) of the Specific Relief Act, 1963.

6. {outcome}

{j2}, J. - I agree."""
    return title, court_header, body


def build_ndps(i: int):
    acc = random.choice(PERSON_NAMES).replace(" ", "_")
    state = random.choice(STATE_NAMES)
    court_header, _ = random.choice(COURTS[:9])
    j1 = random.choice(JUDGES)
    date = rand_date(2022, 2025)
    fir = random.randint(20, 300)
    qty = random.choice([210, 350, 450, 520])
    section_s = random.choice(["21", "22", "25", "29"])
    counsel_p = random.choice(["Merchant", "Sethi", "Naphade", "Luthra"])
    app = random.choice(APP_NAMES)
    p1name, p1cite = PRECEDENTS_NDPS[i % len(PRECEDENTS_NDPS)]
    bond = random.choice([100000, 150000, 200000])

    title = f"{acc.replace('_', ' ')} vs State of {state} ... on {date}"
    cites = f"{random.randint(2023, 2025)} Cri LJ {random.randint(500, 3800)}, ({random.randint(2023, 2024)}) DLT (Crl) {random.randint(200, 800)}"
    body = f"""{title}
{cites}
Bench: {j1}, J.

JUDGMENT
{j1}, J.

1. The petitioner seeks regular bail under Section 483 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023 in FIR No. {fir}/{random.choice([2023, 2024])} registered under Sections {section_s}, 29 and 61 of the Narcotic Drugs and Psychotropic Substances Act (NDPS Act), 1985 at Special Cell Police Station, {state}.

2. The prosecution case is that {qty} grams of contraband was recovered from a co-accused on {short_date()}. The petitioner stands implicated solely on disclosure statements and alleged telephonic contact under Section 29 NDPS Act.

3. Learned counsel {counsel_p} for the petitioner submitted that no recovery was effected from the conscious possession of the petitioner, and custodial statements are inadmissible per {p1cite} in the case of {p1name}.

4. It was further urged that the search violated the mandatory safeguards of Section 50 of the NDPS Act, and the recovered quantity being intermediate, the embargo under Section 37 NDPS Act does not operate.

5. Learned APP Ms. {app} opposed, placing reliance on Call Detail Records showing contact between the petitioner and the co-accused, and on the panchanama drawn at the time of recovery.

6. Considering that investigation is complete, the charge sheet stands filed, and no contraband was recovered from the petitioner's conscious possession, the petitioner satisfies the parameters for bail under Section 483 BNSS, 2023.

7. Application allowed. Petitioner admitted to bail on furnishing personal bond of Rs. {bond:,}/- with two sureties.

{j1}."""
    return title, court_header, body


BUILDERS = [build_bail, build_arbitration, build_writ, build_civil, build_ndps]
LABELS = {
    0: ("Criminal_Digital_Fraud_Bail", "Cybercrime Bail"),
    1: ("Commercial_Arbitration", "Arbitration S.34"),
    2: ("Constitutional_Writ", "Writ Petition"),
    3: ("Civil_Property", "Civil Appeal"),
    4: ("Criminal_NDPS_Bail", "NDPS Bail"),
}


def main():
    # Original five stay; we add 45 more → total 50
    start_num = 6          # 01–05 already exist
    end_num = 50           # inclusive
    manifest = []
    n = start_num
    cat = 0
    seq_in_cat = {k: 0 for k in LABELS}
    while n <= end_num:
        builder = BUILDERS[cat]
        label, pretty = LABELS[cat]
        seq_in_cat[cat] += 1
        person = builder(seq_in_cat[cat] * 7 + n)
        title, header, body = person
        # Derive a stable file slug from the case title's first party
        first_party = title.split(" vs ")[0].strip().replace(" ", "_").replace(".", "")
        filename = f"{n:02d}_{label}_{first_party[:28]}.pdf"
        pages = create_pdf(filename, header, body)
        manifest.append({"file": filename, "category": pretty, "title": title, "pages": pages})
        print(f"Generated {filename} ({pages} pages)")
        n += 1
        cat = (cat + 1) % len(BUILDERS)

    import json
    with open(os.path.join(TEST_DIR, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"\nDone. {len(manifest)} new PDFs generated. Manifest at {os.path.join(TEST_DIR, 'manifest.json')}")


if __name__ == "__main__":
    main()
