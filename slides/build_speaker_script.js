// Builds slides/Speaker_Script.docx — a verbatim presenter script, one
// section per slide, timed for a ~20-minute talk including the live demo.
// Regenerate with:  npm install docx && node slides/build_speaker_script.js
const fs = require("fs");
const path = require("path");
const {
  AlignmentType, Document, Footer, HeadingLevel, LevelFormat, PageNumber,
  Packer, Paragraph, ShadingType, Table, TableCell, TableRow, TextRun,
  WidthType,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");

const P = (text, opts = {}) => new Paragraph({
  children: [new TextRun({ text, size: 24, ...opts })],
  spacing: { after: 180, line: 300 },
});
const DIRECTION = (text) => new Paragraph({
  children: [new TextRun({ text, italics: true, size: 21, color: "8A6D00" })],
  spacing: { after: 160, line: 280 },
  indent: { left: 360 },
});
const SLIDE = (num, title, minutes) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 360, after: 140 },
  children: [
    new TextRun({ text: `Slide ${num} — ${title}`, bold: true, size: 28 }),
    new TextRun({ text: `   (~${minutes})`, bold: false, size: 22, color: "898781" }),
  ],
});

const children = [];

children.push(
  new Paragraph({ spacing: { before: 600 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Speaker Script", bold: true, size: 48 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [new TextRun({ text: "Trading Against Noise — SHBI-GB.7301 Final Presentation", size: 28 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 },
    children: [new TextRun({ text: "19 slides · ~20 minutes including the live demo · slides/index.html", size: 22, color: "52514E" })] }),
);

children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, text: "Before you start", spacing: { after: 160 } }));
children.push(P("Timing plan: opening and setup ≈ 3 minutes (slides 1–3), the model ≈ 5.5 minutes (slides 4–8, including the full-screen model picture on slide 5), trust and method ≈ 2.5 minutes (slides 9–10), core results ≈ 4 minutes (slides 11–13), the news extension ≈ 2.5 minutes (slides 14–15), risk and reality ≈ 1.5 minutes (slides 16–17), live demo ≈ 4 minutes (slide 18), close ≈ 1 minute (slide 19). If you are running long, the safest cuts are slide 16 (risk profile) and the second half of slide 17 (real-data details) — do NOT cut 14–15; they are the falsification test of the main claim."));
children.push(P("Setup checklist: present with “python3 slides/present.py” — it opens the deck AND makes the demo button start the dashboard automatically; click that button once about a minute before you begin so the first boot and cache warm-up happen off-stage; go full screen; press N once to confirm the speaker-notes toggle works, then leave notes off; have polymarket.com open in another tab in case you want a live URL for the demo. (Fallback if you present from a plain file: start “streamlit run dashboard/app.py” in a terminal first — the button then just opens it.)"));
children.push(P("Text in plain type below is meant to be spoken, roughly verbatim. Italic indented lines are stage directions — do not read them aloud."));

// ---- Slide 1 ----
children.push(SLIDE(1, "Title", "40 sec"));
children.push(P("Hi everyone. We're Anastasia, Qian, Chenhao, and Haoyu. Our project is called Trading Against Noise — it's a simulation study of trading strategies in prediction markets, the Polymarket and Kalshi style markets where you bet on yes-or-no questions."));
children.push(P("Three numbers up front that describe the whole project: a three-layer stochastic model, thirty-seven automated validation tests behind every result, and twenty thousand simulated markets behind every number we'll show you. And one seed — every figure in this talk regenerates exactly from a single random seed, so everything you're about to see is fully reproducible."));

// ---- Slide 2 ----
children.push(SLIDE(2, "The question", "1 min"));
children.push(P("Here's the setup. A contract on the question “Will X happen?” trades at forty cents, and pays out one dollar if X happens, zero if it doesn't. That means the price is literally the market's probability forecast — a forty-cent contract is a forty percent forecast."));
children.push(P("But prices carry noise: thin order books, sentiment, slow reactions to news. So there are two worldviews. If dips below fair value are usually just noise, then buying dips should make money. If the market is basically right, nothing beats just buying and holding."));
children.push(P("Our question is: which world are we in — and precisely what does the answer depend on? We wanted a number, with a confidence interval, not a vibe."));

