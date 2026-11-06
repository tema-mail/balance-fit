// Ядро редактора: разбирает HTML, не пересобирая его. Наружу – только позиции в строке, поэтому всё,
// что не правили, остаётся байт в байт: рантайм Тильды и чужие скрипты этого требуют (опыт 06.11.2026).
// Без зависимостей: тот же код работает при сборке и в браузере.

// Содержимое этих тегов – не видимый текст страницы.
const RAW = new Set(['script', 'style', 'textarea', 'noscript', 'svg', 'template', 'iframe', 'title', 'xmp']);
const ENT = {
  nbsp: ' ', amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", laquo: '«', raquo: '»', mdash: '—', ndash: '–',
  hellip: '…', copy: '©', reg: '®', trade: '™', deg: '°', times: '×', rarr: '→', larr: '←', bull: '•', middot: '·',
  shy: '­', thinsp: ' ', ensp: ' ', emsp: ' ', rsquo: '’', lsquo: '‘', ldquo: '“', rdquo: '”', bdquo: '„', minus: '−', num: '№',
};
const IMG_RE = /\.(jpe?g|png|webp|gif|svg|avif)(\?|$)/i;

export const decode = (s) => s.replace(/&(#x?[0-9a-f]+|[a-z]+);/gi, (m, e) => {
  if (e[0] !== '#') return ENT[e] ?? m;
  const c = e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
  try { return String.fromCodePoint(c); } catch { return m; }
});

