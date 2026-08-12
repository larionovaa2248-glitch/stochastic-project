# Presentation Slides

A self-contained HTML slide deck (18 slides, ~20 minutes including the live
demo). No build step, no dependencies — `index.html` plus the figure PNGs in
`assets/`.

## Present locally

Open `slides/index.html` in any browser (double-click works), or serve it:

```bash
python3 -m http.server 8700 --directory slides
```

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

Slide 17 links to the dashboard at `http://localhost:8601`. Before
presenting, start it:

```bash
streamlit run dashboard/app.py --server.port 8601
```

The dashboard is fully offline-capable (bundled sample markets), so the demo
works without venue Wi-Fi.

## Deploying to Vercel (when ready)

The deck is a static site rooted at this directory. From the repo root:

- **Dashboard link caveat:** the deployed deck's demo button still points to
  `localhost:8601`, which is correct for presenting from your laptop (the
  audience sees your screen). A deployed dashboard would require hosting
  Streamlit separately (e.g. Streamlit Community Cloud) and updating the link.
- Vercel setup: import the GitHub repo, set **Root Directory = `slides`**,
  framework preset **Other**, no build command, output directory `.` —
  or run `vercel deploy` from `slides/`.
