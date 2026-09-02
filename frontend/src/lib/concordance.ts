export interface ConcordanceItem {
  old_act: string;
  old_section: string;
  new_act: string;
  new_section: string;
  title: string;
  key_change: string;
  bailable?: string;
  cognizable?: string;
  forum?: string;
  scope?: string;
}

export const CONCORDANCE_MAP: Record<string, Record<string, ConcordanceItem>> = {
  IPC: {
    '420': {
      old_act: 'Indian Penal Code, 1860',
      old_section: '420',
      new_act: 'Bharatiya Nyaya Sanhita (BNS), 2023',
      new_section: '318(4)',
      title: 'Cheating and dishonestly inducing delivery of property',
      key_change: 'Amalgamated cheating provisions; enhanced penalty for organized digital cyber fraud.',
      bailable: 'Non-bailable',
      cognizable: 'Cognizable',
    },
    '406': {
      old_act: 'Indian Penal Code, 1860',
      old_section: '406',
      new_act: 'Bharatiya Nyaya Sanhita (BNS), 2023',
      new_section: '316',
      title: 'Criminal breach of trust',
      key_change: 'Explicit inclusion of digital asset & escrow misappropriation.',
      bailable: 'Non-bailable',
      cognizable: 'Cognizable',
    },
    '302': {
      old_act: 'Indian Penal Code, 1860',
      old_section: '302',
      new_act: 'Bharatiya Nyaya Sanhita (BNS), 2023',
      new_section: '103(1)',
      title: 'Punishment for murder',
      key_change: 'Introduction of Section 103(2) for mob lynching with separate sentencing.',
      bailable: 'Non-bailable',
      cognizable: 'Cognizable',
    },
    '307': {
      old_act: 'Indian Penal Code, 1860',
      old_section: '307',
      new_act: 'Bharatiya Nyaya Sanhita (BNS), 2023',
      new_section: '109',
      title: 'Attempt to murder',
      key_change: 'Restructured attempt hierarchy with life imprisonment terms.',
      bailable: 'Non-bailable',
      cognizable: 'Cognizable',
    },
    '120B': {
      old_act: 'Indian Penal Code, 1860',
      old_section: '120B',
      new_act: 'Bharatiya Nyaya Sanhita (BNS), 2023',
      new_section: '61(2)',
      title: 'Criminal conspiracy',
      key_change: 'Clarified conspiratorial agreement across electronic networks.',
    },
    '498A': {
      old_act: 'Indian Penal Code, 1860',
      old_section: '498A',
      new_act: 'Bharatiya Nyaya Sanhita (BNS), 2023',
      new_section: '85 / 86',
      title: 'Cruelty by husband or relatives of husband',
      key_change: 'Cruelty defined explicitly under Section 86 with psychological harm thresholds.',
    },
    '124A': {
      old_act: 'Indian Penal Code, 1860',
      old_section: '124A',
      new_act: 'Bharatiya Nyaya Sanhita (BNS), 2023',
      new_section: '152',
      title: 'Acts endangering sovereignty, unity and integrity of India',
      key_change: 'Colonial sedition replaced by targeted sovereignty protections.',
    },
    '379': {
      old_act: 'Indian Penal Code, 1860',
      old_section: '379',
      new_act: 'Bharatiya Nyaya Sanhita (BNS), 2023',
      new_section: '303(2)',
      title: 'Punishment for theft',
      key_change: 'Community service introduced for first-time petty theft under ₹5,000.',
    },
    '34': {
      old_act: 'Indian Penal Code, 1860',
      old_section: '34',
      new_act: 'Bharatiya Nyaya Sanhita (BNS), 2023',
      new_section: '3(5)',
      title: 'Acts done by several persons in furtherance of common intention',
      key_change: 'Preserved core doctrine of joint vicarious liability.',
    },
  },
  CRPC: {
    '439': {
      old_act: 'Code of Criminal Procedure, 1973',
      old_section: '439',
      new_act: 'Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023',
      new_section: '483',
      title: 'Special powers of High Court / Sessions regarding bail',
      key_change: 'Explicit hearing timelines; mandatory digital notices to victim/informant.',
      forum: 'High Court / Sessions Court',
    },
    '438': {
      old_act: 'Code of Criminal Procedure, 1973',
      old_section: '438',
      new_act: 'Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023',
      new_section: '482',
      title: 'Anticipatory Bail (Apprehension of arrest)',
      key_change: 'High Court and Sessions concurrent jurisdiction preserved with structured compliance.',
      forum: 'High Court / Sessions Court',
    },
    '437': {
      old_act: 'Code of Criminal Procedure, 1973',
      old_section: '437',
      new_act: 'Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023',
      new_section: '480',
      title: 'Bail in non-bailable offences by Magistrate',
      key_change: 'Relaxed bail norms for undertrials completing one-third of sentence.',
      forum: 'Magistrate Court',
    },
    '482': {
      old_act: 'Code of Criminal Procedure, 1973',
      old_section: '482',
      new_act: 'Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023',
      new_section: '528',
      title: 'Inherent powers of High Court',
      key_change: 'Unchanged scope for quashing FIRs and preventing abuse of legal process.',
      forum: 'High Court',
    },
    '167': {
      old_act: 'Code of Criminal Procedure, 1973',
      old_section: '167',
      new_act: 'Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023',
      new_section: '187',
      title: 'Custody procedure during investigation',
      key_change: '15-day police custody can now be staggered across first 40/60 days.',
      forum: 'Magistrate Court',
    },
    '41A': {
      old_act: 'Code of Criminal Procedure, 1973',
      old_section: '41A',
      new_act: 'Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023',
      new_section: '35(3)',
      title: 'Notice of appearance before police officer',
      key_change: 'Prior sanction from DSP rank required before arresting persons for offences < 3 years.',
    },
    '154': {
      old_act: 'Code of Criminal Procedure, 1973',
      old_section: '154',
      new_act: 'Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023',
      new_section: '173',
      title: 'Information in cognizable cases (FIR / e-FIR)',
      key_change: 'Mandatory acceptance of Zero-FIR and electronic FIR with 3-day verification protocol.',
    },
    '164': {
      old_act: 'Code of Criminal Procedure, 1973',
      old_section: '164',
      new_act: 'Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023',
      new_section: '183',
      title: 'Recording of confessions and statements',
      key_change: 'Mandatory audio-video electronic recording of victim and witness statements.',
    },
  },
  IEA: {
    '65B': {
      old_act: 'Indian Evidence Act, 1872',
      old_section: '65B',
      new_act: 'Bharatiya Sakshya Adhiniyam (BSA), 2023',
      new_section: '63',
      title: 'Admissibility of electronic records and mandatory certification',
      key_change: 'Harmonized certificate schedule; electronic signatures and hash validation explicitly codified.',
      scope: 'Electronic Evidence',
    },
    '27': {
      old_act: 'Indian Evidence Act, 1872',
      old_section: '27',
      new_act: 'Bharatiya Sakshya Adhiniyam (BSA), 2023',
      new_section: '23',
      title: 'Information received from accused in custody (Discovery)',
      key_change: 'Preserved discovery doctrine with video verification of panchanama recoveries.',
      scope: 'Recovery Memo',
    },
    '45': {
      old_act: 'Indian Evidence Act, 1872',
      old_section: '45',
      new_act: 'Bharatiya Sakshya Adhiniyam (BSA), 2023',
      new_section: '39',
      title: 'Opinions of experts',
      key_change: 'Expanded to digital forensics, cryptographic keys, cyber incident examiners, and audio-video biometric experts.',
    },
    '32(1)': {
      old_act: 'Indian Evidence Act, 1872',
      old_section: '32(1)',
      new_act: 'Bharatiya Sakshya Adhiniyam (BSA), 2023',
      new_section: '26(a)',
      title: 'Statements by person who cannot be found / dead (Dying Declaration)',
      key_change: 'Clarified multi-media recording protocols for dying declarations.',
    },
  },
};

export function findConcordance(actName?: string | null, sectionNumber?: string | null): ConcordanceItem | null {
  if (!sectionNumber) return null;
  const act = (actName || '').toUpperCase();
  const sec = sectionNumber.replace(/Section|Sec\.?|u\/s/gi, '').trim();

  if (act.includes('IPC') || act.includes('PENAL')) {
    return CONCORDANCE_MAP.IPC[sec] ?? null;
  }
  if (act.includes('CRPC') || act.includes('CRIMINAL PROCEDURE')) {
    return CONCORDANCE_MAP.CRPC[sec] ?? null;
  }
  if (act.includes('EVIDENCE') || act.includes('IEA')) {
    return CONCORDANCE_MAP.IEA[sec] ?? null;
  }

  // Cross check if section exists uniquely in any map
  if (CONCORDANCE_MAP.IPC[sec]) return CONCORDANCE_MAP.IPC[sec];
  if (CONCORDANCE_MAP.CRPC[sec]) return CONCORDANCE_MAP.CRPC[sec];
  if (CONCORDANCE_MAP.IEA[sec]) return CONCORDANCE_MAP.IEA[sec];

  return null;
}
