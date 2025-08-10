"""
Main FastAPI application for the EthixAI backend.

This module wires together the API routes, middleware, and dependency
injection. It exposes endpoints for health checks, listing companies,
rescoring individual companies, running a full rescoring cron job, and
updating company details. It also configures CORS and rate limiting.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import auth, models, scoring, supabase


def create_app() -> FastAPI:
    """Application factory to create and configure the FastAPI app."""
    app = FastAPI(title="EthixAI Backend", version="1.0.0")

    # Configure CORS
    allowed_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
    origins = [origin.strip() for origin in allowed_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )

    # Rate limiting: 10 requests per second globally
    app.add_middleware(auth.RateLimiterMiddleware, max_requests=10, window_seconds=1.0)

    @app.get("/health", response_model=dict)
    async def health() -> Dict[str, str]:
        """Health check endpoint returning a simple status payload."""
        return {"status": "ok"}

    @app.get("/companies", response_model=List[models.Company])
    async def get_companies(
        q: Optional[str] = Query(None, description="Search query for company name or ticker"),
        order: str = Query("-ethics_score", description="Sort order, prefix column with '-' for descending"),
        limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return"),
        offset: int = Query(0, ge=0, description="Number of records to skip"),
    ) -> List[models.Company]:
        """List companies with optional search and sorting."""
        companies = await supabase.list_companies(q=q, order=order, limit=limit, offset=offset)
        return [models.Company(**c) for c in companies]

    @app.post("/score/{company_id}", response_model=dict)
    async def score_one(
        company_id: str,
        _=Depends(auth.verify_api_key),
    ) -> Dict[str, Any]:
        """Rescore an individual company and update its record."""
        score_val, reason = await scoring.score_company(company_id)
        updated = await supabase.update_company(company_id, score_val, reason)
        return {"id": company_id, "score": score_val, "reason": reason, "updated": updated}

    @app.post("/score/cron", response_model=dict)
    async def score_all(_=Depends(auth.verify_api_key)) -> Dict[str, Any]:
        """Rescore all companies in the database.

        Returns a summary containing the number of companies rescored.
        """
        batch_size = 200
        offset_val = 0
        total_updated = 0
        while True:
            companies = await supabase.list_companies(limit=batch_size, offset=offset_val)
            if not companies:
                break
            for company in companies:
                company_id = company["id"]
                try:
                    score_val, reason = await scoring.score_company(company_id)
                    await supabase.update_company(company_id, score_val, reason)
                    total_updated += 1
                except Exception as exc:
                    # Log the error; for simplicity, we'll continue processing
                    print(f"Error rescoring {company_id}: {exc}")
            offset_val += batch_size
        return {"rescored": total_updated}

    @app.patch("/companies/{company_id}", response_model=models.Company)
    async def update_company_fields(
        company_id: str,
        payload: models.CompanyUpdate,
        _=Depends(auth.verify_api_key),
    ) -> models.Company:
        """Update arbitrary fields on a company record."""
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided for update")
        updated = await supabase.update_company_fields(company_id, update_data)
        return models.Company(**updated)

    return app


app = create_app()
