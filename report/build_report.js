// Builds report/Stochastic_Modeling_Final_Report.docx from the committed
// results and figures.
// Regenerate with:  npm install docx && node report/build_report.js
const fs = require("fs");
const path = require("path");
const {
  AlignmentType, BorderStyle, Document, Footer, HeadingLevel, ImageRun,
  LevelFormat, PageBreak, PageNumber, Packer, Paragraph, ShadingType, Table,
  TableCell, TableRow, TableOfContents, TextRun, WidthType,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FIG = (name) => fs.readFileSync(path.join(ROOT, "report", "figures", name));

// ---------- helpers ----------------------------------------------------------
const P = (text, opts = {}) => new Paragraph({
  children: [new TextRun({ text, ...opts.run })],
  spacing: { after: 160, line: 276 },
  ...opts.para,
});
const H1 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 } });
const H2 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 160 } });
const BULLET = (children) => new Paragraph({
  children, numbering: { reference: "bullets", level: 0 }, spacing: { after: 100, line: 276 },
});
const bullet = (text) => BULLET([new TextRun(text)]);
const R = (text, opts = {}) => new TextRun({ text, ...opts });
const B = (text) => new TextRun({ text, bold: true });
const I = (text) => new TextRun({ text, italics: true });

// math-ish paragraph: parts are [text, {subScript|superScript|italics}] tuples
const MATH = (parts) => new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 120, after: 160 },
  children: parts.map(([t, o]) => new TextRun({ text: t, font: "Cambria Math", size: 23, ...(o || {}) })),
});
const sub = { subScript: true };

const FIGURE = (file, caption, widthPx = 600) => {
  const img = FIG(file);
  // PNGs are 2x exports; 1800x1040 (900x520 logical) except grids 1400x1120 and interaction 1600x1040
  const dims = { "fig_grid_profit.png": [1400, 1120], "fig_grid_ploss.png": [1400, 1120],
                 "fig_headline_interaction.png": [1600, 1040] };
  const [w, h] = dims[file] || [1800, 1040];
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 160, after: 60 },
      children: [new ImageRun({ type: "png", data: img,
        transformation: { width: widthPx, height: Math.round(widthPx * h / w) } })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 220 },
      children: [new TextRun({ text: caption, italics: true, size: 19, color: "52514E" })],
    }),
  ];
};

const CELL = (text, opts = {}) => new TableCell({
  width: { size: opts.w, type: WidthType.DXA },
  shading: opts.header ? { type: ShadingType.CLEAR, fill: "EFEFEC" } : undefined,
  margins: { top: 60, bottom: 60, left: 100, right: 100 },
  children: [new Paragraph({
    alignment: opts.left ? AlignmentType.LEFT : AlignmentType.CENTER,
    children: [new TextRun({ text, bold: !!opts.header, size: 19 })],
  })],
});
const TABLE = (widths, rows) => new Table({
  columnWidths: widths,
  width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  rows: rows.map((cells, ri) => new TableRow({
    children: cells.map((c, ci) => CELL(c, { w: widths[ci], header: ri === 0, left: ci === 0 })),
  })),
});
const CAPTION = (text) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 60, after: 220 },
  children: [new TextRun({ text, italics: true, size: 19, color: "52514E" })],
});

// ---------- content ----------------------------------------------------------
const children = [];

// Title block
children.push(
  new Paragraph({ spacing: { before: 2400 } }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Trading Against Noise:", bold: true, size: 56 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: "A Stochastic Simulation Study of Prediction-Market Trading Policies", bold: true, size: 34 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 400 }, children: [new TextRun({ text: "SHBI-GB.7301, Stochastic Modeling & Simulation", size: 26 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "NYU Summer 2026, Final Project Report", size: 26 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 400 }, children: [new TextRun({ text: "Anastasia Larionova · Qian Shen · Chenhao Xi · Haoyu Zheng", size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "August 2026", size: 24, color: "52514E" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 300 }, children: [new TextRun({ text: "Code, data, and interactive dashboard: github.com/larionovaa2248-glitch/stochastic-project", size: 20, color: "52514E" })] }),
  new Paragraph({ children: [new PageBreak()] }),
);

// TOC
children.push(
  new Paragraph({ text: "Contents", heading: HeadingLevel.HEADING_1 }),
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ children: [new PageBreak()] }),
);

// ---------------- 1. Background ----------------
children.push(H1("1. Background and Motivation"));
children.push(H2("1.1 What a prediction market is"));
children.push(P("A prediction market is an exchange for binary contracts on real-world events. On platforms such as Polymarket or Kalshi, a contract on the question “Will X happen?” trades at a price between $0 and $1 and pays $1 if the event occurs and $0 otherwise. Because the payoff is exactly $1 on a YES, the traded price has a natural interpretation as the market’s consensus probability of the event: a contract trading at $0.40 is, loosely, a 40% forecast. These markets aggregate dispersed information remarkably well, but they are not oracles: prices carry noise from order flow, thin liquidity, sentiment, and slow reactions to news."));
children.push(H2("1.2 The question we study"));
children.push(P("That gap between price and probability is the entire opportunity for a trader. If prices are sometimes wrong, a rule that recognizes “too cheap” moments should profit; if prices are essentially right, no rule beats simply holding. Our study asks a precise version of this question: can a simple, mechanical trading rule, one that compares the current price to a smoothed estimate of recent prices, systematically beat a buy-and-hold benchmark, and how does the answer depend on how noisy and how sluggish the market is?"));
children.push(P("We answer it with a Monte Carlo simulation rather than with historical backtests, for a reason worth stating up front: in a simulation we control the ground truth. We can build a world in which the true probability exists and is hidden, tune exactly how wrong the market price is allowed to be, and then measure a policy’s profit against that known truth over tens of thousands of independent replications with proper confidence intervals. A historical backtest of the same rule could never separate skill from luck this cleanly, because reality never reveals its hidden probabilities."));
children.push(H2("1.3 Deliverables and rubric mapping"));
children.push(P("The project comprises (i) a vectorized, seeded simulation engine and policy library; (ii) a validation suite of 37 automated tests covering the professor’s five required correctness checks; (iii) a batch-experiment layer producing every number in this report with 95% confidence intervals; (iv) a calibration module that sets simulator inputs from live Polymarket data with a fully offline fallback; and (v) an interactive Streamlit dashboard used for the class demo. All code, result CSVs, and figures are reproducible from a single documented master seed (20260812)."));

