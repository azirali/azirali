#!/usr/bin/env python3
"""Builds the animated SVGs embedded in README.md (assets/dark, assets/light).

    pip install fonttools uharfbuzz
    python3 scripts/build_assets.py

Images in a README are shown through <img>, which can't load web fonts, so all
text is converted to outlines here. Fonts (Google Fonts, OFL) and tech icons
(skillicons.dev, MIT) are downloaded into .cache/ on the first run.
"""

from __future__ import annotations

import math
import random
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache"
OUT = ROOT / "assets"


# --------------------------------------------------------------------------
# Content
# --------------------------------------------------------------------------

TAGLINES = [
    "building web & mobile products",
    "shipping with Flutter, React & Node.js",
    "automating workflows with AI agents",
    "idea → design → code → production",
]

CODE = [
    "const olzhas = {",
    '  role: "Full-Stack Developer & Founder @ AZIRAL",',
    '  based: "Astana, Kazakhstan",',
    '  craft: ["ideation", "design", "development", "deployment"],',
    "  stack: {",
    '    web: ["TypeScript", "React", "Next.js", "Astro"],',
    '    mobile: ["Flutter", "Dart", "React Native"],',
    '    backend: ["Node.js", "Hono", "Python", "PostgreSQL"],',
    "  },",
    '  loves: ["clean code", "automation", "AI-first workflows"],',
    '  status: "open to new opportunities & collaborations",',
    "} as const;",
]

# (title, skillicons ids, extra chips without an icon)
STACK = [
    [
        ("Frontend", ["ts", "js", "react", "nextjs", "astro", "tailwind", "vite"], []),
        ("Design & Tools", ["figma", "vscode", "idea", "git", "github", "bash"], []),
    ],
    [
        ("Backend", ["nodejs", "express", "python", "fastapi", "java", "spring"], ["Hono", "REST APIs"]),
        ("Data & DevOps", ["postgres", "redis", "docker", "nginx", "linux", "githubactions"],
         ["Drizzle ORM", "Meilisearch", "Traefik"]),
    ],
    [
        ("Mobile", ["flutter", "dart", "react"], ["React Native", "iOS & Android"]),
        ("AI-first engineering", [], ["Claude Code", "Cursor", "OpenAI Codex", "Google Antigravity",
                                      "GitHub Copilot", "Agentic workflows", "LLM integrations"]),
    ],
]


@dataclass
class Project:
    slug: str
    name: str
    mark: str
    repo: str
    description: str
    stack: list[str]
    badge: str | None  # "live" | "private" | None
    accent: tuple[str, str]


PROJECTS = [
    Project("aziralpdf", "AziralPDF", "PDF", "azirali/AziralPDF-app",
            "Self-hosted PDF platform with 50+ tools, a REST API and a desktop app.",
            ["Java 25", "Spring Boot", "React", "TypeScript", "Docker"], None, ("#2F7BFF", "#22D3EE")),
    Project("crm", "AZIRAL CRM", "CRM", "azirali/AZIRAL-CRM",
            "Mobile-first business workspace: clients, projects, tasks, money and documents.",
            ["Flutter", "Dart", "FastAPI", "PostgreSQL", "Redis"], "private", ("#8B5CF6", "#2F7BFF")),
    Project("books", "Aziral Books", "BK", "AZIRALGROUP/aziral-books-backend",
            "Book catalog aggregator and OPDS API over Open Library, Gutendex and Internet Archive.",
            ["TypeScript", "Hono", "PostgreSQL", "Meilisearch"], None, ("#F59E0B", "#EF4444")),
    Project("ecotaxi", "EcoTaxi", "ET", "azirali/EcoTaxi",
            "Eco-friendly ride-hailing app with a complete 22-screen passenger flow.",
            ["React 19", "TypeScript", "Vite", "Tailwind 4"], "live", ("#10B981", "#22D3EE")),
    Project("videogen", "AI Video Generator", "AI", "azirali/aziral-video-gen",
            "From a topic to a finished marketing short: script, footage, voice-over, subtitles.",
            ["Python", "FastAPI", "Streamlit", "moviepy", "LLMs"], None, ("#EC4899", "#8B5CF6")),
    Project("solidcore", "Solidcore", "SC", "azirali/Solidcore",
            "Employee onboarding, training, tests and mood analytics with admin workspaces.",
            ["React 18", "TypeScript", "Vite", "Tailwind 4"], "live", ("#06B6D4", "#3B82F6")),
]

# Lucide icons (ISC, lucide-static 1.x); brand icons from lucide-brands.
ICONS = {
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/>'
             '<path d="M2 12h20"/>',
    "mail": '<path d="m22 7-8.991 5.727a2 2 0 0 1-2.009 0L2 7"/><rect x="2" y="4" width="20" height="16" rx="2"/>',
    "linkedin": '<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/>'
                '<rect width="4" height="12" x="2" y="9"/><circle cx="4" cy="4" r="2"/>',
    "instagram": '<rect width="20" height="20" x="2" y="2" rx="5" ry="5"/>'
                 '<path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>'
                 '<line x1="17.5" x2="17.51" y1="6.5" y2="6.5"/>',
    "arrow": '<path d="M7 7h10v10"/><path d="M7 17 17 7"/>',
    "sparkles": '<path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 '
                '0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0'
                '-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z"/>'
                '<path d="M20 2v4"/><path d="M22 4h-4"/><circle cx="4" cy="20" r="2"/>',
}

