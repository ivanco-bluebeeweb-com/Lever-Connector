"""Typed handler parameters and response entities for Lever Connector."""
from __future__ import annotations

from typing import Any

from imperal_sdk import sdl
from pydantic import BaseModel, Field


class NoParams(BaseModel):
    pass


class ConnectionParams(BaseModel):
    api_key: str = Field("", description="Lever API key with the required access scopes.")
    label: str = Field("", description="Optional friendly account label, e.g. 'Acme Recruiting'.")


class ConnectionIdParams(BaseModel):
    connection_id: str = Field("", description="Connected Lever account id from list_connections.")


class ResourceListParams(ConnectionIdParams):
    limit: int = Field(50, ge=1, le=100, description="Maximum records to return (1-100).")
    cursor: str = Field("", description="Cursor from Lever's previous list response.")
    include_confidential_fields: bool = Field(False, description="Request confidential fields when the key has permission.")


class ResourceGetParams(ConnectionIdParams):
    resource_id: str = Field(..., description="Lever resource id.")
    include_confidential_fields: bool = Field(False, description="Request confidential fields when permitted.")


class OpportunityListParams(ResourceListParams):
    posting_id: str = Field("", description="Optional posting id filter.")
    stage_id: str = Field("", description="Optional pipeline stage id filter.")
    owner_id: str = Field("", description="Optional opportunity owner/user id filter.")
    archived: bool | None = Field(None, description="Filter by archived state; omit for both active and archived.")


class OpportunityCreateParams(ConnectionIdParams):
    contact_id: str = Field(..., description="Existing Lever contact/candidate id.")
    posting_id: str = Field("", description="Optional posting/job id to associate.")
    stage_id: str = Field("", description="Initial pipeline stage id.")
    owner_id: str = Field("", description="Recruiter/user id that owns this opportunity.")
    source: str = Field("", description="Candidate source name or Lever source id.")
    tags: list[str] = Field(default_factory=list, description="Initial opportunity tags.")


class OpportunityStageParams(ConnectionIdParams):
    opportunity_id: str = Field(..., description="Opportunity to move in the recruiting pipeline.")
    stage_id: str = Field(..., description="Destination Lever stage id.")


class OpportunityArchiveParams(ConnectionIdParams):
    opportunity_id: str = Field(..., description="Opportunity to archive or restore.")
    archived: bool = Field(True, description="True archives; false restores the opportunity.")
    archive_reason_id: str = Field("", description="Optional Lever archive reason id when archiving.")


class OpportunityUpdateParams(ConnectionIdParams):
    opportunity_id: str = Field(..., description="Opportunity to update.")
    owner_id: str = Field("", description="New recruiter/owner id.")
    tags: list[str] | None = Field(None, description="Full replacement tag list; omit to retain tags.")
    sources: list[str] | None = Field(None, description="Full replacement source list; omit to retain sources.")
    links: list[str] | None = Field(None, description="Full replacement profile/link list; omit to retain links.")


class ContactCreateParams(ConnectionIdParams):
    name: str = Field(..., description="Candidate's full name.")
    emails: list[str] = Field(default_factory=list, description="Candidate email addresses.")
    phones: list[str] = Field(default_factory=list, description="Candidate phone numbers.")
    headline: str = Field("", description="Candidate headline or current role.")
    location: str = Field("", description="Candidate location.")
    links: list[str] = Field(default_factory=list, description="Portfolio, LinkedIn, GitHub or other profile links.")


class ContactUpdateParams(ContactCreateParams):
    contact_id: str = Field(..., description="Existing Lever contact id.")


class PostingCreateParams(ConnectionIdParams):
    text: str = Field(..., description="Job title shown to candidates.")
    team: str = Field("", description="Hiring team name or id.")
    location: str = Field("", description="Job location.")
    description: str = Field("", description="Candidate-facing job description HTML/text.")
    state: str = Field("published", description="Lever posting state, normally 'published' or 'internal'.")


class PostingUpdateParams(ConnectionIdParams):
    posting_id: str = Field(..., description="Posting/job id to update.")
    text: str = Field("", description="New job title.")
    team: str = Field("", description="New hiring team.")
    location: str = Field("", description="New job location.")
    description: str = Field("", description="New candidate-facing job description.")
    state: str = Field("", description="New posting state.")


class InterviewCreateParams(ConnectionIdParams):
    opportunity_id: str = Field(..., description="Opportunity/candidate being interviewed.")
    interviewer_ids: list[str] = Field(..., min_length=1, description="One or more Lever user ids for interviewers.")
    date: int = Field(..., description="Interview start as Unix milliseconds.")
    duration: int = Field(3600000, ge=60000, description="Duration in milliseconds.")
    timezone: str = Field("UTC", description="IANA timezone, e.g. Europe/Chisinau.")
    subject: str = Field("Interview", description="Calendar/interview subject.")
    location: str = Field("", description="Meeting room or video-call URL.")