// ---------------- 2. Model ----------------
children.push(H1("2. Model Construction and Assumptions"));
children.push(P("The model has three layers, simulated in order every period t = 0, 1, …, T. The structure was fixed in the approved proposal and implemented exactly as specified; each layer’s formula and the reasoning behind it follow."));

children.push(H2("2.1 Layer 1, the hidden true probability"));
children.push(MATH([["q", null], ["t+1", sub], [" = clip( q", null], ["t", sub], [" + σ", null], ["q", sub], [" · √(q", null], ["t", sub], ["(1 − q", null], ["t", sub], [")) · Z", null], ["t", sub], [" ,  ε, 1 − ε ),   Z", null], ["t", sub], [" ~ N(0,1) iid,  ε = 0.001", null]]));
children.push(P("Each contract carries a true probability qₜ of settling YES that evolves as a bounded random walk and is never shown to any trading policy. Three assumptions are baked into this formula, each with a purpose:"));
children.push(bullet("Martingale increments. The shocks Zₜ are zero-mean and symmetric, so E[qₜ₊₁ | qₜ] = qₜ. This is the discrete analogue of an efficient forecast: today’s truth is the best predictor of tomorrow’s. It also gives us sharp, testable implications (Section 4), the average of q_T across replications must equal q₀, and the settlement frequency must too."));
children.push(bullet("State-dependent step size. The √(q(1−q)) factor shrinks steps as q approaches 0 or 1, the same variance structure as a Bernoulli random variable. Probabilities near certainty move less, a 2-point swing is routine at q = 0.5 and enormous at q = 0.98. This keeps the walk inside (0,1) naturally, with the ε-clip as a numerical guard rather than the binding mechanism."));
children.push(bullet("Markov dynamics. Tomorrow’s truth depends only on today’s, not the path taken. This is the simplest defensible information structure and keeps the model within the course’s Markov-process framework."));

children.push(H2("2.2 Layer 2, the observed market price"));
children.push(P("Traders see only a noisy price pₜ. We implement two required variants that differ in one economically crucial way, whether mispricings persist:"));
children.push(MATH([["Variant A (iid noise):    p", null], ["t", sub], [" = clip( q", null], ["t", sub], [" + η", null], ["t", sub], [" ,  0.01, 0.99 ),   η", null], ["t", sub], [" ~ N(0, σ", null], ["p", sub], ["²) iid", null]]));
children.push(MATH([["Variant B (partial adjustment):    p", null], ["t", sub], [" = clip( p", null], ["t−1", sub], [" + κ (q", null], ["t", sub], [" − p", null], ["t−1", sub], [") + η", null], ["t", sub], [" ,  0.01, 0.99 )", null]]));
children.push(P("Variant A says the market re-prices from scratch each period: errors are transient and vanish next period. Variant B says the market only closes a fraction κ ∈ (0,1] of its gap to the truth each period, a standard partial-adjustment scheme, so a shock to the price decays geometrically at rate (1−κ) and a cheap contract stays cheap for roughly 1/κ periods. Small κ therefore means sluggish, exploitable markets. Setting κ = 1 collapses Variant B into Variant A exactly (our implementation reproduces this path-for-path with identical random draws, and a test enforces it), which lets us treat persistence as a single continuous dial from “fully efficient repricing” to “very sticky.” Section 5.2 shows the two mechanisms acting on identical random draws, side by side."));

children.push(H2("2.3 Layer 3, settlement"));
children.push(MATH([["Y ~ Bernoulli(q", null], ["T", sub], ["):   draw U ~ Uniform(0,1),  Y = 1{U < q", null], ["T", sub], ["}", null]]));
children.push(P("At the horizon the contract settles by a single Bernoulli draw with success probability q_T, generated by the inverse transform method (Lecture 2). Profit per unit held is the payout minus the entry price, minus a per-trade cost c when costs are enabled. Settlement against the hidden q_T, not the final price, is what makes the design honest: a policy profits only by buying below true value, never by predicting the noise itself."));

