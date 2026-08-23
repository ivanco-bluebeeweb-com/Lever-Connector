"""Lever Connector extension declaration and lifecycle hooks.

The connector uses a user-owned Lever API key (BYOK) rather than a shared
Imperal credential. Lever is an ATS containing sensitive candidate and hiring
information, so each customer retains control of their own access and can
revoke it in Lever at any time. A key is sent through HTTP Basic Auth only to
Lever's official API endpoint and is never returned in action results.

`write_mode="both"` enables the guided in-app connection form while retaining
the generic Imperal secret-management fallback. Provider-side permissions stay
controlled by the scopes granted to the key in Lever.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "lever-connector",
    version="0.1.0",
    display_name="Lever",
    description="Operate your Lever recruiting pipeline: candidates, opportunities, jobs, interviews, feedback, offers and recruiting health.",
    icon="icon.svg",
    actions_explicit=True,
    capabilities=["lever:read", "lever:write"],
)

chat = ChatExtension(
    ext,
    tool_name="lever",
    description="Lever ATS and recruiting operations: candidates, opportunities, job postings, interviews, feedback, offers, requisitions, webhooks and recruiting health.",
)

ext.secret(
    "lever_connections",
    "Vault-encrypted JSON array of connected Lever accounts and their user-owned API keys. Managed only by connect_lever and disconnect_lever.",
    required=False,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=180,
)(lambda: None)


@ext.health_check
async def health_check(ctx):
    """A connection-aware health endpoint without exposing any secret."""
    raw = await ctx.secrets.get("lever_connections")
    import json
    try:
        connections = json.loads(raw) if raw else []
    except (TypeError, ValueError):
        connections = []
    count = len(connections) if isinstance(connections, list) else 0
    return {
        "healthy": count > 0,
        "detail": f"{count} Lever account(s) connected" if count else "No Lever account connected",
    }
