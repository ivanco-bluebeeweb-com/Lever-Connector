"""Small, safe async client for Lever's official REST API v1."""
from __future__ import annotations

from typing import Any

import httpx

API_BASE = "https://api.lever.co/v1"


class LeverAPIError(RuntimeError):
    """Normalized provider failure safe to show in an action error."""


def _message(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict):
            return str(body.get("message") or body.get("error") or response.text)
    except ValueError:
        pass
    return response.text or f"Lever returned HTTP {response.status_code}."


async def request(
    api_key: str,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | list[Any] | None = None,
) -> Any:
    """Call Lever without ever retaining or returning the credential."""
    if not api_key:
        raise LeverAPIError("No Lever API key is saved for this connection.")
    url = f"{API_BASE}/{path.lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                params={k: v for k, v in (params or {}).items() if v not in (None, "")},
                json=body,
                auth=httpx.BasicAuth(api_key, ""),
                headers={"Accept": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise LeverAPIError(f"Could not reach Lever: {exc}") from exc

    if response.status_code == 429:
        raise LeverAPIError("Lever rate-limited this request. Please retry shortly.")
    if response.status_code >= 400:
        raise LeverAPIError(f"Lever API error ({response.status_code}): {_message(response)}")
    if response.status_code == 204 or not response.content:
        return {}
    try:
        return response.json()
    except ValueError as exc:
        raise LeverAPIError("Lever returned a non-JSON response.") from exc


async def get(api_key: str, path: str, **kwargs: Any) -> Any:
    return await request(api_key, "GET", path, **kwargs)


async def post(api_key: str, path: str, **kwargs: Any) -> Any:
    return await request(api_key, "POST", path, **kwargs)


async def put(api_key: str, path: str, **kwargs: Any) -> Any:
    return await request(api_key, "PUT", path, **kwargs)


async def delete(api_key: str, path: str, **kwargs: Any) -> Any:
    return await request(api_key, "DELETE", path, **kwargs)


def rows(payload: Any) -> tuple[list[dict[str, Any]], bool, str]:
    """Normalize Lever list envelopes while retaining pagination information."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)], False, ""
    if not isinstance(payload, dict):
        return [], False, ""
    data = payload.get("data", payload.get("items", []))
    return (
        [item for item in data if isinstance(item, dict)] if isinstance(data, list) else [],
        bool(payload.get("hasNext", False)),
        str(payload.get("next") or ""),
    )