children.push(H2("2.4 Trading policies"));
children.push(P("The policy family under study smooths the observed price into a fair-value estimate with an exponential moving average and buys on sufficiently large dips below it:"));
children.push(MATH([["f", null], ["0", sub], [" = p", null], ["0", sub], [",   f", null], ["t", sub], [" = α p", null], ["t", sub], [" + (1 − α) f", null], ["t−1", sub], [";    buy 1 unit when  f", null], ["t", sub], [" − p", null], ["t", sub], [" > δ,  then hold to settlement", null]]));
children.push(P("The smoothing weight α sets the memory of the estimate (small α = long memory) and the threshold δ sets how big a dip must be before it is called a mispricing rather than wiggle. We evaluate the full 3×3 grid α ∈ {0.1, 0.3, 0.6} × δ ∈ {0.02, 0.05, 0.10} against two benchmarks: buy-and-hold (buy one unit at t = 0, ignore the path, the “market is right” position) and never-trade (profit identically zero, the sanity floor). An optional symmetric exit rule (close when pₜ − fₜ > δ) is implemented and exposed in the dashboard but disabled in all reported results, which use the pure buy-and-hold-to-settlement family from the specification."));
children.push(P("A design constraint we treat as inviolable is no lookahead: a policy’s decision at time t may depend only on prices up to and including t. The interface enforces this structurally, decide(price_history) receives a copy of p₀…pₜ and nothing else; there is no channel through which the hidden truth, future prices, or the settlement outcome could reach a policy. Section 4 describes the tests that guard this property, including one that was strengthened after an adversarial review caught a weakness."));

children.push(H2("2.5 Randomness and reproducibility"));
children.push(P("Every stochastic function takes an explicit numpy.random.Generator; nothing touches global random state. All randomness flows through standard normal draws or the inverse transform method, drawn up front in a fixed order (Layer-1 shocks, then Layer-2 noise, then settlement uniforms). Two properties follow. First, any seeded run is exactly reproducible, every number in this report regenerates from seed 20260812. Second, because Variants A and B consume identical draws, and because all policies at a given parameter point are evaluated on the same simulated batch, every comparison in this study uses common random numbers (Lecture 7), which pairs away path-level luck and shrinks comparison variance by roughly an order of magnitude."));

children.push(H2("2.6 Model extension, Poisson news arrivals (default off)"));
children.push(P("The approved model’s hidden truth diffuses: it moves by many small Gaussian steps, so its increments are thin-tailed. Real event probabilities also lurch, a court ruling, an injury report, a debate moment, producing rare, large moves. The canonical stochastic-process model for “rare events arriving at random times” is the Poisson process: events occur independently at a constant average rate, so the number of events in any window is Poisson-distributed and the waiting times between events are exponential and memoryless. We use its discrete-time counterpart: each period, independently, a news event fires with probability λ, a Bernoulli arrival process. Interarrival times are then geometric (the discrete analogue of exponential, and the same memoryless story: having waited ten periods for news tells you nothing about the eleventh), the event count over T periods is Binomial(T, λ) ≈ Poisson(λT) for small λ, and λ has a direct reading: news arrives about once every 1/λ periods."));
children.push(P("When an event fires, the truth takes an extra zero-mean shock on top of its usual diffusion step, damped by the same √(q(1−q)) factor so jumps also respect the (0, 1) barriers. Layer 1 becomes:"));
children.push(MATH([["q", null], ["t+1", sub], [" = clip( q", null], ["t", sub], [" + √(q", null], ["t", sub], ["(1 − q", null], ["t", sub], [")) · [ σ", null], ["q", sub], [" Z", null], ["t", sub], [" + B", null], ["t", sub], [" σ", null], ["J", sub], [" G", null], ["t", sub], [" ] ,  ε, 1 − ε )", null]]));
children.push(MATH([["B", null], ["t", sub], [" ~ Bernoulli(λ) iid (the arrival process),   G", null], ["t", sub], [" ~ N(0, 1) iid (the jump size),   λ = 0 recovers the approved model", null]]));
children.push(P("Three properties make this a disciplined extension rather than a new model. First, the increments remain zero-mean, E[qₜ₊₁ | qₜ] = qₜ exactly as before, so the martingale structure, and with it every Section-4 validation check (settlement calibration included), survives with jumps on; the test suite runs all checks in both regimes. Second, the increment distribution becomes a two-component Gaussian mixture: conditional variance rises from σ_q²·q(1−q) to (σ_q² + λσ_J²)·q(1−q), and because the extra variance arrives in rare large doses rather than uniformly, the increments acquire excess kurtosis, fat tails, which is precisely the feature the diffusion lacks. A naive alternative, simply raising σ_q, would match the variance but not the tails: more wiggle is not the same as occasional lurches. Third, reproducibility is preserved by construction: when λ = 0 the implementation draws no additional random numbers, so the approved model’s seeded output is bit-for-bit unchanged, pinned by a golden-value regression test."));
children.push(P("All headline results (Sections 5.1–5.6) use the approved model. Section 5.7 then turns the arrivals on deliberately and, with the same experimental machinery, quantifies what news does to every model case, including mapping the frontier in (λ, σ_J) where the trading edge dies."));