// ---- Slide 3 ----
children.push(SLIDE(3, "Why simulation", "1 min"));
children.push(P("Why simulate instead of backtesting real data? Because real data has a fatal flaw for this question: the true probability is never revealed. If a strategy made money on historical prices, you cannot tell whether it found real mispricings or got lucky."));
children.push(P("In a simulation, we control the truth. We build a world where the true probability exists but is hidden from the trader, we tune exactly how wrong the market price is allowed to be, and then we grade every strategy against the truth we planted — over tens of thousands of independent replications, which gives us honest confidence intervals."));
children.push(P("One boundary we kept strict: real Polymarket data is used only to set realistic input parameters. We never fit the model to real data and never backtest on it — so nothing we claim today is a claim about making money on the real Polymarket."));

// ---- Slide 4 ----
children.push(SLIDE(4, "The model — three layers", "1 min"));
children.push(P("The model has three layers, simulated in order every period, and the three boxes on screen are the whole architecture. Layer one: a hidden true probability that drifts every period as a bounded random walk — and no trader ever sees it. Layer two: the observed market price — the truth plus error, and the only thing our strategies are allowed to look at. Layer three: settlement — at the horizon the contract pays one dollar with exactly the hidden probability at expiry."));
children.push(DIRECTION("Read the boxes top to bottom, then land the last line."));
children.push(P("Profit is payout minus entry price, minus fees. And notice what this design guarantees: because settlement is graded against the hidden truth, a strategy can only make money by systematically buying below true value. It cannot profit by predicting the noise itself. Let me show you what one of these markets actually looks like."));

// ---- Slide 5 ----
children.push(SLIDE(5, "The model, one picture", "1 min"));
children.push(P("Here is one full contract, period by period. The dashed orange line is the hidden truth — slow, wandering, invisible to everyone in the market. The blue line is the price the trader actually sees: it rattles around that truth, sometimes above, sometimes below. The green line is our strategy's smoothed estimate of fair value."));
children.push(DIRECTION("Trace the dashed line first, then the blue, then the green. Then point at the triangle, then the star."));
children.push(P("Watch the little green triangle: right there the price dipped far enough below the smoothed estimate that the strategy called it a mispricing and bought — at about thirty cents. And the star at the end is settlement: this contract came up YES, paid one dollar, and the trade made seventy cents. One market, one life, one all-or-nothing outcome — which is exactly why every number in the rest of this talk is an average over twenty thousand of these, with error bars."));

// ---- Slide 6 ----
children.push(SLIDE(6, "Layer 1 — the hidden truth", "1 min"));
children.push(P("Layer one in one formula. Tomorrow's truth equals today's truth plus a Gaussian shock, scaled by sigma-q and by the square root of q times one-minus-q, then clipped to stay strictly between zero and one."));
children.push(P("Three deliberate choices here. First, the shocks are zero-mean, which makes the truth a martingale — today's probability is the best forecast of tomorrow's. That's the natural efficiency assumption, and it gives us sharp testable predictions we'll use for validation. Second, that square-root factor is the Bernoulli variance shape: probabilities near zero or one move less, so the walk stays a probability naturally rather than by brute-force clipping. Third, it's Markov — tomorrow depends only on today — which is the simplest defensible information structure."));

// ---- Slide 7 ----
children.push(SLIDE(7, "Layer 2 — two price mechanisms", "1.5 min"));
children.push(P("Layer two is where market quality lives, and it comes in two required variants. Variant A: the price is the truth plus fresh noise every period. Errors are born and die within one period — an instantly self-correcting market. Variant B: the price only closes a fraction kappa of its gap to the truth each period. Now errors persist — a shock decays slowly, and a cheap contract stays cheap for roughly one-over-kappa periods."));
children.push(P("The elegant part: set kappa equal to one and variant B becomes variant A — exactly, path for path, on identical random draws. We enforce that with a test. So instead of two separate models, we get one continuous dial that runs from instant repricing down to very sticky mispricing."));
children.push(P("Keep these two dials separate in your head: sigma-p is how MUCH error the price carries; kappa is how LONG that error lives. The punchline of our whole study hangs on which of those two matters."));

