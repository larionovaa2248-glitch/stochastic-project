// Builds report/How_to_View_Project.docx, the one-page orientation note that
// ships at the top level of the submission zip (converted to PDF).
// Regenerate with:  npm install docx && node report/build_howto.js
const fs = require("fs");
const path = require("path");
const {
  AlignmentType, Document, HeadingLevel, LevelFormat, Packer, Paragraph,
  TextRun,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");

const P = (text, opts = {}) => new Paragraph({
  children: [new TextRun({ text, size: 24, ...opts })],
  spacing: { after: 200, line: 300 },
});
const H = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 140 },
  children: [new TextRun({ text, bold: true, size: 28 })],
});
const LI = (text) => new Paragraph({
  children: [new TextRun({ text, size: 24 })],
  numbering: { reference: "bullets", level: 0 },
  spacing: { after: 120, line: 300 },
});
const CODE = (text) => new Paragraph({
  children: [new TextRun({ text, font: "Consolas", size: 22 })],
  spacing: { after: 200 }, indent: { left: 480 },
});

const children = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200, after: 100 },
    children: [new TextRun({ text: "How to View This Project", bold: true, size: 40 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 300 },
    children: [new TextRun({ text: "Trading Against Noise · SHBI-GB.7301 Final Project · " +
      "Larionova, Shen, Xi, Zheng", size: 22, color: "52514E" })] }),

  H("1. The report"),
  P("Open “Final Report.pdf” in this folder (19 pages). The editable Word " +
    "version and everything that produced it live in the background folder " +
    "(background/report/Stochastic_Modeling_Final_Report.docx)."),

  H("2. The slides"),
  P("Double-click “Trading Against Noise — Slides.html”. It opens in any web " +
    "browser with no setup: use the left/right arrow keys (or click) to move " +
    "through the 19 slides, and press N to show the speaker notes on each slide."),

  H("3. Running the simulation and interactive dashboard (optional)"),
  P("The only requirement is Python 3.11 or newer (free from python.org). One " +
    "command sets up an isolated environment, installs the packages, runs the " +
    "37-test validation suite, and opens the interactive dashboard in your browser:"),
  LI("Windows: open the background folder and double-click run.bat"),
  LI("Mac (or Linux): open Terminal, then run:"),
  CODE("cd path/to/background        (drag the folder into Terminal to fill the path)"),
  CODE("python3 run.py"),
  P("The first run takes a few minutes to install packages; after that it starts " +
    "in seconds. The dashboard appears at http://localhost:8601 and works fully " +
    "offline (five real Polymarket price histories are bundled). Useful variants:"),
  LI("python run.py --experiments   regenerates every result CSV and figure " +
     "from the master seed (20260812)"),
  LI("python run.py --slides   serves the slide deck with a demo button that " +
     "boots the dashboard in one click"),

  H("Where everything lives"),
  LI("background/src/ – the simulation engine, trading policies, experiments, " +
     "calibration, and validation code"),
  LI("background/tests/ – the 37-test validation suite (run with: python -m pytest)"),
  LI("background/results/ – every experiment CSV, the numeric summary, and the " +
     "review log; background/report/figures/ – all figures"),
  LI("background/notebooks/analysis.ipynb – the executed analysis walkthrough"),
  P("Everything is also on GitHub: github.com/larionovaa2248-glitch/stochastic-project"),
];

const doc = new Document({
  styles: { default: { document: { run: { font: "Calibri", size: 24 } } } },
  numbering: { config: [{ reference: "bullets",
    levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
      alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 480, hanging: 240 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 },
      margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = path.join(ROOT, "report", "How_to_View_Project.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out);
});