// ---------------- 3. Simulation design ----------------
children.push(H1("3. Simulation and Experiment Design"));
children.push(H2("3.1 Vectorized batches and output analysis"));
children.push(P("The engine simulates all replications of a batch as one 2-D array (replications × time), with the only Python loop over time, a batch of 20,000 hundred-period markets simulates in well under a second, which is what makes the interactive dashboard possible. For every policy we report the professor’s three measures plus an interval: expected profit, P(loss), mean loss given loss, and a CLT-based 95% confidence interval, mean ± 1.96·s/√n (Lecture 3). Comparisons against buy-and-hold use paired differences on common paths, and “beats buy-and-hold” always means the paired-difference CI lies entirely above zero, never a bare comparison of two means."));
children.push(H2("3.2 Run-length control"));
children.push(P("Following the Lecture 3 sequential procedure, a run-length controller doubles the number of replications until the CI half-width falls below a user tolerance. For the headline cell (EMA α=0.3, δ=0.05 at κ=0.2) reaching a ±0.005 half-width required 64,000 replications:"));
children.push(TABLE([2340, 2340, 2340], [
  ["Round", "Total replications", "95% CI half-width"],
  ["0", "1,000", "0.0307"], ["1", "2,000", "0.0215"], ["2", "4,000", "0.0152"],
  ["3", "8,000", "0.0108"], ["4", "16,000", "0.0076"], ["5", "32,000", "0.0054"],
  ["6", "64,000", "0.0038  ✓ (≤ 0.005)"],
]));
children.push(CAPTION("Table 1. Sequential run-length control: half-width shrinks as 1/√n; the tolerance binds at n = 64,000 (final estimate +0.0571 ± 0.0038)."));
children.push(...FIGURE("fig_run_length.png", "Figure 1. Run-length control on log–log axes: the observed half-width tracks the theoretical 1/√n slope until it crosses the 0.005 tolerance."));
children.push(H2("3.3 Sweep design"));
children.push(P("The experiment layer sweeps three dials, observation noise σ_p ∈ {0, 0.01, 0.02, 0.05, 0.08, 0.12}, persistence κ ∈ {0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0}, and per-trade cost c ∈ {0, 0.01, 0.02}, around a baseline market (q₀ = 0.40, T = 100, σ_q = 0.02, σ_p = 0.05, Variant B) chosen for realism in Section 5. Each sweep point uses an independent seeded batch of n = 20,000; within a point, all eleven policies share the same paths (common random numbers). Every CSV in results/ carries the full measure set for all nine grid policies and both benchmarks."));

// ---------------- 4. Validation ----------------
children.push(H1("4. Validation: Why the Numbers Can Be Trusted"));
children.push(P("Thirty-seven automated tests run in under a second and gate every change. The five required checks, each a named test:"));
children.push(bullet("Zero-noise limit. With σ_p = 0 and κ = 1 the price equals the hidden probability exactly; the degenerate EMA (α=1, δ=0) never detects a mispricing and never trades; and by optional stopping on the martingale qₜ, every grid policy’s expected profit equals buy-and-hold’s (all ≈ 0), verified with paired-difference confidence bands."));
children.push(bullet("Martingale property. Across 20,000 replications, mean q_T = 0.3996 against q₀ = 0.40 (SE 0.0005), and the settlement frequency is 0.4030 (SE 0.0035), both within their bands, confirming E[q_T] = q₀ and P(Y=1) = E[q_T] by the law of total expectation."));
children.push(bullet("Settlement calibration. Contracts started at q₀ = x settle YES a fraction ≈ x of the time across x ∈ {0.10, 0.25, 0.50, 0.75, 0.90}, the simulator’s probabilities mean what they claim."));
children.push(bullet("No lookahead. A behavioural test perturbs all prices after t = 40 by +0.30 and verifies, through the real evaluation harness, that every trade decision before t = 40 is bit-identical, including for a deliberately “future-hungry” probe policy that trades on max(history) and would flip immediately if even one future price leaked. A complementary perturbation of past prices confirms decisions do change, so the test has power. Structural tests additionally pin the decide() signature and verify the harness hands each policy exactly p₀…pₜ as a fresh copy."));
children.push(bullet("Seed reproducibility. Identical seeds give bit-identical batches; different seeds differ. A golden-value test additionally pins five path values and the settlement vector of a fixed seed, so any accidental change to the random stream, including from the news-jump extension, fails the suite."));
children.push(P("Process note. The engine was also subjected to an adversarial multi-agent review (four independent reviewer perspectives, each finding attacked by two verifiers) before the experiment phase. It confirmed one real defect, the original future-perturbation check never actually showed the shocked prices to the policy, making it vacuous, which we repaired as described above, and it validated the rest of the engine against the specification. The full review log ships in the repository (results/review_log.md)."));

// ---------------- 5. Results ----------------
children.push(H1("5. Results and Model Performance"));
children.push(H2("5.1 One market, period by period"));
children.push(...FIGURE("fig_single_path.png", "Figure 2. A single simulated contract (Variant B, κ = 0.2). The dashed line is the hidden truth qₜ no trader can see; the blue line is the observed price; the green line is the EMA estimate; the triangle marks the policy’s entry. This contract settled YES: the policy earned $0.700 on a $0.300 entry."));
children.push(P("Figure 2 shows the model’s mechanics on one path: the price rattles around the slow-moving truth, the EMA smooths the rattle, and the policy buys when the price falls far enough below its own smoothed history. The contract’s all-or-nothing settlement is why per-path outcomes are extreme, the interesting quantities are averages over many replications."));