BUTTONS = [("website", "globe", "aziral.com"), ("linkedin", "linkedin", "LinkedIn"),
           ("email", "mail", "Email"), ("instagram", "instagram", "Instagram")]

SECTIONS = [("about", "01", "About me"), ("stack", "02", "Tech stack"),
            ("projects", "03", "Featured projects"), ("activity", "04", "GitHub activity")]


# --------------------------------------------------------------------------
# Themes
# --------------------------------------------------------------------------

@dataclass
class Theme:
    name: str
    bg: str
    panel: str
    panel2: str
    border: str
    text: str
    muted: str
    faint: str
    blue: str
    sky: str
    cyan: str
    violet: str
    green: str
    amber: str
    name_to: str
    shine: str
    star: str
    glow: float
    grid: str
    code: dict


DARK = Theme(
    "dark", bg="#05070E", panel="#0A0F1C", panel2="#111A2E", border="#1C2740", text="#E8EEF9",
    muted="#8A9BB8", faint="#4B5A75", blue="#2F7BFF", sky="#60A5FA", cyan="#22D3EE", violet="#8B5CF6",
    green="#22C55E", amber="#F59E0B", name_to="#8FB8FF", shine="#FFFFFF", star="#FFFFFF", glow=0.5,
    grid="#1A2540",
    code=dict(kw="#C4A1FF", prop="#7DD3FC", str="#9EE6A8", punct="#7D8BA6", ident="#E8EEF9"),
)
LIGHT = Theme(
    "light", bg="#F6F9FF", panel="#FFFFFF", panel2="#F1F5FD", border="#DCE4F2", text="#0B1324",
    muted="#56647D", faint="#A3AEC2", blue="#1F5EFF", sky="#3B82F6", cyan="#0891B2", violet="#7C3AED",
    green="#16A34A", amber="#D97706", name_to="#1F5EFF", shine="#FFFFFF", star="#1F5EFF", glow=0.2,
    grid="#D5DFF0",
    code=dict(kw="#7C3AED", prop="#0369A1", str="#15803D", punct="#64748B", ident="#0B1324"),
)


# --------------------------------------------------------------------------
# Downloads, fonts, text outlines
# --------------------------------------------------------------------------

def fetch(url: str, ua: str = "Mozilla/5.0") -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def cached(name: str, url: str, ua: str = "Mozilla/5.0") -> Path:
    path = CACHE / name
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(fetch(url, ua))
    return path


def font_path(family: str, weight: int) -> Path:
    path = CACHE / "fonts" / f"{family.replace(' ', '')}-{weight}.ttf"
    if not path.exists():
        # An old user agent makes the CSS API serve plain static .ttf files.
        css = fetch(f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:wght@{weight}",
                    ua="Mozilla/4.0").decode()
        url = re.search(r"url\((https://[^)]+\.ttf)\)", css).group(1)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(fetch(url))
    return path


def num(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


class Font:
    def __init__(self, family: str, weight: int):
        path = font_path(family, weight)
        self._hb = hb.Font(hb.Face(path.read_bytes()))
        tt = TTFont(path)
        self._glyphs = tt.getGlyphSet()
        self._names = tt.getGlyphOrder()
        self._upem = tt["head"].unitsPerEm

    def _shape(self, text: str):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self._hb, buf, {})
        return buf.glyph_infos, buf.glyph_positions

    def width(self, text: str, size: float, tracking: float = 0) -> float:
        _, pos = self._shape(text)
        return sum(p.x_advance for p in pos) * size / self._upem + tracking * size * max(len(pos) - 1, 0)

    def d(self, text: str, size: float, x: float, y: float, anchor: str = "start", tracking: float = 0) -> str:
        """SVG path data for `text` with its baseline at y."""
        if anchor != "start":
            w = self.width(text, size, tracking)
            x -= w / 2 if anchor == "middle" else w
        infos, pos = self._shape(text)
        s = size / self._upem
        pen = SVGPathPen(self._glyphs, ntos=num)
        for info, p in zip(infos, pos):
            self._glyphs[self._names[info.codepoint]].draw(
                TransformPen(pen, (s, 0, 0, -s, x + p.x_offset * s, y - p.y_offset * s)))
            x += p.x_advance * s + tracking * size
        return pen.getCommands()

    def text(self, text: str, size: float, x: float, y: float, fill: str, anchor: str = "start",
             tracking: float = 0, extra: str = "") -> str:
        return f'<path d="{self.d(text, size, x, y, anchor, tracking)}" fill="{fill}"{extra}/>'

    def wrap(self, text: str, size: float, max_width: float) -> list[str]:
        lines, line = [], ""
        for word in text.split():
            trial = f"{line} {word}".strip()
            if line and self.width(trial, size) > max_width:
                lines.append(line)
                line = word
            else:
                line = trial
        return lines + [line] if line else lines


DISPLAY = Font("Unbounded", 800)
DISPLAY_SEMI = Font("Unbounded", 600)
GROTESK = Font("Space Grotesk", 700)
SANS = Font("Inter", 400)
SANS_MEDIUM = Font("Inter", 500)
SANS_SEMI = Font("Inter", 600)
MONO = Font("JetBrains Mono", 400)
MONO_SEMI = Font("JetBrains Mono", 600)


