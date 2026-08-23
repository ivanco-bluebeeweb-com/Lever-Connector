"""Lever Connector sidebar and connection-help modal.

The sidebar deliberately contains no Card wrappers. Every input has a visible
label and a contextual placeholder; the setup steps live only in the modal.
"""
from __future__ import annotations

from imperal_sdk import ui
from app import ext
import handlers as h


def _settings_button() -> ui.UINode:
    return ui.Button("App settings", variant="secondary", size="sm", full_width=True,
                     icon="settings", on_click=ui.Call("__panel__lever_settings"))


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
    return ui.Empty(message="Nothing to show here -- this app is managed entirely from the sidebar.", icon="👈")