children.push(H2("5.2 Variant A vs Variant B, side by side"));
children.push(...FIGURE("fig_variant_ab.png", "Figure 3. One seed, two price mechanisms. Variants A and B consume identical random draws, so the dashed hidden truth and the noise shocks are the same in both lines, the only difference is the adjustment mechanism. The Variant A price (blue) jitters tightly around the truth and re-centres every period; the Variant B price (green, κ = 0.2) wanders away and returns only slowly, e.g. the persistent under-pricing episodes around t ≈ 55–60 and t ≈ 85–95."));
children.push(P("Figure 3 is the clearest way to see what κ buys. Under Variant A every pricing error is born and dies within one period: the blue line is noisy but honest on average at every instant. Under Variant B the same shocks accumulate: a run of negative noise pushes the green line into a genuine, lasting under-pricing that takes ~1/κ periods to close. A smoothing rule sees both worlds differently, under A it harvests instant mean-reversion; under B it can sit inside a persistent mispricing episode. The quantitative comparison (both at σ_p = 0.05, no costs, n = 20,000, common paths within each column):"));
children.push(TABLE([3320, 2560, 2560], [
  ["", "Variant A (κ = 1)", "Variant B (κ = 0.3)"],
  ["Grid winner", "EMA(α=0.1, δ=0.10)", "EMA(α=0.1, δ=0.10)"],
  ["Winner E[profit]", "+0.0888  [+0.0825, +0.0952]", "+0.1015  [+0.0949, +0.1082]"],
  ["Winner P(loss)", "54.1%", "58.8%"],
  ["Paired edge vs BH", "+0.0907  [+0.0881, +0.0934]", "+0.1034  [+0.1020, +0.1049]"],
  ["Buy-and-hold E[profit]", "−0.0019", "−0.0019"],
  ["Grid cells beating BH", "8 of 9", "8 of 9"],
]));
children.push(CAPTION("Table 2. The same experiment under each variant (full tables: policy_comparison_variantA.csv and policy_comparison_variantB_kappa03.csv). Persistence raises the winner’s edge by about 14% but changes nothing qualitative: same winning cell, same 8-of-9 pattern."));
children.push(P("The two variants agree on every qualitative conclusion, same winning cell, same benchmark behaviour, same near-sweep of the grid, and differ only in degree: moderate persistence makes the same rule about 14% more profitable, exactly the interior-peak effect quantified in Section 5.4. This is why the rest of the analysis can treat κ as a continuous dial rather than studying two separate models."));

children.push(H2("5.3 The policy grid at the baseline"));
children.push(...FIGURE("fig_grid_profit.png", "Figure 4. Expected profit per $1 contract over the (α, δ) grid at the baseline market (Variant B, κ = 0.3, σ_p = 0.05, n = 20,000, no costs). The outlined cell is the winner; its lead over buy-and-hold is CI-significant.", 430));
children.push(TABLE([2900, 1610, 2130, 1310, 1410], [
  ["Policy", "E[profit]", "95% CI", "P(loss)", "E[loss | loss]"],
  ["EMA(α=0.1, δ=0.10), winner", "+0.1015", "[+0.0949, +0.1082]", "58.8%", "−$0.289"],
  ["EMA(α=0.3, δ=0.10)", "+0.0629", "[+0.0580, +0.0678]", "31.5%", "−$0.259"],
  ["EMA(α=0.3, δ=0.05)", "+0.0614", "[+0.0546, +0.0682]", "60.2%", "−$0.336"],
  ["EMA(α=0.6, δ=0.10)", "−0.0000", "[−0.0001, +0.0000]", "0.0%", "−$0.180"],
  ["Buy-and-hold", "−0.0019", "[−0.0087, +0.0049]", "60.2%", "−$0.400"],
  ["Never-trade", "0", "n/a", "0%", "n/a"],
]));
children.push(CAPTION("Table 3. Selected rows of the baseline comparison (full 11-policy table in results/policy_comparison_variantB_kappa03.csv). The winner’s paired edge over buy-and-hold is +0.1034, CI [+0.1020, +0.1049]."));
children.push(P("Three observations. First, buy-and-hold earns nothing in expectation, as it must, since it buys at a price whose noise is mean-zero and collects an expectation-preserving payout; its CI comfortably covers zero. Second, eight of nine EMA cells beat it significantly, with a clear gradient toward slow smoothing and wide thresholds: α = 0.1 builds a long-memory estimate, and δ = 0.10 only pulls the trigger on roughly two-sigma dips, the ones most likely to be genuine mispricing rather than wiggle. Third, the corner cell (α=0.6, δ=0.10) almost never trades, fast smoothing keeps the EMA glued to the price, so a 10-cent gap essentially never opens, a useful reminder that these two dials interact: δ is measured in units of how much the EMA is allowed to lag."));
children.push(P("The profit asymmetry deserves note: the winning policy loses more often than not (P(loss) = 58.8%) yet is strongly profitable, because conditioning on entry at a depressed price makes wins (payout $1 minus a cheap entry) larger than losses (a cheap entry forfeited). Its losses are also smaller than buy-and-hold’s (−$0.289 vs −$0.400 conditional on losing), buying dips also means paying less when wrong."));

