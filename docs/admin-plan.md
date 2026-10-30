# План админки Balance (30.10.2026)

Тип (разведка admin-auditor 30.10): визитка/услуги с заявками. Товаров и онлайн-записи нет: расписание – виджет myfitt,
ЛК – mobifitness/reservi, заявки живого сайта – Тильда (проект 4906566) + копия в Calltouch; на копии заблокированы
(public/no-leads.js, решение владельца 13.10). Репозиторий ПУБЛИЧНЫЙ.

Основа – кабинет rozalii (~/Sites/rozalii, тоже копия Тильды, 28.10) без «Товаров» и «Товарного спроса».
Реальные цифры аналитики – только зашифрованными (сейф ALEX KROWN: scripts/seal-admin.mjs + Vault.astro),
сырые выгрузки (data/seo, src/data/analytics) – в .gitignore.
Адрес: правило «admin.<домен>» (28.10) применить нельзя – домена у копии нет, кабинет на Pages /balance-fit/admin/.

| Модуль | Эталон | Данные | Что заблокировано |
|---|---|---|---|
| Страницы сайта по сущностям | rozalii index.astro ← EV GROUPS | 71 страница из src/data/pages | – |
| Карточка страницы (SEO, сниппет, кластер) | rozalii page-cards.py ← EV page_seo | HTML страниц | «Цифры страницы», AEO/GEO – замок по стандарту (своего счётчика нет) |
| Заявки (доска, список, архив) | rozalii Leads.tsx ← Milovini/EV | пример с меткой | приёмника нет: живые заявки в Тильде 4906566, копия формы не шлёт |
| Метрика и каналы | ALEX KROWN metrika-ev.py ← EV | Метрика 71090701 (view), настоящие | Search Console – сервисный ключ не добавлен в ресурс |
| SEO-аналитика (бренд наверху) | ALEX KROWN seo-ev.py ← EV seo_map | Метрика + Вебмастер (verified), настоящие | GSC – нет доступа; XMLRiver не запрашиваем |
| Позиции | rozalii positions.astro + Locked | – | замок до слова владельца |
| Рекомендации | rozalii recommendations.astro + Locked | – | замок всегда |

## Шаги (≤3 файла кода, коммит после каждого; правки по verify-plan 30.10)
0.  .gitignore: data/, src/data/analytics/ – до первых выгрузок (сделано).
1а. package.json (+preact, @astrojs/preact под Astro 7.3), astro.config.mjs (интеграция preact).
1б. src/layouts/Admin.astro, src/styles/admin.css, src/lib/url.ts (rozalii). Вкладки: Страницы, Заявки, Метрика,
    SEO-аналитика, Позиции 🔒, Рекомендации 🔒. Без счётчика товаров.
1в. Замок: scripts/lock-admin.mjs, scripts/admin-crypto.mjs (rz_ → bf_, РОЗАЛИЯ → BALANCE, ~/.config/balance-fit),
    .github/workflows/pages.yml – шаг замка до upload, падение без секретов ADMIN_LOGIN/ADMIN_PASS.
2.  src/pages/admin/index.astro – пишется заново по src/data/pages (83 файла: 71 страница + 12 редиректов; каталога нет).
    Группы: Главная (index, main), Империал (imperial*, + старые адреса borodinskaya* – редиректы), Абрикосово (*_abricosovo,
    abricosovo, lkabrikosovo, menu_abricosovo), Адмирал (*_admiral, admiral), Общие (day, cafe, keitering, loyalty, newyear,
    challenge, job, spa, kids…), Юридические (dogovor*, oferta*, pravila*, privacy, rekvizit*, security*, oplata*),
    Технические (редиректы Тильды, metrika, position, 404).
3.  Карточки: scripts/page-cards.py (без products.json и ветки catalog), scripts/admin/page_seo_ev.py (без search-index –
    «поиска на сайте нет»), package.json build = astro build && python3 scripts/page-cards.py dist (до замка).
4.  Заявки: src/pages/admin/leads.astro + src/islands/admin/Leads.tsx – пример с меткой, без товаров, формы сайта (t702 и др.).
5.  Сейф: scripts/seal-admin.mjs (пути dist/admin/<раздел>, public/admin/vault), src/components/admin/Vault.astro
    (asset → BASE_URL). Порядок ЛОКАЛЬНО: сбор аналитики → npm run build → node scripts/seal-admin.mjs --no-build →
    коммит public/admin/vault/*.json (шифр). В Actions сырых данных нет: metrika/seo без файла рисуют сейф (Vault), не цифры.
6.  Метрика: scripts/metrika-ev.py (EV_SERVER ~/Documents/ev-sibir/server только на маке, вывод src/data/analytics/,
    счётчик 71090701, цели «Заявка / Тильда», «Звонок Calltouch», «Заявка / Квиз»…, ключ Вебмастера), metrika.astro.
7.  SEO-аналитика: scripts/seo-ev.py (бренд – data/seo/brand-rules.json, кластеры «Бренд: Империал / Абрикосово /
    Адмирал / Balance» первыми, затем «Без бренда»; страницы – src/data/pages; Вебмастер – ywm EV), seo.astro.
8.  positions.astro, recommendations.astro – только каркас Admin + Locked.astro (без Positions-острова и стенда).
9.  Сверка admin-reference-check, приёмка admin-acceptor, строка в docs/РЕШЕНИЯ.md и в memory/rules.md admin-builder.

`npm run port` админку не трогает: админка только читает src/data/pages, своих правок страниц пока не пишет.