// ---- Slide 8 ----
children.push(SLIDE(8, "The trading policies", "1 min"));
children.push(P("The strategy family is deliberately simple. Keep an exponential moving average of the price — that's the fair-value estimate. When today's price sits more than delta below that average, buy one unit and hold to settlement. Alpha controls the memory of the average; delta controls how big a dip has to be before you call it a mispricing instead of a wiggle. We test a full three-by-three grid of alpha and delta, against two benchmarks: buy-and-hold — the “market is right” position — and never-trade, which is the sanity floor at exactly zero."));
children.push(P("And one engineering constraint we treat as sacred: no lookahead. A policy's decide function receives a copy of prices up to now — and that is its entire universe. There is no code path through which the hidden truth, future prices, or the outcome could reach it."));

// ---- Slide 9 ----
children.push(SLIDE(9, "Why trust the numbers", "1.5 min"));
children.push(P("Thirty percent of this project's grade is implementation correctness, so here is the trust story. Thirty-seven automated tests gate every change. The five required checks: in the zero-noise limit the price equals the truth exactly and every strategy collapses to buy-and-hold, as theory demands. The martingale check: across twenty thousand runs, the mean final truth is 0.3996 against a starting value of 0.40, and settlement frequency matches too. Calibration: contracts started at ten percent settle yes about ten percent of the time, and so on across the grid. Seed reproducibility, pinned by a golden-value test on the exact random stream."));
children.push(P("And the one I want to highlight: the no-lookahead test. We shock every price after period forty and verify that every trade decision before period forty is bit-for-bit identical — including for a probe policy we built specifically to exploit any leak."));
children.push(P("Honest disclosure: our first version of that test had a bug — it never actually showed the shocked prices to the policy, so it could never fail. An adversarial review caught it, we rebuilt the test through the real trading harness, and the fix is documented in the repo. We're telling you this because a test that cannot fail is worse than no test — and now we know ours can."));

// ---- Slide 10 ----
children.push(SLIDE(10, "Experiment design", "1 min"));
children.push(P("Methodology in three bullets. One: every estimate comes with a ninety-five percent confidence interval from the central limit theorem. Two: every policy at a given parameter setting is evaluated on the SAME simulated paths — common random numbers — and every claim that something “beats buy-and-hold” is a paired-difference interval sitting entirely above zero. Pairing removes path luck and shrinks comparison variance by roughly a factor of ten. Three: run-length control — this chart — where we keep doubling the number of replications until the interval is as tight as we demanded. For our headline cell, a half-width of half a cent took sixty-four thousand replications."));
children.push(DIRECTION("Gesture at the log-log chart — the line is the theoretical one-over-root-n slope."));

// ---- Slide 11 ----
children.push(SLIDE(11, "Baseline results", "1.5 min"));
children.push(P("Now the results. This is the full policy grid at our baseline market — moderate persistence, realistic noise. Eight of the nine grid cells beat buy-and-hold with statistical significance. The winner, outlined, is slow smoothing with a wide threshold: alpha 0.1, delta 0.10. It earns about ten cents per one-dollar contract, while buy-and-hold earns nothing — which it must, since it buys at a fair price on average."));
children.push(P("The winner's character is patience in both dials: a long-memory estimate, and a trigger that only fires on roughly two-sigma dips — the dips most likely to be genuine mispricing. And notice the corner cell — fast smoothing with a wide threshold — that one almost never trades: a fast average hugs the price so closely that a ten-cent gap never opens. The two dials interact."));

// ---- Slide 12 ----
children.push(SLIDE(12, "Headline — how much persistence?", "1.5 min"));
children.push(P("Our headline experiment asked: how sluggish does the market need to be before the strategy wins? We expected a threshold — some kappa below which it works and above which it doesn't."));
children.push(P("The model said: wrong expectation. The edge is positive and significant at EVERY kappa from 0.05 to 1, at every fee level up to two cents. Even the worst case for the trader — no persistence at all and two-cent fees — leaves better than nine cents of edge."));
children.push(P("What persistence does instead is shape the edge, with a peak at kappa around 0.2 to 0.3. The intuition cuts both ways: if the market corrects too fast, the dip you bought has mostly closed by tomorrow — profitable, but small. If it corrects too slowly, the mispricing outlives the contract and never finishes paying you. The sweet spot is dips that last long enough to catch, and correct before settlement."));

