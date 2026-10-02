// Renders assets/header-{dark,light}.svg: the animated banner at the top of the README.
// Pure SVG + CSS animation, so it works inside GitHub's <img> sandbox without external services.
import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');

const THEMES = {
  dark: { bg: '#0A0A0A', grid: '#1A1A1A', text: '#F5F3EE', muted: '#8A8A8A', accent: '#0047FF', glow: '#0047FF' },
  light: { bg: '#F5F3EE', grid: '#E8E5DF', text: '#0A0A0A', muted: '#6B6B6B', accent: '#0047FF', glow: '#7FA3FF' },
};

const ROLES = ['Full-stack developer', 'Founder of AZIRAL', 'Open-source author'];
const W = 1200;
const H = 320;

// The AZIRAL "A" mark as a constellation: two strokes, a crossbar, and stars on the joints.
const STARS = [
  [160, 70], [100, 250], [220, 250], [127, 190], [193, 190],
];
const LINES = [
  [0, 1], [0, 2], [3, 4],
];

const header = (t) => {
  const grid = [];
  for (let x = 0; x <= W; x += 40) grid.push(`<line x1="${x}" y1="0" x2="${x}" y2="${H}"/>`);
  for (let y = 0; y <= H; y += 40) grid.push(`<line x1="0" y1="${y}" x2="${W}" y2="${y}"/>`);

  const lines = LINES.map(([a, b], i) => {
    const [x1, y1] = STARS[a];
    const [x2, y2] = STARS[b];
    const len = Math.hypot(x2 - x1, y2 - y1).toFixed(1);
    return `<line class="draw" style="--len:${len};animation-delay:${0.2 + i * 0.35}s" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
  }).join('\n      ');
  const stars = STARS.map(
    ([x, y], i) => `<circle class="star" style="animation-delay:${1.2 + i * 0.25}s" cx="${x}" cy="${y}" r="6"/>`,
  ).join('\n      ');

  const cycle = ROLES.length * 3; // seconds per full loop
  const roles = ROLES.map(
    (role, i) => `<text class="role" style="animation-delay:${i * 3}s" x="300" y="220">${role}</text>`,
  ).join('\n    ');

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Olzhas Azirali: full-stack developer, founder of AZIRAL, open-source author">
  <style>
    .name { font: 700 64px system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; fill: ${t.text}; letter-spacing: -1.5px; }
    .kicker { font: 600 15px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; fill: ${t.accent}; letter-spacing: 3px; }
    .role { font: 400 30px system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; fill: ${t.muted}; opacity: 0; animation: role ${cycle}s infinite; }
    .meta { font: 400 15px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; fill: ${t.muted}; }
    .cursor { fill: ${t.accent}; animation: blink 1s steps(1) infinite; }
    .grid line { stroke: ${t.grid}; stroke-width: 1; }
    .draw { stroke: ${t.accent}; stroke-width: 3; stroke-linecap: round; stroke-dasharray: var(--len); stroke-dashoffset: var(--len); animation: draw 1s ease-out forwards; }
    .star { fill: ${t.accent}; opacity: 0; animation: twinkle 3s ease-in-out infinite; }
    .glow { animation: pulse 6s ease-in-out infinite; transform-origin: 160px 170px; }
    @keyframes draw { to { stroke-dashoffset: 0; } }
    @keyframes twinkle { 0%, 100% { opacity: .35; } 50% { opacity: 1; } }
    @keyframes pulse { 0%, 100% { opacity: .45; transform: scale(1); } 50% { opacity: .8; transform: scale(1.08); } }
    @keyframes role { 0% { opacity: 0; transform: translateY(8px); } 4%, 29% { opacity: 1; transform: translateY(0); } 33%, 100% { opacity: 0; transform: translateY(-8px); } }
    @keyframes blink { 50% { opacity: 0; } }
    @media (prefers-reduced-motion: reduce) {
      .draw { stroke-dashoffset: 0; animation: none; }
      .star { opacity: 1; animation: none; }
      .glow { animation: none; }
      .role { animation: none; }
      .role:first-of-type { opacity: 1; }
      .cursor { animation: none; }
    }
  </style>
  <defs>
    <radialGradient id="glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="${t.glow}" stop-opacity=".55"/>
      <stop offset="100%" stop-color="${t.glow}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="fade" x1="0" x2="1" y1="0" y2="0">
      <stop offset="0%" stop-color="${t.bg}" stop-opacity="0"/>
      <stop offset="100%" stop-color="${t.bg}" stop-opacity="1"/>
    </linearGradient>
    <clipPath id="frame"><rect width="${W}" height="${H}" rx="16"/></clipPath>
  </defs>
  <g clip-path="url(#frame)">
    <rect width="${W}" height="${H}" fill="${t.bg}"/>
    <g class="grid">
      ${grid.join('')}
    </g>
    <rect x="${W / 2}" width="${W / 2}" height="${H}" fill="url(#fade)"/>
    <circle class="glow" cx="160" cy="170" r="190" fill="url(#glow)"/>
    <g>
      ${lines}
      ${stars}
    </g>
    <text class="kicker" x="300" y="92">ASTANA, KAZAKHSTAN · AZIRAL.COM</text>
    <text class="name" x="296" y="160">Olzhas Azirali</text>
    ${roles}
    <rect class="cursor" x="300" y="246" width="14" height="3"/>
    <text class="meta" x="${W - 40}" y="${H - 32}" text-anchor="end">building products from idea to production</text>
  </g>
</svg>
`;
};

await mkdir(join(root, 'assets'), { recursive: true });
for (const [name, theme] of Object.entries(THEMES)) {
  await writeFile(join(root, `assets/header-${name}.svg`), header(theme));
}
console.log('Rendered assets/header-{dark,light}.svg');
