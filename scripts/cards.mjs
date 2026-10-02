// Renders assets/cards/*.svg: project cards and a stats strip for the README, in dark and light.
// Live numbers (stars, language, npm downloads, merged PRs) come from the GitHub and npm APIs;
// the nightly workflow re-runs this script. Any API failure falls back to the last known values
// or hides that number, so a flaky API never breaks the profile.
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const USER = 'azirali';

const PROJECTS = [
  {
    slug: 'lucide-brands',
    repo: 'azirali/lucide-brands',
    title: 'lucide-brands',
    description: 'The brand icons lucide removed in 1.1, back as drop-in React, Vue and vanilla JS icons, plus a codemod that migrates a project in one command.',
    tags: ['npm', 'React', 'Vue', 'Codemod'],
    npm: 'lucide-brands',
    featured: true,
  },
  {
    slug: 'aziral-video-gen',
    repo: 'azirali/aziral-video-gen',
    title: 'AI Video Generator',
    description: 'Topic in, finished marketing short out: script, stock footage, voice-over and subtitles.',
    tags: ['Python', 'FastAPI', 'LLMs'],
  },
  {
    slug: 'ecotaxi',
    repo: 'azirali/EcoTaxi',
    title: 'EcoTaxi',
    description: 'Eco-friendly ride-hailing app with a 22-screen passenger flow.',
    tags: ['React 19', 'TypeScript', 'Tailwind 4'],
  },
  {
    slug: 'solidcore',
    repo: 'azirali/Solidcore',
    title: 'Solidcore',
    description: 'Employee onboarding, training, tests and mood analytics, with employee and admin workspaces.',
    tags: ['React', 'TypeScript', 'Vite'],
  },
  {
    slug: 'aziral-books',
    repo: 'AZIRALGROUP/aziral-books-backend',
    title: 'Aziral Books',
    description: 'Book catalog aggregator over OPDS, Open Library and the Internet Archive.',
    tags: ['TypeScript', 'Hono', 'PostgreSQL'],
  },
];

const LANGUAGE_COLORS = {
  TypeScript: '#3178C6', JavaScript: '#F1E05A', Python: '#3572A5', Dart: '#00B4AB', Java: '#B07219',
  Vue: '#41B883', Kotlin: '#A97BFF', Go: '#00ADD8', Rust: '#DEA584', HTML: '#E34C26', CSS: '#563D7C', Shell: '#89E051',
};

const THEMES = {
  dark: { bg: '#0A0A0A', border: '#262626', text: '#F5F3EE', muted: '#8A8A8A', accent: '#0047FF', chip: '#161616' },
  light: { bg: '#FFFFFF', border: '#E8E5DF', text: '#0A0A0A', muted: '#6B6B6B', accent: '#0047FF', chip: '#F5F3EE' },
};

const SANS = "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
const MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace';

const escape = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const compact = (n) => (n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : String(n));

// Rough word wrap for SVG text (no layout engine): average glyph width ~0.53em for system-ui.
function wrap(text, width, fontSize, maxLines) {
  const perLine = Math.floor(width / (fontSize * 0.53));
  const lines = [];
  let line = '';
  for (const word of text.split(' ')) {
    if ((line + ' ' + word).trim().length > perLine) {
      lines.push(line.trim());
      line = word;
    } else {
      line += ' ' + word;
    }
  }
  if (line.trim()) lines.push(line.trim());
  if (lines.length > maxLines) {
    lines.length = maxLines;
    lines[maxLines - 1] = lines[maxLines - 1].replace(/\s*\S*$/, '') + '…';
  }
  return lines;
}

async function getJson(url, headers = {}) {
  try {
    const res = await fetch(url, { headers: { 'user-agent': `${USER}-profile-cards`, ...headers } });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return await res.json();
  } catch (error) {
    console.warn(`! ${url}: ${error.message}`);
    return null;
  }
}

const github = (path) =>
  getJson(`https://api.github.com${path}`, {
    accept: 'application/vnd.github+json',
    ...(process.env.GITHUB_TOKEN ? { authorization: `Bearer ${process.env.GITHUB_TOKEN}` } : {}),
  });