def skill_icon(name: str, theme: Theme, x: float, y: float, size: float, uid: str) -> str:
    """A skillicons.dev icon inlined as a nested <svg> (no external requests at view time)."""
    raw = cached(f"icons/{name}-{theme.name}.svg",
                 f"https://skillicons.dev/icons?i={name}&theme={theme.name}").read_text()
    inner = re.search(r"<g transform=\"translate\(0, 0\)\">\s*(<svg.*</svg>)\s*</g>", raw, re.S).group(1)
    ids = set(re.findall(r'id="([^"]+)"', inner))
    for i in sorted(ids, key=len, reverse=True):
        inner = re.sub(rf'id="{re.escape(i)}"', f'id="{uid}-{i}"', inner)
        inner = re.sub(rf'(url\(#|href="#){re.escape(i)}([)"])', rf"\g<1>{uid}-{i}\2", inner)
    tag = re.match(r"<svg[^>]*>", inner).group(0)
    attrs = re.sub(r'\s(xmlns|width|height|x|y)="[^"]*"', "", tag[4:-1])
    return (f'<svg x="{num(x)}" y="{num(y)}" width="{num(size)}" height="{num(size)}"{attrs}>'
            + inner[len(tag):])


# --------------------------------------------------------------------------
# SVG helpers
# --------------------------------------------------------------------------

def document(w: int, h: int, label: str, defs: list[str], body: list[str]) -> str:
    attr = escape(label, {'"': "&quot;"})
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'fill="none" role="img" aria-label="{attr}"><title>{escape(label)}</title>'
            f'<defs>{"".join(defs)}</defs>{"".join(body)}</svg>\n')


def radial(id_: str, color: str, opacity: float) -> str:
    return (f'<radialGradient id="{id_}"><stop offset="0" stop-color="{color}" stop-opacity="{opacity}"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')


