#!/usr/bin/env node
// site-editor build: накладывает правки на собранный сайт и готовит данные для панели.
// Шаг сборки сайта: astro build && site-editor build. Ошибка в одной правке сборку не роняет:
// правка, которая не нашлась, попадает в отчёт и видна в панели.
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { applyEdits, extract, linkKey } from '../lib/html.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));

function args(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i++) if (argv[i].startsWith('--')) out[argv[i].slice(2)] = argv[++i];
  return out;
}

function htmlFiles(dir, root = dir) {
  const out = [];
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      const rel = path.relative(root, p);
      if (rel === 'admin' || rel === '_astro' || rel === '_t') continue; // кабинет и ресурсы – не страницы сайта
      out.push(...htmlFiles(p, root));
    } else if (e.name.endsWith('.html')) out.push(p);
  }
  return out;
}

export const pagePath = (rel) => {
  const p = '/' + rel.split(path.sep).join('/');
  return p.endsWith('/index.html') ? p.slice(0, -'index.html'.length) : p;
};
const dataName = (page) => (page === '/' ? 'index' : page.replace(/^\/|\/$/g, '').replace(/[^\p{L}\p{N}._-]+/gu, '__')) + '.json';
const isRedirect = (html) => /<meta[^>]+http-equiv=["']?refresh/i.test(html);

export function build({ dist = 'dist', edits: editsFile = 'editor/edits.json', base = process.env.PUBLIC_BASE || '', admin = 'admin/editor' }) {
  base = base.replace(/\/$/, '');
  const list = existsSync(editsFile) ? JSON.parse(readFileSync(editsFile, 'utf8')).edits ?? [] : [];
  const hits = {};
  const pages = [];
  for (const file of htmlFiles(dist)) {
    const source = readFileSync(file, 'utf8');
    if (isRedirect(source)) continue;
    const page = pagePath(path.relative(dist, file));
    const { html, hits: h } = applyEdits(source, page, list, base);
    if (html !== source) writeFileSync(file, html);
    for (const [id, n] of Object.entries(h)) hits[id] = (hits[id] || 0) + n;
    pages.push({ page, ...extract(html, base) });
  }

  // на скольких страницах встречается: панель спрашивает «менять везде?»
  const where = { texts: {}, images: {}, links: {} };
  const keyOf = (l) => l.href + '\n' + linkKey(l.text);
  for (const p of pages) {
    for (const k of Object.keys(p.texts)) where.texts[k] = (where.texts[k] || 0) + 1;
    for (const k of Object.keys(p.images)) where.images[k] = (where.images[k] || 0) + 1;
    for (const k of new Set(p.links.map(keyOf))) where.links[k] = (where.links[k] || 0) + 1;
  }

  const out = path.join(dist, admin);
  const data = path.join(out, 'data');
  rmSync(data, { recursive: true, force: true });
  mkdirSync(data, { recursive: true });
  for (const p of pages) {
    writeFileSync(path.join(data, dataName(p.page)), JSON.stringify({
      page: p.page,
      texts: Object.entries(p.texts).map(([t, n]) => ({ t, n, pages: where.texts[t] })),
      images: Object.entries(p.images).map(([src, n]) => ({ src, n, pages: where.images[src] })),
      links: p.links.map((l) => ({ ...l, pages: where.links[keyOf(l)] })),
    }));
  }
  const orphans = list.filter((e) => !hits[e.id]).map((e) => e.id);
  const index = pages.map((p) => ({ page: p.page, title: p.title, data: dataName(p.page) })).sort((a, b) => a.page.localeCompare(b.page));
  writeFileSync(path.join(data, 'pages.json'), JSON.stringify(index));
  writeFileSync(path.join(data, 'report.json'), JSON.stringify({ at: new Date().toISOString(), edits: list.length, applied: list.length - orphans.length, orphans }));

  const assets = path.join(HERE, '..', 'assets');
  if (existsSync(assets)) cpSync(assets, path.join(out, 'assets'), { recursive: true });
  return { pages: pages.length, edits: list.length, orphans };
}

if (process.argv[1] && path.resolve(process.argv[1]).endsWith('site-editor.mjs') || process.argv[1]?.endsWith('site-editor')) {
  const [cmd, ...rest] = process.argv.slice(2);
  if (cmd !== 'build') { console.error('Использование: site-editor build [--dist dist] [--edits editor/edits.json] [--base /подпапка]'); process.exit(2); }
  const r = build(args(rest));
  console.log(`site-editor: страниц ${r.pages}, правок ${r.edits}${r.orphans.length ? `, не нашлись: ${r.orphans.join(', ')}` : ''}`);
}