// ---- Slide 13 ----
children.push(SLIDE(13, "The twist — noise creates the edge", "1.5 min"));
children.push(P("So if persistence isn't the driver, what is? This heatmap is the real answer, and it's the central slide of the talk. Read it by rows: at every persistence level, the edge scales with the amount of noise. Tiny noise, tiny edge. Big noise, twenty cents of edge. And the bottom line of the table: at exactly zero noise, the edge is exactly nothing — statistically indistinguishable from zero at any kappa."));
children.push(P("So the mechanism is: observation noise CREATES the opportunity; persistence only shapes how easy it is to harvest. Which makes sense once you say it out loud — a dip-buying rule is fundamentally a bet that dips are noise, not news. In this model, by construction, every dip IS noise. Which should make you suspicious: is the result circular? The only honest answer is to build a world where dips CAN be news — and that's exactly what we did next."));

// ---- Slide 14 ----
children.push(SLIDE(14, "The jump model — Poisson arrivals", "1.5 min"));
children.push(P("So here is that test. We let the hidden truth take news shocks, and the right tool for “rare events arriving at random times” is the Poisson process. In discrete time it's beautifully simple: every period, independently, a news event fires with probability lambda. That single assumption buys the whole Poisson toolkit — waiting times between events are geometric, meaning memoryless: having waited ten periods for news tells you nothing about the eleventh; and the number of events over the horizon is approximately Poisson with mean lambda times T. Lambda reads directly as “news arrives about once every one-over-lambda periods.”"));
children.push(P("The formula on screen is Layer one with one extra term: the usual diffusion shock, plus — only when the Bernoulli fires — a second, larger zero-mean shock, both damped by the same square-root factor so jumps respect the probability boundaries."));
children.push(DIRECTION("Point at the B-sub-t term in the formula, then tick off the three bullets."));
children.push(P("Three properties keep this disciplined. The jumps are zero-mean, so the truth is still a martingale — all thirty-seven validation tests pass with jumps switched on. The increments become a Gaussian mixture: same idea as before plus fat tails — occasional lurches, which is exactly what a plain diffusion can't produce; just raising sigma-q would add wiggle, not lurches. And when lambda is zero the code draws no extra random numbers at all, so the approved model is untouched, bit for bit — we pin that with a regression test."));
children.push(P("And look what happens on the very first path we examined — seed forty-two, on screen. The truth jumps down on news, three diamonds. The price slides after it, lagging. That slide reads as a dip against the moving average — so our strategy buys real bad news at forty cents. The contract settles at zero. Minus forty cents. Under jumps, some dips are news, and the rule cannot tell."));

// ---- Slide 15 ----
children.push(SLIDE(15, "What news does to the edge", "1.5 min"));
children.push(P("Now the same machinery, quantified — twenty thousand replications per cell, all four model worlds: both price variants, jumps on and off. Headline: the edge survives moderate news everywhere, but it pays a steep tax — down about a quarter at one news event per twenty periods, down nearly two-thirds at one per five. The erosion is close to linear in lambda."));
children.push(P("Then we swept news rate and jump size together, and that's this heatmap — we call it the news frontier. The edge falls along both axes, and in the top-right corner it actually crosses zero: at one large news event every five periods, dip-buying doesn't just stop winning — it becomes significantly WORSE than buy-and-hold."));
children.push(DIRECTION("Trace a diagonal from bottom-left (≈ the approved model) to the X in the top-right corner."));
children.push(P("Two adaptations happen on the way to that frontier, and they're my favorite findings in the project. First, the winning threshold shrinks — from ten cents down to two. As news gets common, BIG dips stop being bargains and start being information, so the surviving strategy retreats to small, quick dips that news rarely produces. Second, under variant A the winner flips from slow smoothing to fast smoothing: when the world can jump, long memory stops being patience and becomes a stale anchor. So the full thesis, now with its boundary: the edge equals the share of the market's error budget that is noise rather than news — and we can point to the exact spot where the sign flips."));

// ---- Slide 16 ----
children.push(SLIDE(16, "Risk profile", "1 min"));
children.push(P("A quick look past the averages, because a real trader cares about the distribution. Settlement is all-or-nothing, so profits are bimodal — you see a loss lobe, paths where we bought and the contract died, and a win lobe where it paid. Here's the counterintuitive part: the winning strategy loses MORE often than not — fifty-nine percent of the time — and is still strongly profitable. Buying cheap cuts both ways: when you're wrong you've lost a smaller stake — twenty-nine cents versus forty for buy-and-hold — and when you're right, the payout is the same dollar bought at a discount. It doesn't lose less often; it loses less."));

