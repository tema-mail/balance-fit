"""Раздел «SEO-аналитика» Balance – реестр и стили кодом эталона EV SIBIR (seo_map), обёртка – с ALEX KROWN.

Владелец 30.10.2026: «снять запросы по топу… отдельно сильно интересуют брендовые запросы, поднести наверх».
Поэтому над реестром EV – панели в его же стиле (как «Источники» и «Страницы входа» у ALEX KROWN):
бренд по клубам, топ брендовых запросов, топ без бренда, куда входят по бренду. Реестр EV – ниже, кластеры
«Бренд: …» идут первыми (сортировка эталона по имени кластера).

Запросов к API здесь нет – только готовые выгрузки (квота Метрики общая на логин):
  • data/seo/ – агент yandex-dannye 30.10.2026: фразы Метрики 12 мес и год назад (queries-12m*.json), Вебмастер
    search-queries/popular (webmaster-queries.json, окно 16.07–06.10.2026), правило бренда (brand-rules.json),
    страницы входа по бренду (brand-landing-pages.json);
  • Search Console – выгрузка из интерфейса 05.10.2026 (GSC_XLSX): сервисному ключу ресурс не выдан, API нет.
Запуск (после сборки сайта): python3 scripts/seo-ev.py → src/data/analytics/seo-ev.json (папка в .gitignore).
"""

from __future__ import annotations

import html
import json
import os
import pathlib
import re
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEO = ROOT / "data" / "seo"
OUT = ROOT / "src" / "data" / "analytics"
EV = pathlib.Path(os.environ.get("EV_SERVER", "~/Documents/ev-sibir/server")).expanduser()
GSC_XLSX = pathlib.Path(os.environ.get("GSC_XLSX", "~/Documents/SEO базовое/artifacts/balance-fit-llm-handoff-2026-10-05/raw/"
                                       "gsc-performance-16-months-2025-06-03--2026-10-02.xlsx")).expanduser()
GSC_PERIOD = ("2025-06-03", "2026-10-02")
SITE = "https://balance-fit.ru"

sys.path.insert(0, str(EV))
import seo_map  # noqa: E402

CLUB_NAME = {"общий бренд": "сеть Balance", "Империал": "Империал", "Абрикосово": "Абрикосово", "Адмирал": "Адмирал"}
TOP = 40  # строк в каждом топе


def load(name: str) -> dict:
    return json.loads((SEO / name).read_text(encoding="utf-8"))


def by_phrase(rows: list[dict]) -> dict:
    """Фразы Метрики приходят по поисковым системам – складываем в одну строку на фразу."""
    out: dict[str, dict] = {}
    for r in rows:
        k = r["phrase"].strip().lower()
        x = out.setdefault(k, {"phrase": k, "visits": 0, "goals": 0, "brand": r.get("brand"), "club": r.get("club")})
        x["visits"] += r.get("visits") or 0
        x["goals"] += r.get("goals") or 0
    return out


def gsc_rows() -> tuple[dict, str]:
    """Лист «Запросы» выгрузки Search Console (xlsx без сторонних библиотек): запрос → клики, показы, позиция."""
    if not GSC_XLSX.is_file():
        return {}, f"нет файла выгрузки {GSC_XLSX.name}"
    z = zipfile.ZipFile(GSC_XLSX)
    ss = [re.sub(r"<[^>]+>", "", s) for s in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode(), re.S)]
    names = re.findall(r'<sheet [^>]*name="([^"]+)"', z.read("xl/workbook.xml").decode())
    sheet = z.read(f"xl/worksheets/sheet{names.index('Запросы') + 1}.xml").decode()
    out = {}
    for row in re.findall(r"<row[^>]*>(.*?)</row>", sheet, re.S)[1:]:
        cells = []
        for attrs, v in re.findall(r"<c\b([^>]*)>(?:<v>([^<]*)</v>)?", row):
            cells.append(ss[int(v)] if 't="s"' in attrs and v else v)
        if len(cells) >= 5 and cells[0]:
            q = html.unescape(cells[0]).strip().lower()
            out[q] = {"clicks": int(float(cells[1] or 0)), "shows": int(float(cells[2] or 0)), "pos": float(cells[4] or 0)}
    return out, ""


def classify():
    """Правило бренда агента (brand-rules.json, brand_name.regex) уже проставлено в выгрузках Метрики и Вебмастера;
    фразы Google делим тем же правилом."""
    rx = load("brand-rules.json")["brand_name"]["regex"]
    return re.compile("|".join(f"(?:{r})" for r in rx), re.I)


