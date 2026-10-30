#!/usr/bin/env python3
"""Карточки страниц для админки («Страницы сайта» → клик по странице) – как в кабинете EV SIBIR (evolutioncarservice.ru/admin).

Код карточки не переписан: это модуль эталона scripts/admin/page_seo_ev.py (копия ~/Documents/ev-sibir/server/page_seo.py),
обёртка только подменяет данные под Balance (перенос с rozalii ← кабинет-стандарт Milovini):
  • кластеры – по клубам и типам страниц Balance (вместо марок и моделей EV);
  • картинки – ресурсы Тильды /_t/static/… (у EV /images/…), с учётом подпапки Pages;
  • локальное SEO – город клуба: Краснодар (Империал, Абрикосово, сеть) или Туапсе (Адмирал);
  • переадресации Тильды (meta refresh) карточек не получают – это не страницы.
Решение владельца 18.10.2026: «я хочу попадать внутрь страницы… кластеры и запросы оставь, чтобы было видно, а всё остальное
перекрой – это раздел только для тех, кто на SEO-ведении». Поэтому открыт блок «Что стоит в SEO» и заголовок «Кластер и запросы»
с названием кластера; AEO, GEO, локальное SEO и таблица спроса и показов – размыты под замком (вид – Locked.astro).

Запуск – после `astro build`, до scripts/lock-admin.mjs: python3 scripts/page-cards.py dist
Пишет dist/admin/page/<адрес страницы>/index.html; шапку и вкладки берёт из готовой dist/admin/index.html.
"""
import html
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent / "admin"))
import page_seo_ev as ev  # noqa: E402

BASE = (os.environ.get("PUBLIC_BASE") or "/").rstrip("/")
# адрес показа: домен из PUBLIC_SITE_URL + подпапка Pages (PUBLIC_SITE_URL не задан – боевой домен balance-fit.ru)
SITE_URL = (os.environ.get("PUBLIC_SITE_URL") or "https://balance-fit.ru").rstrip("/") + BASE
CITY, CITY_STEM = "Краснодар", "краснодар"

CLUBS = {"imperial": "Империал", "abricosovo": "Абрикосово", "admiral": "Адмирал"}
LEGAL = re.compile(r"^(dogovor|oferta|pravila|privacy|rekvizit|security|oplata|loyalty$|position$|metrika$)")
TOPICS = [  # тема страницы по адресу Тильды – как в «Страницах сайта» админки
    ("cards", "клубные карты и абонементы"), ("table", "расписание групповых программ"), ("schedule", "расписание групповых программ"),
    ("kids-uslugi", "детский клуб: услуги"), ("kids", "детский фитнес"), ("spa", "спа и салон красоты"),
    ("services", "услуги клуба"), ("sale", "акции"), ("promotions", "акции"), ("contacts", "контакты и адрес"),
    ("cafe", "кафе клуба"), ("menu", "кафе клуба"), ("job", "вакансии"), ("lk", "личный кабинет"),
]


def club_of(path: str) -> str:
    """Клуб по адресу: у Тильды страницы Империала без суффикса, у других клубов – с _abricosovo / _admiral."""
    if re.search(r"abr|abricosovo|abrikosovo", path):
        return "abricosovo"
    if re.search(r"admiral|_adm$", path):
        return "admiral"
    return "imperial" if re.match(r"(imperial|lk$|spa/price|day$|contacts$|job$|kids-uslugi$|cafe$)", path) else ""


def city_of(route: str) -> tuple[str, str]:
    return ("Туапсе", "туапсе") if club_of(route.strip("/")) == "admiral" else (CITY, CITY_STEM)


def cluster_of(route: str) -> str:
    """Кластер запросов страницы – по адресу, как у эталона (там структура раздела и есть структура кластеров)."""
    path = route.strip("/")
    if not path:
        return "Бренд: сеть фитнес-клубов Balance в Краснодаре и Туапсе"
    if LEGAL.match(path):
        return "Юридические документы – вне поискового продвижения"
    club = club_of(path)
    city = city_of(route)[0]
    if path in CLUBS:
        return f"Бренд и клуб: фитнес-клуб Balance {CLUBS[path]} ({city})"
    topic = next((t for k, t in TOPICS if k in path), "")
    if club and topic:
        return f"Клуб {CLUBS[club]}: {topic} ({city})"
    if club:
        return f"Клуб {CLUBS[club]}: страница клуба ({city})"
    if path == "main":
        return "Фитнес-клуб с бассейном в Краснодаре"
    return f"Сеть Balance: {topic or 'страница сети'}"


ev.cluster_of = cluster_of