def glow_filter(id_: str, blur: float) -> str:
    return (f'<filter id="{id_}" x="-100%" y="-100%" width="300%" height="300%">'
            f'<feGaussianBlur stdDeviation="{blur}" result="b"/>'
            f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')


def discrete(id_attr: str, frames: list[tuple[float, float]], cycle: float) -> str:
    """A discrete SMIL animation from (time, value) frames over a looping cycle."""
    frames = sorted(frames)
    if frames[0][0] > 0:
        frames.insert(0, (0, frames[-1][1]))
    times = ";".join(f"{t / cycle:.5f}".rstrip("0").rstrip(".") or "0" for t, _ in frames)
    values = ";".join(num(v) for _, v in frames)
    return (f'<animate attributeName="{id_attr}" calcMode="discrete" dur="{cycle}s" '
            f'repeatCount="indefinite" keyTimes="{times}" values="{values}"/>')


def chip(label: str, x: float, y: float, t: Theme, size: float = 17, h: float = 36,
         fill: str | None = None, stroke: str | None = None, color: str | None = None,
         stroke_opacity: float = 1) -> tuple[str, float]:
    w = SANS_MEDIUM.width(label, size) + 28
    out = (f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{h}" rx="{h / 2}" '
           f'fill="{fill or t.panel2}" stroke="{stroke or t.border}" stroke-opacity="{stroke_opacity}"/>'
           + SANS_MEDIUM.text(label, size, x + 14, y + h / 2 + size * 0.36, color or t.text))
    return out, w


# --------------------------------------------------------------------------
# Assets
# --------------------------------------------------------------------------

def hero(t: Theme) -> str:
    W, H = 1200, 440
    rnd = random.Random(42)
    defs = [
        f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="28"/></clipPath>',
        radial("gBlue", t.blue, t.glow), radial("gViolet", t.violet, t.glow * 0.9), radial("gCyan", t.cyan, t.glow * 0.7),
        f'<pattern id="dots" width="28" height="28" patternUnits="userSpaceOnUse">'
        f'<circle cx="2" cy="2" r="1.3" fill="{t.grid}"/></pattern>',
        '<radialGradient id="fadeG" cx="0.75" cy="0.5" r="0.65"><stop offset="0" stop-color="#fff"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>',
        f'<mask id="fade"><rect width="{W}" height="{H}" fill="url(#fadeG)"/></mask>',
        f'<linearGradient id="nameG" gradientUnits="userSpaceOnUse" x1="72" y1="120" x2="640" y2="300">'
        f'<stop offset="0" stop-color="{t.text}"/><stop offset="0.55" stop-color="{t.text}"/>'
        f'<stop offset="1" stop-color="{t.name_to}"/></linearGradient>',
        f'<linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="260" y2="0" '
        f'gradientTransform="translate(-320 0)">'
        f'<stop offset="0" stop-color="{t.shine}" stop-opacity="0"/>'
        f'<stop offset="0.5" stop-color="{t.shine}" stop-opacity="{0.85 if t.name == "dark" else 0.75}"/>'
        f'<stop offset="1" stop-color="{t.shine}" stop-opacity="0"/>'
        f'<animateTransform attributeName="gradientTransform" type="translate" values="-320 0;760 0;760 0" '
        f'keyTimes="0;0.4;1" dur="6s" repeatCount="indefinite"/></linearGradient>',
        f'<linearGradient id="coreStroke" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t.cyan}"/>'
        f'<stop offset="1" stop-color="{t.blue}"/></linearGradient>',
        f'<radialGradient id="coreFill" cx="0.35" cy="0.3" r="0.9"><stop offset="0" stop-color="{t.panel2}"/>'
        f'<stop offset="1" stop-color="{t.bg}"/></radialGradient>',
        f'<linearGradient id="markG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t.cyan}"/>'
        f'<stop offset="1" stop-color="{t.blue}"/></linearGradient>',
        f'<linearGradient id="edge" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="600" y2="0" '
        f'gradientTransform="translate(-600 0)">'
        f'<stop offset="0" stop-color="{t.cyan}" stop-opacity="0"/><stop offset="0.5" stop-color="{t.cyan}"/>'
        f'<stop offset="1" stop-color="{t.blue}" stop-opacity="0"/>'
        f'<animateTransform attributeName="gradientTransform" type="translate" values="-600 0;1200 0" '
        f'dur="7s" repeatCount="indefinite"/></linearGradient>',
        glow_filter("glow", 4), glow_filter("softGlow", 10),
    ]
    body = ['<g clip-path="url(#frame)">', f'<rect width="{W}" height="{H}" fill="{t.bg}"/>',
            f'<rect width="{W}" height="{H}" fill="url(#dots)" mask="url(#fade)"/>']

    for cx, cy, r, grad, path, dur in ((900, 150, 380, "gBlue", "0 0;-70 50;0 0", 16),
                                      (1150, 430, 320, "gViolet", "0 0;-90 -40;0 0", 21),
                                      (120, -60, 320, "gCyan", "0 0;80 40;0 0", 18)):
        body.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#{grad})">'
                    f'<animateTransform attributeName="transform" type="translate" values="{path}" '
                    f'dur="{dur}s" repeatCount="indefinite"/></circle>')

    for _ in range(54):
        x, y = rnd.uniform(10, W - 10), rnd.uniform(10, H - 10)
        r = rnd.choice((0.7, 0.9, 1.1, 1.4, 1.8))
        peak = rnd.uniform(0.5, 1) * (1 if t.name == "dark" else 0.45)
        dur = rnd.uniform(2.5, 6)
        body.append(f'<circle cx="{num(x)}" cy="{num(y)}" r="{r}" fill="{t.star}" opacity="0">'
                    f'<animate attributeName="opacity" values="0;{num(peak)};0" dur="{num(dur)}s" '
                    f'begin="{num(-rnd.uniform(0, dur))}s" repeatCount="indefinite"/></circle>')

    # Orbit system: three tilted rings. Each planet is drawn twice, behind and in
    # front of the core, and only the copy on the correct side is visible.
    ox, oy, tilt = 925, 222, math.radians(-16)
    rings = [(118, 0.36, 9, 2, t.cyan), (176, 0.36, 15, 2, t.sky), (234, 0.36, 24, 3, t.violet)]
    back, front = [], []
    for i, (rx, k, dur, planets, color) in enumerate(rings):
        ry = rx * k
        dash = ' stroke-dasharray="2 7"' if i == 1 else ""
        back.append(f'<ellipse cx="{ox}" cy="{oy}" rx="{rx}" ry="{num(ry)}" transform="rotate(-16 {ox} {oy})" '
                    f'stroke="{t.sky}" stroke-opacity="{0.35 if t.name == "dark" else 0.45}" stroke-width="1.4"{dash}/>')
        for p in range(planets):
            steps = 72
            xs, ys, rs, back_op, front_op = [], [], [], [], []
            for s in range(steps + 1):
                a = 2 * math.pi * (s / steps + p / planets)
                ex, ey = rx * math.cos(a), ry * math.sin(a)
                xs.append(ox + ex * math.cos(tilt) - ey * math.sin(tilt))
                ys.append(oy + ex * math.sin(tilt) + ey * math.cos(tilt))
                depth = math.sin(a)  # >0: in front of the core
                rs.append(4.2 + 1.8 * depth)
                front_op.append(1 if depth >= 0 else 0)
                back_op.append(0.55 if depth < 0 else 0)
            anim = (f'<animate attributeName="cx" values="{";".join(num(v) for v in xs)}" dur="{dur}s" repeatCount="indefinite"/>'
                    f'<animate attributeName="cy" values="{";".join(num(v) for v in ys)}" dur="{dur}s" repeatCount="indefinite"/>'
                    f'<animate attributeName="r" values="{";".join(num(v) for v in rs)}" dur="{dur}s" repeatCount="indefinite"/>')
            for layer, ops in ((back, back_op), (front, front_op)):
                layer.append(f'<circle r="4" fill="{color}" filter="url(#glow)">{anim}'
                             f'<animate attributeName="opacity" values="{";".join(num(v) for v in ops)}" '
                             f'dur="{dur}s" repeatCount="indefinite"/></circle>')
    body += back
    for begin in (0, 1.5):
        body.append(f'<circle cx="{ox}" cy="{oy}" r="62" stroke="{t.cyan}" stroke-width="1.5" opacity="0">'
                    f'<animate attributeName="r" values="62;120" dur="3s" begin="{begin}s" repeatCount="indefinite"/>'
                    f'<animate attributeName="opacity" values="0.6;0" dur="3s" begin="{begin}s" repeatCount="indefinite"/>'
                    f'</circle>')
    body.append(f'<circle cx="{ox}" cy="{oy}" r="70" fill="{t.blue}" opacity="{0.22 if t.name == "dark" else 0.12}" '
                f'filter="url(#softGlow)"/>')
    body.append(f'<circle cx="{ox}" cy="{oy}" r="62" fill="url(#coreFill)" stroke="url(#coreStroke)" stroke-width="2"/>')
    body.append(DISPLAY.text("A", 64, ox + 2, oy + 24, "url(#markG)", anchor="middle"))
    body += front

    # Text block
    x0 = 72
    pill_label = "Open to collaborations"
    pw = SANS_SEMI.width(pill_label, 19) + 58
    body.append(f'<rect x="{x0}" y="66" width="{num(pw)}" height="40" rx="20" fill="{t.green}" '
                f'fill-opacity="{0.12 if t.name == "dark" else 0.08}" '
                f'stroke="{t.green}" stroke-opacity="0.45"/>')
    body.append(f'<circle cx="{x0 + 22}" cy="86" r="5" fill="{t.green}"/>'
                f'<circle cx="{x0 + 22}" cy="86" r="5" fill="{t.green}">'
                f'<animate attributeName="r" values="5;12" dur="1.8s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values="0.6;0" dur="1.8s" repeatCount="indefinite"/></circle>')
    body.append(SANS_SEMI.text(pill_label, 19, x0 + 40, 93, t.green))

    name_size = 84
    for line, y in (("Olzhas", 194), ("Azirali", 284)):
        d = DISPLAY.d(line, name_size, x0 - 4, y)
        body.append(f'<path d="{d}" fill="url(#nameG)"/><path d="{d}" fill="url(#shine)"/>')

    prefix = "Full-Stack Developer · Founder @ "
    body.append(SANS_MEDIUM.text(prefix, 25, x0, 340, t.muted))
    body.append(SANS_SEMI.text("AZIRAL", 25, x0 + SANS_MEDIUM.width(prefix, 25), 340, t.sky))

    # Typing tagline
    ty, size = 394, 23
    body.append(MONO_SEMI.text("$", size, x0, ty, t.cyan))
    tx = x0 + MONO.width("$ ", size)
    cw = MONO.width("a", size)
    slot, cycle = 5.0, 5.0 * len(TAGLINES)
    cursor = []
    for i, line in enumerate(TAGLINES):
        n, start = len(line), i * slot
        frames = [(start, 0)]
        frames += [(start + 0.15 + k * 0.045, k * cw) for k in range(1, n + 1)]
        erase_at = start + slot - 0.55
        frames += [(erase_at + k * 0.012, (n - k) * cw) for k in range(1, n + 1)]
        cursor += frames
        frames.append((start + slot - 0.01, 0))
        static_w = num(n * cw + 4) if i == 0 else "0"
        defs.append(f'<clipPath id="type{i}"><rect x="{num(tx)}" y="{ty - 30}" width="{static_w}" height="42">'
                    f'{discrete("width", frames, cycle)}</rect></clipPath>')
        body.append(f'<g clip-path="url(#type{i})">{MONO.text(line, size, tx, ty, t.text)}</g>')
    cursor_frames = [(time, tx + w + 3) for time, w in cursor]
    body.append(f'<rect x="{num(tx + len(TAGLINES[0]) * cw + 3)}" y="{ty - 21}" width="11" height="26" rx="2" '
                f'fill="{t.cyan}">'
                f'{discrete("x", cursor_frames, cycle)}'
                f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1s" '
                f'repeatCount="indefinite"/></rect>')

    body.append(MONO.text("51.17°N · 71.45°E — ASTANA", 15, W - 40, H - 32, t.faint, anchor="end",
                          tracking=0.08))
    body.append(f'<rect y="{H - 2}" width="{W}" height="2" fill="url(#edge)"/>')
    body.append("</g>")
    body.append(f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="27.5" stroke="{t.border}" '
                f'stroke-width="1.5"/>')
    return document(W, H, "Olzhas Azirali — Full-Stack Developer & Founder @ AZIRAL", defs, body)


