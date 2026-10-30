"""Копия ~/Documents/ev-sibir/server/page_seo.py (эталон карточки страницы, EV SIBIR) без изменений – запускается
обёрткой scripts/page-cards.py с подменой данных под Milovini. Обновлять копированием из эталона, не правкой."""
"""Карточка страницы для админки: что реально стоит в SEO на выложенной странице.

Всё читается из самого HTML в SITE_ROOT, ничего не берётся из отдельного
списка — иначе карточка со временем разошлась бы с тем, что опубликовано.

Частотности запросов (Яндекс по Новосибирску, показы в Яндексе и Google) —
внешние данные, из кода сайта их взять нельзя. Они приходят из снапшотов в
server/data/ и подмешиваются в seo_map.py: Wordstat и позиции в выдаче —
XMLRiver, показы — Google Search Console. Там, где ответа по фразе ещё нет,
колонка остаётся пустой, а не заполняется выдуманным числом или нулём.
"""

import html
import json
import pathlib
import re

CSS = """
.prow a.pcard{text-decoration:none;color:inherit}
.pd{max-width:960px;margin:0 auto}
.pd .back{display:inline-block;margin:0 0 14px;font-size:13px;color:#005653;text-decoration:none}
.pd h1{margin:0 0 4px;font-size:20px;font-weight:600;line-height:1.3}
.pd .url{font-size:13px;color:#005653;word-break:break-all}
.pd .hero{display:flex;gap:16px;align-items:flex-start;background:#fff;border:1px solid #dfe4e3;
 border-radius:12px;padding:16px;margin-bottom:14px}
.pd .hero img,.pd .hero .nobadge{width:120px;height:88px;border-radius:9px;object-fit:cover;
 background:#eef1f0;flex:0 0 auto}
.pd .kind{display:inline-block;margin-top:8px;font-size:12px;color:#77817e}
.fld{padding:11px 0;border-bottom:1px solid #f0f3f2}
.fld:last-child{border-bottom:none}
.fld .k{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#77817e;margin-bottom:4px}
.fld .v{font-size:14px;line-height:1.5;word-break:break-word}
.fld .v.none{color:#b3261e}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{display:inline-block;background:#eef3f1;border-radius:6px;padding:2px 8px;font-size:12px;color:#36423f}
.chip.warn{background:#fdecea;color:#b3261e}
.alts{display:flex;flex-wrap:wrap;gap:8px}
.alt{display:flex;gap:7px;align-items:center;background:#f7f9f8;border:1px solid #eceff0;border-radius:8px;
 padding:4px 8px 4px 4px;max-width:100%}
.alt img{width:34px;height:26px;border-radius:5px;object-fit:cover;background:#eef1f0;flex:0 0 auto}
.alt span{font-size:11px;line-height:1.35;color:#55605d;word-break:break-word}
.alt.empty span{color:#a8b0ad;font-style:italic}
.checks{margin:0;padding:0;list-style:none;font-size:14px;line-height:1.8}
.checks li span{display:inline-block;width:18px;font-weight:600}
.checks .yes span{color:#136c2e}
.checks .no span{color:#b3261e}
.kwt{width:100%;border-collapse:collapse;font-size:13px}
.kwt th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#77817e;
 font-weight:600;padding:0 10px 8px 0;vertical-align:bottom}
.kwt td{padding:8px 10px 8px 0;border-top:1px solid #f0f3f2;vertical-align:top}
.kwt td.num{color:#a8b0ad;text-align:right;white-space:nowrap}
.note{margin:12px 0 0;font-size:13px;line-height:1.5;color:#55605d;background:#fffaf0;
 border:1px solid #f0d9a8;border-radius:9px;padding:11px 13px}
@media(max-width:700px){.pd .hero{flex-direction:column}.kwt th:nth-child(n+2),.kwt td:nth-child(n+2){font-size:12px}}
"""