// ---- Slide 17 ----
children.push(SLIDE(17, "Grounding in reality", "1 min"));
children.push(P("Are our dials realistic? We pull real price histories straight from Polymarket's public APIs — you can paste any market URL into our dashboard — and map them onto model inputs by method of moments: the lag-one autocovariance of price changes identifies the observation noise, the residual variance identifies the hidden volatility. Five real markets ship with the repo as offline samples, so everything works without wifi."));
children.push(P("The verdict: real hidden-volatility estimates run from 0.002 to 0.019 per hour-step, so our default of 0.02 sits at the realistic-but-volatile end — the right stress setting. And to repeat the scope guard: real data sets inputs only. We do not backtest on it, and we make no claims about real-world profits."));

// ---- Slide 18 ----
children.push(SLIDE(18, "Live demo", "4–5 min"));
children.push(P("Enough slides — let's break the market live."));
children.push(DIRECTION("Click “Open the dashboard”. Demo script, in order:"));
children.push(DIRECTION("1. Single Path Explorer: hit Resimulate two or three times. Say: “dashed line is the truth the trader can't see; blue is what they trade on.”"));
children.push(DIRECTION("2. Policy Lab: drag delta from 0.05 up to 0.15 and watch the verdict banner flip from ‘beats buy-and-hold’ to ‘no significant difference’. Say: “same market, same data — the strategy just stopped finding trades, and the confidence interval says so.”"));
children.push(DIRECTION("3. Load a real market: paste a Polymarket URL (or pick the NVIDIA bundled sample if wifi is down), click Fetch, then Prefill. Point out the real series overlaid on the simulation and the implied parameters."));
children.push(DIRECTION("4. News jumps: open the 🗞️ expander, toggle jumps on, Resimulate until a down-jump path appears. Say: “watch the strategy buy a dip that was actually news.”"));
children.push(DIRECTION("5. If time allows: Policy Grid tab — point at the outlined winner; Sensitivity tab — the kappa curve live."));
children.push(P("Everything you just saw is seeded — if you run this at home with the same seed, you get these exact paths, trades, and intervals."));

// ---- Slide 19 ----
children.push(SLIDE(19, "Conclusions", "1 min"));
children.push(P("To land the plane. A naive dip-buying rule beats buy-and-hold decisively in this model — ten cents per dollar contract, significant across the entire persistence range, surviving realistic fees. The threshold we went looking for doesn't exist: noise creates the edge, persistence only shapes it, and news erodes it linearly — all the way to a frontier we mapped, where the sign actually flips."));
children.push(P("The bigger lesson we'd offer: the most valuable output of a simulation study isn't the number you asked for — it's the mechanism it forces you to articulate. We asked how much persistence a trader needs. The model told us we'd asked the wrong question, and handed us a better one: count the noise, not the stickiness."));
children.push(P("Everything — code, thirty-seven tests, every CSV, the dashboard, and these slides — is on GitHub and regenerates from one seed. Thank you. Questions?"));
children.push(DIRECTION("Likely questions: “Can I make money on Polymarket with this?” → scope-guard answer: the approved model assumes all mispricing is noise; slides 14–15 show what news does, and real markets sit somewhere on that frontier — we haven't located them on it yet. “Why EMA and not something smarter?” → the point was whether even a naive rule finds the noise; smarter rules are future work. “Why is buy-and-hold exactly zero?” → martingale truth plus mean-zero noise at entry: it pays a fair price on average. “Why Bernoulli instead of a ‘real’ Poisson?” → Bernoulli-per-period IS the Poisson process in discrete time: geometric interarrivals are the discrete exponential, and the count converges to Poisson(λT); our whole model lives in discrete time, so this is the native formulation."));

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Calibri", size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal",
        run: { font: "Calibri", size: 34, bold: true, color: "1A1A19" } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal",
        run: { font: "Calibri", size: 28, bold: true, color: "1A1A19" } },
    ],
  },
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
  const out = path.join(ROOT, "slides", "Speaker_Script.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out, `(${(buf.length / 1024).toFixed(0)} KB)`);
});