def section(t: Theme, number: str, title: str) -> str:
    W, H = 1200, 92
    body = [MONO_SEMI.text(number, 22, 4, 56, t.cyan)]
    x = 4 + MONO_SEMI.width(number, 22) + 18
    body.append(f'<rect x="{num(x)}" y="36" width="2" height="26" rx="1" fill="{t.border}"/>')
    x += 22
    label = title.upper()
    body.append(DISPLAY_SEMI.text(label, 26, x, 59, t.text, tracking=0.1))
    start = x + DISPLAY_SEMI.width(label, 26, tracking=0.1) + 28
    defs = [f'<linearGradient id="line" gradientUnits="userSpaceOnUse" x1="{num(start)}" y1="0" x2="{W}" y2="0">'
            f'<stop offset="0" stop-color="{t.blue}"/><stop offset="0.6" stop-color="{t.violet}" stop-opacity="0.35"/>'
            f'<stop offset="1" stop-color="{t.violet}" stop-opacity="0"/></linearGradient>',
            glow_filter("glow", 3)]
    body.append(f'<rect x="{num(start)}" y="48" width="{num(W - start)}" height="2" rx="1" fill="url(#line)"/>')
    body.append(f'<circle cy="49" r="4" fill="{t.cyan}" filter="url(#glow)">'
                f'<animate attributeName="cx" values="{num(start)};{W - 40}" dur="3.5s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.75;1" dur="3.5s" '
                f'repeatCount="indefinite"/></circle>')
    return document(W, H, title, defs, body)


