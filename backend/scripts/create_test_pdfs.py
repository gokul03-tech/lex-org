"""Generate realistic test PDF judgments for LexOrch-KG multi-agent verification."""
import os
import fitz  # PyMuPDF

TEST_DIR = "/home/gokul/Downloads/final-year-project/backend/test_data"
os.makedirs(TEST_DIR, exist_ok=True)

def create_pdf(filename: str, title: str, text: str):
    doc = fitz.open()
    
    # Split text into pages
    paragraphs = text.strip().split("\n\n")
    page_paragraphs = []
    current_page = []
    curr_len = 0
    
    for p in paragraphs:
        if curr_len + len(p) > 1800:
            page_paragraphs.append("\n\n".join(current_page))
            current_page = [p]
            curr_len = len(p)
        else:
            current_page.append(p)
            curr_len += len(p)
    if current_page:
        page_paragraphs.append("\n\n".join(current_page))
        
    for p_idx, page_content in enumerate(page_paragraphs):
        page = doc.new_page(width=595, height=842) # A4
        
        # Header / Title on first page
        y = 50
        if p_idx == 0:
            page.insert_text((50, y), title, fontsize=12, fontname="helv", color=(0.1, 0.1, 0.1))
            y += 30
            
        rect = fitz.Rect(50, y, 545, 780)
        page.insert_textbox(rect, page_content, fontsize=9.5, fontname="helv", color=(0.2, 0.2, 0.2))
        
        # Indian Kanoon footer pagination
        footer_text = f"Indian Kanoon- http://indiankanoon.org/doc/9876543/{p_idx + 1}"
        page.insert_text((180, 810), footer_text, fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))
        
    pdf_path = os.path.join(TEST_DIR, filename)
    doc.save(pdf_path)
    doc.close()
    print(f"Generated test PDF: {pdf_path} ({len(page_paragraphs)} pages)")

# ── 1. Cybercrime / Bail Judgment (New Criminal Law) ──
DOC_1_TEXT = """Vikram Dev vs The State Of Maharashtra ... on 14 March, 2024
(2024) 2 Bom CR 412, 2024 Cri LJ 1580
Bench: Revati Mohite Dere, J. and Gauri Godse, J.

JUDGMENT
Revati Mohite Dere, J.

1. The applicant, Vikram Dev, has approached this Court under Section 482 of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023, seeking regular bail in connection with C.R. No. 102 of 2024 registered with Cyber Crime Police Station, Bandra, Mumbai. The offences alleged against the applicant are punishable under Section 111 of the Bharatiya Nyaya Sanhita (BNS), 2023 and Section 66D of the Information Technology Act, 2000.

2. The case of the prosecution is that on 15-01-2024, an organized syndicate executed a sophisticated OTP phishing and corporate SIM-swap scheme resulting in wrongful loss of Rs. 3.8 Crores to a commercial entity. The applicant was arrested on 22-01-2024 on the allegation that he facilitated logistics and server infrastructure for the prime conspirators.

3. Mr. Merchant, learned Senior Counsel for the applicant, submitted that the investigation is complete and the charge sheet has already been filed on 05-03-2024. He contends that the applicant had no mens rea or knowledge of the phishing fraud. Furthermore, the electronic evidence sought to be relied upon by the prosecution, namely Call Detail Records (CDR) and cell-site logs, has been obtained without compliance with mandatory statutory certification under Section 63 of the Bharatiya Sakshya Adhiniyam (BSA), 2023.

4. Counsel for the applicant placed strong reliance on the judgment reported in (2011) 1 SCC 694 in the case of Sanjay Chandra v. Central Bureau of Investigation, where the Supreme Court settled the principle that bail is the rule and jail is the exception. He also cited the landmark decision reported in (2014) 10 SCC 473 in the case of Anvar P.V. v. P.K. Basheer regarding the mandatory nature of electronic evidentiary certificates.

5. On the other hand, the learned APP Ms. Shinde for the State vehemently opposed the bail plea. She argued that the applicant operated a key logistics conduit under Section 111 of the Bharatiya Nyaya Sanhita (BNS), 2023. She further pointed out that bank ledger audits and panchanama dated 25-01-2024 establish physical proximity of the applicant's leased vehicles near cyber operating nodes.

6. We have considered the rival submissions and perused the charge sheet materials. The custodial interrogation of the applicant has concluded. The main conspirators who received the siphoned funds in offshore accounts remain absconding. No direct financial transfer has been traced to the applicant's accounts. Continued incarceration would amount to pre-trial punishment.

7. In view of the above circumstances, the applicant is directed to be released on bail on executing a P.R. Bond of Rs. 50,000/- with one or two local sureties. Bail application is allowed.

Gauri Godse, J. - I agree."""

