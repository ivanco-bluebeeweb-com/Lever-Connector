# Lever Connector — Preparation

**Version:** 0.1.0  
**Prepared:** 2026-08-23  
**Product owner:** Vlad / Bluebeeweb  
**Status:** designed — implementation follows this document

## 1. Application passport

**Lever Connector** connects a customer-owned Lever recruiting account to Imperal. It gives recruiting teams a safe operational layer for candidates, pipeline opportunities, postings, interviews, feedback, requisitions, offers and compliance-aware recruiting reports.

It is being built now because the Imperal app portfolio needs a dedicated ATS/HR layer rather than forcing hiring workflows through CRM, task or generic automation products.

## 2. Human problem

When a recruiter or hiring manager needs to move a candidate through a hiring process, they must inspect several parts of Lever manually — the opportunity record, current stage, interviewer schedule, feedback, posting and owner — then chase missing decisions. This creates delayed responses, stale candidates, incomplete interview feedback and weak visibility into which jobs are blocked.

The connector makes the live Lever data operable in natural language while preserving Lever as the system of record.

## 3. Users, roles and rights

| Role | Job to be done | Connector access |
|---|---|---|
| Recruiter | Source, qualify and progress candidates quickly | Read/write opportunities, notes, interviews, feedback and applications within Lever scopes. |
| Hiring manager | Review pipeline, feedback and open roles | Read pipeline, candidates, interviews and reports; provider scopes control writes. |
| Talent operations | Maintain recruiting data and workflows | Manage postings, templates, requisitions, fields and webhooks where Lever permits. |
| HR/compliance lead | Monitor data handling and hiring process health | Audit events, archive reasons, reports and configuration review. |
| Imperal administrator | Connect/disconnect an account securely | Manages connection only; never receives exposed secret values. |

## 4. Primary scenarios and human decisions

### A. Candidate progression

`new applicant → recruiter reviews opportunity → Imperal shows current stage/owner/context → recruiter explicitly moves stage or archives → Lever confirms result → panels refresh`

- **Happy path:** existing opportunity is read, stage is changed, current pipeline view refreshes.
- **Missing/error path:** connection, permission, stage id or opportunity id is absent; return a human-readable provider-safe error.
- **Blocked state:** API key lacks scope or opportunity is confidential; report the capability limitation without exposing data.
- **Recovery:** user connects a permitted API key or chooses a stage returned from `list_stages`.
- **Human decision:** candidate disposition, archive reason and stage movement remain explicitly initiated by a person.

### B. Interview feedback closure

`interview is complete → recruiter runs feedback-gap report → missing feedback is shown with opportunity context → human contacts interviewer or records feedback → report refreshes`

No feedback score, hiring recommendation, rejection or offer decision is generated autonomously.

### C. Posting and requisition readiness

`talent operations reads posting/requisition → Imperal shows state and pipeline signals → human updates a provider-authorized record → Lever remains source of truth`

## 5. Value and success criteria

- Reduce time to identify active opportunities without recent movement.
- Surface every completed interview lacking feedback in one call.
- Provide a clear pipeline/owner/posting overview without manually collating records.
- Ensure every write returns an explicit Lever outcome and refreshed UI.
- Maintain zero secret exposure in responses, panels, errors and audit summaries.

Failure signals: a handler silently writes without an explicit result; an aggregate report claims data it did not read; a UI form lacks a label; a user must reload manually to see context changes.

## 6. Scope and boundaries

### Included

- Full public Lever API coverage identified in `CONNECTOR_DISCOVERY.md`, subject to the actual scopes and plan permissions of each connected account.
- Imperal reports for stale candidates, interview-feedback gaps, recruiter workload, posting pipeline health and account health.
- Explicit-ID bulk wrappers that report partial failures rather than hiding them.

### Excluded or constrained

- No autonomous hiring, rejection, offer approval, candidate ranking or legal/EEO judgement.
- No attempt to bypass Lever permissions, plan limits, confidential-data controls or requisition API management.
- No use of deprecated candidate file/interview list routes when current opportunity-scoped routes exist.
- No receipt or processing of a webhook inbound body until a verified Imperal inbound endpoint is configured.
- No undocumented API write is simulated as supported.

## 7. Data, privacy and integrations