def read(site_root: str, route: str):
    """read_page эталона + подмена того, что у эталона зашито под EV (картинки и город)."""
    p = ev.read_page(site_root, route)
    if not p:
        return None
    rel = route.strip("/")
    src = (pathlib.Path(site_root) / rel / "index.html" if rel else pathlib.Path(site_root) / "index.html").read_text(encoding="utf-8", errors="ignore")
    imgs = []
    # у Тильды картинки ленивые: адрес в data-original, в src – пусто или заглушка
    for tag in re.findall(r"<img\b[^>]*>", src):
        s = ev._attr(tag, "data-original") or ev._attr(tag, "src")
        if ("/_t/static/" in s or "tildacdn" in s) and not s.endswith(".svg") and s not in [i["src"] for i in imgs]:
            imgs.append({"src": s, "alt": ev._attr(tag, "alt").strip()})
    p["images"] = imgs
    p["badge"] = imgs[0]["src"] if imgs else ""
    body = ev._text(re.sub(r"<(script|style)\b.*?</\1>", " ", src, flags=re.S)).lower()
    title, desc = p["title"].lower(), p["desc"].lower()
    city, CITY_STEM = city_of(route)
    local_ld = next((o for t, o in ev._ld_types(src) if t in ("LocalBusiness", "Store", "Organization")), None)
    p["local"] = [
        ("Схема организации с адресом", bool(local_ld), "разметка есть" if local_ld else "нет разметки организации"),
        (f"Город в Title", CITY_STEM in title, "запрос почти всегда с городом"),
        ("Город в описании", CITY_STEM in desc, "показывается в выдаче"),
        ("Город в тексте страницы", CITY_STEM in body, f"упоминаний: {body.count(CITY_STEM)}"),
    ]
    return p


LOCK_CSS = """
.pd .lockzone{position:relative;border-radius:12px;overflow:hidden;margin-bottom:14px}
.pd .lockzone__blur{filter:blur(5px);opacity:.55;pointer-events:none;user-select:none}
.pd .lockzone__card{position:absolute;left:50%;top:70px;transform:translateX(-50%);width:min(520px,calc(100% - 28px));
 background:#fff;border:1px solid #e2e5e3;border-radius:16px;padding:24px 22px;box-shadow:0 20px 60px rgba(28,32,31,.14);text-align:center}
.pd .lockzone__card h2{margin:8px 0 6px;font-size:18px;font-weight:600}
.pd .lockzone__card p{margin:0 0 8px;font-size:14px;color:#1e1e1e}
.pd .lockzone__card ul{margin:0;padding-left:18px;text-align:left;font-size:13px;line-height:1.55;color:#55605d}
.pd .ghost{display:inline-block;height:10px;border-radius:5px;background:#d9dedc}
.pd .cluster-open{margin:0 0 6px}
.pd .snipchk{display:flex;gap:10px;font-size:13px;line-height:1.7}.pd .snipchk b{font-weight:600;min-width:200px}@media(max-width:700px){.pd .snipchk b{min-width:130px}}
.pd a.url{display:inline;border:0;padding:0;border-radius:0}
.pd .snip{display:grid;gap:3px;padding:14px 16px;border:1px solid #eceeed;border-radius:10px;background:#fafbfa}
.pd .snip__url{font-size:12px;color:#55605d}.pd .snip__t{font-size:18px;color:#1a0dab;line-height:1.3}.pd .snip__d{font-size:13.5px;color:#4d5156;line-height:1.5}
"""
LOCK_ICON = ('<svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
             'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4.5" y="10.5" width="15" height="10" rx="2.5"/>'
             '<path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/><circle cx="12" cy="15.2" r="1.3"/><path d="M12 16.5v1.6"/></svg>')


def snippet_html(p) -> str:
    """Сниппет в поиске (как в редакторе товара): заголовок, адрес, описание – с длиной и местом, где обрежется.
    Владелец 18.10.2026: «важно, как отображается сниппет на всех страницах… SEO, дальше сниппет, а потом AEO, GEO»."""
    def cut(text: str, n: int) -> str:
        return text if len(text) <= n else text[: n - 1].rstrip() + "…"
    title, desc = p["title"] or "", p["desc"] or ""
    crumbs = " › ".join(["balance-fit.ru"] + [x for x in p["route"].split("/") if x][:2])
    def row(name, value, limit):
        n = len(value)
        state = ("пусто", "#b3261e") if not n else (f"{n} знаков – обрежется после {limit}", "#a86b00") if n > limit else (f"{n} знаков – помещается", "#136c2e")
        return f'<div class="snipchk"><b>{name}</b><span style="color:{state[1]}">{state[0]}</span></div>'
    return (f'<div class="panel"><h2>Как выглядит в поиске (сниппет)</h2>'
            f'<div class="snip"><span class="snip__url">{html.escape(crumbs)}</span>'
            f'<span class="snip__t">{html.escape(cut(title, 60)) or "<i>без заголовка</i>"}</span>'
            f'<span class="snip__d">{html.escape(cut(desc, 160)) or "<i>описание не задано – поисковик возьмёт кусок текста страницы</i>"}</span></div>'
            f'<div style="margin-top:10px">{row("Заголовок (Title)", title, 60)}{row("Описание (Description)", desc, 160)}</div>'
            f'<p style="margin:6px 0 0;font-size:12.5px;color:#77817e">Google показывает около 60 знаков заголовка и 160 – описания; Яндекс – до 70 и 160. '
            f'Поисковик может заменить описание фрагментом текста, если сочтёт его точнее.</p></div>')


