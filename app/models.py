"""
Pydantic models for the EthixAI backend.

These models define the shape of data exchanged via the API. They are used
for validation, serialization, and documentation of API responses and
requests.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CompanyBase(BaseModel):
    """Base fields shared by all company models."""

    name: str = Field(..., description="Name of the company")
    ticker: Optional[str] = Field(None, description="Stock ticker symbol")


class CompanyCreate(CompanyBase):
    """Model for creating a new company."""

    ethics_score: int = Field(..., ge=0, le=100, description="Ethics score between 0 and 100")
    source_reason: str = Field(..., description="Reasoning behind the ethics score")


class CompanyUpdate(BaseModel):
    """Model for updating existing company fields."""

    name: Optional[str] = Field(None, description="Name of the company")
    ticker: Optional[str] = Field(None, description="Stock ticker symbol")
    ethics_score: Optional[int] = Field(None, ge=0, le=100, description="Ethics score between 0 and 100")
    source_reason: Optional[str] = Field(None, description="Reasoning behind the ethics score")


class Company(CompanyBase):
    """Full representation of a company returned to clients."""

    id: str = Field(..., description="UUID of the company")
    ethics_score: Optional[int] = Field(None, ge=0, le=100, description="Ethics score between 0 and 100")
    source_reason: Optional[str] = Field(None, description="Reasoning behind the ethics score")
    last_updated: Optional[datetime] = Field(None, description="Timestamp of last update")

    class Config:
        from_attributes = True