def _text(s: str) -> str:
    """Снимает теги и схлопывает пробелы — для заголовков, внутри которых
    попадаются <br> и вложенные span."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _attr(tag: str, name: str) -> str:
    m = re.search(rf'{name}="([^"]*)"', tag)
    return html.unescape(m.group(1)) if m else ""


def _ld_types(src: str):
    """Типы схем Schema.org, которые реально отдаются на странице."""
    types = []
    for block in re.findall(
        r'<script type="application/ld\+json"[^>]*>(.*?)</script>', src, re.S
    ):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            t = item.get("@type") if isinstance(item, dict) else None
            if isinstance(t, str):
                types.append((t, item))
    return types


def _badge(route: str, shots) -> str:
    """Та же плашка, что и в списке страниц: сначала фото самой модели,
    потом любая картинка, кроме фона первого экрана."""
    slug = route.strip("/").rsplit("/", 1)[-1]
    return next(
        (x for x in shots if slug and x.rsplit("/", 1)[-1].rsplit(".", 1)[0] == slug),
        next((x for x in shots if "hero" not in x.rsplit("/", 1)[-1]), shots[0] if shots else ""),
    )


def cluster_of(route: str) -> str:
    """Кластер — к какой группе запросов относится страница. Считается из
    адреса: структура раздела и есть структура кластеров."""
    parts = [p for p in route.split("/") if p]
    if route == "/":
        return "Общий спрос: техцентр китайских авто в Новосибирске"
    if parts and parts[0] == "legal":
        return "Юридические документы — вне поискового продвижения"
    if parts and parts[0] == "service":
        if len(parts) == 1:
            return "Хаб раздела: техобслуживание китайских электромобилей"
        brand = parts[1].replace("-", " ").upper()
        if len(parts) == 2:
            return f"Марка {brand}: сервис, ТО, ремонт, русификация"
        return f"Модель {brand} {parts[2].upper()}: ТО и обслуживание конкретной модели"
    if parts and parts[0] == "rusifikaciya":
        countries = {"kitay": "китайских", "yaponiya": "японских", "koreya": "корейских", "germaniya": "немецких"}
        if len(parts) == 1:
            return "Хаб русификации: любые марки и страны ввоза"
        if parts[1] in countries:
            return f"Русификация {countries[parts[1]]} автомобилей: страновой хаб"
        if len(parts) >= 3:
            return f"Русификация {parts[1].upper()} {parts[2].upper()}: конкретная модель"
        return f"Русификация {parts[1].replace('-', ' ').upper()}: марка, все рынки"
    return "Служебная страница — из поиска закрыта"


def read_page(site_root: str, route: str):
    """Собирает карточку одной страницы. None, если такой страницы нет."""
    root = pathlib.Path(site_root)
    rel = route.strip("/")
    f = root / "index.html" if not rel else root / rel / "index.html"
    if not f.is_file():
        return None
    src = f.read_text(encoding="utf-8", errors="ignore")

    title = re.search(r"<title>(.*?)</title>", src, re.S)
    desc = re.search(r'name="description" content="(.*?)"', src)
    keys = re.search(r'name="keywords" content="(.*?)"', src)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", src, re.S)

    # только контентные картинки: иконки интерфейса декоративные, у них alt
    # пустой намеренно, и в списке они были бы шумом
    imgs = []
    for tag in re.findall(r"<img\b[^>]*>", src):
        s = _attr(tag, "src")
        if s.startswith("/images/"):
            imgs.append({"src": s, "alt": _attr(tag, "alt").strip()})

    ld = _ld_types(src)
    ld_names = [t for t, _ in ld]
    faq = next((o for t, o in ld if t == "FAQPage"), None)

    body_text = _text(re.sub(r"<(script|style)\b.*?</\1>", " ", src, flags=re.S))
    low = body_text.lower()

    # Есть ли страница в llms.txt и в поиске по сайту — используется в блоке GEO.
    llms = (root / "llms.txt")
    in_llms = route in llms.read_text(encoding="utf-8", errors="ignore") if llms.is_file() else False
    idx = (root / "search-index.json")
    in_index = False
    if idx.is_file():
        try:
            in_index = any(e.get("url") == route for e in json.loads(idx.read_text(encoding="utf-8")))
        except ValueError:
            in_index = False

    # Короткий прямой ответ в начале страницы: и быстрый ответ поисковика,
    # и генеративный ответ забирают первый осмысленный абзац. Берём текст
    # между H1 и первым H2 — на наших шаблонах это вступление.
    intro = ""
    if h1:
        after_h1 = src[h1.end():]
        chunk = after_h1[: after_h1.find("<h2")] if "<h2" in after_h1 else after_h1[:4000]
        paras = [_text(x) for x in re.findall(r"<p[^>]*>(.*?)</p>", chunk, re.S)]
        # порог в 20 слов отсекает подзаголовок героя и приписку про цену:
        # ответом считается только содержательный абзац, а не подпись
        intro = next((t for t in paras if len(t.split()) >= 20), "")
    intro_words = len(intro.split())

    # AEO — попадание в прямые ответы: быстрый ответ («нулевая позиция»),
    # расширенные сниппеты, блок «люди спрашивают». Поисковик забирает
    # готовый фрагмент, поэтому на странице он должен существовать отдельно.
    aeo = [
        ("Блок вопросов и ответов (FAQPage)",
         bool(faq),
         f'{len(faq.get("mainEntity", []))} вопросов' if faq else "на странице нет блока FAQ"),
        ("Короткий ответ сразу под H1",
         bool(intro) and intro_words <= 70,
         f"{intro_words} слов во вступлении" if intro else "под H1 нет абзаца-ответа"),
        ("Таблица или список с ценами",
         "₽" in body_text and ("<table" in src or "<ul" in src or "<ol" in src),
         "из таблиц и списков собирают расширенный сниппет"),
        ("Хлебные крошки (BreadcrumbList)", "BreadcrumbList" in ld_names, "путь до страницы размечен"),
    ]

    # GEO — Generative Engine Optimization: цитируемость страницы в ответах
    # генеративного поиска (Яндекс Нейро, Google AI Overviews, ChatGPT,
    # Perplexity). Это не геолокация: привязка к городу — отдельный блок ниже.
    # Такой ответ собирается из самодостаточных фрагментов с конкретикой,
    # поэтому проверяем разметку, доступ ИИ-роботам и наличие фактов.
    robots = (root / "robots.txt")
    robots_text = robots.read_text(encoding="utf-8", errors="ignore") if robots.is_file() else ""
    ai_bots = ("GPTBot", "OAI-SearchBot", "PerplexityBot", "ClaudeBot", "Google-Extended")
    blocked = [b for b in ai_bots if re.search(rf"User-agent:\s*{b}[\s\S]{{0,200}}?Disallow:\s*/\s", robots_text, re.I)]
    numbers = len(re.findall(r"\b\d[\d\s]*(?:₽|км|кВт|мес|год|лет|часов|дней)", body_text))
    geo = [
        ("Страница в llms.txt", in_llms, "карта сайта для ИИ-поисковиков"),
        ("Разметка Schema.org", bool(ld_names),
         ", ".join(sorted(set(ld_names))) if ld_names else "на странице нет JSON-LD"),
        ("Проверяемая конкретика в тексте", numbers >= 3,
         f"чисел с единицами: {numbers} — цены, сроки, мощности"),
        ("ИИ-роботам доступ не закрыт", not blocked,
         f"robots.txt закрывает: {', '.join(blocked)}" if blocked else "GPTBot, OAI-SearchBot, PerplexityBot и другие"),
        ("Страница в поиске по сайту", in_index, "search-index.json"),
    ]

    # Локальное SEO — то, что раньше стояло в этой админке под именем GEO:
    # привязка к Новосибирску. Термин GEO в поиске 2026 занят генеративной
    # выдачей, поэтому блоки разведены.
    local_ld = next((o for t, o in ld if t in ("AutoRepair", "LocalBusiness", "AutoDealer")), None)
    addr = ""
    if local_ld:
        a = local_ld.get("address") or {}
        addr = ", ".join(x for x in [a.get("addressLocality"), a.get("streetAddress")] if x)
    local = [
        ("Схема организации с адресом", bool(local_ld), addr or "нет разметки организации"),
        ("Город в Title", "новосибирск" in (title.group(1).lower() if title else ""), "запрос почти всегда с городом"),
        ("Город в описании", "новосибирск" in (desc.group(1).lower() if desc else ""), "показывается в выдаче"),
        ("Город в тексте страницы", "новосибирск" in low, f"упоминаний: {low.count('новосибирск')}"),
    ]

    return {
        "route": route,
        "title": _text(title.group(1)) if title else "",
        "desc": _text(desc.group(1)) if desc else "",
        "h1": _text(h1.group(1)) if h1 else "",
        "keywords": [html.unescape(k.strip()) for k in keys.group(1).split(",") if k.strip()] if keys else [],
        "h2": [_text(x) for x in re.findall(r"<h2[^>]*>(.*?)</h2>", src, re.S)],
        "h3": [_text(x) for x in re.findall(r"<h3[^>]*>(.*?)</h3>", src, re.S)],
        "images": imgs,
        "badge": _badge(route, [i["src"] for i in imgs]),
        "aeo": aeo,
        "geo": geo,
        "local": local,
        "cluster": cluster_of(route),
        "noindex": "noindex" in src.lower(),
        "words": len(body_text.split()),
    }


def _fld(key: str, value: str, empty: str = "не заполнено") -> str:
    v = html.escape(value) if value else f'<span class="none">{empty}</span>'
    cls = "v" if value else "v none"
    return f'<div class="fld"><div class="k">{key}</div><div class="{cls}">{v}</div></div>'


def _checks(items) -> str:
    li = []
    for name, ok, hint in items:
        mark = "✓" if ok else "✕"
        li.append(
            f'<li class="{"yes" if ok else "no"}"><span>{mark}</span>{html.escape(name)}'
            f' <span style="width:auto;color:#8a938f;font-weight:400;font-size:12px">— {html.escape(hint)}</span></li>'
        )
    return f'<ul class="checks">{"".join(li)}</ul>'


def detail_body(p, site_url: str, stats_html: str = "") -> str:
    """Карточка в том порядке, в котором её просил владелец: бейдж, тайтл,
    дескриптор, H1, ключевые слова, альт-теги, прямые ответы (AEO),
    цитируемость в нейросетях (GEO), локальное SEO, кластер и запросы."""
    badge = (
        f'<img src="{html.escape(p["badge"])}" alt="" loading="lazy">'
        if p["badge"] else '<span class="nobadge"></span>'
    )
    alts = "".join(
        f'<span class="alt{"" if i["alt"] else " empty"}">'
        f'<img src="{html.escape(i["src"])}" alt="" loading="lazy">'
        f'<span>{html.escape(i["alt"]) if i["alt"] else "без alt — декоративная"}</span></span>'
        for i in p["images"]
    ) or '<span class="chip warn">картинок на странице нет</span>'
    filled = sum(1 for i in p["images"] if i["alt"])

    kw_rows = "".join(
        f'<tr><td>{html.escape(k)}</td>'
        f'<td class="num" title="Нужен доступ к Яндекс.Вордстат">—</td>'
        f'<td class="num" title="Нужен доступ к Яндекс.Вебмастеру">—</td>'
        f'<td class="num" title="Нужен доступ к Google Search Console">—</td></tr>'
        for k in p["keywords"]
    ) or '<tr><td colspan="4" style="color:#b3261e">Ключевые слова на странице не заданы</td></tr>'

    chips = "".join(f'<span class="chip">{html.escape(k)}</span>' for k in p["keywords"])

    return f"""<main><div class="pd">