children.push(H2("5.4 Headline experiment: how much persistence does the edge need?"));
children.push(...FIGURE("fig_headline_kappa.png", "Figure 5. The best grid policy’s paired edge over buy-and-hold as a function of κ, for three per-trade cost levels (bands: 95% CIs). The edge is positive and significant everywhere, peaking near κ ≈ 0.2–0.3."));
children.push(P("We designed this experiment expecting a threshold: the κ below which mispricing persists long enough for a smoothing rule to catch it. The simulation returned a more interesting answer: at realistic noise (σ_p = 0.05) there is no threshold. The best EMA cell beats buy-and-hold with CI-significance at every κ from 0.05 to 1.0 and at every cost level up to 2¢ per trade. Even the worst case for the trader, κ = 1 (fully transient noise) with 2¢ costs, leaves a paired edge of +0.0939, CI [+0.0913, +0.0965]."));
children.push(P("Persistence instead shapes the edge, with an interior maximum near κ ≈ 0.2–0.3 (+0.1023, CI [+0.1007, +0.1038] at κ = 0.3). The intuition on both flanks is mechanical. When κ is large, errors correct almost immediately, so the dip the policy buys has mostly closed by the next period, profitable (the entry price was still below true value) but less so. When κ is very small (0.05), shocks persist for ~20 periods: dips last long enough to catch easily, but the mispricing also fails to finish correcting before the horizon, and entry prices reflect older, staler truths. In between sits the sweet spot: dips persist long enough to identify, and correct fully before settlement."));
children.push(P("Costs barely move the comparison (the three curves in Figure 5 nearly coincide), for a subtle reason worth flagging: both the EMA policy and buy-and-hold trade at most once, so a per-trade fee hits both nearly equally, and the EMA policy occasionally stays out entirely and saves the fee. The paired edge is therefore almost cost-invariant, even as absolute profits fall with c (best-cell profit at κ = 0.3: +0.102 → +0.092 → +0.082 across c = 0, 1¢, 2¢)."));

children.push(H2("5.5 The deeper finding: noise creates the edge, persistence shapes it"));
children.push(...FIGURE("fig_headline_interaction.png", "Figure 6. Best-cell paired edge over buy-and-hold across the (κ, σ_p) grid at c = 1¢. All 28 cells are CI-significant; the edge climbs with noise at every persistence level.", 470));
children.push(P("Sweeping noise and persistence jointly reveals the study’s central result. Reading Figure 6 by rows: at σ_p = 0.01 the edge is a razor-thin +0.008– +0.017 per contract; at σ_p = 0.05 it is roughly +0.08–+0.10; at σ_p = 0.08 it reaches +0.14. Reading by columns: at any fixed noise level, moving κ barely changes the edge by comparison. And the zero-noise sweep column (Table 3) closes the argument: with σ_p = 0 no policy in the grid beats buy-and-hold at any κ, the largest paired difference is +0.0027 and not significant."));
children.push(TABLE([2340, 3120, 2340], [
  ["σ_p (noise)", "Best-cell paired edge vs BH", "CI-significant?"],
  ["0.00", "+0.0027", "no"],
  ["0.01", "+0.0121", "yes"],
  ["0.02", "+0.0331", "yes"],
  ["0.05", "+0.0913", "yes"],
  ["0.08", "+0.1385", "yes"],
  ["0.12", "+0.2061", "yes"],
]));
children.push(CAPTION("Table 4. Noise sweep at κ = 1 (Variant A limit): the edge scales with observation noise and vanishes exactly when noise does."));
children.push(P("The economic reading: a dip-buying rule is fundamentally a bet that price movements below trend are noise, not news. In the approved model, where the hidden truth is a martingale and every deviation of price from truth is, by construction, transient error, that bet is correct by design, and its profitability is proportional to how much error there is to harvest. Mispricing persistence (κ) only governs how easy the harvesting is. This framing also tells us exactly where the result should break, when dips can be news, and Section 5.7 tests that prediction directly."));

children.push(H2("5.6 Risk profile"));
children.push(...FIGURE("fig_profit_distribution.png", "Figure 7. Per-contract profit distributions, EMA(0.3, 0.05) vs buy-and-hold (κ = 0.2, c = 1¢, n = 20,000). Binary settlement makes both bimodal; the EMA policy’s mass sits to the right in both lobes and it has a third spike at exactly zero (paths where it never entered)."));
children.push(P("Expected profit is not the whole story for a trader. Figure 7 shows both strategies inherit the contract’s all-or-nothing character, profits cluster in a loss lobe (bought, settled NO) and a win lobe (bought, settled YES). The EMA policy’s advantages are visible in both: its loss lobe sits closer to zero (it pays less when wrong) and its win lobe sits further right (it pays less when right, too). Its P(loss) is similar to buy-and-hold’s at these settings, so the rule does not reduce how often you lose, it reduces how much losing costs and increases how much winning pays."));

