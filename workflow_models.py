"""KING ZARRY AI workflow engine models.

The workflow engine is intentionally additive: existing agents and action gateways
remain the execution authority for their supported actions.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class WorkflowStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    RESEARCHING = "researching"
    PLAN_READY = "plan_ready"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RiskLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class WorkflowStep:
    id: str
    workflow_id: str
    position: int
    title: str
    action: str
    status: StepStatus = StepStatus.PENDING
    risk: RiskLevel = RiskLevel.GREEN
    requires_approval: bool = False
    input: Dict[str, Any] = field(default_factory=dict)
    output: Dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class Workflow:
    id: str
    user_id: str
    goal: str
    status: WorkflowStatus = WorkflowStatus.CREATED
    risk: RiskLevel = RiskLevel.GREEN
    requires_approval: bool = False
    plan: List[WorkflowStep] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    potential_revenue: float = 0.0
    estimated_cost: float = 0.0