<a class="back" href="/admin">← Все страницы сайта</a>
<div class="hero">{badge}
<div><h1>{html.escape(p["title"] or p["route"])}</h1>
<a class="url" href="{site_url}{p["route"]}" target="_blank" rel="noopener">{site_url}{p["route"]}</a>
<div class="kind">{p["words"]} слов на странице{" · закрыта от индексации" if p["noindex"] else ""}</div></div></div>
{stats_html}

<div class="panel"><h2>Что стоит в SEO</h2>
{_fld("Тайтл", p["title"])}
{_fld("Дескриптор", p["desc"])}
{_fld("H1", p["h1"], "H1 на странице нет")}
<div class="fld"><div class="k">Ключевые слова ({len(p["keywords"])})</div>
<div class="{"v" if chips else "v none"}"><div class="chips">{chips or "не заданы"}</div></div></div>
<div class="fld"><div class="k">Структура заголовков</div>
<div class="v">H2 — {len(p["h2"])}, H3 — {len(p["h3"])}</div></div>
<div class="fld"><div class="k">Альт-теги картинок ({filled} из {len(p["images"])} заполнены)</div>
<div class="v"><div class="alts">{alts}</div></div></div>
</div>

<div class="panel"><h2>Прямые ответы поисковика (AEO)</h2>
<p style="margin:0 0 10px;font-size:13px;color:#55605d">Быстрый ответ над выдачей — «нулевая позиция», расширенный сниппет и блок
«люди спрашивают». Поисковик забирает готовый фрагмент страницы, поэтому фрагмент должен быть.</p>
{_checks(p["aeo"])}</div>

