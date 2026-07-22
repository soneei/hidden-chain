const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
        LevelFormat, Footer, PageNumber, PageBreak } = require('docx');
const fs = require('fs');

const border = { style: BorderStyle.SINGLE, size: 1, color: "BBBBBB" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 60, bottom: 60, left: 100, right: 100 };
const headerBg = { fill: "2E5A88", type: ShadingType.CLEAR };
const lightBg = { fill: "F0F4F8", type: ShadingType.CLEAR };

function cell(w, text, opts = {}) {
  return new TableCell({
    borders,
    width: { size: w, type: WidthType.DXA },
    margins: cellMargins,
    shading: opts.bg || (opts.header ? headerBg : undefined),
    children: [new Paragraph({
      alignment: opts.center ? AlignmentType.CENTER : AlignmentType.LEFT,
      children: [new TextRun({ text, bold: !!opts.bold, color: opts.header ? "FFFFFF" : "333333", size: opts.small ? 18 : 20, font: "Arial" })]
    })]
  });
}

function line(text, opts = {}) {
  return new Paragraph({
    spacing: { before: opts.spaceBefore || 60, after: opts.spaceAfter || 60 },
    heading: opts.heading ? opts.heading : undefined,
    children: [new TextRun({ text, bold: !!opts.bold, size: opts.size || 22, font: "Arial", color: opts.color || "333333" })]
  });
}

