# Production readiness — audit item 11

Дата: 2026-10-05
Ветка: audit/production-readiness-10of10-20261005
Base: main

## Цель

Закрыть остаточные технические проблемы и организационные риски после блоков 1–10, не изменяя main.

## Проверка workflow-структуры

- `production-observability.yml`: production PR trigger направлен на `main`; push trigger оставлен для audit-ветки.
- `p2-p3-quality.yml`: является основным комплексным quality/live-smoke gate для audit branch и PR в `main`.
- `supabase-rls-integration.yml`: выполняет RLS integration на push audit-ветки.
- `rls-audit.yml`: отдельный PR gate для `main`. Несмотря на похожие шаги, его нельзя безопасно удалить без доступа к branch protection/rulesets, потому что он может быть зарегистрирован как required status check.
- `branch-quality.yml`: legacy compatibility workflow. Его PR trigger на `main` может пересекаться с новым P2/P3 gate, но удаление без проверки required checks небезопасно. Его старые push branches не влияют на audit branch.

## Исправление

В `production-observability.yml` исправлен PR trigger: проверка production observability должна запускаться при PR в `main`, а не только на старой audit-ветке.

## Безопасность изменений

- Runtime-код не изменялся в рамках этого блока.
- main не изменялся.
- Дублирующие/legacy workflow не удалялись без проверки branch protection, которая недоступна текущему GitHub integration connection.
- Платёжный контур не затрагивался.

## Оставшиеся внешние ограничения

1. GitHub-hosted runner allocation для текущего audit workflow может задерживать фактический CI.
2. Полный live acceptance зависит от production secrets/environment.
3. Проверка required status checks через GitHub branch-protection API недоступна текущему connector permission scope.

## Решение

**Item 11: PASS WITH EXTERNAL INFRASTRUCTURE CONDITIONS.**

Кодовые остаточные исправления, доступные без риска для main, выполнены. Оставшиеся пункты требуют либо фактического CI runner, либо административного доступа GitHub к branch protection/rulesets.

Следующий этап: **Item 12 — финальная приёмка audit branch и решение о готовности PR #70 к merge.**

Правило: main не изменять до завершения Item 12.