def tokenize(line: str):
    pattern = re.compile(r'("(?:[^"\\]|\\.)*")|\b(const|as)\b|([A-Za-z_]\w*)(?=:)|([A-Za-z_$][\w$]*)|(\s+)|(.)')
    for m in pattern.finditer(line):
        s, kw, prop, ident, space, punct = m.groups()
        kind = "str" if s else "kw" if kw else "prop" if prop else "ident" if ident else None if space else "punct"
        yield m.group(0), kind


def about(t: Theme) -> str:
    W = 1200
    bar, pad, lh, size = 58, 30, 38, 22
    status = 38
    H = bar + pad * 2 + lh * len(CODE) + status
    cw = MONO.width("a", size)
    code_x, top = 104, bar + pad + 26
    defs = [f'<clipPath id="win"><rect width="{W}" height="{H}" rx="22"/></clipPath>',
            f'<linearGradient id="wm" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t.cyan}"/>'
            f'<stop offset="1" stop-color="{t.violet}"/></linearGradient>',
            radial("aGlow", t.blue, t.glow * 0.6)]
    body = ['<g clip-path="url(#win)">', f'<rect width="{W}" height="{H}" fill="{t.panel}"/>',
            '<circle cx="1060" cy="250" r="320" fill="url(#aGlow)"/>',
            DISPLAY.text("A", 340, 1030, 470, "url(#wm)", anchor="middle",
                         extra=f' opacity="{0.08 if t.name == "dark" else 0.06}"'),
            f'<rect width="{W}" height="{bar}" fill="{t.panel2}"/>',
            f'<rect y="{bar - 1}" width="{W}" height="1" fill="{t.border}"/>']
    for i, c in enumerate(("#FF5F57", "#FEBC2E", "#28C840")):
        body.append(f'<circle cx="{32 + i * 24}" cy="{bar / 2}" r="7" fill="{c}"/>')
    tab_w = MONO_SEMI.width("olzhas.ts", 17) + 64
    body.append(f'<rect x="120" y="12" width="{num(tab_w)}" height="{bar - 12}" rx="10" fill="{t.panel}"/>'
                f'<rect x="120" y="{bar - 6}" width="{num(tab_w)}" height="6" fill="{t.panel}"/>')
    body.append(f'<rect x="136" y="{bar / 2 - 5}" width="22" height="16" rx="3" fill="#3178C6"/>')
    body.append(MONO_SEMI.text("TS", 10, 147, bar / 2 + 7, "#FFFFFF", anchor="middle"))
    body.append(MONO_SEMI.text("olzhas.ts", 17, 168, bar / 2 + 9, t.text))
    body.append(MONO.text("~/aziral/profile", 16, W - 32, bar / 2 + 7, t.faint, anchor="end"))

    begin = 0.3
    for i, line in enumerate(CODE):
        y = top + i * lh
        body.append(MONO.text(str(i + 1), size, code_x - 34, y, t.faint, anchor="end"))
        parts, col = [], 0
        for tok, kind in tokenize(line):
            if kind:
                parts.append(MONO.text(tok, size, code_x + col * cw, y, t.code[kind]))
            col += len(tok)
        dur = max(0.18, len(line) * 0.012)
        full = num(len(line) * cw + 8)
        defs.append(f'<clipPath id="ln{i}"><rect x="{code_x - 2}" y="{y - 28}" width="{full}" height="{lh}">'
                    f'<animate attributeName="width" values="0;0;{full}" keyTimes="0;{begin / (begin + dur):.3f};1" '
                    f'dur="{num(begin + dur)}s" fill="freeze"/></rect></clipPath>')
        body.append(f'<g clip-path="url(#ln{i})">{"".join(parts)}</g>')
        begin += dur + 0.06
    last_y = top + (len(CODE) - 1) * lh
    body.append(f'<rect x="{num(code_x + len(CODE[-1]) * cw + 4)}" y="{last_y - 21}" width="11" height="26" rx="2" '
                f'fill="{t.cyan}" opacity="0"><set attributeName="opacity" to="1" begin="{num(begin)}s"/>'
                f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1s" '
                f'begin="{num(begin)}s" repeatCount="indefinite"/></rect>')

    sy = H - status
    body.append(f'<rect y="{sy}" width="{W}" height="{status}" fill="{t.blue}"/>')
    left = ["main", "0 problems", "Astana, KZ"]
    x = 24
    for item in left:
        body.append(MONO.text(item, 15, x, sy + 25, "#FFFFFF"))
        x += MONO.width(item, 15) + 34
    body.append(MONO.text(f"Ln {len(CODE)}, Col {len(CODE[-1]) + 1}   UTF-8   TypeScript", 15, W - 24, sy + 25,
                          "#FFFFFF", anchor="end"))
    body.append("</g>")
    body.append(f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="21.5" stroke="{t.border}" '
                f'stroke-width="1.5"/>')
    alt = "olzhas.ts — " + " ".join(line.strip() for line in CODE)
    return document(W, H, alt, defs, body)


