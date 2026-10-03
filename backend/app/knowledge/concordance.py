"""Indian Statutory Concordance Engine: IPC ↔ BNS, CrPC ↔ BNSS, IEA ↔ BSA.

Provides bidirectional section mapping, statutory change descriptions,
and procedural transition implications for the 2023/2024 criminal codes.
"""

from typing import Any, Optional

# IPC → BNS (Bharatiya Nyaya Sanhita, 2023)
IPC_TO_BNS: dict[str, dict[str, Any]] = {
    "420": {
        "new_section": "318(4)",
        "new_act": "Bharatiya Nyaya Sanhita (BNS), 2023",
        "title": "Cheating and dishonestly inducing delivery of property",
        "key_change": "Amalgamated cheating provisions; enhanced penalty for organized digital cyber deception.",
        "bailable": "Non-bailable",
        "cognizable": "Cognizable"
    },
    "406": {
        "new_section": "316",
        "new_act": "Bharatiya Nyaya Sanhita (BNS), 2023",
        "title": "Punishment for criminal breach of trust",
        "key_change": "Explicit inclusion of electronic assets, digital keys, and automated escrow misappropriation.",
        "bailable": "Non-bailable",
        "cognizable": "Cognizable"
    },
    "302": {
        "new_section": "103(1)",
        "new_act": "Bharatiya Nyaya Sanhita (BNS), 2023",
        "title": "Punishment for murder",
        "key_change": "Introduction of Section 103(2) for mob lynching and hate crimes with separate sentencing brackets.",
        "bailable": "Non-bailable",
        "cognizable": "Cognizable"
    },
    "307": {
        "new_section": "109",
        "new_act": "Bharatiya Nyaya Sanhita (BNS), 2023",
        "title": "Attempt to murder",
        "key_change": "Restructured attempt hierarchy with life imprisonment provisions preserved.",
        "bailable": "Non-bailable",
        "cognizable": "Cognizable"
    },
    "120B": {
        "new_section": "61(2)",
        "new_act": "Bharatiya Nyaya Sanhita (BNS), 2023",
        "title": "Criminal conspiracy",
        "key_change": "Clarified conspiratorial agreement thresholds across digital networks.",
        "bailable": "Depends on offence",
        "cognizable": "Depends on offence"
    },
    "498A": {
        "new_section": "85 / 86",
        "new_act": "Bharatiya Nyaya Sanhita (BNS), 2023",
        "title": "Husband or relative subjecting woman to cruelty",
        "key_change": "Cruelty defined explicitly under Section 86 with psychological and mental harm thresholds.",
        "bailable": "Non-bailable",
        "cognizable": "Cognizable"
    },
    "124A": {
        "new_section": "152",
        "new_act": "Bharatiya Nyaya Sanhita (BNS), 2023",
        "title": "Act endangering sovereignty, unity and integrity of India",
        "key_change": "Colonial 'Sedition' replaced with targeted protection of national sovereignty and unity.",
        "bailable": "Non-bailable",
        "cognizable": "Cognizable"
    },
    "379": {
        "new_section": "303(2)",
        "new_act": "Bharatiya Nyaya Sanhita (BNS), 2023",
        "title": "Punishment for theft",
        "key_change": "Community service introduced as punishment for first-time petty theft under Rs. 5,000.",
        "bailable": "Non-bailable",
        "cognizable": "Cognizable"
    },
    "34": {
        "new_section": "3(5)",
        "new_act": "Bharatiya Nyaya Sanhita (BNS), 2023",
        "title": "Acts done by several persons in furtherance of common intention",
        "key_change": "Preserved core doctrine of joint vicarious liability.",
        "bailable": "N/A",
        "cognizable": "N/A"
    }
}