# Стили блока «Цифры страницы» – из эталона ~/Documents/ev-sibir/server/page_stats.py (CSS), без правок,
# плюс замок. Модуль эталона тянет Метрику, Search Console и базу заявок – его не запускаем: своего счётчика у копии нет.
STATS_CSS = """
.pst{background:#fff;border:1px solid #dfe4e3;border-radius:12px;padding:16px 18px;margin-bottom:14px}
.pst h2{margin:0;font-size:16px;font-weight:600}
.pst .top{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;justify-content:space-between;margin-bottom:12px}
.pst .seg{display:flex;flex-wrap:wrap;gap:4px;background:#eef1f0;border-radius:9px;padding:3px}
.pst .seg a{padding:5px 10px;border-radius:7px;font-size:13px;color:#2b302e;text-decoration:none}
.pst .seg a.on{background:#005653;color:#fff}
.pst .kp{display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:1px;background:#dfe4e3;
  border:1px solid #dfe4e3;border-radius:10px;overflow:hidden}
.pst .kp>div{background:#fff;padding:10px 12px;display:grid;gap:2px;align-content:start}
.pst .kp span{font-size:12px;color:#646b68}.pst .kp b{font-size:20px;font-variant-numeric:tabular-nums}
.pst .kp small{font-size:11px;color:#8a938f;line-height:1.35}
@media(max-width:420px){.pst .kp>div:last-child:nth-child(odd){grid-column:1/-1}}
.pst .note{margin:10px 0 0;font-size:12px;color:#77817e;line-height:1.5}
.pst--locked .seg a{pointer-events:none;opacity:.6}
.pst--locked .kp b{display:block;height:22px;width:62%;border-radius:6px;background:#c9cfcc;filter:blur(3px)}
.pst--locked .blurlist{filter:blur(4px);opacity:.6;pointer-events:none;user-select:none;margin-top:8px}
.pst--locked .blurlist i{display:block;height:10px;border-radius:5px;background:#d9dedc;margin:9px 0}
.pst__lock{display:flex;gap:12px;align-items:center;margin-top:12px;padding:12px 14px;border:1px solid #e2e5e3;border-radius:10px;background:#f7f9f8}
.pst__lock svg{flex:none;color:#1c201f}
.pst__lock b{display:block;font-size:14px}.pst__lock span{font-size:13px;color:#55605d}
"""


def stats_locked() -> str:
    """«Цифры страницы» как у EV (7 плиток, неделя–год, заявки со страницы) – закрыто: подписи видны, цифр нет.
    Владелец 18.10.2026: «плашку как на EV, только её закрой… замочек, что функционал доступен, если вы у нас на
    SEO-ведении… чтобы он был виден; собирать не надо»."""
    tiles = [
        ("Показы в поиске", "Яндекс и Google вместе"), ("Заходы на сайт", "из них из поиска"),
        ("Просмотры", "все открытия страницы"), ("Заявки", "формы на этой странице"),
        ("Целевые действия", "формы · звонки · мессенджеры"), ("CR в действия", "действия / просмотры"),
        ("Отказы", "доля визитов с отказом"),
    ]
    kp = "".join(f'<div><span>{t}</span><b></b><small>{n}</small></div>' for t, n in tiles)
    seg = "".join(f'<a class="{"on" if k == "Месяц" else ""}">{k}</a>' for k in ("Неделя", "Месяц", "Квартал", "Год"))
    return (f'<div class="pst pst--locked"><div class="top"><h2>Цифры страницы</h2><div class="seg">{seg}</div></div>'
            f'<div class="kp">{kp}</div>'
            f'<div class="pst__lock">{LOCK_ICON.replace("44", "34")}<div><b>Цифры страницы: функционал закрыт</b>'
            f'<span>Доступен клиентам на постоянном SEO-ведении: показы, заходы, заявки и конверсия этой страницы '
            f'по неделям, месяцам, кварталам и годам.</span></div></div>'
            f'<h2 style="margin-top:14px;font-size:14px">Заявки с этой страницы за период</h2>'
            f'<div class="blurlist" aria-hidden="true"><i style="width:58%"></i><i style="width:46%"></i><i style="width:52%"></i></div></div>')


