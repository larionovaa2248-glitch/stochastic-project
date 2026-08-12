"""Build a single-file version of the slide deck with all images embedded.

    python slides/build_standalone.py

Writes slides/Trading_Against_Noise_Slides.html — one double-clickable file
that renders the full deck anywhere, no server and no assets folder needed.
(The live-demo button falls back to plainly opening localhost:8601, since
the one-click boot needs present.py.)
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

SLIDES = Path(__file__).resolve().parent
SRC = SLIDES / "index.html"
OUT = SLIDES / "Trading_Against_Noise_Slides.html"

html = SRC.read_text(encoding="utf-8")

def inline(match: re.Match) -> str:
    rel = match.group(1)
    data = (SLIDES / rel).read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f'src="data:image/png;base64,{b64}"'

html, n = re.subn(r'src="(assets/[^"]+\.png)"', inline, html)
OUT.write_text(html, encoding="utf-8")
print(f"inlined {n} images -> {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")