class InterviewUpdateParams(ConnectionIdParams):
    interview_id: str = Field(..., description="Interview id to update.")
    date: int | None = Field(None, description="New start time as Unix milliseconds.")
    duration: int | None = Field(None, ge=60000, description="New duration in milliseconds.")
    timezone: str = Field("", description="New IANA timezone.")
    subject: str = Field("", description="New subject.")
    location: str = Field("", description="New location or video URL.")
    interviewer_ids: list[str] | None = Field(None, description="Replacement interviewer user ids.")


class FeedbackCreateParams(ConnectionIdParams):
    opportunity_id: str = Field(..., description="Opportunity to receive feedback.")
    interview_id: str = Field("", description="Optional interview id the feedback belongs to.")
    text: str = Field(..., description="Structured or free-text interviewer feedback.")
    score: int | None = Field(None, ge=1, le=4, description="Optional Lever score (1-4) when configured.")


class NoteCreateParams(ConnectionIdParams):
    opportunity_id: str = Field(..., description="Opportunity to receive the internal note.")
    text: str = Field(..., description="Internal recruiting note text.")


class OfferCreateParams(ConnectionIdParams):
    opportunity_id: str = Field(..., description="Opportunity receiving an offer.")
    posting_id: str = Field("", description="Associated posting id.")
    owner_id: str = Field("", description="Offer owner/user id.")
    fields: dict[str, Any] = Field(default_factory=dict, description="Offer form fields matching the Lever offer configuration.")


class RequisitionCreateParams(ConnectionIdParams):
    text: str = Field(..., description="Requisition title/name.")
    fields: dict[str, Any] = Field(default_factory=dict, description="Configured requisition field values.")


class RequisitionUpdateParams(RequisitionCreateParams):
    requisition_id: str = Field(..., description="Requisition id to update.")


class WebhookCreateParams(ConnectionIdParams):
    url: str = Field(..., description="HTTPS endpoint where Lever should deliver events.")
    event: str = Field(..., description="Lever webhook event name, e.g. candidateCreated.")
    configuration: dict[str, Any] = Field(default_factory=dict, description="Optional provider-supported webhook configuration.")


class WebhookUpdateParams(ConnectionIdParams):
    webhook_id: str = Field(..., description="Webhook id to update.")
    url: str = Field("", description="Replacement HTTPS delivery endpoint.")
    event: str = Field("", description="Replacement event name.")
    configuration: dict[str, Any] | None = Field(None, description="Replacement provider configuration.")


class DeleteParams(ConnectionIdParams):
    resource_id: str = Field(..., description="Provider resource id to permanently delete.")


class StaleCandidateReportParams(ResourceListParams):
    days_without_activity: int = Field(7, ge=1, le=365, description="Flag active opportunities untouched for this many days.")
    posting_id: str = Field("", description="Optional posting/job id to limit the report.")


class PipelineHealthParams(ResourceListParams):
    posting_id: str = Field("", description="Optional posting/job id to limit the health report.")


class OpportunityFileListParams(ResourceListParams):
    opportunity_id: str = Field(..., description="Opportunity whose attached files should be listed.")


class ApplyToPostingParams(ConnectionIdParams):
    posting_id: str = Field(..., description="Public or internal Lever posting id to apply to.")
    name: str = Field(..., description="Applicant full name.")
    email: str = Field(..., description="Applicant email address.")
    phone: str = Field("", description="Applicant phone number.")
    comments: str = Field("", description="Optional applicant cover note.")
    fields: dict[str, Any] = Field(default_factory=dict, description="Answers keyed by Lever posting application-field ids.")


class FileUploadParams(ConnectionIdParams):
    opportunity_id: str = Field(..., description="Opportunity that will receive the file.")
    filename: str = Field(..., description="Original filename including extension.")
    content_base64: str = Field(..., description="Base64-encoded file bytes. Do not include a data URL prefix.")
    mime_type: str = Field("application/octet-stream", description="File MIME type, e.g. application/pdf.")


class BulkOpportunityStageParams(ConnectionIdParams):
    opportunity_ids: list[str] = Field(..., min_length=1, max_length=100, description="Explicit opportunity ids to move.")
    stage_id: str = Field(..., description="Destination pipeline stage id.")


class GenericActionParams(ConnectionIdParams):
    """Explicit provider path/body for documented advanced API resources."""
    resource_id: str = Field("", description="Optional resource id for a resource-specific operation.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Fields accepted by the documented Lever endpoint.")


class LeverConnection(sdl.Entity):
    id: str = ""
    title: str = ""
    connected: bool = False
    detail: str = ""


class LeverRecord(sdl.Entity):
    id: str = ""
    title: str = ""
    detail: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)


class LeverRecordList(sdl.Entity):
    records: list[LeverRecord] = Field(default_factory=list)
    has_next: bool = False
    next_cursor: str = ""


class RecruitingFinding(sdl.Entity):
    severity: str = "info"
    title: str = ""
    detail: str = ""
    opportunity_id: str = ""


class RecruitingHealthReport(sdl.Entity):
    active_opportunities: int = 0
    archived_opportunities: int = 0
    stage_counts: dict[str, int] = Field(default_factory=dict)
    stale_candidates: int = 0
    findings: list[RecruitingFinding] = Field(default_factory=list)