def fmt(n) -> str:
    return "–" if n is None else f"{n:,}".replace(",", " ") if isinstance(n, int) else f"{n:.1f}".replace(".", ",")


def delta(now: int, prev: int | None) -> str:
    if not prev:
        return '<span class="nc">нет данных</span>'
    d = (now - prev) / prev * 100
    color = "#136c2e" if d >= 0 else "#b3261e"
    return f'<span style="color:{color}">{"+" if d >= 0 else "−"}{abs(d):.0f}%</span>'


def table(head: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th>{h}</th>" for h in head)
    trs = "".join("<tr>" + "".join(f'<td class="phrase">{c}</td>' if i == 0 else f"<td>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div style="overflow-x:auto"><table class="smt"><tr>{th}</tr>{trs}</table></div>'


def main() -> None:
    q12, qprev = load("queries-12m.json"), load("queries-12m_prev.json")
    wm = load("webmaster-queries.json")
    lp = load("brand-landing-pages.json")
    m12, mprev = by_phrase(q12["rows"]), by_phrase(qprev["rows"])
    wmq = {x["phrase"].strip().lower(): x for x in wm["queries"]}
    gsc, gsc_err = gsc_rows()
    brand_rx = classify()
    p12, pprev = q12["meta"]["period"], qprev["meta"].get("period", {})
    wm_from, wm_to = "16.07.2026", "06.10.2026"  # фактическое окно popular (meta.effective_period_note)

    # --- сводка бренда по клубам: Метрика 12 мес / год назад, Вебмастер
    sp, spp = q12["split"], qprev.get("split", {})
    clubs = ["общий бренд", "Империал", "Абрикосово", "Адмирал"]
    wclub = wm["totals_popular"]["brand_by_club"]
    land = lp["data"]["12m"]
    rows = []
    for c in clubs:
        now, prev = sp["brand_by_club"].get(c, 0), (spp.get("brand_by_club") or {}).get(c)
        pages = (land.get(c) or {}).get("pages") or []
        top = ", ".join(f'<span class="pg">{html.escape(p["startURL"].replace(SITE, "") or "/")}</span> {fmt(p["visits"])}' for p in pages[:3])
        w = wclub.get(c, {})
        rows.append([f"Бренд: {CLUB_NAME[c]}", fmt(now), fmt(prev), delta(now, prev), fmt(int(w.get("shows", 0))), fmt(int(w.get("clicks", 0))), top])
    nb_now, nb_prev = sp["nonbrand"]["visits"], (spp.get("nonbrand") or {}).get("visits")
    rows.append(["Без бренда", fmt(nb_now), fmt(nb_prev), delta(nb_now, nb_prev), fmt(int(wm["totals_popular"]["nonbrand"]["shows"])),
                 fmt(int(wm["totals_popular"]["nonbrand"]["clicks"])), '<span class="nc">–</span>'])
    t = q12["totals"]
    clubs_panel = (
        f'<div class="panel"><h2>Брендовый спрос по клубам</h2>'
        f'<p style="margin:0 0 12px;font-size:13px;color:#55605d">Визиты из поиска с известной фразой – Яндекс Метрика '
        f'{p12["date1"]} – {p12["date2"]} и тот же период год назад; показы и клики – Яндекс Вебмастер {wm_from} – {wm_to}. '
        f'Бренд – {sp["brand_share_of_visits_with_phrase"] * 100:.0f}% визитов с известной фразой. Фраза скрыта у '
        f'{t["not_provided_share"] * 100:.0f}% визитов из поиска ({fmt(t["visits_not_provided"])} из {fmt(t["organic_visits"])}): '
        f'Google фраз не передаёт совсем, Яндекс – часть.</p>'
        + table(["Кластер", "Визиты, 12 мес", "Год назад", "Изменение", "Показы Яндекс", "Клики Яндекс", "Куда входят (визиты)"], rows)
        + '<div class="note">Числа страниц входа – нижняя граница: Метрика отдаёт страницу входа не для всех визитов фразы. '
          'Адрес или район без названия Balance («фитнес на Бородинской») считается небрендом.</div></div>')

    # --- топы: бренд и небренд, Метрика + Вебмастер + Google
    def row_of(k: str) -> list[str]:
        m, w, g, pr = m12.get(k, {}), wmq.get(k, {}), gsc.get(k), mprev.get(k, {})
        club = m.get("club") or w.get("club")
        return [html.escape(k), html.escape(CLUB_NAME.get(club, club or "–")), fmt(m.get("visits")), fmt(pr.get("visits")),
                fmt(int(w["shows"])) if w else "–", fmt(int(w["clicks"])) if w else "–",
                fmt(w.get("avg_show_position")) if w and w.get("avg_show_position") else "–",
                f'{fmt(g["clicks"])} / {fmt(g["shows"])}' if g else "–"]

    def is_brand(k: str) -> bool:
        x = m12.get(k) or wmq.get(k)
        return bool(x["brand"]) if x and x.get("brand") is not None else bool(brand_rx.search(k))

    keys = set(m12) | set(wmq)
    head = ["Запрос", "Клуб", "Визиты 12 мес", "Год назад", "Показы Яндекс", "Клики Яндекс", "Позиция Яндекс", "Google: клики / показы"]
    brand_keys = sorted((k for k in keys if is_brand(k)), key=lambda k: (-(m12.get(k, {}).get("visits") or 0), -(wmq.get(k, {}).get("shows") or 0)))
    other_keys = sorted((k for k in keys if not is_brand(k)), key=lambda k: (-(wmq.get(k, {}).get("shows") or 0), -(m12.get(k, {}).get("visits") or 0)))
    note = (f'Визиты – Яндекс Метрика {p12["date1"]} – {p12["date2"]} (органика, все поисковики). Показы, клики и средняя позиция '
            f'показа – Яндекс Вебмастер {wm_from} – {wm_to} (API отдаёт только последние ~3 месяца). Google – выгрузка Search Console '
            f'{GSC_PERIOD[0]} – {GSC_PERIOD[1]}{"" if gsc else " (" + gsc_err + ")"}. Прочерк – источник фразу не отдал, это не ноль.')
    brand_panel = (f'<div class="panel"><h2>Топ брендовых запросов ({len(brand_keys)} всего, первые {TOP} по визитам)</h2>'
                   f'<p style="margin:0 0 12px;font-size:13px;color:#55605d">{note}</p>' + table(head, [row_of(k) for k in brand_keys[:TOP]]) + "</div>")
    other_panel = (f'<div class="panel"><h2>Топ запросов без бренда ({len(other_keys)} всего, первые {TOP} по показам в Яндексе)</h2>'
                   f'<p style="margin:0 0 12px;font-size:13px;color:#55605d">Показов много, кликов почти нет: средняя позиция '
                   f'8–12 – вторая страница выдачи и низ первой. {note}</p>' + table(head, [row_of(k) for k in other_keys[:TOP]]) + "</div>")
    g_brand = sorted(((k, v) for k, v in gsc.items() if brand_rx.search(k)), key=lambda kv: -kv[1]["clicks"])
    g_other = sorted(((k, v) for k, v in gsc.items() if not brand_rx.search(k)), key=lambda kv: -kv[1]["shows"])
    google_panel = ""
    if gsc:
        gh = ["Запрос", "Клики", "Показы", "Позиция"]
        gr = lambda kv: [html.escape(kv[0]), fmt(kv[1]["clicks"]), fmt(kv[1]["shows"]), fmt(kv[1]["pos"])]  # noqa: E731
        google_panel = (f'<div class="panel"><h2>Google отдельно: Search Console {GSC_PERIOD[0]} – {GSC_PERIOD[1]}</h2>'
                        f'<p style="margin:0 0 12px;font-size:13px;color:#55605d">Google – половина поиска сайта, но Метрике фраз не '
                        f'передаёт. Выгрузка из интерфейса Search Console 05.10.2026 ({len(gsc)} запросов – больше интерфейс не отдаёт). '
                        f'Бренд – тем же правилом.</p><details class="xq" open><summary>Брендовые ({len(g_brand)}), по кликам</summary>'
                        + table(gh, [gr(kv) for kv in g_brand[:20]]) + f'</details><details class="xq" style="margin-top:12px">'
                        f'<summary>Без бренда ({len(g_other)}), по показам</summary>' + table(gh, [gr(kv) for kv in g_other[:20]]) + "</details></div>")

    # --- реестр EV: фразы с заметным спросом, кластер – бренд по клубу или небренд
    reg = []
    for k in keys:
        m, w, g = m12.get(k, {}), wmq.get(k, {}), gsc.get(k)
        if (m.get("visits") or 0) < 10 and (w.get("shows") or 0) < 30:
            continue
        club = m.get("club") or w.get("club")
        cl = f"Бренд: {CLUB_NAME.get(club, 'сеть Balance')}" if is_brand(k) else (f"Небренд: {club}" if club in CLUB_NAME else "Небренд: фитнес, спорт, спа")
        reg.append({
            "phrase": k, "pages": [], "cluster": cl, "real_query_match": True,
            "demand_nsk": dict(seo_map.NOT_COLLECTED), "demand_rf": dict(seo_map.NOT_COLLECTED),
            "yandex_impressions": {"status": "measured", "value": int(w["shows"])} if w else dict(seo_map.NOT_COLLECTED),
            "google_impressions": {"status": "measured", "value": g["shows"]} if g else dict(seo_map.NOT_COLLECTED),
            "yandex_position": {"status": "measured", "position": round(w["avg_show_position"], 1)} if w.get("avg_show_position") else dict(seo_map.NOT_COLLECTED),
            "google_position": {"status": "measured", "position": round(g["pos"], 1)} if g else dict(seo_map.NOT_COLLECTED),
        })
    n_pages = sum(1 for f in (ROOT / "src" / "data" / "pages").glob("*.json") if "redirect" not in json.loads(f.read_text(encoding="utf-8")))
    body = seo_map.render_body(reg, [], None, n_pages, None, None)
    fixes = [
        ("Карта поискового спроса</h1>", "SEO-аналитика</h1>"),
        (f"Реестр ключевых слов сайта EV Sibir ({n_pages} страниц), сверенный с реальными поисковыми запросами. "
         "Архитектура и дисциплина — по технологии, собранной для TEYES; масштаб — под наш сайт.",
         f"Поисковые запросы balance-fit.ru ({n_pages} страниц): брендовые – первыми. Ключевых слов в meta keywords у страниц "
         "нет, поэтому реестр – фразы, по которым сайт реально находили (Метрика, Вебмастер, Search Console). Ключи не выдумываются."),
        ("ключевых слов в реестре", "запросов в реестре"), ("подтверждены реальным запросом", "реальные запросы"),
        ("реальных запросов вне реестра", "запросов вне реестра"), ("Кластеры по числу ключевых слов", "Кластеры по числу запросов"),
        ("— считается по разделу страницы (марка, модель, документ), не угадывается отдельно для каждого слова.",
         "– брендовый по клубу (название Balance + клуб, адрес или город) или небрендовый; правило – brand-rules.json."),
        ("На каких страницах сайта эта фраза реально стоит в keywords — можно пересекаться, одна фраза бывает нужна двум страницам.",
         "Страница входа по фразе – в панели «Брендовый спрос по клубам»; в реестре не заполняется."),
        ("Отмечено «да», если похожая формулировка реально встретилась в выгрузке Яндекс.Вебмастера — то есть кто-то так и искал, "
         "а не только мы так думаем.", "Все фразы реестра – реальные: по ним были визиты (Метрика) или показы (Вебмастер, Search Console)."),
        ("Широкая частотность Wordstat по Новосибирску и по России отдельно — не складывать. Пока не собрано: нужен доступ к XMLRiver "
         "или Яндекс.Директ.", "Частотность Wordstat по Краснодару и по России отдельно – не складывать. Не собрано: XMLRiver платный, "
         "запросов не делали."),
        ("по данным Вебмастера и Search Console.", f"Яндекс – Вебмастер {wm_from} – {wm_to}, Google – Search Console "
         f"{GSC_PERIOD[0]} – {GSC_PERIOD[1]}."),
        ("Отдельный замер текущей выдачи, не то же самое, что показы за период.",
         "Средняя позиция показа за тот же период (Вебмастер, Search Console), не замер текущей выдачи."),
        ("Спрос НСК</th><th>Спрос РФ", "Спрос Краснодар</th><th>Спрос РФ"),
    ]
    for a, b in fixes:
        body = body.replace(a, b)
    body = body.replace("<main>", "", 1).replace("</main>", "", 1)
    anchor = '<div class="panel">\n  <h2>Кластеры'
    body = body.replace(anchor, clubs_panel + brand_panel + other_panel + google_panel + "\n" + anchor, 1)
    body = body.replace("—", "–")
    css = seo_map.CSS + ".sm .smt .pg{white-space:nowrap}.sm table.smt td{color:#1e1e1e}@media(max-width:700px){.sm .cl-row{grid-template-columns:1fr 70px 30px}}"
    OUT.mkdir(parents=True, exist_ok=True)
    out = {"fetched_at": q12["meta"].get("pulled"), "html": f"<style>{css}</style>{body}"}
    (OUT / "seo-ev.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"SEO-аналитика: бренд {len(brand_keys)} фраз, без бренда {len(other_keys)}, Google {len(gsc)} ({gsc_err or 'ок'}), реестр {len(reg)}")


if __name__ == "__main__":
    main()
