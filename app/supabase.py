"""
Supabase interaction layer for EthixAI.

This module encapsulates all communication with the Supabase REST API. It
provides helpers for listing companies, updating a company’s ethics score,
and retrieving detailed information about a company. The service role key
is used for all requests because some operations (like updates) require
privileged access. Ensure that this key is kept secret and never exposed
to untrusted clients.
"""

from __future__ import annotations

import os
import urllib.parse
from typing import Any, Dict, List, Optional

import httpx


def _build_headers() -> Dict[str, str]:
    """Construct headers for authenticated Supabase requests."""
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_key:
        raise RuntimeError("SUPABASE_KEY environment variable not set")
    return {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }


async def list_companies(
    q: Optional[str] = None,
    order: str = "-ethics_score",
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Fetch a list of companies from Supabase.

    Args:
        q: Optional search query. Filters company names (case-insensitive).
        order: Field to sort by, prefix with '-' for descending.
        limit: Maximum number of records to return.
        offset: Number of records to skip before beginning to return records.

    Returns:
        A list of dictionaries representing companies.
    """
    base_url = os.getenv("SUPABASE_URL")
    if not base_url:
        raise RuntimeError("SUPABASE_URL environment variable not set")
    table_endpoint = f"{base_url}/rest/v1/companies"
    params: Dict[str, str] = {
        "select": "id,name,ticker,ethics_score,source_reason,last_updated",
    }
    if q:
        pattern = f"%{q}%"
        encoded = urllib.parse.quote(pattern)
        params["or"] = f"name.ilike.{encoded},ticker.ilike.{encoded}"
    if order.startswith("-"):
        order_column = order[1:]
        order_dir = "desc"
    else:
        order_column = order
        order_dir = "asc"
    params["order"] = f"{order_column}.{order_dir}"
    range_header = {"Range": f"{offset}-{offset + limit - 1}"}
    headers = _build_headers() | range_header
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(table_endpoint, params=params, headers=headers)
        response.raise_for_status()
        return response.json()


async def fetch_company(company_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single company record by its ID."""
    base_url = os.getenv("SUPABASE_URL")
    if not base_url:
        raise RuntimeError("SUPABASE_URL environment variable not set")
    endpoint = f"{base_url}/rest/v1/companies"
    params = {
        "select": "id,name,ticker,ethics_score,source_reason,last_updated",
        "id": f"eq.{company_id}",
    }
    headers = _build_headers()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(endpoint, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data[0] if data else None


async def update_company(company_id: str, score: int, reason: str) -> Dict[str, Any]:
    """Update a company's ethics score and reason in Supabase."""
    base_url = os.getenv("SUPABASE_URL")
    if not base_url:
        raise RuntimeError("SUPABASE_URL environment variable not set")
    endpoint = f"{base_url}/rest/v1/companies"
    params = {"id": f"eq.{company_id}"}
    payload = {"ethics_score": score, "source_reason": reason}
    headers = _build_headers()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(endpoint, params=params, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()[0]


async def update_company_fields(company_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """Update arbitrary fields on a company record."""
    base_url = os.getenv("SUPABASE_URL")
    if not base_url:
        raise RuntimeError("SUPABASE_URL environment variable not set")
    endpoint = f"{base_url}/rest/v1/companies"
    params = {"id": f"eq.{company_id}"}
    headers = _build_headers()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.patch(endpoint, params=params, json=fields, headers=headers)
        resp.raise_for_status()
        return resp.json()[0]