# CrPC → BNSS (Bharatiya Nagarik Suraksha Sanhita, 2023)
CRPC_TO_BNSS: dict[str, dict[str, Any]] = {
    "439": {
        "new_section": "483",
        "new_act": "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023",
        "title": "Special powers of High Court or Court of Session regarding bail",
        "key_change": "Explicit timelines for bail hearings; mandatory digital notice to complainant in specified offences.",
        "forum": "High Court / Sessions Court"
    },
    "438": {
        "new_section": "482",
        "new_act": "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023",
        "title": "Direction for grant of bail to person apprehending arrest (Anticipatory Bail)",
        "key_change": "Preserved High Court and Sessions concurrent jurisdiction; structured conditions of cooperation.",
        "forum": "High Court / Sessions Court"
    },
    "437": {
        "new_section": "480",
        "new_act": "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023",
        "title": "When bail may be taken in case of non-bailable offence",
        "key_change": "Relaxed bail norms for first-time undertrial prisoners who completed one-third sentence.",
        "forum": "Magistrate Court"
    },
    "482": {
        "new_section": "528",
        "new_act": "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023",
        "title": "Saving of inherent powers of High Court",
        "key_change": "Unchanged scope for quashing FIRs/proceedings to prevent abuse of judicial process.",
        "forum": "High Court"
    },
    "167": {
        "new_section": "187",
        "new_act": "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023",
        "title": "Procedure when investigation cannot be completed in 24 hours",
        "key_change": "Police custody of 15 days can now be sought in staggered tranches within first 40/60 days.",
        "forum": "Magistrate Court"
    },
    "41A": {
        "new_section": "35(3)",
        "new_act": "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023",
        "title": "Notice of appearance before police officer",
        "key_change": "Prior sanction from DSP rank required before arresting persons for offences punishable under 3 years.",
        "forum": "Investigating Agency"
    },
    "154": {
        "new_section": "173",
        "new_act": "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023",
        "title": "Information in cognizable cases (FIR / e-FIR)",
        "key_change": "Mandatory acceptance of Zero-FIR and electronic FIR with 3-day verification protocol.",
        "forum": "Police Station"
    },
    "164": {
        "new_section": "183",
        "new_act": "Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023",
        "title": "Recording of confessions and statements",
        "key_change": "Mandatory audio-video electronic recording of victim and witness statements.",
        "forum": "Judicial Magistrate"
    }
}

# IEA → BSA (Bharatiya Sakshya Adhiniyam, 2023)
IEA_TO_BSA: dict[str, dict[str, Any]] = {
    "65B": {
        "new_section": "63",
        "new_act": "Bharatiya Sakshya Adhiniyam (BSA), 2023",
        "title": "Admissibility of electronic records and mandatory certification",
        "key_change": "Harmonized certificate schedule; electronic signatures and hash validation explicitly codified.",
        "scope": "Electronic Evidence"
    },
    "27": {
        "new_section": "23",
        "new_act": "Bharatiya Sakshya Adhiniyam (BSA), 2023",
        "title": "How much of information received from accused may be proved",
        "key_change": "Preserved recovery memo doctrine with emphasis on independent panchas and video verification.",
        "scope": "Confessional Discoveries"
    },
    "45": {
        "new_section": "39",
        "new_act": "Bharatiya Sakshya Adhiniyam (BSA), 2023",
        "title": "Opinions of experts",
        "key_change": "Expanded to digital forensics, cryptographic keys, cyber incident examiners, and audio-video biometric experts.",
        "scope": "Expert Evidence"
    },
    "32(1)": {
        "new_section": "26(a)",
        "new_act": "Bharatiya Sakshya Adhiniyam (BSA), 2023",
        "title": "Statements by person who cannot be found or is dead (Dying Declaration)",
        "key_change": "Clarified multi-media recording protocols for dying declarations.",
        "scope": "Hearsay Exception"
    }
}


def lookup_concordance(act_name: str, section_number: str) -> Optional[dict[str, Any]]:
    """Look up new corresponding statutory section for an old law citation."""
    act_clean = act_name.upper()
    sec_clean = section_number.strip().replace("Section", "").replace("Sec.", "").strip()

    if "IPC" in act_clean or "PENAL" in act_clean:
        match = IPC_TO_BNS.get(sec_clean)
        if match:
            return {"old_act": "Indian Penal Code, 1860", "old_section": sec_clean, **match}

    if "CRPC" in act_clean or "CRIMINAL PROCEDURE" in act_clean:
        match = CRPC_TO_BNSS.get(sec_clean)
        if match:
            return {"old_act": "Code of Criminal Procedure, 1973", "old_section": sec_clean, **match}

    if "EVIDENCE" in act_clean or "IEA" in act_clean:
        match = IEA_TO_BSA.get(sec_clean)
        if match:
            return {"old_act": "Indian Evidence Act, 1872", "old_section": sec_clean, **match}

    return None
