# Presentation Slides

A self-contained HTML slide deck (19 slides, ~20 minutes including the live
demo). No build step, no dependencies — `index.html` plus the figure PNGs in
`assets/`.

## Present locally (recommended)

```bash
python3 slides/present.py
```

This serves the deck at http://localhost:8700, opens it in your browser, and
— the important part — makes the demo slide's **"Open the dashboard" button
start Streamlit automatically**: click it and the button shows "Starting the
dashboard…", boots `dashboard/app.py` on port 8601, waits until it answers,
and opens it. No separate terminal needed. (Stopping `present.py` leaves a
started dashboard running.)

Alternatively, open `slides/index.html` directly or serve it with any static
server — everything works except the auto-start: then launch the dashboard
yourself first (`streamlit run dashboard/app.py`).

Controls: **←/→** (or space / click) to navigate · **N** toggles speaker
notes · **Home/End** jump · URL hash (`#/12`) deep-links a slide · print to
PDF via the browser for a handout.

## Speaker script

`Speaker_Script.docx` is a verbatim presenter script — one section per slide
with timing marks (~20 minutes total), stage directions in italics, a
pre-talk setup checklist, the 5-step demo walkthrough, and prepared answers
for likely questions. Regenerate it with:

```bash
npm install docx && node slides/build_speaker_script.js
```

## The live-demo slide

Slide 18's button opens the dashboard at `http://localhost:8601`. When the
deck is served by `present.py` the button starts it for you; otherwise start
it before presenting:

```bash
streamlit run dashboard/app.py --server.port 8601
```

Tip: click the button once ~a minute before the demo so the first boot and
cache warm-up happen off-stage. The dashboard is fully offline-capable
(bundled sample markets), so the demo works without venue Wi-Fi.

## Deploying to Vercel (when ready)

The deck is a static site rooted at this directory. From the repo root:

- **Dashboard link caveat:** the deployed deck's demo button still points to
  `localhost:8601`, which is correct for presenting from your laptop (the
  audience sees your screen). A deployed dashboard would require hosting
  Streamlit separately (e.g. Streamlit Community Cloud) and updating the link.
- Vercel setup: import the GitHub repo, set **Root Directory = `slides`**,
  framework preset **Other**, no build command, output directory `.` —
  or run `vercel deploy` from `slides/`.