def stack(t: Theme) -> str:
    W, gap, pad = 1200, 24, 26
    pw = (W - gap) / 2
    icon, icon_gap = 58, 18
    title_h, icons_h, chip_h, chip_gap = 64, icon + 22, 36, 10

    def chip_rows(chips, width):
        rows, row, x = [], [], 0
        for c in chips:
            w = SANS_MEDIUM.width(c, 17) + 28
            if row and x + w > width:
                rows.append(row)
                row, x = [], 0
            row.append(c)
            x += w + chip_gap
        return rows + [row] if row else rows

    def panel_height(icons, chips):
        h = title_h + (icons_h if icons else 0)
        rows = chip_rows(chips, pw - pad * 2)
        return h + len(rows) * (chip_h + chip_gap) + pad - (0 if rows else 8)

    defs = [glow_filter("glow", 3),
            f'<linearGradient id="aiBorder" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="600" y2="0">'
            f'<stop offset="0" stop-color="{t.violet}"/><stop offset="0.5" stop-color="{t.cyan}"/>'
            f'<stop offset="1" stop-color="{t.blue}"/>'
            f'<animateTransform attributeName="gradientTransform" type="translate" values="0 0;300 0;0 0" '
            f'dur="8s" repeatCount="indefinite"/></linearGradient>']
    body, y, n = [], 0, 0
    for row in STACK:
        rh = max(panel_height(icons, chips) for _, icons, chips in row)
        for col, (title, icons, chips) in enumerate(row):
            x = col * (pw + gap)
            ai = not icons
            stroke = "url(#aiBorder)" if ai else t.border
            body.append(f'<rect x="{num(x + 0.75)}" y="{num(y + 0.75)}" width="{num(pw - 1.5)}" height="{num(rh - 1.5)}" '
                        f'rx="22" fill="{t.panel}" stroke="{stroke}" stroke-width="1.5"/>')
            body.append(f'<rect x="{num(x + pad)}" y="{y + 30}" width="4" height="18" rx="2" '
                        f'fill="{t.violet if ai else t.blue}"/>')
            body.append(DISPLAY_SEMI.text(title.upper(), 17, x + pad + 16, y + 46, t.text, tracking=0.12))
            if ai:
                ix = x + pw - pad - 24
                body.append(f'<g transform="translate({num(ix)} {y + 27}) scale(1)" stroke="{t.violet}" '
                            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS["sparkles"]}</g>')
            cy = y + title_h
            for k, name in enumerate(icons):
                ix = x + pad + k * (icon + icon_gap)
                delay = 0.2 + n * 0.04
                n += 1
                kt = f"0;{delay / (delay + 0.5):.3f};1"
                body.append(f'<g>{skill_icon(name, t, ix, cy, icon, f"{name}{n}")}'
                            f'<animate attributeName="opacity" values="0;0;1" keyTimes="{kt}" dur="{num(delay + 0.5)}s" '
                            f'fill="freeze"/><animateTransform attributeName="transform" type="translate" '
                            f'values="0 10;0 10;0 0" keyTimes="{kt}" dur="{num(delay + 0.5)}s" fill="freeze"/></g>')
            if icons:
                cy += icons_h
            for r in chip_rows(chips, pw - pad * 2):
                cx = x + pad
                for c in r:
                    if ai:
                        out, w = chip(c, cx, cy, t, stroke=t.violet, stroke_opacity=0.35)
                    else:
                        out, w = chip(c, cx, cy, t)
                    body.append(out)
                    cx += w + chip_gap
                cy += chip_h + chip_gap
        y += rh + gap
    H = int(y - gap)
    names = "; ".join(f"{title}: " + ", ".join(icons + chips) for row in STACK for title, icons, chips in row)
    return document(W, H, f"Tech stack — {names}", defs, body)


def project(t: Theme, p: Project) -> str:
    W, H, pad = 600, 304, 32
    a1, a2 = p.accent
    defs = [f'<clipPath id="card"><rect width="{W}" height="{H}" rx="24"/></clipPath>',
            radial("glow", a1, 0.38 if t.name == "dark" else 0.16),
            f'<linearGradient id="tile" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a1}"/>'
            f'<stop offset="1" stop-color="{a2}"/></linearGradient>',
            f'<linearGradient id="sweep" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="240" y2="0" '
            f'gradientTransform="translate(-300 0)">'
            f'<stop offset="0" stop-color="{a2}" stop-opacity="0"/><stop offset="0.5" stop-color="{a2}"/>'
            f'<stop offset="1" stop-color="{a2}" stop-opacity="0"/>'
            f'<animateTransform attributeName="gradientTransform" type="translate" values="-300 0;900 0;900 0" '
            f'keyTimes="0;0.45;1" dur="7s" begin="{PROJECTS.index(p) * 0.6}s" repeatCount="indefinite"/>'
            f'</linearGradient>']
    body = ['<g clip-path="url(#card)">', f'<rect width="{W}" height="{H}" fill="{t.panel}"/>',
            '<circle cx="40" cy="20" r="260" fill="url(#glow)"/>', "</g>",
            f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="23.25" stroke="{t.border}" stroke-width="1.5"/>',
            f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="23.25" stroke="url(#sweep)" '
            f'stroke-width="1.5" opacity="0.9"/>']
    body.append(f'<rect x="{pad}" y="{pad}" width="64" height="64" rx="18" fill="url(#tile)"/>')
    size = 22 if len(p.mark) < 3 else 17
    body.append(DISPLAY.text(p.mark, size, pad + 32, pad + 32 + size * 0.37, "#FFFFFF", anchor="middle"))
    body.append(GROTESK.text(p.name, 31, pad + 84, pad + 30, t.text))
    body.append(MONO.text(p.repo, 16, pad + 84, pad + 58, t.muted))

    if p.badge:
        color, label = (t.green, "LIVE") if p.badge == "live" else (t.amber, "PRIVATE")
        bw = MONO_SEMI.width(label, 14, tracking=0.1) + (44 if p.badge == "live" else 28)
        bx = W - pad - bw
        body.append(f'<rect x="{num(bx)}" y="{pad + 4}" width="{num(bw)}" height="30" rx="15" fill="{color}" '
                    f'fill-opacity="0.12" stroke="{color}" stroke-opacity="0.45"/>')
        tx = bx + 14
        if p.badge == "live":
            body.append(f'<circle cx="{num(bx + 17)}" cy="{pad + 19}" r="4" fill="{color}">'
                        f'<animate attributeName="opacity" values="1;0.3;1" dur="1.6s" repeatCount="indefinite"/></circle>')
            tx = bx + 30
        body.append(MONO_SEMI.text(label, 14, tx, pad + 24, color, tracking=0.1))
    else:
        body.append(f'<g transform="translate({W - pad - 26} {pad + 6}) scale(1.1)" stroke="{t.muted}" '
                    f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS["arrow"]}</g>')

    for i, line in enumerate(SANS.wrap(p.description, 22, W - pad * 2)[:3]):
        body.append(SANS.text(line, 22, pad, pad + 122 + i * 32, t.text, extra=' opacity="0.86"'))

    cx, cy = pad, H - pad - 34
    for s in p.stack:
        w = SANS_MEDIUM.width(s, 16) + 26
        if cx + w > W - pad:
            break
        body.append(f'<rect x="{num(cx)}" y="{cy}" width="{num(w)}" height="34" rx="17" fill="{t.panel2}" '
                    f'stroke="{t.border}"/>')
        body.append(SANS_MEDIUM.text(s, 16, cx + 13, cy + 22.5, t.muted))
        cx += w + 8
    alt = f"{p.name} — {p.description} Stack: {', '.join(p.stack)}."
    return document(W, H, alt, defs, body)