<div class="panel"><h2>Цитируемость в ответах нейросетей (GEO)</h2>
<p style="margin:0 0 10px;font-size:13px;color:#55605d">Попадание в генеративную выдачу: Яндекс Нейро, Google AI Overviews, ChatGPT,
Perplexity. Это не геолокация — привязка к городу ниже, отдельным блоком.</p>
{_checks(p["geo"])}</div>

<div class="panel"><h2>Локальное SEO: привязка к Новосибирску</h2>
<p style="margin:0 0 10px;font-size:13px;color:#55605d">По этому нас находят по местным запросам — город в заголовке, описании и тексте,
адрес в разметке организации.</p>
{_checks(p["local"])}</div>

<div class="panel"><h2>Кластер и запросы</h2>
{_fld("Кластер", p["cluster"])}
<div style="margin-top:14px"><table class="kwt">
<tr><th>Ключевое слово</th><th>Спрос в Яндексе,<br>Новосибирск / мес.</th>
<th>Показы в Яндексе,<br>за месяц</th><th>Показы в Google,<br>за месяц</th></tr>
{kw_rows}</table>
<p class="note">Частотности пока пустые: это внешние данные, из кода сайта их не взять.
Спрос по Новосибирску даёт Яндекс.Вордстат (или API Директа), показы — Яндекс.Вебмастер
и Google Search Console. Как появится доступ, колонки заполнятся сами — разметка под них уже готова.</p>
</div></div>
</div></main>"""