children.push(H2("5.7 With and without news: the full model-case matrix (extension results)"));
children.push(P("Everything above uses the approved model, in which every dip is noise. Here we turn the Poisson news-jump extension of Section 2.6 on deliberately and re-run the same machinery, so the study covers all four model worlds: each price variant, with and without news. Settings: σ_p = 0.05, c = 1¢, n = 20,000 per cell; the jump cases use λ = 0.05 (one news event per ~20 periods) with jump scale 0.20."));
children.push(TABLE([3160, 1560, 1560, 2380], [
  ["Model case", "Best cell", "Best E[profit]", "Paired edge vs BH (95% CI)"],
  ["Variant A · no jumps", "EMA(0.1, 0.10)", "+0.0842", "+0.0938  [+0.0913, +0.0964]"],
  ["Variant B (κ=0.3) · no jumps", "EMA(0.1, 0.10)", "+0.0967", "+0.1024  [+0.1008, +0.1040]"],
  ["Variant A · jumps (λ=0.05)", "EMA(0.6, 0.05)", "+0.0661", "+0.0757  [+0.0731, +0.0783]"],
  ["Variant B (κ=0.3) · jumps (λ=0.05)", "EMA(0.1, 0.10)", "+0.0677", "+0.0778  [+0.0758, +0.0798]"],
]));
children.push(CAPTION("Table 5. The four model cases under identical settings (results/model_case_matrix.csv). News jumps cut the edge by roughly a quarter in both variants; every case remains CI-significant at this news intensity."));
children.push(P("Two things stand out. First, the qualitative conclusion is robust across all four worlds: the EMA family still beats buy-and-hold significantly everywhere at this news intensity, and the A-vs-B ordering survives jumps. Second, news is expensive: turning jumps on removes about 25% of the edge in both variants, exactly as the noise-vs-news framing of Section 5.5 predicts: some of the dips the policy buys are now genuine repricings rather than harvestable error. A subtle and satisfying detail: under Variant A with jumps, the winning cell shifts from slow smoothing (α = 0.1) to fast smoothing (α = 0.6). A fast EMA re-centres on the truth’s new level within a couple of periods after a jump, so it stops reading the post-jump price as a bargain; a slow EMA keeps comparing prices against a stale pre-jump anchor. When the world can jump, long memory becomes a liability."));
children.push(...FIGURE("fig_jump_sweep.png", "Figure 8. Extension headline: the best-cell edge over buy-and-hold as news intensity λ rises (Variant B, κ = 0.3, jump scale 0.20, c = 1¢, 95% CI band). λ = 0 is the approved model."));
children.push(TABLE([1900, 2400, 2340, 2160], [
  ["λ (news rate)", "≈ one event per", "Best-cell edge vs BH", "vs approved model"],
  ["0.00", "n/a (approved model)", "+0.1029  [+0.1014, +0.1045]", "n/a"],
  ["0.02", "50 periods", "+0.0928  [+0.0910, +0.0945]", "−10%"],
  ["0.05", "20 periods", "+0.0786  [+0.0765, +0.0807]", "−24%"],
  ["0.10", "10 periods", "+0.0643  [+0.0620, +0.0666]", "−37%"],
  ["0.20", "5 periods", "+0.0387  [+0.0360, +0.0414]", "−62%"],
]));
children.push(CAPTION("Table 6. The jump-rate sweep behind Figure 8 (results/sweep_jump_rate.csv). The erosion is monotone and roughly linear in λ; at this jump size the edge is heading toward zero but has not crossed it even at one news event per five periods."));
children.push(P("The sweep answers the extension’s question quantitatively: the dip-buying edge decays monotonically, and roughly linearly, in news intensity, losing about a tenth of its value already at one news event per fifty periods and nearly two-thirds at one per five. It remains CI-significant throughout this particular range because moderate-sized jumps (σ_J = 0.20) still leave plenty of ordinary noise to harvest. So we pushed further and mapped the frontier itself, sweeping news rate and jump size jointly:"));
children.push(...FIGURE("fig_jump_frontier.png", "Figure 9. The news frontier: best-cell paired edge over buy-and-hold across (λ, σ_J) at c = 1¢, n = 20,000 per cell. The edge declines along both axes; in the top-right cell (λ = 0.20, σ_J = 0.60) the X marks the crossing, no grid policy beats buy-and-hold, and the best cell significantly LOSES (−0.0066, CI [−0.0089, −0.0044]).", 470));
children.push(P("Figure 9 is the completed answer to “when does dip-buying stop working?” The edge falls along both axes, more frequent news and bigger news are separately costly, and the zero crossing is real and reachable: at one large news event (σ_J = 0.60) every five periods, dip-buying goes from harvesting noise to being CI-significantly worse than buy-and-hold. Two adaptations are visible on the way to the frontier. As news intensifies, the winning threshold shrinks from δ = 0.10 toward δ = 0.02: large dips become suspect, increasingly likely to be genuine repricings, so the best surviving strategy retreats to small, quick dips that news rarely produces. And throughout, slow smoothing (α = 0.1) holds on under Variant B, because the price’s own sluggishness still hides some harvestable error inside every post-news adjustment path. The frontier gives the study’s thesis its final, falsifiable form: dip-buying earns exactly as much as the market’s error budget is noise rather than news, and we can now say where the sign flips."));
children.push(...FIGURE("fig_jump_path.png", "Figure 10. The mechanism on one path (Variant B, κ = 0.3, λ = 0.04, seed 42): the truth (dashed) takes three downward news jumps (diamonds); the lagging price reads as a dip against the EMA and the policy buys at ≈ $0.40; the contract settles NO for −$0.399. Under jumps, some dips are news, and the rule cannot tell."));
children.push(P("Figure 10 shows why the edge erodes, on the exact path used in the live demo. After the first cluster of bad news the price slides toward the truth’s new, lower level; on the way down it sits below its own smoothed history, which is precisely the buy signal. The policy purchases a contract that is still overpriced relative to the post-news truth. Averaged over thousands of paths, these adversely-selected entries are what Table 6 measures. The asymmetry is worth noting: upward jumps create genuine bargains (price lags below the new truth), but the dip rule cannot buy them, rising prices sit above their EMA, so news hurts the rule on both sides: it buys the bad surprises and misses the good ones."));

