"""
Pydantic schemas for the API requests and responses.
Defined in a separate module to prevent circular imports between routes and pipeline modules.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat query from the user."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The user's question about HDFC mutual fund schemes.",
        examples=["What is the expense ratio of HDFC Mid Cap Fund?"],
    )


class CitationInfo(BaseModel):
    """Citation metadata attached to every assistant response."""
    source_url: str | None = Field(
        default=None,
        description="Verified URL from chunk metadata (never LLM-generated).",
    )
    scheme_name: str | None = Field(
        default=None,
        description="Name of the mutual fund scheme cited.",
    )
    section: str | None = Field(
        default=None,
        description="Section of the source document.",
    )


class ChatResponse(BaseModel):
    """Structured response from the FAQ assistant."""
    answer: str = Field(
        ...,
        description="The assistant's facts-only answer (≤ 3 sentences).",
    )
    citation: CitationInfo = Field(
        default_factory=CitationInfo,
        description="Source citation for the answer.",
    )
    footer: str = Field(
        ...,
        description="Last-updated footer string.",
    )
    query_type: str = Field(
        ...,
        description="Classification of the query: factual, advisory, out_of_scope, pii_blocked.",
    )
