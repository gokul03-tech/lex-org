import type { AnalysisModel } from '@/types/case-workspace';

export function exportJson(raw: unknown, caseId: string) {
  const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(JSON.stringify(raw ?? {}, null, 2))}`;
  const a = document.createElement('a');
  a.setAttribute('href', jsonString);
  a.setAttribute('download', `LexOrch_Analysis_${caseId}.json`);
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function docHtml(a: AnalysisModel): string {
  const esc = (s: string) =>
    (s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

  const court = a.courtChip.value || 'IN THE HIGH COURT OF JUDICATURE';
  const caseTitle = a.caseTitle.value || 'IN THE MATTER OF LEGAL ADVISORY';
  const petitioner = a.metadataTiles.find((t) => t.key === 'petitioner')?.field.value || 'APPLICANT / PETITIONER';
  const respondent = a.metadataTiles.find((t) => t.key === 'respondent')?.field.value || 'STATE / RESPONDENT';

  const statutes = a.statutes.map((s) => `<li><b>${esc(s.display)}</b>: ${esc(s.context || 'Statutory mandate invoked')}</li>`).join('');
  const precedents = a.precedents.map((p) => `<li><b>${esc(p.name)}</b> (${esc(p.citation)})<br/><span style="color:#444">${esc(p.summary || '')}</span></li>`).join('');
  const issues = a.issues.map((i, n) => `<li style="margin-bottom:8px"><b>Issue ${n + 1}:</b> ${esc(i.text)}${i.evidence ? `<br/><i style="color:#555;font-size:10pt">Document Quote: "${esc(i.evidence)}" (p.${i.page || '1'})</i>` : ''}</li>`).join('');

  const timelineRows = a.timeline.map((t) => `
    <tr>
      <td style="padding:6px 12px;border:1px solid #ccc;font-weight:bold;width:120px">${esc(t.date)}</td>
      <td style="padding:6px 12px;border:1px solid #ccc">${esc(t.fact)}${t.page ? ` <span style="color:#777">(p.${esc(t.page)})</span>` : ''}</td>
    </tr>
  `).join('');

  return `
  <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">
  <head>
    <meta charset="utf-8">
    <title>Court Legal Brief - ${esc(caseTitle)}</title>
    <style>
      body { font-family: 'Times New Roman', Georgia, serif; line-height: 1.6; color: #111; margin: 40px; }
      h1, h2, h3 { text-align: center; text-transform: uppercase; }
      .header-box { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #222; padding-bottom: 15px; }
      .cause-title { margin: 25px 0; padding: 15px; border: 1px solid #999; background: #fdfdfd; }
      .section-heading { font-size: 13pt; font-weight: bold; margin-top: 25px; border-bottom: 1px solid #333; padding-bottom: 4px; text-transform: uppercase; }
      table { width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 11pt; }
      .verification { margin-top: 40px; padding: 15px; border: 1px solid #444; font-size: 10.5pt; }
      .footer-note { font-size: 9pt; color: #666; margin-top: 30px; text-align: center; border-top: 1px solid #ccc; padding-top: 10px; }
    </style>
  </head>
  <body>
    <div class="header-box">
      <h2 style="margin:0;font-size:14pt">${esc(court)}</h2>
      <p style="margin:5px 0 0 0;font-size:11pt;letter-spacing:1px">APPELLATE / ORIGINAL EXTRAORDINARY JURISDICTION</p>
    </div>

    <div class="cause-title">
      <p style="margin:0 0 5px 0;font-weight:bold">IN THE MATTER OF:</p>
      <table style="border:none;margin:0">
        <tr>
          <td style="border:none;vertical-align:top;width:70%"><b>${esc(petitioner)}</b></td>
          <td style="border:none;text-align:right;vertical-align:top">...PETITIONER / APPLICANT</td>
        </tr>
        <tr>
          <td style="border:none;text-align:center;padding:10px 0;font-weight:bold" colspan="2">VERSUS</td>
        </tr>
        <tr>
          <td style="border:none;vertical-align:top"><b>${esc(respondent)}</b></td>
          <td style="border:none;text-align:right;vertical-align:top">...RESPONDENTS</td>
        </tr>
      </table>
    </div>

    <div class="section-heading">I. SYNOPSIS AND SUMMARY OF CASE FACTS</div>
    <p style="text-align:justify;font-size:11pt">${esc(a.summary.value)}</p>

    ${timelineRows ? `
    <div class="section-heading">II. CHRONOLOGICAL LIST OF DATES AND EVENTS</div>
    <table>
      <thead>
        <tr style="background:#eee">
          <th style="padding:6px 12px;border:1px solid #ccc;text-align:left">Date</th>
          <th style="padding:6px 12px;border:1px solid #ccc;text-align:left">Event / Record Finding</th>
        </tr>
      </thead>
      <tbody>${timelineRows}</tbody>
    </table>
    ` : ''}

    ${issues ? `
    <div class="section-heading">III. QUESTIONS OF LAW &amp; SUBSTANTIAL ISSUES</div>
    <ol style="font-size:11pt">${issues}</ol>
    ` : ''}

    ${statutes ? `
    <div class="section-heading">IV. APPLICABLE STATUTORY PROVISIONS &amp; CODES</div>
    <ul style="font-size:11pt">${statutes}</ul>
    ` : ''}

    ${precedents ? `
    <div class="section-heading">V. BINDING JUDICIAL PRECEDENTS &amp; AUTHORITIES</div>
    <ul style="font-size:11pt">${precedents}</ul>
    ` : ''}

    <div class="section-heading">VI. OPERATIVE CONCLUSION &amp; PRAYER</div>
    <p style="text-align:justify;font-size:11pt">${esc(a.conclusion.value)}</p>

    <div class="verification">
      <p style="margin:0 0 10px 0;font-weight:bold;text-transform:uppercase">VERIFICATION CLAUSE</p>
      <p style="margin:0;text-align:justify">
        Verified at New Delhi on this day that the contents of the above legal advisory brief are true and correct to the best of my knowledge derived from the case records, statutory enactments, and grounded judicial databases. Nothing material has been concealed therefrom.
      </p>
      <br/><br/>
      <table style="border:none;width:100%">
        <tr>
          <td style="border:none;text-align:left;width:50%"><b>Date:</b> ${new Date().toLocaleDateString('en-GB')}</td>
          <td style="border:none;text-align:right;width:50%"><b>ADVOCATE FOR PETITIONER / APPLICANT</b></td>
        </tr>
      </table>
    </div>

    <div class="footer-note">
      Synthesized by <b>LexOrch-KG</b> (Trust Index: <b>${a.trustScore}%</b>) • Zero-Hallucination Multi-Agent Verification • BGE-M3 / Qdrant / FalkorDB Graph Grounded
    </div>
  </body>
  </html>`;
}

export function exportDocx(analysis: AnalysisModel, caseId: string) {
  const blob = new Blob(['\ufeff', docHtml(analysis)], { type: 'application/msword' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Court_Brief_${caseId}.doc`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
