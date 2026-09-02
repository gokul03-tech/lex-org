import type { AnalysisModel } from '@/types/case-workspace';

export function buildCompleteBriefHtml(a: AnalysisModel): string {
  const esc = (s: string) =>
    (s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

  const court = a.courtChip.value || 'IN THE HIGH COURT OF JUDICATURE';
  const caseTitle = a.caseTitle.value || 'IN THE MATTER OF LEGAL ADVISORY';
  const petitioner = a.metadataTiles.find((t) => t.key === 'petitioner')?.field.value || 'APPLICANT / PETITIONER';
  const respondent = a.metadataTiles.find((t) => t.key === 'respondent')?.field.value || 'STATE / RESPONDENT';

  // 1. Metadata Tiles
  const metaRows = a.metadataTiles
    .map(
      (tile) => `
      <tr style="border-bottom:1px solid #e2e8f0">
        <td style="padding:6px 10px;font-weight:bold;width:35%;color:#334155;background:#f8fafc;font-size:10pt">${esc(tile.label)}</td>
        <td style="padding:6px 10px;font-size:10pt;color:#0f172a">${esc(tile.field.value || 'Unstated in record')}</td>
      </tr>`
    )
    .join('');

  // 2. Timeline
  const timelineRows = a.timeline
    .map(
      (t) => `
    <tr style="border-bottom:1px solid #e2e8f0">
      <td style="padding:6px 10px;font-weight:bold;width:120px;color:#1e293b;background:#f8fafc">${esc(t.date)}</td>
      <td style="padding:6px 10px;color:#334155">${esc(t.fact)}${t.page ? ` <span style="color:#64748b;font-size:9pt">(Source: p.${esc(t.page)})</span>` : ''}</td>
    </tr>`
    )
    .join('');

  // 3. Formulated Issues
  const issuesList = a.issues
    .map(
      (i, n) => `
    <li style="margin-bottom:10px;page-break-inside:avoid">
      <div style="font-weight:bold;color:#0f172a">Issue #${n + 1}: ${esc(i.text)}</div>
      ${i.evidence ? `<div style="margin-top:3px;padding:6px 10px;background:#f1f5f9;border-left:3px solid #6366f1;font-size:9.5pt;font-style:italic;color:#334155">"${esc(i.evidence)}" (p.${esc(i.page || '1')})</div>` : ''}
    </li>`
    )
    .join('');

  // 4. Statutes
  const statutesList = a.statutes
    .map(
      (s) => `
    <li style="margin-bottom:6px">
      <b>${esc(s.display)}</b>: ${esc(s.context || 'Statutory provision invoked in record')}
    </li>`
    )
    .join('');

  const articlesList = a.articles
    .map(
      (art) => `
    <li style="margin-bottom:6px">
      <b>${esc(art.display)}</b>: ${esc(art.context || `Constitutional provision (${art.act})`)}
    </li>`
    )
    .join('');

  // 5. Precedents
  const precedentsList = a.precedents
    .map(
      (p) => `
    <li style="margin-bottom:8px;page-break-inside:avoid">
      <span style="font-weight:bold;color:#0f172a">${esc(p.name)}</span> (${esc(p.citation)})
      ${p.summary ? `<div style="font-size:9.5pt;color:#475569;margin-top:2px">${esc(p.summary)}</div>` : ''}
    </li>`
    )
    .join('');

  // 6. Evidence Matrix
  const evidenceRows = a.evidence
    .map(
      (ev) => `
    <tr style="border-bottom:1px solid #e2e8f0">
      <td style="padding:6px 10px;font-weight:bold;color:#0f172a;width:30%">${esc(ev.label)}</td>
      <td style="padding:6px 10px;color:#334155">${esc(ev.detail)}</td>
      <td style="padding:6px 10px;width:15%;text-align:center">
        <span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:8.5pt;font-weight:bold;${ev.reliability === 'HIGH' ? 'background:#dcfce7;color:#166534;' : 'background:#ffe4e6;color:#9f1239;'}">
          ${esc(ev.reliability)}
        </span>
      </td>
    </tr>`
    )
    .join('');

  // 7. Counsel Submissions
  const submissionsA = a.submissionsA.items.map((it) => `<li style="margin-bottom:4px">${esc(it)}</li>`).join('');
  const submissionsB = a.submissionsB.items.map((it) => `<li style="margin-bottom:4px">${esc(it)}</li>`).join('');

  // 8. Strategic Roadmap
  const strengths = a.riskStrengths.items.map((it) => `<li style="margin-bottom:4px">${esc(it)}</li>`).join('');
  const gaps = a.riskGaps.items.map((it) => `<li style="margin-bottom:4px">${esc(it)}</li>`).join('');
  const actions = a.riskAction.items.map((it) => `<li style="margin-bottom:4px">${esc(it)}</li>`).join('');

  return `
  <!DOCTYPE html>
  <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">
  <head>
    <meta charset="utf-8">
    <title>Comprehensive Court Legal Brief - ${esc(caseTitle)}</title>
    <style>
      @page { size: A4; margin: 20mm 15mm 20mm 15mm; }
      body { font-family: 'Times New Roman', Georgia, serif; line-height: 1.5; color: #111; margin: 20px; font-size: 11pt; }
      h1, h2, h3 { text-align: center; text-transform: uppercase; margin: 0; }
      .header-box { text-align: center; margin-bottom: 20px; border-bottom: 2px solid #111; padding-bottom: 12px; }
      .cause-title { margin: 15px 0; padding: 12px; border: 1px solid #777; background: #fafafa; }
      .section-heading { font-size: 11.5pt; font-weight: bold; margin-top: 20px; margin-bottom: 8px; border-bottom: 1.5px solid #222; padding-bottom: 3px; text-transform: uppercase; page-break-after: avoid; }
      table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 10pt; }
      ol, ul { margin: 6px 0 10px 20px; padding: 0; }
      .grid-box { display: table; width: 100%; margin: 10px 0; }
      .grid-col { display: table-cell; width: 50%; vertical-align: top; padding: 6px; }
      .card-box { border: 1px solid #cbd5e1; padding: 10px; border-radius: 4px; background: #fff; }
      .verification { margin-top: 30px; padding: 12px; border: 1px solid #333; font-size: 10pt; page-break-inside: avoid; }
      .footer-note { font-size: 8.5pt; color: #64748b; margin-top: 25px; text-align: center; border-top: 1px solid #cbd5e1; padding-top: 8px; }
      @media print {
        body { margin: 0; }
        .no-print { display: none; }
      }
    </style>
  </head>
  <body>
    <div class="header-box">
      <h2 style="font-size:13pt;letter-spacing:0.5px">${esc(court)}</h2>
      <p style="margin:4px 0 0 0;font-size:10pt;letter-spacing:1px;font-weight:bold">APPELLATE &amp; ORIGINAL EXTRAORDINARY JURISDICTION</p>
      <p style="margin:3px 0 0 0;font-size:9pt;color:#555">TRUST INDEX: <b>${a.trustScore}%</b> • ZERO-HALLUCINATION MULTI-AGENT VERIFICATION</p>
    </div>

    <div class="cause-title">
      <p style="margin:0 0 4px 0;font-weight:bold;font-size:10pt">IN THE MATTER OF:</p>
      <table style="border:none;margin:0">
        <tr>
          <td style="border:none;vertical-align:top;width:70%;font-weight:bold;font-size:11pt">${esc(petitioner)}</td>
          <td style="border:none;text-align:right;vertical-align:top;font-size:10pt">...PETITIONER / APPLICANT</td>
        </tr>
        <tr>
          <td style="border:none;text-align:center;padding:6px 0;font-weight:bold;font-size:10pt" colspan="2">VERSUS</td>
        </tr>
        <tr>
          <td style="border:none;vertical-align:top;font-weight:bold;font-size:11pt">${esc(respondent)}</td>
          <td style="border:none;text-align:right;vertical-align:top;font-size:10pt">...RESPONDENTS</td>
        </tr>
      </table>
    </div>

    <!-- I. SYNOPSIS -->
    <div class="section-heading">I. EXECUTIVE ADVISORY SYNOPSIS</div>
    <p style="text-align:justify;margin:6px 0 12px 0">${esc(a.summary.value)}</p>

    <!-- II. GROUNDED METADATA MATRIX -->
    <div class="section-heading">II. GROUNDED CASE PARAMETERS &amp; METADATA MATRIX</div>
    <table>
      <tbody>${metaRows}</tbody>
    </table>

    <!-- III. TIMELINE -->
    ${timelineRows ? `
    <div class="section-heading">III. CHRONOLOGICAL LIST OF DATES AND CASE FACTS</div>
    <table>
      <thead>
        <tr style="background:#f1f5f9;border-bottom:1.5px solid #cbd5e1">
          <th style="padding:6px 10px;text-align:left;width:120px">Date</th>
          <th style="padding:6px 10px;text-align:left">Event / Record Finding</th>
        </tr>
      </thead>
      <tbody>${timelineRows}</tbody>
    </table>
    ` : ''}

    <!-- IV. LEGAL ISSUES -->
    ${issuesList ? `
    <div class="section-heading">IV. FORMULATED QUESTIONS OF LAW &amp; GROUNDED DETERMINATIONS</div>
    <ol>${issuesList}</ol>
    ` : ''}

    <!-- V. STATUTORY FRAMEWORK -->
    ${statutesList || articlesList ? `
    <div class="section-heading">V. APPLICABLE STATUTORY FRAMEWORK &amp; CONSTITUTIONAL ARTICLES</div>
    ${statutesList ? `<p style="margin:4px 0;font-weight:bold;font-size:10pt">Enacted Sections:</p><ul>${statutesList}</ul>` : ''}
    ${articlesList ? `<p style="margin:4px 0;font-weight:bold;font-size:10pt">Constitutional Articles:</p><ul>${articlesList}</ul>` : ''}
    ` : ''}

    <!-- VI. PRECEDENTS -->
    ${precedentsList ? `
    <div class="section-heading">VI. BINDING JUDICIAL PRECEDENTS &amp; AUTHORITIES</div>
    <ul>${precedentsList}</ul>
    ` : ''}

    <!-- VII. EVIDENCE MATRIX -->
    ${evidenceRows ? `
    <div class="section-heading">VII. EVIDENCE INTEGRITY &amp; RELIABILITY AUDIT</div>
    <table>
      <thead>
        <tr style="background:#f1f5f9;border-bottom:1.5px solid #cbd5e1">
          <th style="padding:6px 10px;text-align:left">Evidence Item / Exhibit</th>
          <th style="padding:6px 10px;text-align:left">Detail / Finding</th>
          <th style="padding:6px 10px;text-align:center">Reliability</th>
        </tr>
      </thead>
      <tbody>${evidenceRows}</tbody>
    </table>
    ` : ''}

    <!-- VIII. COUNSEL SUBMISSIONS -->
    ${submissionsA || submissionsB ? `
    <div class="section-heading">VIII. COUNSEL SUBMISSIONS ON RECORD</div>
    <table style="border:none">
      <tr>
        <td style="border:none;vertical-align:top;width:50%;padding-right:8px">
          <div class="card-box" style="border-top:3px solid #f43f5e">
            <b style="color:#9f1239">${esc(a.submissionsA.heading)}</b>
            <ul>${submissionsA || '<li>No specific submissions recorded.</li>'}</ul>
          </div>
        </td>
        <td style="border:none;vertical-align:top;width:50%;padding-left:8px">
          <div class="card-box" style="border-top:3px solid #6366f1">
            <b style="color:#4338ca">${esc(a.submissionsB.heading)}</b>
            <ul>${submissionsB || '<li>No specific submissions recorded.</li>'}</ul>
          </div>
        </td>
      </tr>
    </table>
    ` : ''}

    <!-- IX. IRAC OPINION -->
    <div class="section-heading">IX. IRAC LEGAL OPINION &amp; OPERATIVE CONCLUSION</div>
    <div style="margin:8px 0;padding:10px;background:#f8fafc;border-left:4px solid #4f46e5">
      <p style="margin:0 0 6px 0"><b>Operative Finding:</b> ${esc(a.conclusion.value)}</p>
      <p style="margin:0;font-size:9.5pt;color:#64748b">Confidence Score: ${a.trustScore}% • Calibrated against statutory provisions.</p>
    </div>

    <!-- X. STRATEGIC ROADMAP -->
    <div class="section-heading">X. STRATEGIC ROADMAP &amp; ADVERSARIAL ACTION PLAN</div>
    <table style="border:none">
      <tr>
        <td style="border:none;vertical-align:top;width:33%;padding:4px">
          <div class="card-box" style="border-top:3px solid #10b981">
            <b style="color:#065f46">Key Strengths</b>
            <ul>${strengths || '<li>None recorded.</li>'}</ul>
          </div>
        </td>
        <td style="border:none;vertical-align:top;width:33%;padding:4px">
          <div class="card-box" style="border-top:3px solid #f59e0b">
            <b style="color:#92400e">Potential Gaps</b>
            <ul>${gaps || '<li>None recorded.</li>'}</ul>
          </div>
        </td>
        <td style="border:none;vertical-align:top;width:33%;padding:4px">
          <div class="card-box" style="border-top:3px solid #0ea5e9">
            <b style="color:#0369a1">Action Plan</b>
            <ul>${actions || '<li>None recorded.</li>'}</ul>
          </div>
        </td>
      </tr>
    </table>

    <!-- VERIFICATION -->
    <div class="verification">
      <p style="margin:0 0 6px 0;font-weight:bold">VERIFICATION CLAUSE</p>
      <p style="margin:0;text-align:justify">
        Verified at New Delhi on this day that the contents of the above comprehensive case advisory brief are true and correct to the best of my knowledge derived from the physical record, applicable statutory enactments, and grounded judicial databases.
      </p>
      <table style="border:none;width:100%;margin-top:20px">
        <tr>
          <td style="border:none;text-align:left;width:50%"><b>Date:</b> ${new Date().toLocaleDateString('en-GB')}</td>
          <td style="border:none;text-align:right;width:50%"><b>ADVOCATE FOR PETITIONER / APPLICANT</b></td>
        </tr>
      </table>
    </div>

    <div class="footer-note">
      Synthesized by <b>LexOrch-KG</b> (Trust Index: <b>${a.trustScore}%</b>) • Complete All-Pages Legal Dossier • BGE-M3 Dense Vectors + FalkorDB Knowledge Graph Grounded
    </div>
  </body>
  </html>`;
}

export function exportPdf(analysis: AnalysisModel, caseId: string) {
  const html = buildCompleteBriefHtml(analysis);
  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    alert('Please allow popups to download and print the complete PDF dossier.');
    return;
  }
  printWindow.document.open();
  printWindow.document.write(html);
  printWindow.document.close();
  printWindow.focus();
  setTimeout(() => {
    printWindow.print();
  }, 350);
}

export function exportDocx(analysis: AnalysisModel, caseId: string) {
  const html = buildCompleteBriefHtml(analysis);
  const blob = new Blob(['\ufeff', html], { type: 'application/msword' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Court_Brief_${caseId}.doc`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
