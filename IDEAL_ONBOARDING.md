# Lever Connector — идеальный первый запуск

Источник: `ONBOARDING_FIRST_LAUNCH_STANDARD.md`. Целевой пользователь: Recruiter/Talent
Acquisition менеджер на Lever ATS (альтернатива Greenhouse).

## 1. Credential type
API key (одно поле).

## 2. Идеальный флоу
1. **Первое открытие** — `Empty` со ссылкой "Settings > Integrations and API > API
   credentials".
2. **Форма** — api_key (password-type) с лейблом.
3. **После успеха** — `audit_recruiting_pipeline`: объём по стадиям, "застрявшие"
   кандидаты — сразу, воронка визуально как funnel, аналогично Greenhouse.
4. **Ошибка "insufficient scope"** — Lever API keys бывают ограничены по правам чтения/
   записи — конкретное сообщение, если ключ read-only, а вызвана write-функция.

## 3. Разница с реализацией сейчас
См. `UI_COMPONENT_PLAN.md` §0.
