"""
GPT‑based scoring logic for EthixAI.

This module provides a function that takes a company ID, retrieves the
relevant data from Supabase, and queries OpenAI’s GPT model to produce a
fresh ethics score and accompanying rationale. The function returns the
parsed score and reason, which can then be stored back into the database.

Note: This implementation makes blocking HTTP calls. In a production
environment, you might consider using asynchronous OpenAI clients or run
this process in the background to avoid blocking the event loop.
"""

from __future__ import annotations

import json
import os
from typing import Tuple

import openai

from . import supabase


async def score_company(company_id: str) -> Tuple[int, str]:
    """Generate a new ethics score and explanation for a company.

    Args:
        company_id: UUID of the company to score.

    Returns:
        A tuple (score, reason) with the computed ethics score (0–100) and
        a plain‑language explanation.

    Raises:
        RuntimeError: If the OpenAI API key is not set or the company cannot
            be retrieved from Supabase.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set")
    openai.api_key = api_key

    # Fetch company details from Supabase
    company = await supabase.fetch_company(company_id)
    if company is None:
        raise RuntimeError(f"Company with ID {company_id} not found")

    name = company.get("name")
    ticker = company.get("ticker")
    last_score = company.get("ethics_score")

    system_prompt = (
        "You are EthixAI, an AI agent designed to assess the ethical practices of companies."
        " You score companies on a scale from 0 to 100, where higher scores indicate"
        " better ethical performance. Your evaluation should consider factors such as"
        " environmental sustainability, labor practices, corporate governance, data privacy,"
        " and social impact."
    )
    user_prompt = (
        f"Company name: {name}."
        + (f" Ticker: {ticker}." if ticker else "")
        + (f" Previous ethics score: {last_score}." if last_score is not None else "")
        + " Provide a JSON object with two keys: 'score' (an integer between 0 and 100)"
        " and 'reason' (a brief explanation of why you assigned this score)."
        " The explanation should be concise (no more than 100 words) and written in plain English."
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=200,
            temperature=0.2,
        )
    except Exception as exc:
        raise RuntimeError(f"OpenAI API call failed: {exc}")

    try:
        content = response.choices[0].message["content"]
        data = json.loads(content)
        score = int(data["score"])
        reason = str(data["reason"])
    except Exception as exc:
        raise RuntimeError(f"Failed to parse OpenAI response: {exc}. Response: {response}")
    return score, reason
