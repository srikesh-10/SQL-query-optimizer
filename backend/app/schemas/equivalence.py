"""
Pydantic Schemas for SQL Rewrite Correctness & Result Equivalence Validation.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class ColumnCompatibility(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    original_columns: List[str] = Field(default_factory=list, description="Column names in original query.")
    candidate_columns: List[str] = Field(default_factory=list, description="Column names in candidate query.")
    counts_match: bool = Field(..., description="Whether both queries return the same number of columns.")
    names_match: bool = Field(..., description="Whether column names in positional order match.")
    compatible: bool = Field(..., description="Whether schema shapes are compatible for comparison.")
    details: Optional[str] = Field(None, description="Explanatory notes regarding column comparison.")


class CompareResultsRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    original_sql: str = Field(..., description="The original read-only SELECT query.")
    candidate_sql: str = Field(..., description="The proposed rewritten SELECT query to validate.")
    confirmed: bool = Field(..., description="Explicit confirmation that user authorizes executing both queries.")
    row_limit: int = Field(default=1000, ge=1, le=5000, description="Maximum rows to fetch and compare per query.")


class CompareResultsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: Literal["equivalent", "different", "inconclusive", "rejected"] = Field(
        ...,
        description="Outcome of result comparison: 'equivalent', 'different', 'inconclusive', or 'rejected'."
    )
    matched: Optional[bool] = Field(
        None,
        description="True if results matched, False if different/rejected, None if inconclusive."
    )
    original_row_count: Optional[int] = Field(None, description="Number of rows returned by original query (up to limit).")
    candidate_row_count: Optional[int] = Field(None, description="Number of rows returned by candidate query (up to limit).")
    is_complete_comparison: bool = Field(
        ...,
        description="True if neither query exceeded row limit or timed out, guaranteeing full comparison."
    )
    row_limit_applied: int = Field(..., description="Maximum row limit configured for this comparison.")
    column_compatibility: Optional[ColumnCompatibility] = Field(None, description="Column names and compatibility telemetry.")
    order_deterministic: bool = Field(..., description="Whether row ordering was uniquely deterministic.")
    ordering_mode: str = Field(..., description="Comparison mode: 'ordered' or 'multiset'.")
    mismatch_reason: Optional[str] = Field(None, description="Detailed explanation of any divergence, limit, or rejection.")
    error_message: Optional[str] = Field(None, description="Sanitized database or validation error message.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata describing execution environment and snapshots.")
