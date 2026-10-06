UNIVERSAL_EXTRACTION_PROMPT = """
🌐 UNIVERSAL EXTRACTION PROTOCOL - LEXORCH-KG

The following rules are mandatory for ALL document types (Standard Judgments, Academic Case Dossiers, Illustrative/Fictional Files, Civil Suits, Criminal Appeals, Insolvency cases). They OVERRIDE any heuristic keyword shortcuts when extracting via LLM.

### RULE 1: NOISE & DISCLAIMER FILTERING (MANDATORY)
- Identify and IGNORE all academic/illustrative/fictional disclaimers. Do NOT extract them as legal arguments, court findings, strategic grounds, strengths, weaknesses, conclusions, or action items.
- Explicitly exclude any text containing: "This is an academic case study", "Illustrative only", "illustrative case file", "This educational file does not independently conclude", "fictional case file", "case file is fictional", "does not independently conclude that any offence is established", "case itself should not be rewritten", "This document is prepared for academic purposes".
- Treat such disclaimers as document metadata noise only.

### RULE 2: METADATA (DATES, NUMBERS, PROCEDURAL STAGE)
1. DECISION DATE: Extract ONLY from the SIGNATURE BLOCK (very end of document, typically last 500 characters). If a date appears in the first 20% of the text (FIR date, complaint date, transaction date, citation date), treat it as an EVENT date, NOT the judgment/order date.
2. CASE NUMBER: Extract the MAIN appellate/petition number (e.g., "Criminal Petition No. 2458 of 2023", "O.S. No. 142 of 2025", "Criminal Appeal No."). NEVER use an underlying FIR number or lower court number as the main case number.
3. PROCEDURAL STAGE: Identify the actual current proceeding (e.g., "Section 482 Quashing Petition", "Civil Suit for Recovery", "Criminal Appeal", "Writ Petition", "Regular Bail/Anticipatory Bail") rather than the underlying crime/dispute.

### RULE 3: ISSUE EXTRACTION (COMPLETE, NO TRUNCATION)
1. Trigger on: "Main question:", "We frame the following issues", "Questions considered", "Issues for consideration", "Point for determination", "First, whether", "Issue 1:", "The points that arise for determination are".
2. CRITICAL: Read each issue to COMPLETION. Do NOT stop at commas, the word "or", semicolons, or line breaks. Extract the full question until you reach a period followed by a capital letter OR the next section header (numbered heading) OR a double newline. 
3. Extract ALL issues present, not just the first one.

### RULE 4: COUNSEL ATTRIBUTION (STRICT COLUMN ASSIGNMENT)
Assign strictly by SPEAKER or SECTION HEADER. Never infer by argument content.

- PETITIONER/PLAINTIFF/APPLICANT column: ONLY text under/after headers like "Petitioner's Submissions", "Petitioners' Submissions", "Plaintiff's Final Written Submissions", "Applicant's Submissions", "Appellant's Arguments" OR spoken by "Counsel for the petitioners/appellant/plaintiff/applicant", "Learned counsel for the petitioner(s)", "Mr./Ms. ... appearing for the petitioner(s)".
- RESPONDENT/STATE/DEFENDANT column: ONLY text under/after headers like "State's Submissions", "Respondent's Submissions", "Defendant's Final Written Submissions", "Defendant's Written Statement", "Prosecution Submissions", "Respondent's Arguments" OR spoken by "Additional Public Prosecutor", "Public Prosecutor", "Counsel for the State", "Learned counsel for the respondent/defendant".
- PROHIBITION: If text says "Counsel for the petitioners submits X", it MUST go to Petitioner column. If it says "State/Prosecution argues Y", it MUST go to State column. Never swap them.

### RULE 5: EVIDENCE & EXHIBITS (STRUCTURED ONLY)
1. Extract ONLY from explicit sections: "EXHIBIT REGISTER", "List of Documents", "DOCUMENTARY EXHIBITS", "Exhibits", "Documentary Evidence Register".
2. Extract items formatted as "Exhibit P-1 — [description]", "P-1: [description]", "Exhibit D-2 - [description]", "P-4 to P-6: [description]" (expand ranges). 
3. Do NOT extract random narrative sentences, commentary, or meta-text as evidence records. Return structured list only if such a register exists.

### RULE 6: CONCLUSION, DISPOSITION & ACTION PLAN
1. Look for sections: "ORDER", "CONCLUSION", "CONCLUSION AND ORDER", "JUDGMENT AND DECREE", "Final Order", "OPERATIVE ORDER", "IN THE RESULT", "DISPOSITION".
2. Extract the specific operative directives (e.g., "The appeal is allowed", "The accused is released on bail", "Bail is granted subject to...", "The suit is decreed for...", "The petition is dismissed/allowed") — not registry transmission or procedural boilerplate unless it is the core operative direction.
3. Do NOT extract academic commentary as the main conclusion.

### GENERAL SAFETY
- If information is not found after applying these rules, return empty ([]) or null as appropriate. Do NOT invent, fabricate, or hallucinate content.
- Prioritize section-header boundaries over free-form text. When in doubt, exclude noise rather than include it.
"""