/** Сравниваем тексты без учёта вида пробелов: браузер и исходник пишут их по-разному. */
export const norm = (s) => s.replace(/[     ]/g, ' ').replace(/[­​]/g, '').replace(/\s+/g, ' ').trim();
export const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const escAttr = (s) => esc(s).replace(/"/g, '&quot;').replace(/'/g, '&#39;');

export const stripBase = (p, base = '') => (base && (p === base || p.startsWith(base + '/')) ? p.slice(base.length) || '/' : p);
export const withBase = (p, base = '') => (p.startsWith('/') && !p.startsWith('//') ? base + p : p);

/** Разрешённые адреса кнопок. javascript: и data: не пропускаем ни в браузере, ни при сборке. */
export const safeHref = (h) => { const v = String(h).trim(); return /^(https?:\/\/|mailto:|tel:|#|\/(?!\/))/i.test(v) && !/[\s<>"'`\\]/.test(v); };

/** Ключ кнопки: браузер и сборка считают пробелы внутри ссылки по-разному, поэтому сравниваем без них. */
export const linkKey = (s) => norm(s).replace(/\s+/g, '');

/** Обход тегов и текста. onText(start, end), onTag({ name, close, start, end }). */
export function scan(html, onText, onTag) {
  const hasBody = /<body[\s>]/i.test(html);
  let inBody = !hasBody;
  let i = 0;
  const n = html.length;
  const text = (s, e) => { if (inBody && e > s) onText(s, e); };
  while (i < n) {
    const lt = html.indexOf('<', i);
    if (lt < 0) { text(i, n); break; }
    text(i, lt);
    if (html.startsWith('<!--', lt)) { const e = html.indexOf('-->', lt + 4); i = e < 0 ? n : e + 3; continue; }
    if (html[lt + 1] === '!' || html[lt + 1] === '?') { const e = html.indexOf('>', lt); i = e < 0 ? n : e + 1; continue; }
    const close = html[lt + 1] === '/';
    let j = lt + (close ? 2 : 1);
    const s = j;
    while (j < n && /[^\s/>]/.test(html[j])) j++;
    const name = html.slice(s, j).toLowerCase();
    if (!/^[a-z]/.test(name)) { text(lt, lt + 1); i = lt + 1; continue; } // одинокий «<» в тексте
    let q = '';
    while (j < n) {
      const c = html[j];
      if (q) { if (c === q) q = ''; } else if (c === '"' || c === "'") q = c; else if (c === '>') break;
      j++;
    }
    const end = Math.min(j + 1, n);
    const selfClose = html[j - 1] === '/';
    if (name === 'body' && !close) inBody = true;
    if (name === 'body' && close) inBody = false;
    if (inBody) onTag({ name, close, start: lt, end });
    i = end;
    if (!close && !selfClose && RAW.has(name)) {
      const re = new RegExp(`</${name}[\\s>]`, 'i');
      const rest = html.slice(end);
      const m = re.exec(rest);
      if (!m) { i = n; continue; }
      i = end + m.index;
    }
  }
}

function hrefOf(tag) {
  const m = /\shref\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))/i.exec(tag);
  if (!m) return null;
  const value = m[2] ?? m[3] ?? m[4] ?? '';
  const valueStart = m.index + m[0].length - m[1].length + (m[2] !== undefined || m[3] !== undefined ? 1 : 0);
  return { value, start: valueStart, end: valueStart + value.length };
}

function splice(html, parts) {
  if (!parts.length) return html;
  parts.sort((a, b) => a[0] - b[0]);
  let out = '';
  let at = 0;
  for (const [s, e, r] of parts) { out += html.slice(at, s) + r; at = e; }
  return out + html.slice(at);
}

const inScope = (edit, page) => edit.scope === 'all' || edit.scope === page;

function applyText(html, edit) {
  const parts = [];
  scan(html, (s, e) => {
    const raw = html.slice(s, e);
    if (norm(decode(raw)) !== edit.old) return;
    const lead = /^\s*/.exec(raw)[0];
    const trail = /\s*$/.exec(raw)[0];
    parts.push([s, e, lead + esc(edit.new) + trail]);
  }, () => {});
  return [splice(html, parts), parts.length];
}

function applyLink(html, edit, base) {
  const parts = [];
  let a = null;
  scan(html, (s, e) => { if (a) a.text.push(html.slice(s, e)); }, (t) => {
    if (t.name !== 'a') return;
    if (t.close) {
      if (a && a.href && stripBase(decode(a.href.value), base) === edit.old && linkKey(decode(a.text.join(''))) === linkKey(edit.text ?? '')) {
        parts.push([a.href.start, a.href.end, escAttr(withBase(edit.new, base))]);
      }
      a = null;
      return;
    }
    const href = hrefOf(html.slice(t.start, t.end));
    a = { href: href && { ...href, start: t.start + href.start, end: t.start + href.end }, text: [] };
  });
  return [splice(html, parts), parts.length];
}

function applyImage(html, edit, base) {
  const from = withBase(edit.old, base);
  const to = withBase(edit.new, base);
  // размытая заготовка той же картинки (`папка/-/resize/20x/имя`), иначе при загрузке мелькнёт старое фото
  // у Тильды она в другой ветке: большая /_t/static/<папка>/имя, заготовка /_t/thb/<папка>/-/resize/20x/имя
  const rx = (t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const parts = from.split('/');
  const name = parts.pop();
  const folder = parts.pop();
  const thumb = new RegExp(`[^"'\\s()]*/${rx(folder)}/-/[^"'\\s()]*/${rx(name)}`, 'g');
  let out = folder ? html.replace(thumb, to) : html;
  const count = out.split(from).length - 1;
  out = out.split(from).join(to);
  // тот же путь в JSON внутри скриптов записан с \/
  const fromJ = from.replace(/\//g, '\\/');
  const countJ = out.split(fromJ).length - 1;
  if (countJ) out = out.split(fromJ).join(to.replace(/\//g, '\\/'));
  return [out, count + countJ];
}

/** Накладывает правки по порядку. Возвращает новый HTML и сколько раз сработала каждая правка. */
export function applyEdits(html, page, edits, base = '') {
  const hits = {};
  let out = html;
  for (const edit of edits) {
    if (!inScope(edit, page) || !edit.new) continue;
    if (edit.type === 'link' && !safeHref(edit.new)) continue;
    const [next, n] = edit.type === 'text' ? applyText(out, edit)
      : edit.type === 'link' ? applyLink(out, edit, base)
      : edit.type === 'image' ? applyImage(out, edit, base)
      : [out, 0];
    out = next;
    if (n) hits[edit.id] = n;
  }
  return { html: out, hits };
}

function imagesOfTag(tag, add) {
  for (const m of tag.matchAll(/\s(?:src|data-original|data-src|data-lazy-src)\s*=\s*["']([^"']+)["']/gi)) add(m[1]);
  for (const m of tag.matchAll(/url\(\s*(?:&quot;|["'])?([^"')&]+)(?:&quot;|["'])?\s*\)/gi)) add(m[1]);
}

/** Что на странице можно править: видимые тексты, картинки, ссылки. Для индекса редактора. */
export function extract(html, base = '') {
  const texts = {};
  const images = {};
  const links = [];
  let a = null;
  scan(html, (s, e) => {
    const raw = html.slice(s, e);
    if (a) a.text.push(raw);
    const k = norm(decode(raw));
    if (/[\p{L}\p{N}]/u.test(k)) texts[k] = (texts[k] || 0) + 1;
  }, (t) => {
    if (t.name === 'a') {
      if (t.close) {
        if (a && a.href) links.push({ href: stripBase(decode(a.href), base), text: norm(decode(a.text.join(''))) });
        a = null;
      } else {
        const h = hrefOf(html.slice(t.start, t.end));
        a = { href: h && h.value, text: [] };
      }
    }
    if (t.close) return;
    imagesOfTag(html.slice(t.start, t.end), (u) => {
      const clean = decode(u).trim();
      if (clean.startsWith('data:') || !IMG_RE.test(clean)) return;
      const k = stripBase(clean, base);
      images[k] = (images[k] || 0) + 1;
    });
  });
  const title = /<title[^>]*>([^<]*)<\/title>/i.exec(html);
  return { title: title ? norm(decode(title[1])) : '', texts, images, links };
}
