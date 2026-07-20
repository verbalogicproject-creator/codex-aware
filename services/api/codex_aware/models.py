from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class SafetyClass(StrEnum):
    SAFE = "safe"
    PROTECTED = "protected"
    BROWSER_ONLY = "browser_only"
    FORBIDDEN = "forbidden"
    UNCLASSIFIED = "unclassified"


class ReceiptStatus(StrEnum):
    EXECUTED = "executed"
    AWAITING_APPROVAL = "awaiting_approval"
    AWAITING_CONSUMER = "awaiting_consumer"
    DENIED = "denied"
    DEGRADED = "degraded"


class GraphNode(BaseModel):
    id: str
    kind: str
    label: str
    project: str | None = None
    uri: str | None = None
    safety_class: SafetyClass | None = None
    summary: str | None = None
    x: float = 0
    y: float = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    kind: str
    label: str | None = None


class SelectionRequest(BaseModel):
    node_ids: list[str] = Field(min_length=1, max_length=12)


class ActionRequest(BaseModel):
    command: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class EffectAck(BaseModel):
    receipt_id: str
    directive_id: str
    observed: dict[str, Any] = Field(default_factory=dict)


class ProposalDecision(BaseModel):
    proposal_hash: str
    decision: Literal["approved", "rejected"]


class RefreshRequest(BaseModel):
    snapshot_hash: str
    policies: dict[str, dict[str, str]]
    test_result: dict[str, Any] = Field(default_factory=dict)


class PairAttach(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    actor_name: str = Field(min_length=1, max_length=80)


class MCPRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] = Field(default_factory=dict)

