# Lever Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на `POST_CONNECT_EXPERIENCE.md` этого приложения.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Column`(align="start") + `ui.Text`(org) + `ui.Divider` + navigation `ui.ListItem`(Postings/Candidates/Requisitions) + `ui.Button`("App settings") | Без карточек по стандарту. |
| Posting List (center, `center_overlay=True`) | `ui.Stats`(Published postings/Candidates in process/Offers extended) + `ui.DataTable`(title, team, status Badge published/closed, candidates count; sortable) | Табличный обзор открытых вакансий (postings). |
| Pipeline Board (posting detail) | Back-button + `ui.Row`(колонки-стадии через N×`ui.Column`, внутри каждой `ui.List`(кандидаты этой стадии как ListItem)) | В SDK нет Kanban-примитива (см. `UI_COMPONENT_VOCABULARY.md` §4) — pipeline собирается из `Row` колонок, каждая — `List`. |
| Candidate Detail (Opportunity) | Back-button + `ui.KeyValue`(contact/source/current stage/owner) + `ui.Timeline`(stage changes + interview events) + `ui.TagInput`(tags, editable=True) + `ui.TextArea`(param_name="note", placeholder="Добавить заметку...") | `TagInput` — прямое попадание для тегов кандидата (Lever активно их использует); `Timeline` для истории продвижения. |
| Feedback Form Viewer | `ui.KeyValue`(scorecard fields/overall rating) | Фидбек интервьюера как набор полей — KeyValue. |
| Requisition List | `ui.DataTable`(req name, headcount, status Badge open/filled/closed; sortable) | Табличный обзор заявок на найм (headcount requisitions). |
| Archive Reason Dialog | `ui.Dialog`(title="Архивировать кандидата?", content=`ui.Select`(param_name="archive_reason"), confirm_label="Архивировать") | Архивация — значимое действие с обязательной причиной, требует Dialog. |
| Reports Dashboard | `ui.Chart`(type="bar" — candidates by stage) + `ui.Stats`(avg time in stage) | Метрики воронки — числовая сводка + чарт. |
| App Settings | `ui.Accordion`([Connections+Disconnect, Webhooks CRUD, Stage Mapping]) | Централизованные настройки по стандарту. |

## 2. User flow (валидно по panel lifecycle)

1. **SESSION INIT** → `__panel__lever_sidebar` рендерит org + разделы,
   `auto_action` открывает Posting List.
2. Posting List: клик по вакансии → `ui.Call(posting_id=...)` → Pipeline
   Board на том же center handler.
3. Клик по кандидату → `ui.Call(opportunity_id=...)` → Candidate Detail;
   `Select`(стадия, отдельный элемент на экране) двигает кандидата по
   воронке через `on_change` → `refresh_panels`.
4. Candidate Detail: клик "Архивировать" → `ui.Dialog` с обязательным
   `archive_reason` → подтверждение → `ui.Call` → `refresh_panels` убирает
   карточку из активного pipeline.
5. Feedback Form Viewer: раскрывается из Timeline-события интервью (клик
   на элемент Timeline → `ui.Call(feedback_id=...)`), back-button возвращает
   к Candidate Detail.
6. Reports Dashboard: read-only, обновляется вручную.
7. App Settings: доступен из sidebar в любой момент.

## 3. Экраны/карточки (конкретно для этого приложения)

- **Screen: Sidebar** — ListItem секции: Postings, Candidates, Requisitions.
- **Screen: Posting List** — Stats(3) + DataTable(4 колонки).
- **Screen: Pipeline Board** — Row из N Column, каждая — List кандидатов стадии.
- **Screen: Candidate Detail** — KeyValue + Timeline + TagInput + TextArea.
- **Screen: Feedback Form Viewer** — KeyValue(scorecard fields).
- **Screen: Requisition List** — DataTable(3 колонки).
- **Screen: Reports Dashboard** — Chart + Stats.
- **Screen: App Settings** — Accordion(3 секции).

Ограничение SDK, учтённое в плане: нет drag-and-drop между стадиями pipeline —
перенос кандидата только через `Select` на карточке кандидата.