# ── 2. Commercial Arbitration Judgment (Civil / Contract) ──
DOC_2_TEXT = """Apex Infrastructure Pvt. Ltd. vs National Highways Authority of India ... on 18 January, 2023
AIR 2023 DEL 145, (2023) 1 DLT 89
Bench: Prathiba M. Singh, J.

JUDGMENT
Prathiba M. Singh, J.

1. The petitioner, Apex Infrastructure Pvt. Ltd., has filed this petition under Section 34 of the Arbitration and Conciliation Act, 1996 challenging the Arbitral Award dated 14-08-2022 passed by the Arbitral Tribunal in disputes arising out of the EPC Construction Agreement dated 12-05-2018.

2. The respondent, National Highways Authority of India (NHAI), had awarded a four-lane highway construction package to the petitioner. The petitioner raised claims for price escalation and idle machinery charges under Section 73 of the Indian Contract Act, 1872, alleging that the respondent failed to provide 90% unencumbered Right of Way (RoW) within the stipulated period.

3. Mr. Sethi, learned Senior Counsel for the petitioner, contended that the majority award suffers from patent illegality on the face of the record under Section 34(2A) of the Arbitration and Conciliation Act. He submitted that the Arbitral Tribunal completely ignored contemporaneous correspondence dated 20-11-2019 and 15-02-2020 wherein NHAI admitted delay in forest clearances.

4. In support of his contentions, counsel relied upon the decision reported in (2015) 3 SCC 49 in the case of Associate Builders v. Delhi Development Authority, wherein the Supreme Court laid down the contours of the public policy test. He further referred to the ruling reported in (2019) 15 SCC 131 in the case of Ssangyong Engineering & Construction Co. Ltd. v. National Highways Authority of India holding that an award ignoring vital evidence is perverse.

5. Mr. Nanda, learned counsel appearing for the respondent NHAI, defended the impugned award. He argued that the Arbitral Tribunal is the ultimate master of quantity and quality of evidence. Under Section 34 of the Arbitration and Conciliation Act, the court cannot sit as an appellate court to re-appreciate factual findings.

6. Having examined the arbitral record and the award, this Court finds that the Arbitral Tribunal failed to consider Ex. P-14 and Ex. P-18 which established site handover defaults. However, interference with arbitral awards is circumscribed. The findings on liquidated damages cannot be sustained as no loss was proved under Section 74 of the Indian Contract Act.

7. Consequently, the petition under Section 34 is partly allowed and the award to the extent of liquidated damages is set aside.

Prathiba M. Singh, J."""

# ── 3. Constitutional Writ Petition (Supreme Court / Fundamental Rights) ──
DOC_3_TEXT = """Dr. Ananya Sharma vs Union Of India & Ors. ... on 5 May, 2023
[2023] 4 SCR 710, (2023) 6 SCC 301
Bench: D.Y. Chandrachud, CJI and P.S. Narasimha, J.

JUDGMENT
D.Y. Chandrachud, CJI

1. The petitioner has invoked the extraordinary jurisdiction of this Court under Article 32 of the Constitution of India challenging statutory notifications regulating digital privacy and surveillance disclosures. The petitioner contends that the impugned directives violate the fundamental right to privacy under Article 21 and freedom of expression under Article 19(1)(a) of the Constitution.

2. Mr. Kapil Sibal, learned Senior Counsel appearing for the petitioner, submitted that mandatory data localization without judicial oversight fails the four-pronged proportionality standard. He submitted that arbitrary executive interception violates the principles of natural justice and procedural due process under Article 14 and Article 21 of the Constitution of India.

3. The petitioner placed reliance on the nine-judge bench judgment reported in (2017) 10 SCC 1 in the case of Justice K.S. Puttaswamy v. Union of India, which recognized privacy as an intrinsic part of the right to life and personal liberty under Article 21. Reliance was also placed on the decision reported in (2020) 3 SCC 637 in the case of Anuradha Bhasin v. Union of India regarding internet restrictions.

4. The learned Solicitor General of India, Mr. Tushar Mehta, defended the notification, submitting that the measures fall squarely within reasonable restrictions under Article 19(2) in the interests of national security and prevention of cyber terrorism.

5. We have evaluated the constitutional claims. While the State possesses legitimate interests in preventing cross-border cyber threats, any restriction on Article 21 must satisfy the tests of legality, legitimate aim, proportionality, and procedural safeguards.

6. The writ petition under Article 32 of the Constitution is accordingly disposed of with directions to establish an independent oversight committee.

P.S. Narasimha, J. - I agree."""

if __name__ == "__main__":
    create_pdf("01_Cybercrime_Bail_Vikram_Dev.pdf", "IN THE HIGH COURT OF JUDICATURE AT BOMBAY", DOC_1_TEXT)
    create_pdf("02_Commercial_Arbitration_Apex_Infra.pdf", "IN THE HIGH COURT OF DELHI AT NEW DELHI", DOC_2_TEXT)
    create_pdf("03_Constitutional_Writ_Ananya_Sharma.pdf", "IN THE SUPREME COURT OF INDIA", DOC_3_TEXT)
    print("All test PDF files generated in", TEST_DIR)