children.push(H2("5.8 Calibration to real markets: are the parameters realistic?"));
children.push(P("To keep the simulated regimes honest, the calibration module pulls real price histories from Polymarket’s public APIs (metadata from the Gamma API, hourly price series from the CLOB endpoint) and maps them onto model inputs by method of moments. Under Variant A the observed increment is Δpₜ = Δqₜ + ηₜ − ηₜ₋₁, an MA(1) in the noise, giving two estimating equations: Cov(Δpₜ, Δpₜ₋₁) = −σ_p² identifies the noise, and the residual variance, deflated by the mean of p(1−p) as the proxy for the damping factor, identifies σ_q. A test verifies the estimator recovers known parameters from long simulated series within 25% relative error."));
children.push(P("Five diverse markets (politics, geopolitics, financial milestones; 418–743 hourly observations each, fetched 2026-08-10) are committed to the repository as offline samples, so every feature works without network access. Their implied σ_q ranges from 0.002 to 0.019 per step, bracketing our default σ_q = 0.02 at the volatile end, which is the appropriate stress setting for studying trading rules. Their implied iid noise on hourly closes is small (σ_p ≤ 0.002), consistent with hourly aggregation smoothing microstructure noise; we therefore treat σ_p as the stress dimension and sweep it, rather than claiming any single value is “the” real one. Scope guard, stated in the specification and honored throughout: real data sets simulator inputs only. We do not fit the model to real series and we do not backtest policies on real data; no claim in this report is a claim about realized Polymarket profits."));

// ---------------- 6. Conclusion ----------------
children.push(H1("6. Conclusions and Future Work"));
children.push(H2("6.1 What we built"));
children.push(P("A three-layer stochastic model of a prediction market, hidden martingale truth, noisy observed price with tunable persistence, Bernoulli settlement, implemented as a fully vectorized, seed-deterministic simulation engine; a policy library with a structurally lookahead-proof interface; an experiment layer with CLT confidence intervals, common random numbers, and sequential run-length control; a 37-test validation suite; real-data calibration with an offline fallback; and an interactive dashboard that runs every analysis in this report live."));
children.push(H2("6.2 What we found"));
children.push(bullet("A simple EMA dip-buying rule beats buy-and-hold decisively in this model: +0.10 per $1 contract at the baseline, CI-significant across the entire persistence range and up to 2¢ per-trade costs."));
children.push(bullet("The expected threshold, “how small must κ be before the rule works?”, does not exist at realistic noise. Instead the edge has an interior optimum in κ (≈ 0.2–0.3), where mispricings persist long enough to catch and still correct before settlement."));
children.push(bullet("The deeper mechanism: observation noise creates the edge (it vanishes exactly at σ_p = 0 and scales with σ_p everywhere else); persistence and costs only modulate it. Dip-buying profits here because, in the approved model, every dip is noise."));
children.push(bullet("Slow smoothing with a wide threshold (α = 0.1, δ = 0.10) dominates the grid, patience in both dials, while fast smoothing with a wide threshold barely trades at all."));
children.push(bullet("When news exists (Poisson-arrival extension, all four model cases re-run), the mechanism runs in reverse exactly as predicted: the edge erodes monotonically and roughly linearly in news intensity, −24% at one event per 20 periods, −62% at one per 5, because the rule buys downward repricings it cannot distinguish from noise, and cannot buy the upward ones. Under jumps, fast smoothing gains ground on slow smoothing: long memory becomes a stale anchor."));
children.push(bullet("The frontier is real and mapped: sweeping news rate and jump size jointly, the edge declines along both axes and crosses zero at (λ = 0.20, σ_J = 0.60), one large news event per five periods, where dip-buying becomes CI-significantly worse than buy-and-hold. En route to the frontier the surviving strategies retreat to smaller entry thresholds: big dips stop being bargains and start being information."));
children.push(H2("6.3 Limitations"));
children.push(P("The model is deliberately stylized. There is no order book, no price impact, no liquidity constraint, the policy trades one unit at the posted price, so profits should be read as per-contract edges, not fund returns. The truth process has no drift or regime structure. In the approved model every price deviation is transient noise, the exact condition under which dip-buying must win, and while the jump extension relaxes this and confirms the edge survives moderate news, real markets mix noise and news in proportions our hourly real-data estimates cannot separately identify (nor κ from σ_p). These are boundaries of the claim, not flaws in the measurement inside them."));
children.push(H2("6.4 Future directions"));
children.push(bullet("Place real markets on the frontier map. Section 5.7 locates where dip-buying dies in (λ, σ_J) space; the natural completion is empirical: estimate each real market’s news rate and jump size from the frequency and magnitude of outsized moves in its price history (a threshold-exceedance count gives λ; the excess-move distribution gives σ_J), then plot actual Polymarket contracts against the frontier to predict, market by market, where a smoothing rule should and should not work."));
children.push(bullet("Adaptive and asymmetric policies: exit rules (implemented, unstudied), position sizing by signal strength, and Kelly-style stake scaling on the estimated mispricing."));
children.push(bullet("Microstructure realism: bid-ask spread as a state-dependent cost, depth limits, and price impact of the policy’s own trades."));
children.push(bullet("Multi-market extensions: correlated contracts and portfolio-level risk measures across simultaneous markets."));
children.push(P("The broader takeaway we would offer the class: the most valuable output of a simulation study is often not the number you asked for but the mechanism it forces you to articulate. We asked “how much persistence does a trader need?” and the model answered “wrong question: count the noise, not the stickiness.” That answer came with confidence intervals, survived an adversarial review and 37 tests, and regenerates from one seed."));

// ---------- document ----------
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Calibri", size: 32, bold: true, color: "1A1A19" } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: "Calibri", size: 26, bold: true, color: "2A2A28" } },
    ],
  },
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 480, hanging: 240 } } } }],
    }],
  },
  features: { updateFields: true },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "898781" })],
      })] }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = path.join(ROOT, "report", "Stochastic_Modeling_Final_Report.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out, `(${(buf.length / 1024).toFixed(0)} KB)`);
});