async function brandIconPaths(names) {
  const icons = [];
  for (const name of names) {
    try {
      const res = await fetch(`https://cdn.jsdelivr.net/npm/lucide-brands/svg/${name}.svg`);
      if (!res.ok) throw new Error(String(res.status));
      const svg = await res.text();
      icons.push(svg.replace(/^[\s\S]*?<svg[^>]*>/, '').replace(/<\/svg>\s*$/, '').trim());
    } catch (error) {
      console.warn(`! icon ${name}: ${error.message}`);
    }
  }
  return icons;
}

function chip(x, y, label, t) {
  const w = Math.round(label.length * 6.9 + 18);
  return {
    width: w,
    svg: `<rect x="${x}" y="${y}" width="${w}" height="22" rx="11" fill="${t.chip}" stroke="${t.border}"/><text x="${x + w / 2}" y="${y + 15}" text-anchor="middle" font-family="${MONO}" font-size="11.5" fill="${t.muted}">${escape(label)}</text>`,
  };
}

function card(project, data, t, icons) {
  const W = project.featured ? 840 : 410;
  const H = project.featured ? 200 : 180;
  const pad = 24;
  const parts = [];

  parts.push(`<rect x=".5" y=".5" width="${W - 1}" height="${H - 1}" rx="14" fill="${t.bg}" stroke="${t.border}"/>`);
  if (project.featured) {
    parts.push(`<rect x=".5" y=".5" width="4" height="${H - 1}" rx="2" fill="${t.accent}"/>`);
    parts.push(`<text x="${pad}" y="${pad + 6}" font-family="${MONO}" font-size="11" letter-spacing="2" fill="${t.accent}">OPEN SOURCE · ON NPM</text>`);
  }

  const titleY = project.featured ? pad + 38 : pad + 18;
  parts.push(`<text x="${pad}" y="${titleY}" font-family="${SANS}" font-size="${project.featured ? 26 : 20}" font-weight="700" fill="${t.text}">${escape(project.title)}</text>`);

  // Stars: top right on regular cards; right after the title on the featured one (the icons sit top right)
  if (data.stars != null) {
    const starX = project.featured ? pad + project.title.length * 15 + 18 : W - pad - 70;
    parts.push(
      `<g transform="translate(${starX} ${titleY - 17})"><path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z" fill="${t.muted}"/><text x="22" y="13" font-family="${MONO}" font-size="14" fill="${t.text}">${compact(data.stars)}</text></g>`,
    );
  }

  const descWidth = project.featured ? W - pad * 2 - 260 : W - pad * 2;
  const lines = wrap(project.description, descWidth, 14, project.featured ? 3 : 3);
  lines.forEach((line, i) =>
    parts.push(`<text x="${pad}" y="${titleY + 28 + i * 20}" font-family="${SANS}" font-size="14" fill="${t.muted}">${escape(line)}</text>`),
  );

  // Bottom row: language, npm numbers, tags
  let x = pad;
  const y = H - pad - 16;
  if (data.language) {
    parts.push(`<circle cx="${x + 6}" cy="${y + 11}" r="6" fill="${LANGUAGE_COLORS[data.language] ?? t.muted}"/>`);
    parts.push(`<text x="${x + 18}" y="${y + 15}" font-family="${SANS}" font-size="13" fill="${t.text}">${escape(data.language)}</text>`);
    x += 26 + data.language.length * 7.5;
  }
  if (data.version) {
    const c = chip(x, y, `v${data.version}`, t);
    parts.push(c.svg);
    x += c.width + 8;
  }
  if (data.downloads != null) {
    const c = chip(x, y, `${compact(data.downloads)} downloads/mo`, t);
    parts.push(c.svg);
    x += c.width + 8;
  }
  for (const tag of project.tags.filter((tag) => tag !== data.language)) {
    const c = chip(x, y, tag, t);
    if (x + c.width > W - pad) break;
    parts.push(c.svg);
    x += c.width + 8;
  }

  // Featured: a row of the actual icons from the package
  if (project.featured && icons.length) {
    const size = 34;
    const gap = 18;
    const perRow = 5;
    const startX = W - pad - perRow * size - (perRow - 1) * gap;
    icons.slice(0, 10).forEach((inner, i) => {
      const ix = startX + (i % perRow) * (size + gap);
      const iy = pad + 28 + Math.floor(i / perRow) * (size + gap);
      parts.push(
        `<g class="icon" style="animation-delay:${(i * 0.12).toFixed(2)}s" transform="translate(${ix} ${iy}) scale(${size / 24})" fill="none" stroke="${i % 3 === 0 ? t.accent : t.text}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${inner}</g>`,
      );
    });
  }

  const style = project.featured
    ? `<style>.icon{opacity:0;animation:in .5s ease-out forwards}@keyframes in{from{opacity:0}to{opacity:1}}@media (prefers-reduced-motion:reduce){.icon{opacity:1;animation:none}}</style>`
    : '';
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${escape(project.title)}: ${escape(project.description)}">${style}${parts.join('')}</svg>\n`;
}

