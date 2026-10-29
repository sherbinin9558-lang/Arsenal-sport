# Production readiness — audit item 10

Дата: 2026-10-05
Ветка: audit/production-readiness-10of10-20261005
Base: main
PR: #70

## Цель

Финальная проверка готовности audit branch к коммерческому запуску без изменения main.

## Проверенные области

1. Архитектура и tenant isolation — **PASS по audit evidence**.
2. Авторизация, роли и security hardening — **PASS по audit evidence**.
3. CRM / orders / warehouse / products — **PASS по реализованным CRUD/concurrency paths; live acceptance ещё требуется**.
4. Content plan — **PASS по atomic/concurrency paths; live acceptance ещё требуется**.
5. AI seller / automation — **PASS по code paths; live provider smoke ещё требуется**.
6. WebMCP — **PASS по текущей реализации; live browser registration/execution ещё требуется**.
7. Supabase / RLS — **кодовый guard реализован; authenticated RLS integration gate НЕ ПОДТВЕРЖДЁН до успешного прогона на изолированном тестовом проекте**.
8. Security — **PASS**, включая XSRF, auth rate limiting, security events, secret scan/SAST/dependency audit workflows. Supabase Free limitation по leaked-password protection известна и отдельно зафиксирована.
9. Legal — **TECHNICAL + DOCUMENTARY PASS for audit branch / CONDITIONAL commercial pass**. Подготовлены Privacy Policy, Terms, Cookie Policy, GDPR information, DPA, subprocessors, retention, export и deletion request. Перед запуском остаются проверки фактических production providers/regions/cookies и target-market requirements.
10. CI/CD / observability / production gates — **NOT YET VERIFIED**: текущий head SHA не имеет доступных workflow runs в GitHub connector, а live gates требуют production environment secrets.

## Критические блокеры перед merge в main

- Нет подтверждённого успешного полного CI/live-smoke прогона для текущего head SHA.
- Browser/WebMCP smoke требует SAAS_PUBLIC_URL, E2E_EMAIL, E2E_PASSWORD, TELEGRAM_BOT_TOKEN.
- Supabase RLS integration требует три test-only secrets в GitHub Actions environment `supabase-test`: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`. Все три должны принадлежать только изолированному тестовому проекту с ref `qibncofxwuhasekwyffs`; запрещено копировать production URL или ключи.
- Provider smoke требует реальный production Telegram token.
- Production observability healthcheck требует SAAS_PUBLIC_URL и соответствующей настройки.
- PR #70 остаётся draft и не готов к merge.

## Настройка Supabase RLS test environment

Оба RLS workflow должны использовать GitHub Actions environment `supabase-test`, а не `production`. В `supabase-test` должны быть заданы только тестовые значения следующих secrets:

- `SUPABASE_URL` — `https://qibncofxwuhasekwyffs.supabase.co`;
- `SUPABASE_ANON_KEY` — anon key только тестового проекта;
- `SUPABASE_SERVICE_ROLE_KEY` — service-role key только тестового проекта.

**Нельзя копировать production secrets в `supabase-test`.** Workflow и `scripts/supabase_rls_integration.py` должны завершаться с ошибкой до API-запросов и изменения данных, если URL не использует HTTPS и точный разрешённый hostname `qibncofxwuhasekwyffs.supabase.co` (порт отсутствует или 443; userinfo запрещён).

Текущая конфигурация/наличие секретов не считается подтверждённой одним лишь текстом документации. Администратор репозитория должен проверить наличие test-only secrets в `supabase-test` без вывода их значений в логи, а затем запустить RLS audit. До успешного прохождения шага target guard и authenticated RLS matrix gate остаётся **NOT VERIFIED**.

## Решение

**Item 10: CONDITIONAL PASS / NOT READY FOR MERGE YET.**

Это означает, что кодовая и документальная база audit branch существенно подготовлена, но утверждать «10/10 и готово к production» до фактического успешного CI + authenticated browser/WebMCP + provider + RLS smoke нельзя.

## Правило выпуска

1. Не изменять main.
2. Настроить необходимые production secrets/environment.
3. Запустить полный CI и live gates на текущем audit branch.
4. Исправить только реальные failures.
5. Повторить полный прогон до зелёного результата.
6. Только после этого переводить PR из draft и рассматривать merge в main.