| Data | Source / use | Handling |
|---|---|---|
| Candidate identity, contact and opportunity data | Lever API | Retrieved only per the connected account's scopes; returned only for an explicit request. |
| Resumes/files/offers | Lever API | Metadata and signed/download URLs are shown only when authorized; content is not persisted by default. |
| Interview feedback and notes | Lever API | Sensitive HR content; no third-party enrichment or autonomous judgement. |
| API key | User-provided BYOK secret | Encrypted Imperal secret; never echoed, logged, placed in labels or returned by a handler. |
| Webhook secret | Lever configuration | Stored/managed without returning the secret after creation. |

**Tenant isolation:** connection records are stored in the current Imperal account secret, allowing several isolated Lever accounts per user.

**Integration status:** Lever REST API — available; OAuth — available but deferred from first connection UX in favour of verifiable API-key BYOK; inbound webhook delivery — provider capability available, platform route integration unverified; outbound webhook configuration — available.

## 8. P0 useful path

A recruiter connects an API key, lists active opportunities, reads one opportunity, sees its stage/owner/posting context, moves it to a selected valid stage or archives it with an explicit reason, and immediately sees the fresh result. The recruiter can also run stale-candidate and feedback-gap reports.

**Safety gates:** provider scope check; immutable/destructive classification for deletes; explicit action for stage/archive; no manual `confirm` fields duplicating the platform confirmation gate.

**P0 acceptance:** the flow imports, validates, has typed handler parameters, does not disclose secrets, reports provider errors intelligibly, and refreshes affected panels after a successful change.

## 9. Imperal panel UX map

### Left sidebar

- Plain vertically stacked content only — no decorative cards.
- Connection status / connection form with visible label above every input and contextual placeholders.
- Compact list of connected accounts and active opportunity snapshot.
- Dividers between logical blocks.
- Exactly one final secondary **App settings** button, opening the central settings panel.

### Center panels

| State | User sees | Next action |
|---|---|---|
| Empty | “Connect a Lever account to view recruiting data.” | Connect in sidebar. |
| Connected | Opportunities snapshot plus report shortcuts. | Open details or run health report. |
| Detail | Candidate/opportunity context and safe operations. | `← Back to opportunities`. |
| Settings | All connection and webhook settings together. | Save, rotate or disconnect. |
| Blocked | Scope/plan constraint in human terms. | Use a permitted key or ask Lever admin. |

Every selector and saved setting refreshes the affected panels immediately. Settings forms never duplicate setup instructions that are already presented in their help modal.

## 10. Safety, approval and audit

- **Read actions:** no confirmation.
- **Normal writes:** explicit human invocation; no inferred/automatic action.
- **Destructive actions:** `action_type="destructive"`, allowing Imperal's confirmation card; no duplicate boolean confirm field.
- **Bulk actions:** explicit IDs only, continue through per-item errors and return a complete result.
- **Audit:** provider audit-event reading plus connector outcomes for connections and write operations.
- **Fail closed:** missing credentials, malformed connection record, unknown account id or provider permission failure never falls back to another account.

## 11. Discovery and hypothesis validation

Before expanding beyond the implemented maximum release, verify with a pilot team:

1. Which report causes the most weekly follow-up work: stale candidates, missing feedback or requisition readiness?
2. Which Lever scopes are commonly unavailable in real customer API keys?
3. Whether onboarding needs OAuth in addition to API key BYOK.
4. Whether users need a direct inbound webhook event workspace after provider-side webhooks are configured.

Use anonymized opportunity metadata only; no real resume or feedback content is required for scenario testing.

## 12. Delivery plan and live criteria

| Slice | Flow | Panel location | Tests | Live criterion | Status |
|---|---|---|---|---|---|
| Foundation | secure connection/client/schemas | sidebar/settings | import + validate | connection check returns real provider-safe result | planned |
| Pipeline | opportunities, contacts, stages, postings | sidebar + center | handler/client contract checks | candidate movement visible after refresh | planned |
| Recruiting operations | interviews, feedback, notes, files, offers | center | scenario paths | feedback gap report matches seeded data | planned |
| Admin/configuration | requisitions, forms, users, audit, webhooks | settings + center | permissions/error tests | provider constraints are intelligible | planned |
| Value-add | health and workload reports, explicit bulk actions | center | PST | summaries reconcile with list endpoints | planned |

### Roadmap after P0

| Priority | Future slice | Entry condition |
|---|---|---|
| P1 | OAuth authorization UX | At least two pilot teams cannot use API-key access under their Lever governance policy. |
| P2 | Verified inbound webhook event workspace | Imperal publishes a signed inbound routing contract and one pilot has a real-time use case. |
| P3 | Cross-app HRIS/onboarding handoff | A pilot documents a human-approved downstream workflow and its minimal data contract. |
