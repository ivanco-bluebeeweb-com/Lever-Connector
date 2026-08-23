"""Single App settings screen for Lever connection management."""
from __future__ import annotations

from imperal_sdk import ui
from app import ext
import handlers as h


@ext.panel("lever_settings", slot="center")
async def lever_settings_panel(ctx) -> ui.UINode:
    connections = await h._load(ctx)
    if not connections:
        return ui.Stack(direction="v", gap=1, align="start", children=[
            ui.Text("Connections", variant="heading"),
            ui.Text("No Lever accounts connected yet.", variant="caption"),
        ])
    rows: list[ui.UINode] = [ui.Text("Connections", variant="heading")]
    for index, item in enumerate(connections):
        if index:
            rows.append(ui.Divider())
        rows.append(ui.Stack(direction="v", gap=1, align="start", children=[
            ui.Text(item.get("label") or "Lever", variant="body"),
            ui.Text("The saved API key will be removed from Imperal only.", variant="caption"),
            ui.Button("Disconnect", variant="danger", size="sm",
                      on_click=ui.Call("disconnect_lever", {"connection_id": item.get("id")})),
        ]))
    return ui.Stack(direction="v", gap=2, align="start", children=rows)