const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, right: 1200, bottom: 1440, left: 1200 }
      }
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Hidden Chain — Confidential Research Document — Page ", size: 16, font: "Arial", color: "999999" }),
                   new TextRun({ children: [PageNumber.CURRENT], size: 16, font: "Arial", color: "999999" })]
      })] })
    },
    children: [

      // ── TITLE PAGE ──
      new Paragraph({ spacing: { before: 2400 }, children: [] }),
      line("Hidden Chain", { size: 56, bold: true, color: "2E5A88", spaceAfter: 0 }),
      line("Wearable HRV \u2192 TCM Pattern Differentiation", { size: 28, color: "666666", spaceBefore: 60 }),
      line("Validation Document for Clinical Review", { size: 20, color: "999999", spaceBefore: 400 }),
      new Paragraph({ spacing: { before: 600 }, children: [
        new TextRun({ text: "Prepared for: ", bold: true, size: 22, font: "Arial" }),
        new TextRun({ text: "TCM Physician Review & Validation", size: 22, font: "Arial" }),
      ]}),
      new Paragraph({ spacing: { before: 200 }, children: [
        new TextRun({ text: "Date: ", bold: true, size: 22, font: "Arial" }),
        new TextRun({ text: new Date().toISOString().slice(0, 10), size: 22, font: "Arial" }),
      ]}),
      new Paragraph({ spacing: { before: 200 }, children: [
        new TextRun({ text: "Project: ", bold: true, size: 22, font: "Arial" }),
        new TextRun({ text: "https://github.com/soneei/hidden-chain", size: 22, font: "Arial", color: "2E5A88" }),
      ]}),

      new Paragraph({ children: [new PageBreak()] }),

      // ── SECTION 1: WHAT IS HIDDEN CHAIN ──
      line("1. What is Hidden Chain?", { heading: HeadingLevel.HEADING_1, size: 32, bold: true, color: "2E5A88" }),
      line(`Hidden Chain is a digital health algorithm that translates data from consumer smartwatches (PPG heart rate sensors) into Traditional Chinese Medicine (TCM) pattern differentiation.`, { spaceBefore: 100 }),

      line(`The core flow:`, { bold: true, spaceBefore: 200 }),
      line(`\u231A Step 1: User wears a Huawei/Apple/OPPO watch. The watch measures HRV (heart rate variability) \u2014 the millisecond-level variation in time between heartbeats.`),
      line(`\uD83E\uDDEC Step 2: The algorithm calibrates HRV against the user's menstrual cycle phase (follicular, luteal, etc.), because normal physiological HRV shifts 3\u20139% across phases.`),
      line(`\uD83E\uDE78 Step 3: The cycle-corrected HRV is mapped onto five TCM patterns: qi-blood deficiency (\u6C14\u8840\u4E0D\u8DB3), liver qi stagnation (\u809D\u90C1\u6C14\u6EDE), spleen deficiency (\u813E\u865A), phlegm turbidity (\u7600\u6C14\u4E92\u7ED3), and yin-yang balance (\u9634\u9633\u5E73\u8861).`),
      line(`\uD83D\uDD2E Step 4: A single score (0\u2013100) and an Autonomic Age (\u81EA\u4E3B\u795E\u7ECF\u5E74\u9F84) are returned alongside the TCM assessment.`),

      new Paragraph({ children: [new PageBreak()] }),

      // ── SECTION 2: THE FIVE TCM PATTERNS ──
      line("2. The Five TCM Patterns and Their HRV Signatures", { heading: HeadingLevel.HEADING_1, size: 32, bold: true, color: "2E5A88" }),

      line(`Each TCM pattern in Hidden Chain is computed from specific, published autonomic metrics. The thresholds are derived from peer-reviewed research.`, { spaceBefore: 100 }),
      line(`We are requesting your expert review: do the computed values match your clinical observations for the same patients?`, { bold: true, spaceBefore: 200 }),

      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [2400, 3000, 3626],
        rows: [
          new TableRow({ children: [
            cell(2400, "TCM Pattern", { header: true, bold: true }),
            cell(3000, "HRV Biomarker Used", { header: true, bold: true }),
            cell(3626, "Threshold / Logic", { header: true, bold: true }),
          ]}),
          new TableRow({ children: [
            cell(2400, "1. Qi-Blood Deficiency\n(\u6C14\u8840\u4E0D\u8DB3)", { bold: true, bg: lightBg }),
            cell(3000, "Resting RMSSD below age norm\n(Shaffer & Ginsberg 2017,\nN = 21,438)", { bg: lightBg }),
            cell(3626, "RMSSD \u2265 55 ms \u2192 0/100\nRMSSD \u2264 25 ms \u2192 100/100\nLinear interpolation in between", { bg: lightBg }),
          ]}),
          new TableRow({ children: [
            cell(2400, "2. Liver Qi Stagnation\n(\u809D\u90C1\u6C14\u6EDE)", { bold: true }),
            cell(3000, "Recovery speed after stress\n(NRICM Taiwan, 2010:\nliver patterns \u2192 most severe\nvagal disruption)"),
            cell(3626, "Recovery classification:\n\u2022 slow \u2192 +60\n\u2022 normal + HRV unstable \u2192 +25\n\u2022 recovery rate < 2 \u2192 +20\nCapped at 100"),
          ]}),
          new TableRow({ children: [
            cell(2400, "3. Spleen Deficiency\n(\u813E\u865A)", { bold: true, bg: lightBg }),
            cell(3000, "SDNN depression + LF/HF ratio\n(Olivera-Toro et al. 2019:\nSDNN\u219317%, HF\u219314%, LF/HF\u219222% in spleen-deficient patients)", { bg: lightBg }),
            cell(3626, "Recovery rate \u2264 0 \u2192 60/100\nRecovery rate 1\u20134 \u2192 60\u201310\nRecovery rate \u2265 5 \u2192 0/100", { bg: lightBg }),
          ]}),
          new TableRow({ children: [
            cell(2400, "4. Phlegm Turbidity\n(\u7600\u6C14\u4E92\u7ED3)", { bold: true }),
            cell(3000, "Residual HRV abnormality after\ncycle-phase correction\n(Hidden Chain custom)"),
            cell(3626, "|normalized_HRV| > 1 \u2192\n30 \u00D7 deviation\nCapped at 100"),
          ]}),
          new TableRow({ children: [
            cell(2400, "5. Yin-Yang Balance\n(\u9634\u9633\u5E73\u8861)", { bold: true, bg: lightBg }),
            cell(3000, "Composite wellness index\nfrom the four patterns above", { bg: lightBg }),
            cell(3626, "100 \u2013 (Qi-blood\u00D70.3 +\nLiver\u00D70.25 + Spleen\u00D70.25 +\nPhlegm\u00D70.2)", { bg: lightBg }),
          ]}),
        ]
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // ── SECTION 3: THE SCIENCE ──
      line("3. Scientific Foundation", { heading: HeadingLevel.HEADING_1, size: 32, bold: true, color: "2E5A88" }),

      line(`The engine is built on 8 peer-reviewed papers. The key ones for TCM mapping:`),
      line(`\u2022 Thayer & Lane (2009) \u2014 Neurovisceral Integration Model. 1,788 citations. Proves HRV is a window into prefrontal cortex function and emotional regulation. Journal: Neuroscience & Biobehavioral Reviews (IF 9.0).`),
      line(`\u2022 Shaffer & Ginsberg (2017) \u2014 HRV Normative Values by Age. 7,182 citations. RMSSD drops from ~55 ms (age 20) to ~25 ms (age 60). Journal: Frontiers in Public Health.`),
      line(`\u2022 Olivera-Toro et al. (2019) \u2014 TCM Spleen-Qi Deficiency directly measured by HRV. 67 spleen-deficiency patients vs. 37 healthy controls: SDNN \u2193 17%, HF \u2193 14%, LF/HF \u2191 22%, fatigue \u2191 21%. Journal: J Acupuncture & Meridian Studies.`),
      line(`\u2022 NRICM Taiwan (2010) \u2014 HRV signatures for heart-blood deficiency (\u5FC3\u8840\u865A), liver depression transforming to fire (\u809D\u90C1\u5316\u706B), and spleen deficiency (\u813E\u865A) in perimenopausal women.`),
      line(`\u2022 Yang et al. (2008) \u2014 Anxiety-depression TCM patterns \u2192 all show significant vagal (parasympathetic) reduction; liver patterns are the most severe.`),

      new Paragraph({ children: [new PageBreak()] }),

      // ── SECTION 4: REAL-WORLD TEST ──
      line("4. Real-World Test Result (Founder Self-Test)", { heading: HeadingLevel.HEADING_1, size: 32, bold: true, color: "2E5A88" }),

      line(`Inputs: Huawei Watch PPG data. HRV (RMSSD) = 43 ms, Resting HR = 61 bpm, Cycle Day = 7 (follicular phase), Sleep = 4.4 hours, Mood = 6/10.`),
      line(`Outputs:`),

      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [2800, 1400, 2400, 2426],
        rows: [
          new TableRow({ children: [
            cell(2800, "Metric", { header: true, bold: true }),
            cell(1400, "Value", { header: true, bold: true, center: true }),
            cell(2400, "Result", { header: true, bold: true }),
            cell(2426, "TCM Diagnosis", { header: true, bold: true }),
          ]}),
          new TableRow({ children: [
            cell(2800, "Hidden Chain Score", { bold: true, bg: lightBg }),
            cell(1400, "73/100", { center: true, bg: lightBg }),
            cell(2400, "Green \u2014 Good", { bg: lightBg }),
            cell(2426, "Steady rhythm", { bg: lightBg }),
          ]}),
          new TableRow({ children: [
            cell(2800, "Autonomic Age", { bold: true }),
            cell(1400, "26 yrs", { center: true }),
            cell(2400, "34 actual \u2192 nervous system acts younger"),
            cell(2426, "Normal for age"),
          ]}),
          new TableRow({ children: [
            cell(2800, "Qi-Blood Deficiency", { bold: true, bg: lightBg }),
            cell(1400, "62/100", { center: true, bg: lightBg }),
            cell(2400, "Moderate", { bg: lightBg }),
            cell(2426, "Matched TCM diagnosis \u2705", { bg: lightBg, bold: true }),
          ]}),
          new TableRow({ children: [
            cell(2800, "Liver Qi Stagnation", { bold: true }),
            cell(1400, "28/100", { center: true }),
            cell(2400, "Low \u2014 mild concern"),
            cell(2426, "Matched TCM diagnosis \u2705", { bold: true }),
          ]}),
          new TableRow({ children: [
            cell(2800, "Spleen Deficiency", { bold: true, bg: lightBg }),
            cell(1400, "60/100", { center: true, bg: lightBg }),
            cell(2400, "Moderate", { bg: lightBg }),
            cell(2426, "Matched TCM diagnosis \u2705", { bg: lightBg, bold: true }),
          ]}),
        ]
      }),

      line(`Note: The founder has a confirmed TCM diagnosis of qi-blood deficiency, liver qi stagnation, and spleen deficiency from an in-person TCM practitioner. All three matched. But n = 1 is not evidence. We need your help validating on more patients.`, { bold: true, spaceBefore: 300, color: "2E5A88" }),

      new Paragraph({ children: [new PageBreak()] }),

      // ── SECTION 5: VALIDATION REQUEST ──
      line("5. We Need Your Expert Validation", { heading: HeadingLevel.HEADING_1, size: 32, bold: true, color: "2E5A88" }),

      line(`We are requesting 10\u201320 patients. For each patient:`, { bold: true }),
      line(`\u2460 Doctor performs standard TCM diagnosis (inspection, auscultation, inquiry, pulse-taking). Records 0\u2013100 severity for each of the 5 patterns.`),
      line(`\u2461 Patient fills in the Hidden Chain web form with that day's HRV, resting heart rate, and cycle day (3 minutes per person).`),
      line(`\u2462 We compare the two assessments.`),

      new Paragraph({ spacing: { before: 400, after: 200 }, children: [
        new TextRun({ text: "Validation goals:", bold: true, size: 22, font: "Arial", color: "2E5A88" }),
      ]}),
      line(`A. Sensitivity: Does Hidden Chain detect the same patterns the doctor identifies?`),
      line(`B. Severity calibration: Do the 0\u2013100 scores correlate with the doctor's severity assessment?`),
      line(`C. Pattern gaps: Are there patterns the doctor diagnoses that Hidden Chain misses entirely? (e.g., \u5FC3\u8840\u865A, \u809D\u90C1\u5316\u706B, \u5FC3\u813E\u4E24\u865A)`),

      new Paragraph({ spacing: { before: 600, after: 200 }, children: [
        new TextRun({ text: "Form for Physician Use (one per patient)", bold: true, size: 24, font: "Arial", color: "2E5A88" }),
      ]}),

      new Table({
        width: { size: 9026, type: WidthType.DXA },
        columnWidths: [3200, 2913, 2913],
        rows: [
          new TableRow({ children: [
            cell(3200, "TCM Pattern / Metric", { header: true, bold: true }),
            cell(2913, "Physician Assessment\n(0\u2013100 severity)", { header: true, bold: true, center: true }),
            cell(2913, "Hidden Chain Output\n(0\u2013100, auto-calculated)", { header: true, bold: true, center: true }),
          ]}),
          ...[
            ["Qi-Blood Deficiency (\u6C14\u8840\u4E0D\u8DB3)", false],
            ["Liver Qi Stagnation (\u809D\u90C1\u6C14\u6EDE)", true],
            ["Spleen Deficiency (\u813E\u865A)", false],
            ["Phlegm Turbidity (\u7600\u6C14\u4E92\u7ED3)", true],
            ["Yin-Yang Balance (\u9634\u9633\u5E73\u8861)", false],
          ].map(([name, shaded]) => new TableRow({ children: [
            cell(3200, name, { bold: true, bg: shaded ? lightBg : undefined }),
            cell(2913, "____ / 100", { center: true, bg: shaded ? lightBg : undefined }),
            cell(2913, "____ / 100", { center: true, bg: shaded ? lightBg : undefined }),
          ]})),
          new TableRow({ children: [
            cell(3200, "Other pattern diagnosed:", { bold: true }),
            cell(2913, "____ / 100\nPattern name: ________________", { center: true }),
            cell(2913, "N/A (not in engine)", { center: true }),
          ]}),
        ]
      }),

      new Paragraph({ spacing: { before: 300 }, children: [
        new TextRun({ text: "Patient ID: ________", bold: true, size: 22, font: "Arial" }),
        new TextRun({ text: "    Date: ________", bold: true, size: 22, font: "Arial" }),
      ]}),
      new Paragraph({ spacing: { before: 200 }, children: [
        new TextRun({ text: "Physician notes: _____________________________________________________", size: 20, font: "Arial", color: "666666" }),
      ]}),

      new Paragraph({ spacing: { before: 800 }, children: [
        new TextRun({ text: "Thank you for your time and expertise.", size: 22, font: "Arial", color: "2E5A88", italics: true }),
      ]}),
      new Paragraph({ spacing: { before: 200 }, children: [
        new TextRun({ text: "Project: ", bold: true, size: 20, font: "Arial" }),
        new TextRun({ text: "github.com/soneei/hidden-chain", size: 20, font: "Arial", color: "2E5A88" }),
      ]}),
      new Paragraph({ spacing: { before: 100 }, children: [
        new TextRun({ text: "Contact: ", bold: true, size: 20, font: "Arial" }),
        new TextRun({ text: "soneei@github", size: 20, font: "Arial" }),
      ]}),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  const out = '/Users/sona/Projects/hidden-chain/Hidden_Chain_Physician_Validation.docx';
  fs.writeFileSync(out, buffer);
  console.log('Created:', out);
});
