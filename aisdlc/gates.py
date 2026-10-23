"""Quality gates for the AISDLC pipeline.

A task may only leave a phase when that phase's gate passes. Gates are
deterministic checks over the task's own data, so the pipeline is fully
testable without any external service or LLM.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import Phase, Task


@dataclass
class GateResult:
    phase: Phase
    passed: bool
    reasons: list[str]

    def __bool__(self) -> bool:
        return self.passed


def check_gate(task: Task) -> GateResult:
    """Evaluate the quality gate for the task's current phase."""
    phase = task.phase
    reasons: list[str] = []

    if phase is Phase.REQUIREMENTS:
        if not task.acceptance_criteria:
            reasons.append("no acceptance criteria defined")
        if not task.description.strip():
            reasons.append("no description")

    elif phase is Phase.PLANNING:
        if not task.assignee:
            reasons.append("no assignee assigned")
        if task.estimate_hours <= 0:
            reasons.append("no time estimate")

    elif phase is Phase.DESIGN:
        if "design_doc" not in task.artifacts:
            reasons.append("missing design_doc artifact")

    elif phase is Phase.CODING:
        if "implementation" not in task.artifacts:
            reasons.append("missing implementation artifact")

    elif phase is Phase.TESTING:
        if task.test_pass_rate < 0.8:
            reasons.append(
                f"test pass rate {task.test_pass_rate:.0%} is below 80%"
            )

    elif phase is Phase.REVIEW:
        if task.approvals < 1:
            reasons.append("needs at least 1 approval")

    elif phase is Phase.DEPLOYMENT:
        if "release_notes" not in task.artifacts:
            reasons.append("missing release_notes artifact")

    elif phase is Phase.DONE:
        reasons = []  # terminal phase, nothing to gate

    return GateResult(phase=phase, passed=not reasons, reasons=reasons)