def card_html(p) -> str:
    """Карточка эталона, разрезанная по панелям: «Что стоит в SEO» – открыта, кластер – открыт названием,
    остальное – под замком (размыто, без цифр)."""
    body = ev.detail_body(p, SITE_URL, stats_locked())
    panels = re.split(r'(?=<div class="panel">)', body)
    head, seo = panels[0], panels[1]
    locked = "".join(panels[2:-1] + [re.sub(r"</div></main>\s*$", "", panels[-1])])
    # таблица спроса и показов – без цифр и без пустых «—»: в размытом виде показываем каркас строк
    locked = re.sub(r"<table class=\"kwt\">.*?</table>", lambda m: re.sub(r"<td[^>]*>.*?</td>", '<td><span class="ghost" style="width:70%"></span></td>', m.group(0), flags=re.S), locked, flags=re.S)
    cluster = html.escape(p["cluster"])
    city = city_of(p["route"])[0]
    loc_in, loc_by = ("в Туапсе", "к Туапсе") if city == "Туапсе" else ("в Краснодаре", "к Краснодару")
    head = head.replace('href="/admin"', f'href="{BASE}/admin/"')
    open_cluster = (f'<div class="panel"><h2>Кластер и запросы</h2>'
                    f'<div class="fld cluster-open"><div class="k">Кластер</div><div class="v">{cluster}</div></div>'
                    f'<p style="margin:6px 0 0;font-size:13px;color:#55605d">Запросы кластера, спрос в Яндексе {loc_in} и показы в Яндексе и Google за месяц – в расширенном разборе ниже.</p></div>')
    lock = (f'<div class="lockzone"><div class="lockzone__blur" aria-hidden="true">{locked}</div>'
            f'<div class="lockzone__card">{LOCK_ICON}<h2>Расширенный SEO-разбор страницы: раздел закрыт</h2>'
            f'<p>Доступно клиентам на постоянном SEO-ведении.</p><ul>'
            f'<li>Запросы кластера: спрос в Яндексе {loc_in} и показы в Яндексе и Google за месяц</li>'
            f'<li>Прямые ответы поисковика (AEO): быстрый ответ, расширенный сниппет, «люди спрашивают»</li>'
            f'<li>Цитируемость в ответах нейросетей (GEO): Яндекс Нейро, Google AI Overviews, ChatGPT, Perplexity</li>'
            f'<li>Локальное SEO: привязка страницы {loc_by}</li></ul></div></div>')
    out = head + seo + snippet_html(p) + open_cluster + lock + "</div></main>"
    # тексты эталона про город EV – на город сайта (в размытой части тоже: правда для Balance)
    for a, b in (("к Новосибирску", loc_by), ("по Новосибирску", loc_in), ("Новосибирск", city)):
        out = out.replace(a, b)
    return out.replace("—", "–")


def routes(site_root: pathlib.Path):
    for f in sorted(site_root.rglob("index.html")):
        rel = f.parent.relative_to(site_root).as_posix()
        # служебные страницы показа (карта сайта, материалы, демо кабинета оптовика) – не страницы сайта клиента
        if rel.split("/")[0] in ("admin", "_astro", "_t"):
            continue
        yield "/" if rel == "." else f"/{rel}/"


def main(site_root: str) -> int:
    root = pathlib.Path(site_root)
    tpl_file = root / "admin" / "index.html"
    tpl = tpl_file.read_text(encoding="utf-8")
    if 'id="lock-form"' in tpl:
        sys.exit("page-cards: админка уже закрыта замком – запускать до lock-admin.mjs")
    m0, m1 = tpl.index("<main>"), tpl.index("</main>") + len("</main>")
    style = f"<style>{ev.CSS}{LOCK_CSS}{STATS_CSS}</style>"
    done = 0
    for route in routes(root):
        src = (root / route.strip("/") / "index.html").read_text(encoding="utf-8", errors="ignore")
        if re.search(r'http-equiv="refresh"', src, re.I):  # переадресация Тильды – не страница
            continue
        p = read(site_root, route)
        if not p:
            continue
        page = tpl[:m0] + card_html(p) + tpl[m1:]
        page = re.sub(r"<title>.*?</title>", f"<title>{html.escape(p['title'] or route)} – разбор страницы</title>", page, count=1, flags=re.S)
        page = page.replace("</head>", style + "</head>", 1)
        out = root / "admin" / "page" / route.strip("/") / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        done += 1
    print(f"page-cards: карточек страниц – {done}")
    return done


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Использование: python3 scripts/page-cards.py dist")
    if not main(sys.argv[1]):
        sys.exit("page-cards: в сборке нет страниц")