def button(t: Theme, icon: str, label: str) -> str:
    H, pad, size = 64, 24, 22
    W = int(pad + 26 + 14 + SANS_SEMI.width(label, size) + pad + 2)
    defs = [f'<linearGradient id="b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t.cyan}" '
            f'stop-opacity="0.8"/><stop offset="1" stop-color="{t.violet}" stop-opacity="0.8"/></linearGradient>']
    body = [f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="{(H - 2) / 2}" fill="{t.panel}" '
            f'stroke="url(#b)" stroke-width="1.5"/>',
            f'<g transform="translate({pad} {(H - 26) / 2}) scale({26 / 24})" stroke="{t.sky}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICONS[icon]}</g>',
            SANS_SEMI.text(label, size, pad + 26 + 14, H / 2 + size * 0.36, t.text)]
    return document(W, H, label, defs, body)


def footer(t: Theme) -> str:
    W, H = 1200, 250
    defs = [f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="28"/></clipPath>']
    body = ['<g clip-path="url(#frame)">', f'<rect width="{W}" height="{H}" fill="{t.bg}"/>']
    waves = [(t.violet, 0.22, 168, 14, 600, 0, 19), (t.blue, 0.3, 182, 12, 400, 1.3, 13), (t.cyan, 0.22, 198, 10, 300, 2.1, 9)]
    for i, (color, op, base, amp, period, phase, dur) in enumerate(waves):
        pts = [(x, base + amp * math.sin(2 * math.pi * x / period + phase)) for x in range(0, W + period + 1, 10)]
        d = "M0 " + num(H) + " " + " ".join(f"L{x} {num(y)}" for x, y in pts) + f" L{W + period} {H} Z"
        defs.append(f'<linearGradient id="w{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{color}" '
                    f'stop-opacity="{op * (1 if t.name == "dark" else 0.8)}"/><stop offset="1" stop-color="{color}" '
                    f'stop-opacity="0.04"/></linearGradient>')
        body.append(f'<path d="{d}" fill="url(#w{i})"><animateTransform attributeName="transform" type="translate" '
                    f'values="0 0;-{period} 0" dur="{dur}s" repeatCount="indefinite"/></path>')
    body.append(DISPLAY_SEMI.text("Thanks for stopping by", 36, W / 2, 86, t.text, anchor="middle"))
    tail = "Let's build something great together — "
    full = tail + "aziral.com"
    x = W / 2 - SANS.width(full, 23) / 2
    body.append(SANS.text(tail, 23, x, 128, t.muted))
    body.append(SANS_SEMI.text("aziral.com", 23, x + SANS.width(tail, 23), 128, t.sky))
    body.append("</g>")
    body.append(f'<rect x="0.75" y="0.75" width="{W - 1.5}" height="{H - 1.5}" rx="27.5" stroke="{t.border}" '
                f'stroke-width="1.5"/>')
    return document(W, H, "Thanks for stopping by — let's build something great together: aziral.com", defs, body)


def main() -> None:
    for t in (DARK, LIGHT):
        out = OUT / t.name
        out.mkdir(parents=True, exist_ok=True)
        files = {"hero.svg": hero(t), "about.svg": about(t), "stack.svg": stack(t), "footer.svg": footer(t)}
        for key, number, title in SECTIONS:
            files[f"section-{key}.svg"] = section(t, number, title)
        for p in PROJECTS:
            files[f"project-{p.slug}.svg"] = project(t, p)
        for key, icon, label in BUTTONS:
            files[f"button-{key}.svg"] = button(t, icon, label)
        for name, content in files.items():
            (out / name).write_text(content)
        print(f"{t.name}: {len(files)} files")


if __name__ == "__main__":
    main()
