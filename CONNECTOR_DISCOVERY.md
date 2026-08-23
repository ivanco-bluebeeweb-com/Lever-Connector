# Lever Connector — Connector Discovery

**Discovery date:** 2026-08-23  
**Release scope:** Tier 1 + Tier 2 + Tier 3 (maximum coverage)  
**Decision source:** Vlad explicitly requested Lever with every available Lever-side capability and every Imperal-side efficiency feature.

## 1. Target service and sources

Lever is an applicant tracking system (ATS) and Talent Relationship Management platform. Its public API v1 exposes recruiting data and controlled write operations around the central **Opportunity** record: candidate contact, applications, stage, posting, owner, interviews, feedback, files, notes, offers, tags and source information.

Official sources examined on 2026-08-23:

- [Lever API Overview and Reference](https://hire.lever.co/developer/documentation)
- [Lever Developer use cases](https://hire.lever.co/developer/usecases)
- [Lever Developer updates](https://hire.lever.co/developer/updates)
- [Lever webhook configuration](https://help.lever.co/s/article/Configuring-webhooks)

## 2. API architecture and constraints

- Base API: `https://api.lever.co/v1`.
- Authentication: API key over HTTP Basic Auth, or OAuth 2.0 authorization code flow with optional `offline_access` refresh token. The first release uses BYOK API key authentication because it is explicit, account-scoped, and can be checked at connect time; connection storage permits multiple Lever accounts.
- Authorization is scope-based. Sensitive recruiting data requires the relevant `*:read:admin`/`*:write:admin` scopes, with `confidential:access:admin` needed where confidential records are requested.
- Pagination is cursor-based and all list handlers must surface Lever's `hasNext`/`next` information instead of assuming complete account scans.
- The official reference marks candidate-level file/interview list routes as backward-compatible legacy. Current flows must resolve a contact's opportunities and use `/opportunities/{id}/...` endpoints.
- Requisition writes may require an account Super Admin to enable API management in Lever Requisitions settings. The connector treats this as a provider-side permission outcome, not a connector failure.
- Webhook targets must be HTTPS and Lever supports request signing. The app manages outgoing Lever webhook subscriptions; inbound ingestion requires a platform endpoint and is not silently claimed until platform routing is configured.

## 3. Capability map

| Lever capability | Direction | Connector treatment |
|---|---|---|
| Account connection and access probe | Both | Store BYOK API key per Imperal account; verify with a harmless list request. |
| Opportunities and contacts | Both | List/read/create/update, stage/archive/tag/source/link control; contact data via opportunity. |
| Applications | Both | List/read/create applications for a posting and contact. |
| Postings/jobs | Both | List/read/create/update, questions, access list and candidate application. |
| Stages, archive reasons, disposition stages | Ingress | Lookup data for safe pipeline operations and reports. |
| Interviews | Both | List/read/create/update/delete against an opportunity. |
| Feedback and templates | Both | Capture/review feedback plus CRUD templates where allowed. |
| Notes | Both | List/create/update/delete opportunity notes. |
| Files, resumes and uploads | Both | List/read/download metadata; upload files through Lever upload flow where enabled. |
| Offers | Ingress | List/read/download offer documents and status; no undocumented offer mutation. |
| Sources, tags, referrals | Ingress | Recruiter attribution and sourcing analytics. |
| Requisitions and fields | Both | Full CRUD for requisitions/fields where provider permission exists. |
| Forms and profile-form templates | Both | Read/manage custom data configuration. |
| Users, groups, roles and permissions | Both | Team lookup and allowed admin-level management only where API exposes it. |
| Audit events | Ingress | Compliance review and account audit input. |
| Webhooks | Both | List/create/delete provider webhooks; validate HTTPS endpoint and disclose signed-delivery requirements. |

## 4. Tier 1 — key functions

1. Connect, disconnect and list isolated Lever account connections.
2. List/read/create/update Opportunities; move stage; archive/unarchive; manage tags, sources and links.
3. List/read Postings; create/update postings; inspect application questions and posting access.
4. List/read/create/update/delete Interviews and retrieve/create Feedback.
5. List/create/update/delete opportunity Notes; list opportunity Files and Offers.
6. Read users, stages, archive reasons, sources and tags required for safe recruiting operations.
7. Imperal recruiting health snapshot: active pipeline counts, stale candidates, open postings and feedback/interview signals.

## 5. Tier 2 — full provider coverage

| Capability family | Status | Reason |
|---|---|---|
| Opportunities, contacts, applications | included | Core data model and recruitment workflow. |
| Postings, stages, archive reasons, disposition stages | included | Required for job lifecycle and pipeline governance. |
| Interviews, feedback, feedback templates | included | Required for interview-loop execution and quality control. |
| Notes, files, resumes, uploads | included | Candidate evidence and recruiter collaboration. |
| Offers and offer files | included (read) | Official reference exposes retrieval/listing; mutations are not invented. |
| Sources, tags, referrals | included | Sourcing attribution and candidate organization. |
| Requisitions and requisition fields | included | Full API coverage, provider permission handled clearly. |
| Forms, profile forms and templates | included | Lever configuration coverage. |
| Users, groups, roles, permissions | included | Team visibility and allowed administration. |
| Audit events | included | Compliance and operational traceability. |
| Webhooks | included | Provider-side management; endpoint configuration follows Imperal platform routing. |
| Deprecated candidate file/interview routes | not applicable | Replaced by current Opportunity-scoped endpoints per Lever documentation. |
| Actions absent from official API | not applicable | The connector must not simulate undocumented writes. |

## 6. Tier 3 — Imperal value-add

1. `audit_recruiting_health`: aggregate pipeline, posting, interview, offer and stale-process signals into actionable findings.
2. `get_stale_candidate_report`: identify active opportunities not advanced for a configurable number of days, with owner and stage context.
3. `get_interview_feedback_gaps`: flag interviews that completed without required feedback signals.
4. `get_posting_pipeline_report`: combine posting state, active applicants, stage distribution and hiring velocity indicators.
5. `get_recruiter_workload_report`: aggregate active opportunities by owner/recruiter.
6. `bulk_archive_opportunities` and `bulk_move_opportunities_stage`: explicit-ID convenience wrappers that continue on individual failures and report every result.
7. `build_hiring_handoff`: normalized, least-privilege recruiting summary designed for downstream Imperal HR/onboarding workflows without sending data to third parties itself.

## 7. Release decision

The user requested the maximum form in the opening instruction. Per the Connector Discovery Standard this is an already-given decision to implement Tier 1, Tier 2 and Tier 3 together; no follow-up scope question is required.