function stats(s, t) {
  const W = 840;
  const H = 110;
  const items = [
    ['Public repos', s.repos],
    ['Stars earned', s.stars],
    ['Merged PRs', s.mergedPrs],
    ['npm downloads/mo', s.downloads],
  ];
  const cell = W / items.length;
  const parts = [`<rect x=".5" y=".5" width="${W - 1}" height="${H - 1}" rx="14" fill="${t.bg}" stroke="${t.border}"/>`];
  items.forEach(([label, value], i) => {
    const cx = cell * i + cell / 2;
    if (i > 0) parts.push(`<line x1="${cell * i}" y1="24" x2="${cell * i}" y2="${H - 24}" stroke="${t.border}"/>`);
    parts.push(`<text x="${cx}" y="56" text-anchor="middle" font-family="${SANS}" font-size="30" font-weight="700" fill="${i === 0 ? t.accent : t.text}">${value == null ? '—' : compact(value)}</text>`);
    parts.push(`<text x="${cx}" y="82" text-anchor="middle" font-family="${MONO}" font-size="11" letter-spacing="1.5" fill="${t.muted}">${escape(label.toUpperCase())}</text>`);
  });
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${items.map(([l, v]) => `${l}: ${v ?? 'n/a'}`).join(', ')}">${parts.join('')}</svg>\n`;
}

// ---------------------------------------------------------------------------

const cachePath = join(root, 'assets/cards/data.json');
const cache = JSON.parse(await readFile(cachePath, 'utf8').catch(() => '{}'));
const keep = (fresh, old) => (fresh ?? old ?? null);

const projectData = {};
for (const project of PROJECTS) {
  const old = cache.projects?.[project.slug] ?? {};
  const repo = await github(`/repos/${project.repo}`);
  const data = { stars: keep(repo?.stargazers_count, old.stars), language: keep(repo?.language, old.language) };
  if (project.npm) {
    const meta = await getJson(`https://registry.npmjs.org/${project.npm}/latest`);
    const dl = await getJson(`https://api.npmjs.org/downloads/point/last-month/${project.npm}`);
    data.version = keep(meta?.version, old.version);
    data.downloads = keep(dl?.downloads, old.downloads);
  }
  projectData[project.slug] = data;
}

const user = await github(`/users/${USER}`);
const repos = await github(`/users/${USER}/repos?per_page=100&type=owner`);
const prs = await github(`/search/issues?q=${encodeURIComponent(`author:${USER} type:pr is:merged`)}&per_page=1`);
const oldStats = cache.stats ?? {};
const totals = {
  repos: keep(user?.public_repos, oldStats.repos),
  stars: keep(Array.isArray(repos) ? repos.filter((r) => !r.fork).reduce((sum, r) => sum + r.stargazers_count, 0) : null, oldStats.stars),
  mergedPrs: keep(prs?.total_count, oldStats.mergedPrs),
  downloads: keep(
    Object.values(projectData).reduce((sum, d) => (d.downloads == null ? sum : (sum ?? 0) + d.downloads), null),
    oldStats.downloads,
  ),
};

const icons = await brandIconPaths(['github', 'linkedin', 'youtube', 'instagram', 'figma', 'slack', 'twitter', 'gitlab', 'twitch', 'dribbble']);

await mkdir(join(root, 'assets/cards'), { recursive: true });
for (const [theme, t] of Object.entries(THEMES)) {
  for (const project of PROJECTS) {
    await writeFile(join(root, `assets/cards/${project.slug}-${theme}.svg`), card(project, projectData[project.slug], t, icons));
  }
  await writeFile(join(root, `assets/cards/stats-${theme}.svg`), stats(totals, t));
}
await writeFile(cachePath, `${JSON.stringify({ projects: projectData, stats: totals }, null, 2)}\n`);
console.log('Rendered cards:', JSON.stringify({ projects: projectData, stats: totals }));
