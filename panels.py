"""Lever Connector sidebar and connection-help modal.

The sidebar deliberately contains no Card wrappers. Every input has a visible
label and a contextual placeholder; the setup steps live only in the modal.
"""
from __future__ import annotations

from imperal_sdk import ui
from app import ext
import handlers as h


def _settings_button() -> ui.UINode:
    return ui.Button("App settings", variant="secondary", size="sm", icon="settings", on_click=ui.Call("__panel__lever_settings"))


def _connection_rows(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Text("No Lever accounts connected yet.", variant="caption")
    children: list[ui.UINode] = []
    for index, item in enumerate(connections):
        if index:
            children.append(ui.Divider())
        children.append(ui.Stack(direction="v", gap=1, children=[
            ui.Text(item.get("label") or "Lever", variant="body"),
            ui.Text("API key connected securely", variant="caption"),
        ]))
    return ui.Stack(direction="v", gap=2, align="stretch", children=children)


def _connect_form() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("How do I set this up?", variant="ghost", size="sm", icon="HelpCircle",
                  on_click=ui.Call("__panel__lever_connect_help")),
        ui.Button("Sign in with Lever (OAuth 2.0)", variant="primary", size="sm", icon="login"),
        ui.Divider(),
        ui.Text("Or connect via API Key", variant="caption"),
        ui.Form(action="connect_lever", submit_label="Verify and connect", children=[
            ui.Stack(direction="v", gap=1, align="stretch", children=[
                ui.Text("Lever API key", variant="caption"),
                ui.Password(param_name="api_key", placeholder="Paste the key created in Lever Settings > Integrations and API"),
            ]),
            ui.Stack(direction="v", gap=1, align="stretch", children=[
                ui.Text("Connection label (optional)", variant="caption"),
                ui.Input(param_name="label", placeholder="e.g. Acme Talent Acquisition"),
            ]),
        ]),
    ])


@ext.panel("lever_connect", slot="left", title="Lever", icon="🎯", default_width=320, min_width=260, max_width=420)
async def lever_connect_panel(ctx, **kwargs) -> ui.UINode:
    connections = await h._load(ctx)
    children: list[ui.UINode] = [
        ui.Header(text="Lever", level=2, subtitle="Recruiting operations from candidate to offer"),
    ]
    if connections:
        children.extend([ui.Text("Connected accounts", variant="subtitle"), _connection_rows(connections), ui.Divider()])
        children.extend([
            ui.Button("View pipeline health", variant="primary", size="sm", icon="Target", on_click=ui.Call("__panel__lever_center")),
            ui.Divider(),
        ])
    children.extend([_connect_form(), ui.Divider(), _settings_button()])
    return ui.Stack(direction="v", gap=4, align="stretch", children=children)


@ext.panel("lever_connect_help", slot="center", title="How to connect Lever", center_overlay=True)
async def lever_connect_help(ctx, **kwargs) -> ui.UINode:
    return ui.Dialog(title="How to connect Lever", cancel_label="Close", confirm_label="", content=ui.Stack(direction="v", gap=3, children=[
        ui.Text("1. In Lever, open Settings and locate Integrations and API."),
        ui.Text("2. Create an API key with only the read and write scopes your team needs."),
        ui.Text("3. Paste the key here. Lever verifies it before it is saved."),
        ui.Alert(title="Candidate-data safety", message="Use a dedicated least-privilege key. The key is stored encrypted and is never shown again.", type="warning"),
        ui.Link(label="Open Lever Developer documentation", href="https://hire.lever.co/developer/documentation"),
    ]))


@ext.panel("lever_center", slot="center", title="Lever", icon="🎯", center_overlay=True)
async def lever_center_panel(ctx, **kwargs) -> ui.UINode:
    """Post-connect main screen: a recruiting pipeline health snapshot
    plus flagged stale candidates -- gives a real operational picture
    instead of the previous empty placeholder."""
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Empty(message="Connect a Lever account from the sidebar to see it here.", icon="🎯")

    from schemas import PipelineHealthParams
    conn_id = connections[0].get("id", "")
    body: list[ui.UINode] = [ui.Text("Pipeline health", variant="subtitle")]
    result = await h.audit_recruiting_pipeline(ctx, PipelineHealthParams(connection_id=conn_id))
    if result.success and result.data:
        r = result.data
        body.append(ui.Stats(children=[
            ui.Stat(label="Active", value=str(getattr(r, "active_opportunities", 0))),
            ui.Stat(label="Archived", value=str(getattr(r, "archived_opportunities", 0))),
            ui.Stat(label="Stale", value=str(getattr(r, "stale_candidates", 0))),
        ]))
        stage_counts = getattr(r, "stage_counts", {}) or {}
        if stage_counts:
            body.append(ui.KeyValue(columns=2, items=[
                {"key": k, "value": str(v)} for k, v in list(stage_counts.items())[:10]
            ]))
        findings = getattr(r, "findings", []) or []
        if findings:
            body.append(ui.Divider())
            body.append(ui.Text("Flagged candidates", variant="subtitle"))
            for f in findings[:15]:
                color = {"high": "red", "medium": "yellow"}.get(f.severity, "gray")
                body.append(ui.Stack(direction="h", gap=2, align="center", children=[
                    ui.Badge(label=f.severity.upper(), color=color),
                    ui.Text(f.title, variant="body"),
                    ui.Text(f.detail, variant="caption"),
                ]))
    else:
        body.append(ui.Text("Could not load the pipeline health report.", variant="caption"))

    return ui.Stack(direction="v", gap=3, align="stretch", children=body)