"""Lever ATS chat functions: connection, recruiting records, and health reports."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from imperal_sdk import ActionResult

import lever_client as lc
from app import chat, ext
from schemas import (
    ApplyToPostingParams, BulkOpportunityStageParams, ConnectionIdParams,
    ConnectionParams, ContactCreateParams, ContactUpdateParams, DeleteParams,
    FeedbackCreateParams, GenericActionParams, InterviewCreateParams,
    InterviewUpdateParams, LeverConnection, LeverRecord, LeverRecordList,
    NoParams, NoteCreateParams, OfferCreateParams, OpportunityArchiveParams,
    OpportunityCreateParams, OpportunityFileListParams, OpportunityListParams,
    OpportunityStageParams, OpportunityUpdateParams, PipelineHealthParams,
    PostingCreateParams, PostingUpdateParams, RecruitingFinding,
    RecruitingHealthReport, RequisitionCreateParams, RequisitionUpdateParams,
    ResourceGetParams, ResourceListParams, StaleCandidateReportParams,
    WebhookCreateParams, WebhookUpdateParams,
)

_SECRET = "lever_connections"


async def _load(ctx) -> list[dict[str, Any]]:
    raw = await ctx.secrets.get(_SECRET)
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except (TypeError, ValueError):
        return []


async def _save(ctx, records: list[dict[str, Any]]) -> None:
    await ctx.secrets.set(_SECRET, json.dumps(records))


async def _connection(ctx, connection_id: str) -> dict[str, Any] | None:
    connections = await _load(ctx)
    if not connections:
        return None
    if not connection_id:
        return connections[0]
    return next((c for c in connections if c.get("id") == connection_id), None)


async def _require(ctx, connection_id: str):
    conn = await _connection(ctx, connection_id)
    if conn is None:
        return None, ActionResult.error("No Lever account is connected. Use connect_lever first.", code="LEVER_CONNECTION_MISSING")
    return conn, None


def _conn_entity(conn: dict[str, Any]) -> LeverConnection:
    return LeverConnection(id=conn["id"], title=conn.get("label") or "Lever", connected=True, detail="API key stored securely.")


def _record(item: dict[str, Any]) -> LeverRecord:
    identifier = str(item.get("id") or item.get("_id") or item.get("opportunityId") or "")
    title = str(item.get("name") or item.get("text") or item.get("subject") or item.get("email") or identifier)
    detail = str(item.get("stage") or item.get("state") or item.get("status") or "")
    return LeverRecord(id=identifier, title=title, detail=detail, raw=item)


def _body(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value not in (None, "", [], {})}


async def _list(ctx, connection_id: str, path: str, params: ResourceListParams, extra: dict[str, Any] | None = None) -> ActionResult:
    conn, error = await _require(ctx, connection_id)
    if error:
        return error
    query = _body(limit=params.limit, cursor=params.cursor, confidential=params.include_confidential_fields, **(extra or {}))
    try:
        payload = await lc.get(conn["api_key"], path, params=query)
    except lc.LeverAPIError as exc:
        return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    items, has_next, next_cursor = lc.rows(payload)
    result = LeverRecordList(records=[_record(x) for x in items], has_next=has_next, next_cursor=next_cursor)
    return ActionResult.success(result, f"Loaded {len(items)} Lever record(s).")


async def _get(ctx, connection_id: str, path: str, params: ResourceGetParams) -> ActionResult:
    conn, error = await _require(ctx, connection_id)
    if error:
        return error
    try:
        payload = await lc.get(conn["api_key"], path, params={"confidential": params.include_confidential_fields})
    except lc.LeverAPIError as exc:
        return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(payload if isinstance(payload, dict) else {}), "Lever record loaded.")


@chat.function("connect_lever", "Connect a Lever account with your own API key after verifying it can read the account.", action_type="write", chain_callable=True, data_model=LeverConnection, event="lever-connector.connected", effects=["lever.provider.connected"])
async def connect_lever(ctx, params: ConnectionParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    if not params.api_key:
        return ActionResult.error("A Lever API key is required.", code="LEVER_API_KEY_REQUIRED")
    try:
        await lc.get(params.api_key, "/users", params={"limit": 1})
    except lc.LeverAPIError as exc:
        return ActionResult.error(str(exc), code="LEVER_CREDENTIALS_REJECTED")
    records = await _load(ctx)
    record = {"id": str(uuid.uuid4()), "api_key": params.api_key, "label": params.label}
    records.append(record)
    await _save(ctx, records)
    return ActionResult.success(_conn_entity(record), "Lever account connected.", refresh_panels=["lever_connect", "lever_overview", "lever_settings"])


@chat.function("disconnect_lever", "Disconnect a Lever account: deletes the saved API key only. Nothing in Lever is changed.", action_type="write", chain_callable=True, data_model=LeverConnection, event="lever-connector.disconnected", effects=["lever.provider.disconnected"])
async def disconnect_lever(ctx, params: ConnectionIdParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    records = await _load(ctx)
    remaining = [record for record in records if record.get("id") != params.connection_id]
    if len(records) == len(remaining):
        return ActionResult.error("Lever connection was not found.", code="LEVER_CONNECTION_NOT_FOUND")
    await _save(ctx, remaining)
    return ActionResult.success(LeverConnection(id=params.connection_id, connected=False), "Lever account disconnected.", refresh_panels=["lever_connect", "lever_overview", "lever_settings"])


@chat.function("list_connections", "List connected Lever accounts without exposing their API keys.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.connections.listed")
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    records = await _load(ctx)
    result = LeverRecordList(records=[LeverRecord(id=x["id"], title=x.get("label") or "Lever", detail="Connected") for x in records])
    return ActionResult.success(result, f"{len(records)} Lever connection(s).")


@chat.function("list_opportunities", "List Lever candidate opportunities, optionally filtered by posting, stage, owner or archived state.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.opportunities.listed")
async def list_opportunities(ctx, params: OpportunityListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/opportunities", params, _body(posting_id=params.posting_id, stage_id=params.stage_id, owner_id=params.owner_id, archived=params.archived))


@chat.function("get_opportunity", "Read one Lever opportunity in full, including candidate, stage, postings and owner.", action_type="read", chain_callable=True, data_model=LeverRecord, event="lever-connector.opportunity.loaded")
async def get_opportunity(ctx, params: ResourceGetParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _get(ctx, params.connection_id, f"/opportunities/{params.resource_id}", params)


@chat.function("create_opportunity", "Create a new recruiting opportunity for an existing Lever contact/candidate.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.opportunity.created", effects=["lever.opportunity.created"])
async def create_opportunity(ctx, params: OpportunityCreateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    payload = _body(contact=params.contact_id, posting=params.posting_id, stage=params.stage_id, owner=params.owner_id, source=params.source, tags=params.tags)
    try: result = await lc.post(conn["api_key"], "/opportunities", body=payload)
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Opportunity created.")


@chat.function("update_opportunity_stage", "Move an opportunity to a different Lever pipeline stage.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.opportunity.stage_updated", effects=["lever.opportunity.stage_changed"])
async def update_opportunity_stage(ctx, params: OpportunityStageParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try: result = await lc.put(conn["api_key"], f"/opportunities/{params.opportunity_id}/stage", body={"stage": params.stage_id})
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Opportunity stage updated.")


@chat.function("archive_opportunity", "Archive or restore a Lever opportunity. Archiving removes it from the active recruiting pipeline.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.opportunity.archive_updated", effects=["lever.opportunity.archived"])
async def archive_opportunity(ctx, params: OpportunityArchiveParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try: result = await lc.put(conn["api_key"], f"/opportunities/{params.opportunity_id}/archived", body=_body(archived=params.archived, reason=params.archive_reason_id))
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Opportunity archive state updated.")


@chat.function("update_opportunity", "Update an opportunity's owner, tags, sources or profile links. Omitted fields are unchanged.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.opportunity.updated", effects=["lever.opportunity.updated"])
async def update_opportunity(ctx, params: OpportunityUpdateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    payload = _body(owner=params.owner_id, tags=params.tags, sources=params.sources, links=params.links)
    try: result = await lc.put(conn["api_key"], f"/opportunities/{params.opportunity_id}", body=payload)
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Opportunity updated.")


@chat.function("list_postings", "List Lever job postings and their publication state.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.postings.listed")
async def list_postings(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/postings", params)


@chat.function("get_posting", "Read a single Lever job posting including its candidate-facing configuration.", action_type="read", chain_callable=True, data_model=LeverRecord, event="lever-connector.posting.loaded")
async def get_posting(ctx, params: ResourceGetParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _get(ctx, params.connection_id, f"/postings/{params.resource_id}", params)


@chat.function("create_posting", "Create a Lever job posting with title, team, location and description.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.posting.created", effects=["lever.posting.created"])
async def create_posting(ctx, params: PostingCreateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try: result = await lc.post(conn["api_key"], "/postings", body=_body(text=params.text, team=params.team, location=params.location, description=params.description, state=params.state))
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Posting created.")


@chat.function("update_posting", "Update a Lever job posting. Omitted fields are unchanged.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.posting.updated", effects=["lever.posting.updated"])
async def update_posting(ctx, params: PostingUpdateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try: result = await lc.put(conn["api_key"], f"/postings/{params.posting_id}", body=_body(text=params.text, team=params.team, location=params.location, description=params.description, state=params.state))
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Posting updated.")


@chat.function("list_users", "List Lever recruiting users, interviewers and hiring managers.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.users.listed")
async def list_users(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/users", params)


@chat.function("list_stages", "List configured Lever pipeline stages.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.stages.listed")
async def list_stages(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/stages", params)


@chat.function("create_contact", "Create a candidate contact in Lever with identity and profile details.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.contact.created", effects=["lever.contact.created"])
async def create_contact(ctx, params: ContactCreateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    payload = _body(name=params.name, emails=params.emails, phones=params.phones, headline=params.headline, location=params.location, links=params.links)
    try: result = await lc.post(conn["api_key"], "/contacts", body=payload)
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Candidate contact created.")


@chat.function("get_contact", "Read a Lever candidate contact in full.", action_type="read", chain_callable=True, data_model=LeverRecord, event="lever-connector.contact.loaded")
async def get_contact(ctx, params: ResourceGetParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _get(ctx, params.connection_id, f"/contacts/{params.resource_id}", params)


@chat.function("update_contact", "Update candidate contact profile details without changing omitted fields.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.contact.updated", effects=["lever.contact.updated"])
async def update_contact(ctx, params: ContactUpdateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    payload = _body(name=params.name, emails=params.emails, phones=params.phones, headline=params.headline, location=params.location, links=params.links)
    try: result = await lc.put(conn["api_key"], f"/contacts/{params.contact_id}", body=payload)
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Candidate contact updated.")


@chat.function("list_interviews", "List interviews scheduled in Lever.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.interviews.listed")
async def list_interviews(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/interviews", params)


@chat.function("create_interview", "Schedule an interview for an opportunity with Lever users as interviewers.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.interview.created", effects=["lever.interview.created"])
async def create_interview(ctx, params: InterviewCreateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    payload = _body(opportunity=params.opportunity_id, users=params.interviewer_ids, date=params.date, duration=params.duration, timezone=params.timezone, subject=params.subject, location=params.location)
    try: result = await lc.post(conn["api_key"], "/interviews", body=payload)
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Interview scheduled.")


@chat.function("update_interview", "Reschedule or update a Lever interview.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.interview.updated", effects=["lever.interview.updated"])
async def update_interview(ctx, params: InterviewUpdateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    payload = _body(date=params.date, duration=params.duration, timezone=params.timezone, subject=params.subject, location=params.location, users=params.interviewer_ids)
    try: result = await lc.put(conn["api_key"], f"/interviews/{params.interview_id}", body=payload)
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Interview updated.")


@chat.function("delete_interview", "Delete a scheduled Lever interview. This cannot be undone through the API.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.interview.deleted", effects=["lever.interview.deleted"])
async def delete_interview(ctx, params: DeleteParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try: await lc.delete(conn["api_key"], f"/interviews/{params.resource_id}")
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(LeverRecord(id=params.resource_id, detail="Deleted"), "Interview deleted.")


@chat.function("list_feedback", "List submitted interview feedback in Lever.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.feedback.listed")
async def list_feedback(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/feedback", params)


@chat.function("create_feedback", "Submit interviewer feedback for a candidate opportunity.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.feedback.created", effects=["lever.feedback.created"])
async def create_feedback(ctx, params: FeedbackCreateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try: result = await lc.post(conn["api_key"], "/feedback", body=_body(opportunity=params.opportunity_id, interview=params.interview_id, text=params.text, score=params.score))
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Interview feedback submitted.")


@chat.function("list_notes", "List internal notes on a Lever opportunity.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.notes.listed")
async def list_notes(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/notes", params)


@chat.function("create_note", "Add an internal recruiting note to an opportunity.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.note.created", effects=["lever.note.created"])
async def create_note(ctx, params: NoteCreateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try: result = await lc.post(conn["api_key"], "/notes", body={"opportunity": params.opportunity_id, "text": params.text})
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Recruiting note added.")


@chat.function("list_offers", "List candidate offers in Lever.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.offers.listed")
async def list_offers(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/offers", params)


@chat.function("create_offer", "Create a Lever offer using configured offer-field values.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.offer.created", effects=["lever.offer.created"])
async def create_offer(ctx, params: OfferCreateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try: result = await lc.post(conn["api_key"], "/offers", body=_body(opportunity=params.opportunity_id, posting=params.posting_id, owner=params.owner_id, fields=params.fields))
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Offer created.")


@chat.function("list_requisitions", "List Lever requisitions, subject to the account's requisition API permission.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.requisitions.listed")
async def list_requisitions(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/requisitions", params)


@chat.function("create_requisition", "Create a Lever requisition when the account enables requisition API management.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.requisition.created", effects=["lever.requisition.created"])
async def create_requisition(ctx, params: RequisitionCreateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try: result = await lc.post(conn["api_key"], "/requisitions", body={"text": params.text, "fields": params.fields})
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Requisition created.")


@chat.function("update_requisition", "Update a Lever requisition and its configured field values.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.requisition.updated", effects=["lever.requisition.updated"])
async def update_requisition(ctx, params: RequisitionUpdateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try: result = await lc.put(conn["api_key"], f"/requisitions/{params.requisition_id}", body={"text": params.text, "fields": params.fields})
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Requisition updated.")


@chat.function("list_applications", "List applications in Lever, optionally scoped to a candidate opportunity.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.applications.listed")
async def list_applications(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/applications", params)


@chat.function("get_application", "Read one Lever application in full.", action_type="read", chain_callable=True, data_model=LeverRecord, event="lever-connector.application.loaded")
async def get_application(ctx, params: ResourceGetParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _get(ctx, params.connection_id, f"/applications/{params.resource_id}", params)


@chat.function("list_opportunity_files", "List files and resumes attached to one Lever opportunity.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.opportunity_files.listed")
async def list_opportunity_files(ctx, params: OpportunityFileListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, f"/opportunities/{params.opportunity_id}/files", params)


@chat.function("list_archive_reasons", "List configured archive reasons used when candidates leave the active pipeline.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.archive_reasons.listed")
async def list_archive_reasons(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/archive_reasons", params)


@chat.function("list_disposition_stages", "List Lever disposition stages used for recruiting outcomes.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.disposition_stages.listed")
async def list_disposition_stages(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/disposition_stages", params)


@chat.function("list_sources", "List candidate sources configured in Lever for sourcing attribution.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.sources.listed")
async def list_sources(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/sources", params)


@chat.function("list_tags", "List candidate and opportunity tags configured in Lever.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.tags.listed")
async def list_tags(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/tags", params)


@chat.function("list_referrals", "List employee referrals recorded in Lever.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.referrals.listed")
async def list_referrals(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/referrals", params)


@chat.function("list_audit_events", "List Lever audit events for recruiting-data and configuration oversight.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.audit_events.listed")
async def list_audit_events(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/audit_events", params)


@chat.function("list_feedback_templates", "List interview feedback templates configured in Lever.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.feedback_templates.listed")
async def list_feedback_templates(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/feedback_templates", params)


@chat.function("list_profile_form_templates", "List profile form templates used to collect structured candidate data.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.profile_form_templates.listed")
async def list_profile_form_templates(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/profile_form_templates", params)


@chat.function("list_form_fields", "List configured Lever form fields and their accepted values.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.form_fields.listed")
async def list_form_fields(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/form_fields", params)


@chat.function("list_requisition_fields", "List custom requisition fields configured in Lever.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.requisition_fields.listed")
async def list_requisition_fields(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/requisition_fields", params)


@chat.function("list_webhooks", "List configured Lever webhook subscriptions without exposing signing secrets.", action_type="read", chain_callable=True, data_model=LeverRecordList, event="lever-connector.webhooks.listed")
async def list_webhooks(ctx, params: ResourceListParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    return await _list(ctx, params.connection_id, "/webhooks", params)


@chat.function("create_webhook", "Create a Lever webhook subscription. The target must be HTTPS and able to validate signed deliveries.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.webhook.created", effects=["lever.webhook.created"])
async def create_webhook(ctx, params: WebhookCreateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    if not params.url.startswith("https://"):
        return ActionResult.error("Lever webhook targets must use HTTPS.", code="LEVER_WEBHOOK_HTTPS_REQUIRED")
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try: result = await lc.post(conn["api_key"], "/webhooks", body=_body(url=params.url, event=params.event, configuration=params.configuration))
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Webhook created. Store the provider signing secret securely if Lever returns one.")


@chat.function("update_webhook", "Update a Lever webhook's target URL, event or provider-supported configuration.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.webhook.updated", effects=["lever.webhook.updated"])
async def update_webhook(ctx, params: WebhookUpdateParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    if params.url and not params.url.startswith("https://"):
        return ActionResult.error("Lever webhook targets must use HTTPS.", code="LEVER_WEBHOOK_HTTPS_REQUIRED")
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try: result = await lc.put(conn["api_key"], f"/webhooks/{params.webhook_id}", body=_body(url=params.url, event=params.event, configuration=params.configuration))
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(_record(result), "Webhook updated.")


@chat.function("delete_webhook", "Permanently remove a Lever webhook subscription. This stops future deliveries to that endpoint.", action_type="write", chain_callable=True, data_model=LeverRecord, event="lever-connector.webhook.deleted", effects=["lever.webhook.deleted"])
async def delete_webhook(ctx, params: DeleteParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try: await lc.delete(conn["api_key"], f"/webhooks/{params.resource_id}")
    except lc.LeverAPIError as exc: return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    return ActionResult.success(LeverRecord(id=params.resource_id, title="Webhook"), "Webhook deleted.")


@chat.function("get_stale_candidate_report", "Value-add report: flag active Lever opportunities that have had no recorded update for the chosen number of days.", action_type="read", chain_callable=True, data_model=RecruitingHealthReport, event="lever-connector.stale_candidates.reported")
async def get_stale_candidate_report(ctx, params: StaleCandidateReportParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try:
        payload = await lc.get(conn["api_key"], "/opportunities", params=_body(limit=100, posting_id=params.posting_id, archived=False))
    except lc.LeverAPIError as exc:
        return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    records, has_next, _ = lc.rows(payload)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    cutoff_ms = now_ms - params.days_without_activity * 86_400_000
    findings: list[RecruitingFinding] = []
    for item in records:
        updated = item.get("updatedAt") or item.get("lastInteractionAt") or item.get("createdAt") or 0
        try: is_stale = int(updated) < cutoff_ms
        except (TypeError, ValueError): is_stale = False
        if is_stale:
            record = _record(item)
            findings.append(RecruitingFinding(
                id=record.id,
                title=record.title,
                severity="medium",
                detail=f"No recorded update for at least {params.days_without_activity} day(s).",
            ))
    result = RecruitingHealthReport(
        title="Stale candidate report",
        total_opportunities=len(records),
        stale_count=len(findings),
        findings=findings,
    )
    suffix = " Lever returned a paginated first page; use list_opportunities to continue." if has_next else ""
    return ActionResult.success(result, f"Found {len(findings)} stale active candidate(s).{suffix}")


@chat.function("audit_recruiting_pipeline", "Value-add health snapshot for a Lever pipeline: volume by stage, stale candidates and an explicit pagination warning.", action_type="read", chain_callable=True, data_model=RecruitingHealthReport, event="lever-connector.pipeline.audited")
async def audit_recruiting_pipeline(ctx, params: PipelineHealthParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    try:
        payload = await lc.get(conn["api_key"], "/opportunities", params=_body(limit=100, posting_id=params.posting_id, archived=False))
    except lc.LeverAPIError as exc:
        return ActionResult.error(str(exc), code="LEVER_API_ERROR")
    records, has_next, _ = lc.rows(payload)
    by_stage: dict[str, int] = {}
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    cutoff_ms = now_ms - 7 * 86_400_000
    findings: list[RecruitingFinding] = []
    for item in records:
        stage = str(item.get("stage") or "Unassigned stage")
        by_stage[stage] = by_stage.get(stage, 0) + 1
        updated = item.get("updatedAt") or item.get("lastInteractionAt") or item.get("createdAt") or 0
        try: stale = int(updated) < cutoff_ms
        except (TypeError, ValueError): stale = False
        if stale:
            record = _record(item)
            findings.append(RecruitingFinding(id=record.id, title=record.title, severity="medium", detail="No recorded update in at least seven days."))
    if has_next:
        findings.append(RecruitingFinding(id="pagination", title="More opportunities available", severity="info", detail="This health snapshot covers Lever's first 100 matching active opportunities; continue the paginated list for a complete account-wide review."))
    result = RecruitingHealthReport(
        title="Recruiting pipeline health",
        total_opportunities=len(records),
        stale_count=sum(1 for finding in findings if finding.id != "pagination"),
        by_stage=by_stage,
        findings=findings,
    )
    return ActionResult.success(result, f"Pipeline health built from {len(records)} active opportunity record(s).")


@chat.function("bulk_move_opportunities_to_stage", "Move explicit opportunities to one Lever pipeline stage. Continues across individual provider failures and reports every outcome.", action_type="write", chain_callable=True, data_model=LeverRecordList, event="lever-connector.opportunities.bulk_stage_updated", effects=["lever.opportunity.stage_changed"])
async def bulk_move_opportunities_to_stage(ctx, params: BulkOpportunityStageParams) -> ActionResult:
    """Execute the documented Lever operation safely."""
    conn, error = await _require(ctx, params.connection_id)
    if error: return error
    results: list[LeverRecord] = []
    failures = 0
    for opportunity_id in params.opportunity_ids:
        try:
            payload = await lc.put(conn["api_key"], f"/opportunities/{opportunity_id}/stage", body={"stage": params.stage_id})
            results.append(_record(payload if isinstance(payload, dict) else {"id": opportunity_id, "status": "updated"}))
        except lc.LeverAPIError as exc:
            failures += 1
            results.append(LeverRecord(id=opportunity_id, title="Opportunity", detail=f"Failed: {exc}"))
    return ActionResult.success(LeverRecordList(records=results), f"Moved {len(results) - failures} opportunity(s); {failures} failed.")

